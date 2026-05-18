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


def format_deck_counts(cards: list) -> str:
    """Format a deck list with counts (e.g., '5x Strike, 4x Defend, 1x Bash')."""
    from collections import Counter
    counts = Counter(cards)
    formatted = []
    for card, count in sorted(counts.items()):
        if count > 1:
            formatted.append(f"{count}x {card}")
        else:
            formatted.append(card)
    return ", ".join(formatted)


class KnowledgeBase:
    """Local knowledge base loaded from split JSON files in data/knowledge/.
    
    Knowledge organization is documented in data/knowledge/KNOWLEDGE_MAP.md
    which serves as the master index for all game data files.
    """
    
    def __init__(self, data_dir: Path = None):
        self.data_dir = data_dir or PROJECT_ROOT / "data" / "knowledge"
        self.cards = {}
        self.relics = {}
        self.potions = {}
        self.archetypes = {}
        self.bosses = {}  # Boss strategy data from raw/bosses.json
        self._load_data()
    
    def _load_split_json(self, pattern: str) -> List[Dict]:
        """Load data from multiple JSON files matching a pattern."""
        items = []
        for filepath in self.data_dir.glob(pattern):
            try:
                with open(filepath, encoding="utf-8") as f:
                    data = json.load(f)
                    # Extract items from the data field (skip _meta)
                    if "cards" in data:
                        items.extend(data["cards"])
                    elif "relics" in data:
                        items.extend(data["relics"])
                    elif "enemies" in data:
                        items.extend(data["enemies"])
                    elif "potions" in data:
                        items.extend(data["potions"])
            except Exception as e:
                logger.warning(f"Failed to load {filepath}: {e}")
        return items
    
    def _load_data(self):
        """Load all data from knowledge base JSON files.
        
        File organization is documented in data/knowledge/KNOWLEDGE_MAP.md
        """
        # Load all cards from split files (cards/*.json)
        cards_list = self._load_split_json("cards/*.json")
        for card in cards_list:
            name = card.get("name", "").lower()
            if name:
                self.cards[name] = card
        logger.info(f"Loaded {len(self.cards)} cards from split files")
        
        # Load all relics from split files (relics/*.json)
        relics_list = self._load_split_json("relics/*.json")
        for relic in relics_list:
            name = relic.get("name", "").lower()
            if name:
                self.relics[name] = relic
        logger.info(f"Loaded {len(self.relics)} relics from split files")
        
        # Load potions (single file)
        potions_file = self.data_dir / "potions.json"
        if potions_file.exists():
            with open(potions_file, encoding="utf-8") as f:
                data = json.load(f)
                potions_list = data.get("potions", [])
                for potion in potions_list:
                    name = potion.get("name", "").lower()
                    if name:
                        self.potions[name] = potion
            logger.info(f"Loaded {len(self.potions)} potions")
        
        # Load archetypes (single file)
        archetypes_file = self.data_dir / "archetypes.json"
        if archetypes_file.exists():
            with open(archetypes_file, encoding="utf-8") as f:
                data = json.load(f)
                self.archetypes = data.get("archetypes", {})
            logger.info(f"Loaded archetypes for {len(self.archetypes)} characters")
        
        # Load boss strategies from raw/bosses.json (manually curated, not in knowledge/)
        bosses_file = PROJECT_ROOT / "data" / "raw" / "bosses.json"
        if bosses_file.exists():
            with open(bosses_file, encoding="utf-8") as f:
                bosses_data = json.load(f)
                # Flatten act-based structure for easier lookup
                for act_bosses in bosses_data.values():
                    for boss_name, boss_info in act_bosses.items():
                        self.bosses[boss_name] = boss_info
            logger.info(f"Loaded {len(self.bosses)} boss strategies from raw/bosses.json")
    
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
    
    def get_boss_info(self, boss_name: str) -> Optional[str]:
        """Get boss strategy as formatted text."""
        # Try exact match first
        if boss_name in self.bosses:
            boss_data = self.bosses[boss_name]
            # Check if it's new JSON format or legacy text
            if isinstance(boss_data, dict) and "strategy_tips" in boss_data:
                # New JSON format - format nicely
                tips = "\n".join([f"- {tip}" for tip in boss_data["strategy_tips"]])
                mechanics = "\n".join([f"- {mech}" for mech in boss_data["mechanics"]])
                return f"Mechanics:\n{mechanics}\n\nStrategy:\n{tips}"
            elif isinstance(boss_data, dict) and "raw_text" in boss_data:
                # Legacy text format
                return boss_data["raw_text"]
            else:
                # Old format (direct string)
                return str(boss_data)
        
        # Try case-insensitive match
        boss_lower = boss_name.lower()
        for name, info in self.bosses.items():
            if name.lower() == boss_lower:
                if isinstance(info, dict) and "strategy_tips" in info:
                    tips = "\n".join([f"- {tip}" for tip in info["strategy_tips"]])
                    mechanics = "\n".join([f"- {mech}" for mech in info["mechanics"]])
                    return f"Mechanics:\n{mechanics}\n\nStrategy:\n{tips}"
                elif isinstance(info, dict) and "raw_text" in info:
                    return info["raw_text"]
                else:
                    return str(info)
        
        return None
    
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


# Boss strategies loaded from data/knowledge/enemies/ and data/raw/bosses.json
# No hardcoded boss data - all comes from knowledge base


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
        # Primary: openai/gpt-oss-120b (fast, high quality)
        # Fallback: llama-3.3-70b-versatile (reliable alternative)
        self.model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
        self.fallback_model = os.getenv("GROQ_FALLBACK_MODEL", "llama-3.3-70b-versatile")
        
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

KNOWLEDGE BASE:
All game data is organized in data/knowledge/ directory (see KNOWLEDGE_MAP.md for complete index).
The knowledge base contains 30 split JSON files with comprehensive data:
- Cards: 5 files split by character (365 total cards)
- Relics: 6 files split by rarity pool (178 total relics)
- Enemies: 9 files split by act and difficulty (37 total enemies with strategies)
- Other: potions, keywords, archetypes, ascension modifiers
Each file includes _meta fields with LLM-friendly descriptions.
Load only what's needed based on current context (character, act, query type).

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
            error_str = str(e)
            logger.error(f"Groq API error ({model}): {e}")
            
            # Check if this is a rate limit error
            is_rate_limit = 'rate_limit' in error_str.lower() or '429' in error_str
            
            # On rate limit, try the other model (bidirectional switching)
            if is_rate_limit:
                # Switch to the other model
                other_model = self.fallback_model if model == self.model else self.model
                logger.warning(f"Rate limit on {model}, switching to {other_model}...")
                # Force use of the other model by adjusting retry_count
                new_retry = 1 if model == self.model else 0
                return self._call_groq(messages, stream=False, retry_count=new_retry)
            
            # For non-rate-limit errors, try fallback once
            if retry_count < 1:
                logger.warning(f"Error with {model}, trying fallback...")
                return self._call_groq(messages, stream=False, retry_count=retry_count + 1)
            
            # If both models failed, raise simplified error
            raise Exception("API error")
    
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
            # Use loaded boss strategy from knowledge base
            boss_info = self.kb.get_boss_info(boss)
            if boss_info:
                # Truncate to first 300 chars for context
                boss_summary = boss_info[:300] + "..." if len(boss_info) > 300 else boss_info
                context += f"\n[CURRENT BOSS] {boss}: {boss_summary}"
            else:
                # If not in knowledge base, note it but don't fail
                context += f"\n[CURRENT BOSS] {boss} (data not loaded)"
        
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
        
        # Add recent events for context (no floor numbers since they're not always updated)
        recent_events = self.run_manager.get_recent_events(run, count=3)
        if recent_events:
            events_str = " | ".join([e['details'] for e in recent_events])
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
            return "Sorry, encountered error."
    
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
        card_color = card_data.get("color", "Colorless").upper()  # Normalize to uppercase
        
        # Check if card matches current character or is colorless
        char = run["character"]
        char_color = self.COLOR_MAP.get(char, "Red").upper()  # Normalize to uppercase
        
        # Remove + suffix for base card matching
        base_name = actual_name.rstrip('+')
        
        if card_color != "COLORLESS" and card_color != char_color:
            # Wrong class card - suggest alternatives
            valid_matches = [
                (s, n, c) for s, n, c in matches 
                if c.get("color", "Colorless").upper() in [char_color, "COLORLESS"]
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
            
            # Auto-update strategy after significant card addition
            self.adjust_strategy(silent=True)
            
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
            
            # Auto-update strategy after card removal
            self.adjust_strategy(silent=True)
            
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
            # Auto-update strategy after relic addition (relics can change deck strategy significantly)
            self.adjust_strategy(silent=True)
            
            return f"Added {actual_name}. You have {len(run['relics'])} relics."
        return "Failed to add relic."
    
    def update_floor(self, floor: int, act: int = None) -> str:
        """Update current floor (and optionally act)."""
        run = self.run_manager.get_active_run()
        if not run:
            return "No active run."
        
        old_act = run.get('act', 1)
        run = self.run_manager.advance_floor(floor, new_act=act)
        if run:
            # Auto-update strategy if act changed (new enemies, different priorities)
            new_act = run.get('act', 1)
            if new_act != old_act:
                self.adjust_strategy(silent=True)
            
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
    
    def create_summary_file(self, silent: bool = False) -> str:
        """Export detailed run summary to a markdown file for LLM consumption."""
        run = self.run_manager.get_active_run()
        if not run:
            return "" if silent else "No active run to summarize."
        
        deck = self.run_manager.get_full_deck(run)
        deck_str = format_deck_counts(deck)
        
        # Build comprehensive markdown summary
        summary = f"""# Slay the Spire Run Summary

## Run Information
- **Character**: {run['character'].title()}
- **Ascension**: {run['ascension']}
- **Act**: {run['act']}
- **Floor**: {run['floor']}

## Current Status
- **HP**: {run['hp']}/{run['max_hp']}
- **Gold**: {run['gold']}

## Deck ({len(deck)} cards)
{deck_str}

## Relics
{chr(10).join(f'- {relic}' for relic in run['relics']) if run['relics'] else '- None'}

## Potions
{chr(10).join(f'- {potion}' for potion in run['potions']) if run['potions'] else '- None'}

## Keys
- Ruby: {'✓' if run['keys']['ruby'] else '✗'}
- Emerald: {'✓' if run['keys']['emerald'] else '✗'}
- Sapphire: {'✓' if run['keys']['sapphire'] else '✗'}
"""
        
        # Add boss info if set
        boss_name = run.get('current_boss')
        if boss_name:
            summary += f"\n## Current Boss\n**{boss_name}**\n"
        
        # Add strategy notes
        strategy = run.get("strategy", [])
        if strategy:
            summary += f"\n## Strategy Notes\n"
            summary += "\n".join(f"- {note}" for note in strategy) + "\n"
        
        # Add strategy sections (will be populated by adjust_strategy)
        summary += f"\n## Long-Term Goals\n"
        summary += f"*Strategy will be analyzed when you update strategy or make deck changes.*\n"
        
        summary += f"\n## Short-Term Problems\n"
        summary += f"*Strategy will be analyzed when you update strategy or make deck changes.*\n"
        
        summary += f"\n## Card Priorities\n"
        summary += f"*Strategy will be analyzed when you update strategy or make deck changes.*\n"
        
        # Add archetype hints
        character = run['character'].lower()
        archetype_scores = self.kb.detect_archetype_from_deck(character, deck)
        if archetype_scores:
            summary += f"\n## Detected Archetype Tendencies\n"
            for name, score, matched in archetype_scores:
                if score >= 3:
                    summary += f"- **{name}** (score: {score}, matched: {', '.join(matched[:5])})\n"
        
        # Add recent events (without floor numbers since they're not always updated)
        recent_events = self.run_manager.get_recent_events(run, count=10)
        if recent_events:
            summary += f"\n## Recent Events\n"
            for event in recent_events:
                # Just show the details without floor number
                summary += f"- {event['details']}\n"
        
        # Add card recommendations context
        summary += f"\n---\n\n**This summary was generated for strategic decision-making.**\n"
        summary += f"**You can ask another AI to analyze this run and provide card/relic recommendations.**\n"
        
        # Write to file (no floor number in filename)
        filename = f"run_summary_{run['character']}_A{run['ascension']}.md"
        filepath = Path(filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(summary)
        
        logger.info(f"Created run summary file: {filename}")
        if silent:
            return ""
        return f"Okay, summary file has been created."
    
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
    
    def adjust_strategy(self, silent: bool = False, boss_focus: bool = False) -> str:
        """Comprehensive strategy update: boss tactics, long-term goals, short-term problems, archetypes."""
        run = self.run_manager.get_active_run()
        if not run:
            return "" if silent else "No active run."
        
        # Get current state
        deck = self.run_manager.get_full_deck(run)
        character = run['character'].lower()
        archetype_scores = self.kb.detect_archetype_from_deck(character, deck)
        
        # Format archetype info
        archetype_hints = []
        if archetype_scores:
            for name, score, matched in archetype_scores:
                if score >= 3:
                    archetype_hints.append(f"{name} (score: {score}, cards: {', '.join(matched[:3])})")
        archetype_str = "\n".join([f"  - {hint}" for hint in archetype_hints]) if archetype_hints else "  - No clear archetype yet"
        
        # Get boss-specific context if boss is set
        boss_context = ""
        boss_name = run.get("current_boss")
        if boss_name:
            boss_data = self.kb.bosses.get(boss_name)
            if boss_data and isinstance(boss_data, dict) and "strategy_tips" in boss_data:
                mechanics = "\n".join([f"    - {m}" for m in boss_data["mechanics"]])
                tips = "\n".join([f"    - {t}" for t in boss_data["strategy_tips"]])
                boss_context = f"""\n\nUPCOMING BOSS: {boss_name}
  Mechanics:
{mechanics}
  
  Key tactics:
{tips}"""
        
        # Build comprehensive strategy prompt
        prompt = f"""Analyze my run and provide a COMPLETE strategic overview.

DETECTED ARCHETYPES:
{archetype_str}{boss_context}

Provide a comprehensive strategy update covering ALL of these areas:

1. BOSS TACTICS (if boss is set): 
   - Specific card priorities for THIS BOSS FIGHT ONLY
   - Defensive/offensive balance needed for THIS BOSS
   - Move patterns and key threats from THIS BOSS
   
2. LONG-TERM GOALS:
   - What is the win condition for this deck?
   - What synergies should I build towards?
   - What scaling do I need?

3. SHORT-TERM PROBLEMS (focus on HALLWAY FIGHTS and GENERAL deck weaknesses, NOT the boss):
   - What enemy types in hallways/elites is this deck struggling against? (multi-enemy, high HP, status effects, etc.)
   - What immediate gaps need filling for REGULAR FIGHTS? (AoE, frontload damage, consistent block, card draw)
   - What cards are dead weight or underperforming in normal encounters?

4. CARD PRIORITIES:
   - What should I prioritize in card rewards?
   - What should I skip?
   - Aggressive or defensive picks?

Be concise but cover ALL 4 areas. Format as bullet points under each section."""
        
        # Clear old strategy before getting new recommendations
        self.run_manager.clear_strategy()
        
        # Use chat_message to get AI analysis with full context
        result = self.chat_message(prompt)
        
        # Update the run summary file with the new strategy
        self._update_run_summary_strategy(run, result, boss_name)
        
        # Extract a brief one-sentence summary for speaking
        brief_summary = self._extract_brief_summary(result, boss_name)
        
        if silent:
            logger.info("Strategy revised in background")
            return ""
        return f"Strategy updated. {brief_summary}"
    
    def _extract_brief_summary(self, strategy_text: str, boss_name: str = None) -> str:
        """Extract a brief, actionable one-sentence summary from the full strategy."""
        lines = strategy_text.split('\n')
        
        # Look for the most actionable advice - prioritize Card Priorities and Short-Term sections
        # These sections tend to have the most concrete, immediate actions
        priority_bullets = []
        short_term_bullets = []
        boss_bullets = []
        other_bullets = []
        
        current_section = None
        
        for line in lines:
            line_stripped = line.strip()
            line_lower = line_stripped.lower()
            
            # Track which section we're in
            if 'card' in line_lower and 'priorit' in line_lower:
                current_section = 'priorities'
                continue
            elif 'short' in line_lower and 'term' in line_lower:
                current_section = 'short'
                continue
            elif 'boss' in line_lower and ('tactics' in line_lower or 'strategy' in line_lower):
                current_section = 'boss'
                continue
            elif 'long' in line_lower and 'term' in line_lower:
                current_section = 'long'
                continue
            
            # Extract meaningful bullet points
            if line_stripped.startswith(('-', '•', '*')) and len(line_stripped) > 20:
                bullet = line_stripped.lstrip('-•* ').strip()
                
                if current_section == 'priorities':
                    priority_bullets.append(bullet)
                elif current_section == 'short':
                    short_term_bullets.append(bullet)
                elif current_section == 'boss':
                    boss_bullets.append(bullet)
                else:
                    other_bullets.append(bullet)
        
        # Choose the best bullet to speak
        # Priority: Card Priorities > Short-Term > Boss-specific > Other
        chosen_bullet = None
        
        if priority_bullets:
            # Look for the first "prioritize" or "focus" bullet
            for bullet in priority_bullets:
                if 'prioritiz' in bullet.lower() or 'focus' in bullet.lower() or 'look for' in bullet.lower():
                    chosen_bullet = bullet
                    break
            if not chosen_bullet:
                chosen_bullet = priority_bullets[0]
        elif short_term_bullets:
            # Look for actionable short-term fixes
            for bullet in short_term_bullets:
                if 'need' in bullet.lower() or 'lack' in bullet.lower() or 'add' in bullet.lower():
                    chosen_bullet = bullet
                    break
            if not chosen_bullet:
                chosen_bullet = short_term_bullets[0]
        elif boss_bullets:
            chosen_bullet = boss_bullets[0]
        elif other_bullets:
            chosen_bullet = other_bullets[0]
        
        # Clean up and truncate if needed
        if chosen_bullet:
            # Remove markdown formatting
            chosen_bullet = chosen_bullet.replace('**', '').replace('*', '')
            chosen_bullet = chosen_bullet.replace('__', '').replace('_', '')
            
            # Remove redundant phrases
            chosen_bullet = chosen_bullet.replace('You should ', '').replace('Try to ', '')
            chosen_bullet = chosen_bullet.replace('It would be good to ', '').replace('Consider ', '')
            
            # Capitalize first letter
            if chosen_bullet:
                chosen_bullet = chosen_bullet[0].upper() + chosen_bullet[1:]
            
            # Truncate if too long
            if len(chosen_bullet) > 120:
                chosen_bullet = chosen_bullet[:120].rsplit(' ', 1)[0] + '...'
            
            return chosen_bullet
        
        # Fallback: extract something useful from boss context
        if boss_name:
            # Try to find a specific tactic
            for line in lines[:15]:  # Check first 15 lines
                if line.strip().startswith(('-', '•', '*')) and boss_name.lower() in line.lower():
                    bullet = line.strip().lstrip('-•* ').strip()
                    if len(bullet) > 30 and len(bullet) < 120:
                        return bullet
            return f"Review the boss tactics for {boss_name} in the summary file."
        
        return "Check the run summary file for detailed strategy."
    
    def _update_run_summary_strategy(self, run: dict, strategy_text: str, boss_name: str = None):
        """Update the run summary file with new strategy sections."""
        filename = f"run_summary_{run['character']}_A{run['ascension']}.md"
        filepath = Path(filename)
        
        if not filepath.exists():
            # Create summary if it doesn't exist
            self.create_summary_file(silent=True)
        
        # Read existing summary
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse strategy text to extract meaningful sections
        lines = strategy_text.split('\n')
        
        # Extract sections more robustly
        sections = {
            'boss': [],
            'long': [],
            'short': [],
            'priorities': []
        }
        current_section = None
        
        for line in lines:
            line_stripped = line.strip()
            line_lower = line_stripped.lower()
            
            # Detect bullets more precisely: single -, •, or * followed by space
            is_bullet = (line_stripped.startswith('- ') or 
                        line_stripped.startswith('• ') or 
                        (line_stripped.startswith('* ') and not line_stripped.startswith('** ')))
            
            # Detect section headers (not bullets, may have ** or ##)
            if not is_bullet:
                if ('boss' in line_lower and ('tactics' in line_lower or 'strategy' in line_lower or 'fight' in line_lower)) or (line_lower.startswith('1') and 'boss' in line_lower):
                    current_section = 'boss'
                    continue
                elif ('long' in line_lower and 'term' in line_lower) or (line_lower.startswith('2') and ('long' in line_lower or 'goal' in line_lower)):
                    current_section = 'long'
                    continue
                elif ('short' in line_lower and 'term' in line_lower) or (line_lower.startswith('3') and ('short' in line_lower or 'problem' in line_lower)):
                    current_section = 'short'
                    continue
                elif ('card' in line_lower and 'priorit' in line_lower) or (line_lower.startswith('4') and ('card' in line_lower or 'priorit' in line_lower)):
                    current_section = 'priorities'
                    continue
            
            # Skip empty lines
            if not line_stripped:
                continue
            
            # Skip markdown headers (but we already extracted section info above)
            if line_stripped.startswith('#') and not is_bullet:
                continue
            
            # Add content to current section
            if current_section and line_stripped:
                # Clean up and add content
                if is_bullet:
                    sections[current_section].append(line_stripped)
                elif len(line_stripped) > 15 and not line_stripped.endswith(':') and not line_stripped.startswith('**'):  # Avoid headers and single words
                    # Add as bullet if it looks like content (but not markdown bold headers)
                    sections[current_section].append('- ' + line_stripped)
        
        # Log what we extracted for debugging
        logger.info(f"📊 Strategy parsing: boss={len(sections['boss'])}, long={len(sections['long'])}, short={len(sections['short'])}, priorities={len(sections['priorities'])}")
        
        # Build formatted sections and update file
        import re
        
        # Update Boss Tactics section if we have boss info
        if boss_name and sections['boss']:
            boss_tactics_text = '\n'.join(sections['boss'])
            boss_section = f"""## Boss Tactics
**Fighting: {boss_name}**

{boss_tactics_text}
"""
            if '## Boss Tactics' in content:
                content = re.sub(
                    r'## Boss Tactics\n.*?(?=\n## |\Z)',
                    boss_section.rstrip() + '\n',
                    content,
                    flags=re.DOTALL
                )
            else:
                # Insert after Current Boss
                content = content.replace(
                    f'## Current Boss\n**{boss_name}**\n',
                    f'## Current Boss\n**{boss_name}**\n\n{boss_section}'
                )
        
        # Update Long-Term Goals
        if sections['long']:
            long_term_text = '\n'.join(sections['long'])
            long_section = f"""## Long-Term Goals
{long_term_text}
"""
            content = re.sub(
                r'## Long-Term Goals\n.*?(?=\n## |\Z)',
                long_section.rstrip() + '\n',
                content,
                flags=re.DOTALL
            )
        
        # Update Short-Term Problems
        if sections['short']:
            short_term_text = '\n'.join(sections['short'])
            short_section = f"""## Short-Term Problems
{short_term_text}
"""
            content = re.sub(
                r'## Short-Term Problems\n.*?(?=\n## |\Z)',
                short_section.rstrip() + '\n',
                content,
                flags=re.DOTALL
            )
        
        # Update Card Priorities
        if sections['priorities']:
            priorities_text = '\n'.join(sections['priorities'])
            priorities_section = f"""## Card Priorities
{priorities_text}
"""
            # Check if section exists
            if '## Card Priorities' in content:
                content = re.sub(
                    r'## Card Priorities\n.*?(?=\n## |\Z)',
                    priorities_section.rstrip() + '\n',
                    content,
                    flags=re.DOTALL
                )
            else:
                # Insert before Detected Archetype Tendencies or Recent Events
                if '## Detected Archetype Tendencies' in content:
                    content = content.replace(
                        '## Detected Archetype Tendencies',
                        priorities_section + '\n## Detected Archetype Tendencies'
                    )
                elif '## Recent Events' in content:
                    content = content.replace(
                        '## Recent Events',
                        priorities_section + '\n## Recent Events'
                    )
        
        # Write updated summary
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        total_items = len(sections['boss']) + len(sections['long']) + len(sections['short']) + len(sections['priorities'])
        logger.info(f"✅ Updated {filename} with {total_items} strategy items")

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

    def advise_card_upgrade(self) -> str:
        """Advise which card to upgrade at a campfire or shop."""
        run = self.run_manager.get_active_run()
        if not run:
            return "No active run."
        
        deck = self.run_manager.get_full_deck(run)
        if not deck:
            return "Your deck is empty."
        
        # Build a focused prompt for card upgrade advice
        deck_summary = format_deck_counts(deck)
        
        prompt = f"""I can upgrade a card. Which card should I upgrade?

My deck: {deck_summary}

Consider:
- Upgraded cards are generally stronger (more damage, more block, lower cost, better effects)
- Prioritize cards I'll play often (attacks, key powers, core combo pieces)
- Cards with bigger upgrade gains (e.g., Searing Blow scales infinitely, Whirlwind becomes Whirlwind+)
- My current relics and synergies
- What boss I'm preparing for

Recommend ONE card to upgrade and explain why in 1-2 sentences."""
        
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
        
        # Set boss in run manager
        self.run_manager.set_boss(boss_name)
        
        # Automatically generate comprehensive strategy for this boss
        self.adjust_strategy(silent=True, boss_focus=True)
        
        # Create/update run summary file
        self.create_run_summary(run, silent=True)
        
        return f"Boss set to {boss_name}. Strategy updated in run summary file."
    
    def lookup_card(self, card_name: str) -> str:
        """Look up card info."""
        info = self.kb.get_card_info(card_name)
        return info or f"Card '{card_name}' not found."
