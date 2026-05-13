"""
Gemini API advisor for Slay the Spire with RAG and persistent run storage.

Uses local database for accurate card/relic info, persistent run storage,
and injects full run context with every message.
"""

import os
import sys
import json
import re
from pathlib import Path
from typing import Optional
from difflib import SequenceMatcher

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Suppress deprecation warning
import warnings
warnings.filterwarnings("ignore", category=FutureWarning, module="google.generativeai")

import google.generativeai as genai
from dotenv import load_dotenv
from loguru import logger

from src.advisor.run_manager import RunManager, format_deck_counts


class KnowledgeBase:
    """Local knowledge base loaded from JSON files."""
    
    def __init__(self, data_dir: Path = None):
        self.data_dir = data_dir or PROJECT_ROOT / "data" / "raw"
        self.cards = {}
        self.relics = {}
        self.potions = {}
        self.keywords = {}
        self._load_data()
    
    def _load_data(self):
        """Load all data from JSON files."""
        # Load cards
        cards_file = self.data_dir / "cards.json"
        if cards_file.exists():
            with open(cards_file, encoding="utf-8") as f:
                cards_list = json.load(f)
                for card in cards_list:
                    name = card.get("name", "").lower()
                    if name and not name.endswith("+"):
                        self.cards[name] = card
            logger.info(f"Loaded {len(self.cards)} cards")
        
        # Load relics
        relics_file = self.data_dir / "relics.json"
        if relics_file.exists():
            with open(relics_file, encoding="utf-8") as f:
                relics_list = json.load(f)
                for relic in relics_list:
                    name = relic.get("name", "").lower()
                    if name:
                        self.relics[name] = relic
            logger.info(f"Loaded {len(self.relics)} relics")
        
        # Load potions
        potions_file = self.data_dir / "potions.json"
        if potions_file.exists():
            with open(potions_file, encoding="utf-8") as f:
                potions_list = json.load(f)
                for potion in potions_list:
                    name = potion.get("name", "").lower()
                    if name:
                        self.potions[name] = potion
            logger.info(f"Loaded {len(self.potions)} potions")
    
    def _fuzzy_match(self, query: str, candidates: dict, threshold: float = 0.6) -> list:
        """Find fuzzy matches for a query in candidates."""
        query = query.lower().strip()
        matches = []
        
        for name, data in candidates.items():
            if query == name:
                matches.append((1.0, name, data))
            elif query in name:
                matches.append((0.9, name, data))
            else:
                ratio = SequenceMatcher(None, query, name).ratio()
                if ratio >= threshold:
                    matches.append((ratio, name, data))
        
        matches.sort(key=lambda x: x[0], reverse=True)
        return matches[:3]
    
    def find_cards(self, query: str) -> list:
        return self._fuzzy_match(query, self.cards)
    
    def find_relics(self, query: str) -> list:
        return self._fuzzy_match(query, self.relics)
    
    def get_card_info(self, name: str) -> Optional[str]:
        matches = self.find_cards(name)
        if not matches:
            return None
        _, _, card = matches[0]
        return f"📜 {card['name']} ({card.get('color', 'Colorless')}, {card.get('rarity', 'Common')}, {card.get('type', 'Skill')})\n   Cost: {card.get('cost', '?')} | {card.get('description', 'No description')}"
    
    def get_relic_info(self, name: str) -> Optional[str]:
        matches = self.find_relics(name)
        if not matches:
            return None
        _, _, relic = matches[0]
        return f"🔮 {relic['name']} ({relic.get('tier', 'Common')})\n   {relic.get('description', 'No description')}"
    
    def extract_mentioned_items(self, text: str) -> dict:
        text_lower = text.lower()
        found = {"cards": [], "relics": [], "potions": []}
        
        for name in self.cards:
            if name in text_lower:
                found["cards"].append(name)
        for name in self.relics:
            if name in text_lower:
                found["relics"].append(name)
        for name in self.potions:
            if name in text_lower:
                found["potions"].append(name)
        
        return found


class GeminiAdvisor:
    """Slay the Spire advisor powered by Gemini API with persistent run storage."""
    
    # Character data
    CHARACTERS = {
        "ironclad": {
            "name": "Ironclad",
            "hp": 80,
            "starter_relic": "Burning Blood",
            "starter_relic_desc": "Heal 6 HP after combat",
            "color": "Red",
            "starter_deck": ["Strike", "Strike", "Strike", "Strike", "Strike", 
                           "Defend", "Defend", "Defend", "Defend", "Bash"]
        },
        "silent": {
            "name": "Silent",
            "hp": 70,
            "starter_relic": "Ring of the Snake",
            "starter_relic_desc": "Draw 2 extra cards turn 1",
            "color": "Green",
            "starter_deck": ["Strike", "Strike", "Strike", "Strike", "Strike",
                           "Defend", "Defend", "Defend", "Defend", "Defend",
                           "Survivor", "Neutralize"]
        },
        "defect": {
            "name": "Defect",
            "hp": 75,
            "starter_relic": "Cracked Core",
            "starter_relic_desc": "Channel 1 Lightning at start of combat",
            "color": "Blue",
            "starter_deck": ["Strike", "Strike", "Strike", "Strike",
                           "Defend", "Defend", "Defend", "Defend",
                           "Zap", "Dualcast"]
        },
        "watcher": {
            "name": "Watcher",
            "hp": 72,
            "starter_relic": "Pure Water",
            "starter_relic_desc": "Add Miracle to hand at start of combat",
            "color": "Purple",
            "starter_deck": ["Strike", "Strike", "Strike", "Strike",
                           "Defend", "Defend", "Defend", "Defend",
                           "Eruption", "Vigilance"]
        }
    }
    
    def __init__(self):
        load_dotenv()
        
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment.")
        
        # Load knowledge base
        self.kb = KnowledgeBase()
        
        # Initialize run manager (persistent storage)
        self.run_manager = RunManager()
        
        # Configure Gemini
        genai.configure(api_key=api_key)
        
        self.model = genai.GenerativeModel(
            model_name="gemini-2.5-flash-lite",
            generation_config={
                "temperature": 0.7,
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 500,
            },
            system_instruction=self._get_system_prompt()
        )
        
        # Start fresh chat session
        self.chat = self.model.start_chat(history=[])
        
        # Try to resume latest active run
        resumed_run = self.run_manager.resume_latest_run()
        if resumed_run:
            # Inform Gemini about the resumed run
            self._send_run_context_to_gemini(resumed_run, resumed=True)
        
        logger.info(f"Advisor initialized (KB: {len(self.kb.cards)} cards, {len(self.kb.relics)} relics)")
    
    def _get_system_prompt(self) -> str:
        return """You are an expert Slay the Spire advisor helping a player during their run.

CRITICAL RULES:
1. ONLY use information from [RUN STATE] - never make up or assume deck contents
2. If no [RUN STATE] is provided, there is NO active run
3. The deck shown in [RUN STATE] is the COMPLETE and ACCURATE deck
4. Do NOT invent cards, relics, or events that aren't explicitly stated

GAME KNOWLEDGE:
- 4 characters: Ironclad (80HP), Silent (70HP), Defect (75HP), Watcher (72HP)
- Ascension reduces max HP: -4 at A14, additional -10% at A10
- Act 1: Floors 1-17, Act 2: Floors 18-34, Act 3: Floors 35-51, Act 4: 52+
- Each act has a boss at the end

RESPONSE STYLE:
- Keep responses BRIEF (2-3 sentences) - they're spoken aloud
- Be conversational, not robotic
- Use card counts like "5 Strikes" not "Strike, Strike, Strike..."
- Give specific, actionable advice based on ACTUAL deck state

When I provide [CARD INFO] or [RELIC INFO], that data is accurate - trust it over your memory."""
    
    def _send_run_context_to_gemini(self, run: dict, resumed: bool = False):
        """Send run context to Gemini to establish state."""
        deck = self.run_manager.get_full_deck(run)
        deck_str = format_deck_counts(deck)
        
        action = "RESUMED" if resumed else "STARTED"
        
        context = f"""[RUN {action}]
Character: {run['character']} | Ascension: {run['ascension']}
Act: {run['act']} | Floor: {run['floor']}
HP: {run['hp']}/{run['max_hp']} | Gold: {run['gold']}
Deck ({len(deck)} cards): {deck_str}
Relics: {', '.join(run['relics'])}
Potions: {', '.join(run['potions']) if run['potions'] else 'None'}

Acknowledge briefly."""
        
        try:
            self.chat.send_message(context)
        except Exception as e:
            logger.error(f"Failed to send run context: {e}")
    
    def _build_run_context(self) -> str:
        """Build detailed run context string."""
        run = self.run_manager.get_active_run()
        if not run:
            return "[NO ACTIVE RUN - Start one by saying 'start a new run with [character]']"
        
        deck = self.run_manager.get_full_deck(run)
        deck_str = format_deck_counts(deck)
        
        context = f"""[RUN STATE - THIS IS THE ONLY SOURCE OF TRUTH]
Character: {run['character']} | Ascension: {run['ascension']}
Act: {run['act']} | Floor: {run['floor']}
HP: {run['hp']}/{run['max_hp']} | Gold: {run['gold']}
Deck ({len(deck)} cards): {deck_str}
Relics: {', '.join(run['relics'])}
Potions: {', '.join(run['potions']) if run['potions'] else 'None'}
Keys: {'Ruby ' if run['keys']['ruby'] else ''}{'Emerald ' if run['keys']['emerald'] else ''}{'Sapphire' if run['keys']['sapphire'] else 'None collected'}"""
        
        # Add recent events for context
        recent_events = self.run_manager.get_recent_events(run, count=3)
        if recent_events:
            events_str = " | ".join([f"F{e['floor']}: {e['details']}" for e in recent_events])
            context += f"\nRecent: {events_str}"
        
        return context
    
    def _build_rag_context(self, message: str) -> str:
        """Build RAG context by looking up mentioned cards/relics."""
        context_parts = []
        found = self.kb.extract_mentioned_items(message)
        
        for card_name in found["cards"][:3]:
            info = self.kb.get_card_info(card_name)
            if info:
                context_parts.append(f"[CARD INFO]\n{info}")
        
        for relic_name in found["relics"][:3]:
            info = self.kb.get_relic_info(relic_name)
            if info:
                context_parts.append(f"[RELIC INFO]\n{info}")
        
        return "\n\n".join(context_parts)
    
    def chat_message(self, message: str) -> str:
        """Send a message and get a response with full context."""
        try:
            context_parts = []
            
            # ALWAYS add run state first
            run_context = self._build_run_context()
            context_parts.append(run_context)
            
            # Add RAG context for mentioned cards/relics
            rag_context = self._build_rag_context(message)
            if rag_context:
                context_parts.append(rag_context)
            
            # Combine context with message
            full_message = "\n\n".join(context_parts) + "\n\nPlayer: " + message
            
            logger.debug(f"Sending to Gemini:\n{full_message[:800]}...")
            
            response = self.chat.send_message(full_message)
            return response.text.strip()
            
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return f"Sorry, I encountered an error: {str(e)}"
    
    def start_run(self, character: str, ascension: int = 0) -> str:
        """Start a new run."""
        character = character.lower()
        if character not in self.CHARACTERS:
            return f"Unknown character: {character}. Choose Ironclad, Silent, Defect, or Watcher."
        
        # End any active run first
        if self.run_manager.get_active_run():
            self.run_manager.end_run(victory=False, cause="Abandoned for new run")
        
        char_data = self.CHARACTERS[character]
        
        # Calculate max HP with ascension
        max_hp = char_data["hp"]
        if ascension >= 14:
            max_hp -= 4
        if ascension >= 10:
            max_hp = int(max_hp * 0.9)
        
        # Create persistent run
        run = self.run_manager.create_run(
            character=char_data["name"],
            ascension=ascension,
            starter_deck=char_data["starter_deck"].copy(),
            starter_relic=char_data["starter_relic"],
            max_hp=max_hp,
            color=char_data["color"]
        )
        
        # Reset chat and inform Gemini
        self.chat = self.model.start_chat(history=[])
        self._send_run_context_to_gemini(run, resumed=False)
        
        deck_str = format_deck_counts(char_data["starter_deck"])
        return f"New run started! {char_data['name']} Ascension {ascension}. HP: {max_hp}. Deck: {deck_str}. Good luck!"
    
    def add_card(self, card_name: str) -> str:
        """Add a card to the current run."""
        if not self.run_manager.get_active_run():
            return "No active run. Start one first!"
        
        # Find card in database
        matches = self.kb.find_cards(card_name)
        actual_name = matches[0][2]["name"] if matches else card_name.title()
        
        run = self.run_manager.add_card(actual_name)
        if run:
            deck = self.run_manager.get_full_deck(run)
            return f"Added {actual_name}. Deck now has {len(deck)} cards."
        return "Failed to add card."
    
    def remove_card(self, card_name: str) -> str:
        """Remove a card from the current run."""
        if not self.run_manager.get_active_run():
            return "No active run."
        
        matches = self.kb.find_cards(card_name)
        actual_name = matches[0][2]["name"] if matches else card_name.title()
        
        run = self.run_manager.remove_card(actual_name)
        if run:
            deck = self.run_manager.get_full_deck(run)
            return f"Removed {actual_name}. Deck now has {len(deck)} cards."
        return "Failed to remove card."
    
    def add_relic(self, relic_name: str) -> str:
        """Add a relic to the current run."""
        if not self.run_manager.get_active_run():
            return "No active run."
        
        matches = self.kb.find_relics(relic_name)
        actual_name = matches[0][2]["name"] if matches else relic_name.title()
        
        run = self.run_manager.add_relic(actual_name)
        if run:
            return f"Added {actual_name}. You have {len(run['relics'])} relics."
        return "Failed to add relic."
    
    def update_floor(self, floor: int) -> str:
        """Update current floor."""
        run = self.run_manager.advance_floor(floor)
        if run:
            return f"Now on Floor {run['floor']}, Act {run['act']}."
        return "No active run."
    
    def update_hp(self, current: int, max_hp: int = None) -> str:
        """Update HP."""
        updates = {"hp": current}
        if max_hp:
            updates["max_hp"] = max_hp
        
        run = self.run_manager.update_run(**updates)
        if run:
            return f"HP: {run['hp']}/{run['max_hp']}"
        return "No active run."
    
    def update_gold(self, gold: int) -> str:
        """Update gold."""
        run = self.run_manager.update_run(gold=gold)
        if run:
            return f"Gold: {run['gold']}"
        return "No active run."
    
    def get_run_status(self) -> str:
        """Get current run status."""
        run = self.run_manager.get_active_run()
        if not run:
            return "No active run. Say 'start a new run' to begin!"
        
        deck = self.run_manager.get_full_deck(run)
        
        return (f"Playing {run['character']} Ascension {run['ascension']}. "
                f"Act {run['act']}, Floor {run['floor']}. "
                f"HP {run['hp']}/{run['max_hp']}, {run['gold']} gold. "
                f"Deck has {len(deck)} cards, {len(run['relics'])} relics.")
    
    def end_run(self, victory: bool = False, cause: str = None) -> str:
        """End the current run."""
        run = self.run_manager.get_active_run()
        if not run:
            return "No active run to end."
        
        char = run["character"]
        asc = run["ascension"]
        floor = run["floor"]
        
        self.run_manager.end_run(victory=victory, cause=cause)
        
        result = "Victory!" if victory else f"Defeated on floor {floor}."
        return f"Run ended. {char} A{asc}. {result}"
    
    def lookup_card(self, card_name: str) -> str:
        """Look up card info."""
        info = self.kb.get_card_info(card_name)
        return info or f"Card '{card_name}' not found."
    
    def lookup_relic(self, relic_name: str) -> str:
        """Look up relic info."""
        info = self.kb.get_relic_info(relic_name)
        return info or f"Relic '{relic_name}' not found."


if __name__ == "__main__":
    print("Testing Gemini Advisor with Persistent Storage...")
    print("-" * 50)
    
    try:
        advisor = GeminiAdvisor()
        
        # Check if there's an existing run
        run = advisor.run_manager.get_active_run()
        if run:
            print(f"\n📂 Resumed existing run: {run['character']} A{run['ascension']}")
            print(f"   Floor {run['floor']}, HP {run['hp']}/{run['max_hp']}")
        else:
            print("\n🆕 Starting fresh run...")
            print(advisor.start_run("Silent", 5))
        
        print("\n📊 Run Status:")
        print(advisor.get_run_status())
        
        print("\n💬 Asking about deck:")
        response = advisor.chat_message("What cards are in my starting deck?")
        print(f"Response: {response}")
        
        print("\n➕ Adding Noxious Fumes:")
        print(advisor.add_card("noxious fumes"))
        
        print("\n💬 Asking about synergy:")
        response = advisor.chat_message("Should I take Catalyst next?")
        print(f"Response: {response}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
