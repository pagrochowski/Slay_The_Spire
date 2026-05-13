"""
Gemini API advisor for Slay the Spire with RAG.

Uses local database for accurate card/relic info and injects
full run context with every message.
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

# Suppress deprecation warning for now (google.generativeai still works)
import warnings
warnings.filterwarnings("ignore", category=FutureWarning, module="google.generativeai")

import google.generativeai as genai
from dotenv import load_dotenv
from loguru import logger


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
                # Index by lowercase name for fast lookup
                for card in cards_list:
                    name = card.get("name", "").lower()
                    if name and not name.endswith("+"):  # Skip upgraded versions for search
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
        
        # Load keywords
        keywords_file = self.data_dir / "keywords.json"
        if keywords_file.exists():
            with open(keywords_file, encoding="utf-8") as f:
                keywords_list = json.load(f)
                for kw in keywords_list:
                    name = kw.get("name", "").lower()
                    if name:
                        self.keywords[name] = kw
            logger.info(f"Loaded {len(self.keywords)} keywords")
    
    def _fuzzy_match(self, query: str, candidates: dict, threshold: float = 0.6) -> list:
        """Find fuzzy matches for a query in candidates."""
        query = query.lower().strip()
        matches = []
        
        for name, data in candidates.items():
            # Exact match
            if query == name:
                matches.append((1.0, name, data))
                continue
            
            # Partial match (query is substring of name)
            if query in name:
                matches.append((0.9, name, data))
                continue
            
            # Fuzzy match
            ratio = SequenceMatcher(None, query, name).ratio()
            if ratio >= threshold:
                matches.append((ratio, name, data))
        
        # Sort by match score descending
        matches.sort(key=lambda x: x[0], reverse=True)
        return matches[:3]  # Return top 3 matches
    
    def find_cards(self, query: str) -> list:
        """Find cards matching the query."""
        return self._fuzzy_match(query, self.cards)
    
    def find_relics(self, query: str) -> list:
        """Find relics matching the query."""
        return self._fuzzy_match(query, self.relics)
    
    def find_potions(self, query: str) -> list:
        """Find potions matching the query."""
        return self._fuzzy_match(query, self.potions)
    
    def get_card_info(self, name: str) -> Optional[str]:
        """Get formatted card info."""
        matches = self.find_cards(name)
        if not matches:
            return None
        _, _, card = matches[0]
        
        # Also get upgraded version if exists
        upgraded_name = card["name"].lower() + "+"
        upgraded = self.cards.get(upgraded_name.replace("+", "").lower())
        
        info = f"📜 {card['name']} ({card.get('color', 'Colorless')}, {card.get('rarity', 'Common')}, {card.get('type', 'Skill')})\n"
        info += f"   Cost: {card.get('cost', '?')} | {card.get('description', 'No description')}"
        
        return info
    
    def get_relic_info(self, name: str) -> Optional[str]:
        """Get formatted relic info."""
        matches = self.find_relics(name)
        if not matches:
            return None
        _, _, relic = matches[0]
        
        info = f"🔮 {relic['name']} ({relic.get('tier', 'Common')})\n"
        info += f"   {relic.get('description', 'No description')}"
        
        return info
    
    def extract_mentioned_items(self, text: str) -> dict:
        """Extract cards, relics, and potions mentioned in text."""
        text_lower = text.lower()
        found = {"cards": [], "relics": [], "potions": []}
        
        # Check each card name
        for name in self.cards:
            if name in text_lower:
                found["cards"].append(name)
        
        # Check each relic name
        for name in self.relics:
            if name in text_lower:
                found["relics"].append(name)
        
        # Check each potion name
        for name in self.potions:
            if name in text_lower:
                found["potions"].append(name)
        
        return found


class GeminiAdvisor:
    """Slay the Spire advisor powered by Gemini API with RAG."""
    
    # Character data (loaded once, shared across instances)
    CHARACTERS = {
        "ironclad": {
            "name": "Ironclad",
            "hp": 80,
            "starter_relic": "Burning Blood",
            "starter_relic_desc": "Heal 6 HP after combat",
            "color": "Red",
            "starter_deck": ["Strike", "Strike", "Strike", "Strike", "Strike", "Defend", "Defend", "Defend", "Defend", "Bash"]
        },
        "silent": {
            "name": "Silent",
            "hp": 70,
            "starter_relic": "Ring of the Snake",
            "starter_relic_desc": "Draw 2 extra cards turn 1",
            "color": "Green",
            "starter_deck": ["Strike", "Strike", "Strike", "Strike", "Strike", "Defend", "Defend", "Defend", "Defend", "Defend", "Survivor", "Neutralize"]
        },
        "defect": {
            "name": "Defect",
            "hp": 75,
            "starter_relic": "Cracked Core",
            "starter_relic_desc": "Channel 1 Lightning at start of combat",
            "color": "Blue",
            "starter_deck": ["Strike", "Strike", "Strike", "Strike", "Defend", "Defend", "Defend", "Defend", "Zap", "Dualcast"]
        },
        "watcher": {
            "name": "Watcher",
            "hp": 72,
            "starter_relic": "Pure Water",
            "starter_relic_desc": "Add Miracle to hand at start of combat",
            "color": "Purple",
            "starter_deck": ["Strike", "Strike", "Strike", "Strike", "Defend", "Defend", "Defend", "Defend", "Eruption", "Vigilance"]
        }
    }
    
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment. Add it to .env file.")
        
        # Load knowledge base
        self.kb = KnowledgeBase()
        
        # Configure Gemini
        genai.configure(api_key=api_key)
        
        # Use Gemini 2.5 Flash Lite (better free tier availability)
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
        
        # Start a chat session for conversation history
        self.chat = self.model.start_chat(history=[])
        
        # Run tracking (in-memory)
        self.active_run = None
        
        logger.info(f"Gemini Advisor initialized (KB: {len(self.kb.cards)} cards, {len(self.kb.relics)} relics)")
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for the advisor."""
        return """You are an expert Slay the Spire advisor. You help players make strategic decisions during their runs.

CORE KNOWLEDGE:
- 4 characters: Ironclad (80HP), Silent (70HP), Defect (75HP), Watcher (72HP)
- Ascension reduces max HP by 4 at A14 and additional 10% at A10
- Three acts with bosses: Act 1 (Slime Boss/Hexaghost/Guardian), Act 2 (Champ/Collector/Automaton), Act 3 (Awakened/Time Eater/Donu & Deca)
- Optional Act 4 with the Heart requires 3 keys

STRATEGY PRINCIPLES:
- Early game: prioritize damage and front-loaded solutions
- Scale before Act 2 boss fights
- Deck quality > deck size (remove cards when possible)
- Elites are high risk/reward - take them when healthy

WHEN I PROVIDE CONTEXT:
- [RUN STATE] shows the player's current run details - use this for advice
- [CARD INFO] shows accurate card data from the database
- [RELIC INFO] shows accurate relic data from the database
Trust the provided data over your general knowledge when there's a conflict.

RESPONSE STYLE:
- Keep responses BRIEF (2-3 sentences) since they're spoken aloud
- Be conversational, not robotic
- Give specific, actionable advice
- Reference the player's actual deck/relics when relevant"""

    def _build_run_context(self) -> str:
        """Build detailed run context string."""
        if not self.active_run:
            return ""
        
        r = self.active_run
        
        # Build deck summary
        deck_cards = r.get("cards", [])
        deck_summary = f"Starter deck + {len(deck_cards)} added cards"
        if deck_cards:
            deck_summary += f": {', '.join(deck_cards[:10])}"
            if len(deck_cards) > 10:
                deck_summary += f" (+{len(deck_cards) - 10} more)"
        
        # Build relic list
        relics = r.get("relics", [])
        relics_str = ", ".join(relics) if relics else "None"
        
        context = f"""[RUN STATE]
Character: {r['character']} | Ascension: {r['ascension']}
Floor: {r.get('floor', 1)} | HP: {r.get('hp', r.get('max_hp', '?'))}/{r.get('max_hp', '?')}
Gold: {r.get('gold', 99)} | Potions: {len(r.get('potions', []))}
Deck: {deck_summary}
Relics: {relics_str}
"""
        return context
    
    def _build_rag_context(self, message: str) -> str:
        """Build RAG context by looking up mentioned cards/relics."""
        context_parts = []
        
        # Find mentioned items
        found = self.kb.extract_mentioned_items(message)
        
        # Add card info
        for card_name in found["cards"][:3]:  # Limit to 3 to avoid token bloat
            info = self.kb.get_card_info(card_name)
            if info:
                context_parts.append(f"[CARD INFO]\n{info}")
        
        # Add relic info
        for relic_name in found["relics"][:3]:
            info = self.kb.get_relic_info(relic_name)
            if info:
                context_parts.append(f"[RELIC INFO]\n{info}")
        
        return "\n\n".join(context_parts)
    
    def chat_message(self, message: str) -> str:
        """Send a message and get a response with full context."""
        try:
            # Build full context
            context_parts = []
            
            # Add run state if active
            run_context = self._build_run_context()
            if run_context:
                context_parts.append(run_context)
            
            # Add RAG context (card/relic lookups)
            rag_context = self._build_rag_context(message)
            if rag_context:
                context_parts.append(rag_context)
            
            # Combine context with message
            if context_parts:
                full_message = "\n".join(context_parts) + "\n\nPlayer: " + message
            else:
                full_message = message
            
            logger.debug(f"Sending to Gemini:\n{full_message[:500]}...")
            
            # Get response from Gemini
            response = self.chat.send_message(full_message)
            return response.text.strip()
            
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return f"Sorry, I encountered an error: {str(e)}"
    
    def start_run(self, character: str, ascension: int = 0) -> str:
        """Start tracking a new run."""
        character = character.lower()
        if character not in self.CHARACTERS:
            return f"Unknown character: {character}. Choose Ironclad, Silent, Defect, or Watcher."
        
        char_data = self.CHARACTERS[character]
        
        # Calculate max HP with ascension
        max_hp = char_data["hp"]
        if ascension >= 14:
            max_hp -= 4
        if ascension >= 10:
            max_hp = int(max_hp * 0.9)
        
        self.active_run = {
            "character": char_data["name"],
            "color": char_data["color"],
            "ascension": ascension,
            "floor": 1,
            "hp": max_hp,
            "max_hp": max_hp,
            "gold": 99,
            "cards": [],  # Non-starter cards only
            "relics": [char_data["starter_relic"]],
            "potions": [],
            "starter_deck": char_data["starter_deck"].copy(),
        }
        
        # Notify Gemini about the new run
        context = f"""[NEW RUN STARTED]
Character: {char_data['name']} (Ascension {ascension})
Starting HP: {max_hp}
Starter Relic: {char_data['starter_relic']} - {char_data['starter_relic_desc']}
Starter Deck: {', '.join(char_data['starter_deck'])}

Please acknowledge the new run briefly."""
        
        self.chat.send_message(context)
        
        logger.info(f"Started new run: {char_data['name']} A{ascension}")
        return f"New run started! {char_data['name']} Ascension {ascension}. HP: {max_hp}. Good luck!"
    
    def add_card(self, card_name: str) -> str:
        """Add a card to the current run's deck."""
        if not self.active_run:
            return "No active run. Start one first!"
        
        # Try to find the card in our database
        matches = self.kb.find_cards(card_name)
        if matches:
            _, matched_name, card_data = matches[0]
            actual_name = card_data["name"]
        else:
            actual_name = card_name.title()
        
        self.active_run["cards"].append(actual_name)
        logger.info(f"Added card: {actual_name}")
        
        return f"Added {actual_name} to deck. Deck now has {len(self.active_run['cards'])} non-starter cards."
    
    def add_relic(self, relic_name: str) -> str:
        """Add a relic to the current run."""
        if not self.active_run:
            return "No active run. Start one first!"
        
        # Try to find the relic in our database
        matches = self.kb.find_relics(relic_name)
        if matches:
            _, matched_name, relic_data = matches[0]
            actual_name = relic_data["name"]
        else:
            actual_name = relic_name.title()
        
        self.active_run["relics"].append(actual_name)
        logger.info(f"Added relic: {actual_name}")
        
        return f"Added {actual_name}. You now have {len(self.active_run['relics'])} relics."
    
    def update_state(self, floor: int = None, hp: int = None, gold: int = None) -> str:
        """Update the current run state."""
        if not self.active_run:
            return "No active run."
        
        updates = []
        if floor is not None:
            self.active_run["floor"] = floor
            updates.append(f"Floor {floor}")
        if hp is not None:
            self.active_run["hp"] = hp
            updates.append(f"HP {hp}")
        if gold is not None:
            self.active_run["gold"] = gold
            updates.append(f"Gold {gold}")
        
        if updates:
            return f"Updated: {', '.join(updates)}"
        return "No changes made."
    
    def get_run_status(self) -> str:
        """Get current run status as natural speech."""
        if not self.active_run:
            return "No active run. Say 'start a new run' to begin!"
        
        r = self.active_run
        deck_count = len(r["cards"])
        relic_count = len(r["relics"])
        
        status = f"Playing {r['character']} Ascension {r['ascension']}. "
        status += f"Floor {r.get('floor', 1)}, HP {r.get('hp')}/{r.get('max_hp')}, {r.get('gold', 99)} gold. "
        status += f"Deck has {deck_count} added cards, {relic_count} relics."
        
        return status
    
    def end_run(self, victory: bool = False) -> str:
        """End the current run."""
        if not self.active_run:
            return "No active run to end."
        
        char = self.active_run["character"]
        asc = self.active_run["ascension"]
        floor = self.active_run.get("floor", 1)
        
        result = "Victory!" if victory else f"Defeated on floor {floor}."
        self.active_run = None
        
        return f"Run ended. {char} A{asc}. {result}"
    
    def lookup_card(self, card_name: str) -> str:
        """Look up card information."""
        info = self.kb.get_card_info(card_name)
        if info:
            return info
        return f"Card '{card_name}' not found in database."
    
    def lookup_relic(self, relic_name: str) -> str:
        """Look up relic information."""
        info = self.kb.get_relic_info(relic_name)
        if info:
            return info
        return f"Relic '{relic_name}' not found in database."


if __name__ == "__main__":
    print("Testing Gemini Advisor with RAG...")
    print("-" * 50)
    
    try:
        advisor = GeminiAdvisor()
        
        # Test card lookup
        print("\n📜 Card Lookup Test:")
        print(advisor.lookup_card("noxious fumes"))
        print(advisor.lookup_card("bash"))
        
        # Test run tracking
        print("\n🎮 Starting Run:")
        print(advisor.start_run("Silent", 5))
        
        print("\n📊 Run Status:")
        print(advisor.get_run_status())
        
        # Test chat with RAG
        print("\n💬 Chat with RAG (mentions Noxious Fumes):")
        response = advisor.chat_message("I just got offered Noxious Fumes, Blade Dance, and Backstab. Which should I pick?")
        print(f"Response: {response}")
        
        # Add card and ask follow-up
        print("\n➕ Adding card:")
        print(advisor.add_card("noxious fumes"))
        
        print("\n💬 Follow-up question:")
        response = advisor.chat_message("Now I see Footwork and Catalyst. What synergizes with my poison build?")
        print(f"Response: {response}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
