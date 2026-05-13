"""
Groq API advisor for Slay the Spire with RAG and persistent run storage.

Uses local database for accurate card/relic info, persistent run storage,
and injects full run context with every message.
"""

import os
import sys
import json
import re
from pathlib import Path
from typing import Optional, List, Dict
from difflib import SequenceMatcher

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from groq import Groq
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
        self.archetypes = {}
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
                    if name:
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
        
        # Load archetypes
        archetypes_file = self.data_dir / "archetypes.json"
        if archetypes_file.exists():
            with open(archetypes_file, encoding="utf-8") as f:
                self.archetypes = json.load(f)
            logger.info(f"Loaded archetypes for {len(self.archetypes)} characters")
    
    def find_cards(self, query: str, limit: int = 5) -> list:
        """Find cards matching a query using fuzzy matching."""
        query_lower = query.lower().strip()
        results = []
        
        for name, card in self.cards.items():
            # Exact match
            if query_lower == name:
                results.append((1.0, name, card))
                continue
            # Contains match
            if query_lower in name:
                results.append((0.9, name, card))
                continue
            # Fuzzy match
            ratio = SequenceMatcher(None, query_lower, name).ratio()
            if ratio > 0.6:
                results.append((ratio, name, card))
        
        results.sort(key=lambda x: x[0], reverse=True)
        return results[:limit]
    
    def find_relics(self, query: str, limit: int = 5) -> list:
        """Find relics matching a query."""
        query_lower = query.lower().strip()
        results = []
        
        for name, relic in self.relics.items():
            if query_lower == name:
                results.append((1.0, name, relic))
                continue
            if query_lower in name:
                results.append((0.9, name, relic))
                continue
            ratio = SequenceMatcher(None, query_lower, name).ratio()
            if ratio > 0.6:
                results.append((ratio, name, relic))
        
        results.sort(key=lambda x: x[0], reverse=True)
        return results[:limit]
    
    def get_card_info(self, card_name: str) -> Optional[str]:
        """Get formatted card info string."""
        matches = self.find_cards(card_name, limit=1)
        if not matches:
            return None
        
        _, _, card = matches[0]
        parts = [f"{card['name']} ({card.get('rarity', 'Unknown')} {card.get('type', 'Card')})"]
        parts.append(f"Cost: {card.get('cost', '?')} | {card.get('color', 'Colorless')}")
        if card.get("description"):
            parts.append(card["description"])
        if card.get("upgrade"):
            parts.append(f"Upgraded: {card['upgrade']}")
        return "\n".join(parts)
    
    def get_relic_info(self, relic_name: str) -> Optional[str]:
        """Get formatted relic info string."""
        matches = self.find_relics(relic_name, limit=1)
        if not matches:
            return None
        
        _, _, relic = matches[0]
        parts = [f"{relic['name']} ({relic.get('rarity', 'Unknown')} Relic)"]
        if relic.get("description"):
            parts.append(relic["description"])
        if relic.get("flavor"):
            parts.append(f"Flavor: {relic['flavor']}")
        return "\n".join(parts)
    
    def extract_mentioned_items(self, text: str) -> dict:
        """Extract card/relic names mentioned in text using word boundary matching."""
        import re
        text_lower = text.lower()
        found = {"cards": [], "relics": []}
        
        # Sort by length (longest first) to match "Pommel Strike" before "Strike"
        sorted_cards = sorted(self.cards.keys(), key=len, reverse=True)
        sorted_relics = sorted(self.relics.keys(), key=len, reverse=True)
        
        for name in sorted_cards:
            # Use word boundaries to avoid partial matches
            # e.g., don't match "strike" in "pommel strike"
            pattern = r'\b' + re.escape(name) + r'\b'
            if re.search(pattern, text_lower):
                found["cards"].append(name)
        
        for name in sorted_relics:
            pattern = r'\b' + re.escape(name) + r'\b'
            if re.search(pattern, text_lower):
                found["relics"].append(name)
        
        return found
    
    def get_character_archetypes(self, character: str) -> list:
        """Get all archetypes for a character."""
        char_data = self.archetypes.get(character.lower(), {})
        if isinstance(char_data, dict):
            return char_data.get("archetypes", [])
        return []
    
    def detect_archetype_from_deck(self, character: str, deck: list) -> list:
        """Detect which archetypes the deck is trending toward."""
        archetypes = self.get_character_archetypes(character)
        if not archetypes:
            return []
        
        deck_lower = [c.lower() for c in deck]
        scores = []
        
        for arch in archetypes:
            key_cards = [c.lower() for c in arch.get("key_cards", [])]
            support_cards = [c.lower() for c in arch.get("support_cards", [])]
            
            # Score based on matching cards
            matched = []
            score = 0
            for card in key_cards:
                if card in deck_lower:
                    score += 2
                    matched.append(card)
            for card in support_cards:
                if card in deck_lower:
                    score += 1
                    matched.append(card)
            
            if score > 0:
                scores.append((arch["name"], score, matched))
        
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:3]


# Boss strategies by act
BOSSES = {
    1: {
        "Slime Boss": "Splits at 50% HP into 2 Large Slimes. Focus damage to kill before split, or prepare for multi-target.",
        "The Guardian": "Alternates between offensive and defensive mode. Save damage for offensive mode, block during defensive.",
        "Hexaghost": "6 attacks then big hit. Need good block for Inferno. Attacks scale each cycle."
    },
    2: {
        "Champ": "Executes at 50% HP for big damage. Either burst him down fast or be ready to block Execute.",
        "Collector": "Spawns minions. Kill minions or they buff him. Multi-target helps.",
        "Automaton": "Artifact charges block debuffs. High damage output, needs consistent block."
    },
    3: {
        "Awakened One": "Gains Strength when you play Powers in phase 1. Save Powers for phase 2 if possible.",
        "Time Eater": "Ends your turn after 12 cards. Plan turns carefully, value high-impact single cards.",
        "Donu and Deca": "Kill Donu first (scaling). Deca blocks and removes debuffs."
    },
    4: {
        "Corrupt Heart": "200 HP, massive damage. Need huge scaling and at least 2 of 3 keys.",
        "Spire Shield": "Appears with Heart. Kill or ignore based on deck.",
        "Spire Spear": "Appears with Heart. Usually kill first for less damage taken."
    }
}


class GroqAdvisor:
    """Slay the Spire advisor powered by Groq API with persistent run storage."""
    
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
        
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not found in environment.")
        
        # Load knowledge base
        self.kb = KnowledgeBase()
        
        # Initialize run manager (persistent storage)
        self.run_manager = RunManager()
        
        # Configure Groq client
        self.client = Groq(api_key=api_key)
        self.model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        self.fallback_model = os.getenv("GROQ_FALLBACK_MODEL", "llama-3.1-8b-instant")
        
        # Conversation context for follow-up questions
        self.last_card_choices: List[str] = []  # Cards from last card_choice question
        self.last_relic_choices: List[str] = []  # Relics from last relic question
        
        # Conversation history (OpenAI-style messages)
        self.messages: List[Dict[str, str]] = [
            {"role": "system", "content": self._get_system_prompt()}
        ]
        
        # Try to resume latest active run
        resumed_run = self.run_manager.resume_latest_run()
        if resumed_run:
            # Inform model about the resumed run
            self._send_run_context(resumed_run, resumed=True)
        
        logger.info(f"Groq advisor initialized - Model: {self.model}, Fallback: {self.fallback_model}")
        logger.info(f"Knowledge base: {len(self.kb.cards)} cards, {len(self.kb.relics)} relics")
    
    def _get_system_prompt(self) -> str:
        return """You are an expert Slay the Spire advisor helping a player during their run.

CRITICAL RULES:
1. ONLY use information from [RUN STATE] - never make up or assume deck contents
2. If no [RUN STATE] is provided, there is NO active run
3. The deck shown in [RUN STATE] is the COMPLETE and ACCURATE deck
4. Do NOT invent cards, relics, or events that aren't explicitly stated
5. Solving IMMEDIATE problems takes priority over chasing build archetypes

DECISION MAKING:
When evaluating a card/relic choice, consider:
- Does it solve an immediate problem? (damage, block, scaling, card draw)
- Does it synergize with existing deck?
- Does it help against the upcoming boss?
- Would a skilled player take this? If yes, it increases win odds.
If multiple good options: prefer the one that keeps options open or matches current archetype.

SKIPPING CARDS:
Skipping is ALWAYS a valid option. Recommend SKIP when:
- Deck has 25+ cards and none of the options are exceptional
- None of the cards align with [CURRENT STRATEGY] or immediate needs
- All options are weak/situational cards that would dilute the deck
- Deck already has enough of what's offered (e.g., 3+ AoE cards already)
A lean, focused deck is often better than a bloated one with "okay" cards.

CURRENT STRATEGY:
I will provide [CURRENT STRATEGY] notes that evolve throughout the run.
When you notice a strategic shift (e.g., picked Corruption, found Dead Branch), 
end your response with: [STRATEGY UPDATE: "new strategy note"]
I will track these notes and show them in future queries.

BUILD ARCHETYPES:
Archetypes are GUIDES, not strict rules. They can be mixed and deviated from.
I will provide [ARCHETYPE HINTS] showing which builds the deck is trending toward.
Use this to suggest synergistic picks, but always prioritize immediate needs.

BOSS PREPARATION:
When [CURRENT BOSS] is provided, factor boss mechanics into advice.
Some cards are great generally but terrible against specific bosses.

RESPONSE STYLE:
- Keep responses BRIEF (2-3 sentences) - they're spoken aloud
- Be conversational, not robotic
- Use card counts like "5 Strikes" not "Strike, Strike, Strike..."
- Give specific, actionable advice based on ACTUAL deck state
- When suggesting cards, briefly explain WHY (synergy, boss prep, immediate need)

When I provide [CARD INFO] or [RELIC INFO], that data is accurate - trust it over your memory."""
    
    def _send_run_context(self, run: dict, resumed: bool = False):
        """Send run context to establish state."""
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
            self.messages.append({"role": "user", "content": context})
            response = self._call_groq(self.messages)
            self.messages.append({"role": "assistant", "content": response})
        except Exception as e:
            logger.error(f"Failed to send run context: {e}")
    
    def _call_groq(self, messages: List[Dict[str, str]], stream: bool = False, retry_count: int = 0) -> str:
        """Call Groq API and return response text."""
        # Use fallback model on retry
        model = self.model if retry_count == 0 else self.fallback_model
        
        try:
            if stream:
                completion = self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=0.7,
                    max_completion_tokens=500,
                    top_p=0.95,
                    stream=True,
                )
                
                response_text = ""
                for chunk in completion:
                    if chunk.choices[0].delta.content:
                        response_text += chunk.choices[0].delta.content
                return response_text.strip()
            else:
                completion = self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=0.7,
                    max_completion_tokens=500,
                    top_p=0.95,
                )
                
                # Log completion details for debugging
                choice = completion.choices[0]
                content = choice.message.content
                finish_reason = choice.finish_reason
                
                logger.debug(f"Groq [{model}] - finish: {finish_reason}, len: {len(content) if content else 0}")
                
                # Handle empty response - retry with fallback model
                if not content or len(content.strip()) < 5:
                    if retry_count < 1:
                        logger.warning(f"Empty response from {model} (finish: {finish_reason}), trying fallback model...")
                        return self._call_groq(messages, stream=False, retry_count=retry_count + 1)
                    logger.error(f"Empty response after fallback. finish_reason: {finish_reason}")
                
                return (content or "").strip()
        except Exception as e:
            logger.error(f"Groq API error ({model}): {e}")
            # Try fallback on error too
            if retry_count < 1:
                logger.warning(f"Error with {model}, trying fallback...")
                return self._call_groq(messages, stream=False, retry_count=retry_count + 1)
            raise
    
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
        
        # Add strategy notes if any
        strategy = run.get("strategy", [])
        if strategy:
            context += f"\n[CURRENT STRATEGY] {' | '.join(strategy)}"
        
        # Add boss info if set
        boss = run.get("current_boss")
        if boss:
            act = run.get("act", 1)
            boss_info = BOSSES.get(act, {}).get(boss, "")
            context += f"\n[CURRENT BOSS] {boss}: {boss_info}"
        
        # Detect and add archetype hints
        character = run['character'].lower()
        archetype_scores = self.kb.detect_archetype_from_deck(character, deck)
        if archetype_scores:
            hints = []
            for name, score, matched in archetype_scores:
                if score >= 3:  # Only show if significant match
                    hints.append(f"{name} (matched: {', '.join(matched[:3])})")
            if hints:
                context += f"\n[ARCHETYPE HINTS] Deck trends toward: {'; '.join(hints)}"
        
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
        
        # Prioritize cards that are likely being discussed (longer names first to avoid
        # matching "Strike" when user said "Pommel Strike")
        card_names = sorted(found["cards"], key=len, reverse=True)[:5]
        
        for card_name in card_names:
            info = self.kb.get_card_info(card_name)
            if info:
                context_parts.append(f"[CARD INFO]\n{info}")
        
        for relic_name in found["relics"][:3]:
            info = self.kb.get_relic_info(relic_name)
            if info:
                context_parts.append(f"[RELIC INFO]\n{info}")
        
        return "\n\n".join(context_parts)
    
    def _trim_history(self, max_messages: int = 20):
        """Trim conversation history to prevent context overflow."""
        # Keep system message + last N messages
        if len(self.messages) > max_messages + 1:
            self.messages = [self.messages[0]] + self.messages[-(max_messages):]
    
    def _is_followup_question(self, message: str) -> bool:
        """Detect if message is a follow-up about previous card/relic choices."""
        followup_phrases = [
            "why not", "what about", "the other", "other card", "other option",
            "instead", "rather than", "over the", "compared to", "versus",
            "explain", "why did you", "why that", "why this", "reasoning",
            "elaborate", "more detail", "tell me more", "what makes",
            "the rest", "rejected", "didn't pick", "didn't choose"
        ]
        message_lower = message.lower()
        return any(phrase in message_lower for phrase in followup_phrases)
    
    def set_card_choices(self, cards: List[str]) -> None:
        """Set the current card choices for follow-up context."""
        self.last_card_choices = cards
        logger.debug(f"Stored card choices for follow-up: {cards}")
    
    def set_relic_choices(self, relics: List[str]) -> None:
        """Set the current relic choices for follow-up context."""
        self.last_relic_choices = relics
        logger.debug(f"Stored relic choices for follow-up: {relics}")
    
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
            
            # Add follow-up context if this looks like a follow-up question
            if self._is_followup_question(message):
                followup_context = []
                if self.last_card_choices:
                    cards_str = ", ".join(self.last_card_choices)
                    followup_context.append(f"[PREVIOUS CARD CHOICES] The cards being discussed were: {cards_str}")
                    # Also add card info for the cards being referenced
                    for card_name in self.last_card_choices:
                        info = self.kb.get_card_info(card_name)
                        if info:
                            followup_context.append(f"[CARD INFO]\n{info}")
                if self.last_relic_choices:
                    relics_str = ", ".join(self.last_relic_choices)
                    followup_context.append(f"[PREVIOUS RELIC CHOICES] The relics being discussed were: {relics_str}")
                if followup_context:
                    context_parts.extend(followup_context)
                    logger.debug(f"Added follow-up context for: {self.last_card_choices or self.last_relic_choices}")
            
            # Combine context with message
            full_message = "\n\n".join(context_parts) + "\n\nPlayer: " + message
            
            logger.debug(f"Sending to Groq:\n{full_message[:800]}...")
            
            # Add to history and get response
            self.messages.append({"role": "user", "content": full_message})
            response = self._call_groq(self.messages)
            
            # Validate response
            if not response or len(response.strip()) < 5:
                logger.warning(f"Got empty/short response from model: '{response}'")
                response = "I'm having trouble thinking of advice right now. Could you rephrase?"
            
            # Extract and save strategy updates
            response = self._extract_strategy_updates(response)
            
            logger.info(f"Model response: {response[:200]}...")
            
            self.messages.append({"role": "assistant", "content": response})
            
            # Trim history to prevent overflow
            self._trim_history()
            
            return response
            
        except Exception as e:
            logger.error(f"Groq API error: {e}")
            return f"Sorry, I encountered an error: {str(e)}"
    
    def _extract_strategy_updates(self, response: str) -> str:
        """Extract strategy updates from model response and save them."""
        # Pattern: [STRATEGY UPDATE: "note"] or [STRATEGY UPDATE: note]
        pattern = r'\[STRATEGY UPDATE:\s*"?([^"\]]+)"?\]'
        matches = re.findall(pattern, response, re.IGNORECASE)
        
        for note in matches:
            note = note.strip()
            if note:
                self.run_manager.add_strategy(note)
        
        # Remove strategy update tags from the spoken response
        clean_response = re.sub(pattern, '', response, flags=re.IGNORECASE).strip()
        return clean_response
    
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
        
        # Reset chat history and inform model
        self.messages = [{"role": "system", "content": self._get_system_prompt()}]
        self._send_run_context(run, resumed=False)
        
        deck_str = format_deck_counts(char_data["starter_deck"])
        return f"New run started! {char_data['name']} Ascension {ascension}. HP: {max_hp}. Deck: {deck_str}. Good luck!"
    
    # Color mapping for character validation
    COLOR_MAP = {
        "Ironclad": "Red",
        "Silent": "Green",
        "Defect": "Blue",
        "Watcher": "Purple"
    }
    
    def add_card(self, card_name: str) -> str:
        """Add a card to the current run with validation."""
        run = self.run_manager.get_active_run()
        if not run:
            return "No active run. Start one first!"
        
        # Find card in database
        matches = self.kb.find_cards(card_name, limit=5)
        
        if not matches:
            return f"Card '{card_name}' not found in database. Could you spell it differently?"
        
        # Get best match
        score, _, card_data = matches[0]
        actual_name = card_data["name"]
        card_color = card_data.get("color", "Colorless")
        
        # Check if card matches current character or is colorless
        char = run["character"]
        char_color = self.COLOR_MAP.get(char, "Red")
        
        # Remove + suffix for base card matching
        base_name = actual_name.rstrip('+')
        
        if card_color != "Colorless" and card_color != char_color:
            # Wrong class card - suggest alternatives
            valid_matches = [
                (s, n, c) for s, n, c in matches 
                if c.get("color") in [char_color, "Colorless"]
            ]
            if valid_matches:
                suggestions = ", ".join([c["name"] for _, _, c in valid_matches[:3]])
                return f"'{actual_name}' is a {card_color} card, but you're playing {char}. Did you mean: {suggestions}?"
            return f"'{actual_name}' is a {card_color} card, not available for {char}."
        
        # Low confidence match - ask for confirmation
        if score < 0.7:
            suggestions = ", ".join([c["name"] for _, _, c in matches[:3]])
            return f"Did you mean one of these? {suggestions}"
        
        # Valid card - add it
        run = self.run_manager.add_card(base_name if not actual_name.endswith('+') else actual_name)
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
        """Add a relic to the current run with validation."""
        if not self.run_manager.get_active_run():
            return "No active run."
        
        matches = self.kb.find_relics(relic_name, limit=5)
        
        if not matches:
            return f"Relic '{relic_name}' not found in database. Could you spell it differently?"
        
        score, _, relic_data = matches[0]
        actual_name = relic_data["name"]
        
        # Low confidence match - ask for confirmation
        if score < 0.7:
            suggestions = ", ".join([r["name"] for _, _, r in matches[:3]])
            return f"Did you mean one of these relics? {suggestions}"
        
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
    
    def update_hp(self, current: int = None, max_hp: int = None) -> str:
        """Update HP. Can update current, max, or both independently."""
        updates = {}
        if current is not None:
            updates["hp"] = current
        if max_hp is not None:
            updates["max_hp"] = max_hp
        
        if not updates:
            return "No HP values provided."
        
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
        strategy = run.get("strategy", [])
        
        status = (f"Playing {run['character']} Ascension {run['ascension']}. "
                f"Act {run['act']}, Floor {run['floor']}. "
                f"HP {run['hp']}/{run['max_hp']}, {run['gold']} gold. "
                f"Deck has {len(deck)} cards, {len(run['relics'])} relics.")
        
        if strategy:
            status += f" Strategy: {'; '.join(strategy)}"
        
        return status
    
    def add_strategy(self, note: str) -> str:
        """Manually add a strategy note."""
        if not self.run_manager.get_active_run():
            return "No active run."
        self.run_manager.add_strategy(note)
        return f"Strategy added: {note}"
    
    def clear_strategy(self) -> str:
        """Clear all strategy notes."""
        if not self.run_manager.get_active_run():
            return "No active run."
        self.run_manager.clear_strategy()
        return "Strategy cleared."
    
    def get_strategy(self) -> str:
        """Get current strategy notes."""
        strategy = self.run_manager.get_strategy()
        if not strategy:
            return "No strategy notes yet. The advisor will add them as the run progresses."
        return f"Current strategy: {'; '.join(strategy)}"
    
    def adjust_strategy(self) -> str:
        """Ask the AI to analyze the run and suggest/update strategy."""
        run = self.run_manager.get_active_run()
        if not run:
            return "No active run."
        
        # Build a focused prompt for strategy analysis
        current_strategy = run.get("strategy", [])
        strategy_str = "; ".join(current_strategy) if current_strategy else "None set"
        
        prompt = f"""Analyze my current run and suggest an updated strategy.

Current strategy notes: {strategy_str}

Based on my deck, relics, HP, and floor progress, what should my strategic focus be?
Consider:
- What synergies exist in my deck?
- What am I missing (damage, block, scaling, card draw)?
- What boss am I preparing for?
- Should I be more aggressive or defensive in card picks?

Give me 2-3 concise strategy points. End with [STRATEGY UPDATE: "point1"] for each new point (this replaces old strategy)."""
        
        # Clear old strategy before getting new recommendations
        self.run_manager.clear_strategy()
        
        # Use chat_message to get AI analysis with full context
        return self.chat_message(prompt)

    def advise_card_removal(self) -> str:
        """Advise which card to remove at a removal event (shop, event)."""
        run = self.run_manager.get_active_run()
        if not run:
            return "No active run."
        
        deck = self.run_manager.get_full_deck(run)
        if not deck:
            return "Your deck is empty."
        
        # Build a focused prompt for card removal advice
        deck_summary = format_deck_counts(deck)
        
        prompt = f"""I'm at a card removal event. Which card should I remove from my deck?

My deck: {deck_summary}

Consider:
- Removing basic Strikes/Defends improves deck consistency
- Keep cards that synergize with my relics and archetype
- Think about what boss I'm preparing for
- A leaner deck draws key cards more often

Recommend ONE card to remove and explain why in 1-2 sentences."""
        
        return self.chat_message(prompt)

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
    
    def set_boss(self, boss_name: str) -> str:
        """Set the current boss (for strategy advice)."""
        run = self.run_manager.get_active_run()
        if not run:
            return "No active run."
        
        act = run.get("act", 1)
        act_bosses = BOSSES.get(act, {})
        
        # Try to match boss name
        boss_name_lower = boss_name.lower()
        matched_boss = None
        for boss in act_bosses.keys():
            if boss_name_lower in boss.lower() or boss.lower() in boss_name_lower:
                matched_boss = boss
                break
        
        if matched_boss:
            self.run_manager.set_boss(matched_boss)
            strategy = act_bosses[matched_boss]
            return f"Boss set to {matched_boss}. {strategy}"
        else:
            available = ", ".join(act_bosses.keys())
            return f"Unknown boss '{boss_name}' for Act {act}. Available: {available}"
    
    def lookup_card(self, card_name: str) -> str:
        """Look up card info."""
        info = self.kb.get_card_info(card_name)
        return info or f"Card '{card_name}' not found."
