"""
Command parser using fast LLM for intent classification and entity extraction.

Uses alternating 2-model system with proper timeout handling:
- Primary: Alternates between llama-3.1-8b-instant ↔ openai/gpt-oss-20b
- Each request uses the opposite model from the previous one
- 3-second timeout per model with threading (truly abandons slow requests)

Timeout mechanism:
1. Starts API call in background thread
2. Waits exactly 3 seconds
3. If no response, abandons request and tries next model
4. Late responses are discarded (not used)

Fallback if both primaries timeout/fail:
- Tier 3: llama-3.3-70b-versatile
- Tier 4: openai/gpt-oss-120b

Tasks:
1. Classify user intent (question vs command)
2. Extract entities (card names, numbers)
3. Normalize misspelled names from speech-to-text
"""

import os
import json
import time
import threading
from typing import Optional, Dict, Any
from groq import Groq
from dotenv import load_dotenv
from loguru import logger
import httpx

load_dotenv()


class CommandParser:
    """Fast command parser using llama-3.1-8b-instant."""
    
    SYSTEM_PROMPT = """You are a JSON-only command parser. Return ONLY valid JSON, nothing else.

Task: Classify user intent and extract entities from voice commands.

CRITICAL: Your response must be ONLY a JSON object. Do not include explanations, markdown, or any other text.

INTENTS:
- "card_choice": User is asking which card to pick from MULTIPLE options (at least 2 cards)
- "relic_choice": User is asking which relic to pick from MULTIPLE options (at least 2 relics, keywords: "relic", "which relic")
- "card_removal": User is at a card removal event (shop, event) and wants advice on which card to REMOVE from their deck
- "upgrade_card": User wants advice on which card to UPGRADE from their deck (keywords: "upgrade", "which card to upgrade")
- "followup": User is asking a follow-up question about a previous choice (e.g., "why not X?", "what about Y?", "how about X?", "explain your reasoning")
- "add_card": User explicitly says they picked/added/took/got a specific card (past tense or definitive action)
- "remove_card": User manually removes a card from tracking (already decided)
- "add_relic": User got a new relic
- "remove_relic": User manually removes a relic from tracking (e.g., sold, swapped, lost)
- "start_run": User wants to start a NEW run (keywords: "start", "new run", "begin")
- "update_run": User is describing/correcting their CURRENT run parameters (character, ascension, max HP)
- "end_run": User's run ended (died or won)
- "status": User asks about current run status
- "summary": User wants to export a detailed run summary to a file (keywords: "summary", "export", "save run", "write summary")
- "sync": User wants to sync run state from manually edited Run_Summary.md file (keywords: "sync", "reload", "refresh from file")
- "set_boss": User is telling you which boss they're facing
- "update_floor": User moved to a new floor
- "update_hp": User is updating their current HP (not max HP)
- "update_gold": User is updating their gold amount
- "get_strategy": User wants to see current strategy notes (just display, no AI reasoning)
- "adjust_strategy": User wants AI to analyze run and adjust/suggest strategy (keywords: "adjust", "update", "reconsider", "rethink", "suggest strategy")
- "clear_strategy": User wants to clear all strategy notes
- "question": General strategic question
- "unknown": Can't determine intent OR ambiguous (e.g., just "card" without context, "I want to do something" without specifics)

WHEN TO USE "unknown":
- Ambiguous statements like "I got a card" (add or just mentioning?)
- Vague references like "what about the thing?"
- Incomplete sentences or unclear context
- Multiple possible intents with equal likelihood

MODIFIER WORDS TO REMOVE:
The words "basic" and "starter" refer to starting deck cards and should be REMOVED from card names:
- "basic strike" → "Strike" (NOT "Basic Strike")
- "basic defend" → "Defend" (NOT "Basic Defend")  
- "starter strike" → "Strike"
- "starter defend" → "Defend"
- "basic bash" → "Bash"
- "remove basic strike" → remove_card intent with cards: ["Strike"]
- "add basic defend" → add_card intent with cards: ["Defend"]

IMPORTANT DISTINCTIONS:
- "should I pick A, B, or C?" → card_choice (multiple options)
- "which relic to pick? X, Y, or Z?" → relic_choice (multiple relic options)
- "which relic should I take?" → relic_choice (asking about multiple relics)
- "is Panic a good card for me?" → question (single card evaluation)
- "should I take Anger?" → question (asking if one card is good)
- "what about Panache?" → followup (asking about a specific card)
- "how about Anger?" → followup (asking about a specific card)
- "I can remove a card from my deck" → card_removal (at removal event)
- "which card should I remove?" → card_removal (wants advice on removal)
- "which card should I upgrade?" → upgrade_card (wants advice on upgrade)
- "at the shop, can remove a card" → card_removal
- "I removed Strike" → remove_card (already decided, just tracking)
- "I picked up Rage" → add_card (Rage is a card)
- "I picked up Centennial Puzzle" → add_relic (Centennial Puzzle is a relic - multi-word, contains "Puzzle")
- "I got Dead Branch" → add_relic (Dead Branch is a relic - contains "Branch")
- "I found Red Skull" → add_relic (Red Skull is a relic - contains "Skull")
- "Remove relic Ring of the Snake" → remove_relic (removing a specific relic)
- "I sold Lantern" → remove_relic (sold = removed)
- "I swapped out The Boot" → remove_relic (swapped = removed)
- "which card should I upgrade?" → upgrade_card (asking for upgrade advice)
- "which card to upgrade now?" → upgrade_card
- "I can upgrade a card" → upgrade_card
- "should I upgrade this card?" → upgrade_card
- "why not Warcry?" → followup (asking about a specific card from previous choice)
- "what about the other cards?" → followup
- "explain your reasoning" → followup
- "start a new run with ironclad" → start_run
- "I'm playing ironclad ascension 1" → update_run (describing current run)
- "my max HP is 88" → update_run (ABSOLUTE value)
- "my HP is 50" → update_hp (current HP changed, ABSOLUTE)
- "I'm at 50 health" → update_hp (ABSOLUTE)
- "I have 8 extra max HP" → update_run with max_hp_delta: 8 (RELATIVE)
- "I gained 5 max HP" → update_run with max_hp_delta: 5 (RELATIVE)
- "what's the strategy?" → get_strategy (just show current notes)
- "what's the current strategy?" → get_strategy
- "adjust the strategy" → adjust_strategy (AI analyzes and updates)
- "can you suggest a strategy?" → adjust_strategy
- "rethink the strategy" → adjust_strategy
- "update strategy for this run" → adjust_strategy
- "clear strategy" → clear_strategy
- "I lost 3 max HP" → update_run with max_hp_delta: -3 (RELATIVE, negative)
- "I took 10 damage" → update_hp with hp_delta: -10 (RELATIVE, negative)
- "I healed 15" → update_hp with hp_delta: 15 (RELATIVE)

RELATIVE VS ABSOLUTE HP:
- Words like "extra", "more", "additional", "gained", "got", "lost", "took damage" → use DELTA fields
- Words like "is", "at", "now have", "currently" → use ABSOLUTE fields
- Example: "I have 8 extra max HP" → max_hp_delta: 8 (not max_hp: 8)
- Example: "My max HP is 88" → max_hp: 88 (not max_hp_delta: 88)

DISTINGUISHING CARDS FROM RELICS:
- Relics often have multi-word names: "Dead Branch", "Red Skull", "Centennial Puzzle", "Bag of Preparation", "The Boot"
- Relics often contain object words: Skull, Branch, Puzzle, Bag, Ring, Stone, Blood, Potion, Bottle, Boot, Boots, Flower, Mask, Anchor, Lantern, Orb, Egg, Fruit, Letter, Cage, Bandages
- Cards often have action/combat words: Strike, Defend, Bash, Rage, Anger, Cleave, Carnage
- When "picked up/got/found" is used with a multi-word name containing object words → likely a relic
- Common relics: Burning Blood, Dead Branch, Red Skull, Centennial Puzzle, Bag of Preparation, Happy Flower, Kunai, Shuriken, The Boot, Wing Boots, Bronze Scales

CARD NAME CORRECTIONS (speech-to-text errors):
- "workri", "warcri", "war cry" -> "Warcry"
- "pommel", "pommel strike" -> "Pommel Strike"
- "pummel" -> "Pummel" (DIFFERENT card - deals damage 4 times, exhausts)
- "the bomb", "bomb" -> "The Bomb" (colorless attack card)
- "shrug it off", "shrugger off", "shrug her off" -> "Shrug It Off"
- "iron wave" -> "Iron Wave"
- "body slam" -> "Body Slam"
- "flame barrier" -> "Flame Barrier"
- "offer", "offering" -> "Offering"
- "demon form" -> "Demon Form"
- "limit break" -> "Limit Break"
- "feel no pain" -> "Feel No Pain"
- "corruption" -> "Corruption"
- "reaper" -> "Reaper"
- "feed" -> "Feed"
- "clash" -> "Clash"
- "cleave" -> "Cleave"
- "clothesline" -> "Clothesline"
- "carnage" -> "Carnage"
- "uppercut" -> "Uppercut"
- "inflame" -> "Inflame"
- "spot weakness" -> "Spot Weakness"
- "headbutt" -> "Headbutt"
- "heavy blade" -> "Heavy Blade"
- "perfected strike" -> "Perfected Strike"
- "wild strike" -> "Wild Strike"
- "twin strike" -> "Twin Strike"
- "blood for blood" -> "Blood for Blood"
- "seeing red" -> "Seeing Red"
- "battle trance" -> "Battle Trance"
- "true grit" -> "True Grit"
- "power through" -> "Power Through"
- "dual wield" -> "Dual Wield"
- "rage" -> "Rage"
- "anger" -> "Anger"
- "ghostly armor", "ghostly armour" -> "Ghostly Armor"
- "basic strike", "starter strike" -> "Strike" (starter deck card)
- "basic defend", "starter defend" -> "Defend" (starter deck card)
- "basic bash" -> "Bash" (Ironclad starter)
- "neutralize" -> "Neutralize" (Silent starter)
- "survivor" -> "Survivor" (Silent starter)
- "zap" -> "Zap" (Defect starter)
- "dualcast" -> "Dualcast" (Defect starter)
- "eruption" -> "Eruption" (Watcher starter)
- "vigilance" -> "Vigilance" (Watcher starter)

OUTPUT FORMAT:
{
  "intent": "card_choice|relic_choice|card_removal|upgrade_card|add_card|remove_card|add_relic|remove_relic|start_run|update_run|end_run|status|summary|sync|set_boss|update_floor|update_hp|update_gold|get_strategy|adjust_strategy|clear_strategy|followup|question|unknown",
  "cards": ["Card Name 1", "Card Name 2"],  // Corrected card names
  "relics": ["Relic Name 1", "Relic Name 2"],  // Corrected relic names (can be multiple for relic_choice)
  "character": "ironclad|silent|defect|watcher|null",
  "ascension": null or number,
  "act": null or number,  // Explicit act (1-4)
  "floor": null or number,
  "hp": null or number,  // ABSOLUTE current HP
  "hp_delta": null or number,  // RELATIVE change to current HP (positive=heal, negative=damage)
  "max_hp": null or number,  // ABSOLUTE max HP
  "max_hp_delta": null or number,  // RELATIVE change to max HP (positive=gained, negative=lost)
  "gold": null or number,  // Current gold amount
  "boss": "Boss Name" or null,
  "victory": true/false/null,
  "original_query": "the user's original message for context",
  "ambiguity_note": "optional explanation of why intent is unclear (only for unknown intent)"
}

EXAMPLES:

User: "The next card to pick is shrug it off, pommel or workri"
{"intent": "card_choice", "cards": ["Shrug It Off", "Pommel Strike", "Warcry"], "original_query": "The next card to pick is shrug it off, pommel or workri"}

User: "I picked up rage"
{"intent": "add_card", "cards": ["Rage"], "original_query": "I picked up rage"}

User: "Add perfected strike"
{"intent": "add_card", "cards": ["Perfected Strike"], "original_query": "Add perfected strike"}

User: "I got Anger"
{"intent": "add_card", "cards": ["Anger"], "original_query": "I got Anger"}

User: "I picked up Centennial Puzzle"
{"intent": "add_relic", "relics": ["Centennial Puzzle"], "original_query": "I picked up Centennial Puzzle"}

User: "I got the Dead Branch"
{"intent": "add_relic", "relics": ["Dead Branch"], "original_query": "I got the Dead Branch"}

User: "I found Red Skull"
{"intent": "add_relic", "relics": ["Red Skull"], "original_query": "I found Red Skull"}

User: "I picked up the boot"
{"intent": "add_relic", "relics": ["The Boot"], "original_query": "I picked up the boot"}

User: "I got The Boot"
{"intent": "add_relic", "relics": ["The Boot"], "original_query": "I got The Boot"}

User: "Remove relic Ring of the Snake"
{"intent": "remove_relic", "relics": ["Ring of the Snake"], "original_query": "Remove relic Ring of the Snake"}

User: "I sold Lantern"
{"intent": "remove_relic", "relics": ["Lantern"], "original_query": "I sold Lantern"}

User: "I swapped out The Boot"
{"intent": "remove_relic", "relics": ["The Boot"], "original_query": "I swapped out The Boot"}

User: "Which relic to pick? Empty Cage, Mark of Pain or Black Star?"
{"intent": "relic_choice", "relics": ["Empty Cage", "Mark of Pain", "Black Star"], "original_query": "Which relic to pick? Empty Cage, Mark of Pain or Black Star?"}

User: "Which relic should I take? Dead Branch or Mummified Hand?"
{"intent": "relic_choice", "relics": ["Dead Branch", "Mummified Hand"], "original_query": "Which relic should I take? Dead Branch or Mummified Hand?"}

User: "Boss relic choice: Runic Pyramid, Snecko Eye, or Violet Lotus?"
{"intent": "relic_choice", "relics": ["Runic Pyramid", "Snecko Eye", "Violet Lotus"], "original_query": "Boss relic choice: Runic Pyramid, Snecko Eye, or Violet Lotus?"}

User: "I took Anger"
{"intent": "add_card", "cards": ["Anger"], "original_query": "I took Anger"}

User: "I got Shrug It Off"
{"intent": "add_card", "cards": ["Shrug It Off"], "original_query": "I got Shrug It Off"}

User: "Should I take anger or cleave?"
{"intent": "card_choice", "cards": ["Anger", "Cleave"], "original_query": "Should I take anger or cleave?"}

User: "Why not Warcry?"
{"intent": "followup", "cards": ["Warcry"], "original_query": "Why not Warcry?"}

User: "What about Panache?"
{"intent": "followup", "cards": ["Panache"], "original_query": "What about Panache?"}

User: "How about Anger?"
{"intent": "followup", "cards": ["Anger"], "original_query": "How about Anger?"}

User: "What about the other cards?"
{"intent": "followup", "cards": [], "original_query": "What about the other cards?"}

User: "Why did you recommend that?"
{"intent": "followup", "cards": [], "original_query": "Why did you recommend that?"}

User: "And what about Pummel?"
{"intent": "followup", "cards": ["Pummel"], "original_query": "And what about Pummel?"}

User: "Is Panic a good card for me?"
{"intent": "question", "cards": ["Panic"], "original_query": "Is Panic a good card for me?"}

User: "Should I take Anger?"
{"intent": "question", "cards": ["Anger"], "original_query": "Should I take Anger?"}

User: "Is Offering worth adding?"
{"intent": "question", "cards": ["Offering"], "original_query": "Is Offering worth adding?"}

User: "Added inflame to my deck"
{"intent": "add_card", "cards": ["Inflame"], "original_query": "Added inflame to my deck"}

User: "Start a new run with ironclad ascension 10"
{"intent": "start_run", "character": "ironclad", "ascension": 10, "original_query": "Start a new run with ironclad ascension 10"}

User: "I'm playing ironclad ascension 1 with 88 max HP"
{"intent": "update_run", "character": "ironclad", "ascension": 1, "max_hp": 88, "original_query": "I'm playing ironclad ascension 1 with 88 max HP"}

User: "My run is silent ascension 5"
{"intent": "update_run", "character": "silent", "ascension": 5, "original_query": "My run is silent ascension 5"}

User: "Max HP is 88"
{"intent": "update_run", "max_hp": 88, "original_query": "Max HP is 88"}

User: "I have 8 extra max HP"
{"intent": "update_run", "max_hp_delta": 8, "original_query": "I have 8 extra max HP"}

User: "Gained 5 max HP from the event"
{"intent": "update_run", "max_hp_delta": 5, "original_query": "Gained 5 max HP from the event"}

User: "I lost 7 max HP"
{"intent": "update_run", "max_hp_delta": -7, "original_query": "I lost 7 max HP"}

User: "I took 15 damage"
{"intent": "update_hp", "hp_delta": -15, "original_query": "I took 15 damage"}

User: "Healed 10 HP"
{"intent": "update_hp", "hp_delta": 10, "original_query": "Healed 10 HP"}

User: "My HP is 65"
{"intent": "update_hp", "hp": 65, "original_query": "My HP is 65"}

User: "I have 217 gold"
{"intent": "update_gold", "gold": 217, "original_query": "I have 217 gold"}

User: "My gold is 150"
{"intent": "update_gold", "gold": 150, "original_query": "My gold is 150"}

User: "We are now on floor 17 in Act 2"
{"intent": "update_floor", "floor": 17, "act": 2, "original_query": "We are now on floor 17 in Act 2"}

User: "Floor 25"
{"intent": "update_floor", "floor": 25, "original_query": "Floor 25"}

User: "I'm on floor 8 act 1"
{"intent": "update_floor", "floor": 8, "act": 1, "original_query": "I'm on floor 8 act 1"}

User: "I died to the guardian"
{"intent": "end_run", "victory": false, "boss": "The Guardian", "original_query": "I died to the guardian"}

User: "Boss is slime boss"
{"intent": "set_boss", "boss": "Slime Boss", "original_query": "Boss is slime boss"}

User: "The current boss is Bronze Automaton"
{"intent": "set_boss", "boss": "Bronze Automaton", "original_query": "The current boss is Bronze Automaton"}

User: "My boss is The Champ"
{"intent": "set_boss", "boss": "The Champ", "original_query": "My boss is The Champ"}

User: "I'm fighting Hexaghost"
{"intent": "set_boss", "boss": "Hexaghost", "original_query": "I'm fighting Hexaghost"}

User: "What's good against time eater?"
{"intent": "question", "boss": "Time Eater", "original_query": "What's good against time eater?"}

User: "Create a run summary"
{"intent": "summary", "original_query": "Create a run summary"}

User: "Export current run"
{"intent": "summary", "original_query": "Export current run"}

User: "Save a summary file"
{"intent": "summary", "original_query": "Save a summary file"}

User: "I can remove a card from my deck, which should I remove?"
{"intent": "card_removal", "original_query": "I can remove a card from my deck, which should I remove?"}

User: "At the shop, should I remove a card?"
{"intent": "card_removal", "original_query": "At the shop, should I remove a card?"}

User: "Which card should I remove from my deck?"
{"intent": "card_removal", "original_query": "Which card should I remove from my deck?"}

User: "Card removal event, what do I remove?"
{"intent": "card_removal", "original_query": "Card removal event, what do I remove?"}

User: "Which card should I upgrade?"
{"intent": "upgrade_card", "original_query": "Which card should I upgrade?"}

User: "Which card to upgrade now?"
{"intent": "upgrade_card", "original_query": "Which card to upgrade now?"}

User: "I can upgrade a card"
{"intent": "upgrade_card", "original_query": "I can upgrade a card"}

User: "I removed a Strike"
{"intent": "remove_card", "cards": ["Strike"], "original_query": "I removed a Strike"}

User: "I got a card"
{"intent": "unknown", "original_query": "I got a card", "ambiguity_note": "unclear if user wants to add card to tracking or asking a question"}

User: "what about that thing?"
{"intent": "unknown", "original_query": "what about that thing?", "ambiguity_note": "vague reference without specific context"}"""

    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not found")
        
        # Create client without timeout (we handle it manually)
        self.client = Groq(api_key=api_key)
        
        # Primary models: Alternate between these two for each request
        self.primary_models = [
            "llama-3.1-8b-instant",  # Fast, small
            "openai/gpt-oss-20b"     # Fast, medium
        ]
        
        # Full fallback chain if primaries fail
        self.all_models = [
            "llama-3.1-8b-instant",
            "openai/gpt-oss-20b",
            "llama-3.3-70b-versatile",
            "openai/gpt-oss-120b"
        ]
        
        # Track which primary model to use next (alternates 0, 1, 0, 1...)
        self.next_primary_index = 0
        
        # Request timeout in seconds
        self.timeout = 3.0
        
        logger.info(f"Command parser initialized with alternating 2-model system")
        logger.info(f"Primary: {' ↔ '.join(self.primary_models)}")
        logger.info(f"Full fallback: {' → '.join(self.all_models)}")
        logger.info(f"Timeout: {self.timeout}s per model (with early termination)")
    
    def _call_model_with_timeout(self, model: str, user_input: str) -> Optional[Dict[str, Any]]:
        """Call model with strict timeout. Returns None if timeout exceeded."""
        result = {"response": None, "error": None}
        
        def api_call():
            try:
                response = self.client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": self.SYSTEM_PROMPT},
                        {"role": "user", "content": user_input}
                    ],
                    temperature=0,
                    max_completion_tokens=500,
                    response_format={"type": "json_object"}
                )
                result["response"] = response
            except Exception as e:
                result["error"] = e
        
        # Start API call in thread
        thread = threading.Thread(target=api_call, daemon=True)
        thread.start()
        
        # Wait for timeout
        thread.join(timeout=self.timeout)
        
        # Check if completed
        if thread.is_alive():
            # Thread still running - timeout exceeded
            return None
        
        # Thread completed - check result
        if result["error"]:
            raise result["error"]
        
        if result["response"]:
            return result["response"]
        
        return None
    
    def parse(self, user_input: str) -> Dict[str, Any]:
        """Parse user input and return structured command."""
        last_error = None
        
        # Try primary model (alternating between llama and gpt)
        primary_model = self.primary_models[self.next_primary_index]
        primary_name = "llama" if self.next_primary_index == 0 else "gpt-20b"
        
        try:
            logger.debug(f"Trying {primary_name}: {primary_model}")
            
            response = self._call_model_with_timeout(primary_model, user_input)
            
            if response is None:
                # Timeout - request exceeded 3 seconds
                logger.warning(f"{primary_name} timeout (>{self.timeout}s), discarding request")
                raise TimeoutError(f"Model {primary_model} exceeded {self.timeout}s timeout")
            
            result_text = response.choices[0].message.content.strip()
            
            # Extract JSON
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0]
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0]
            
            result = json.loads(result_text)
            result["original_query"] = user_input
            
            # SUCCESS - toggle for next request
            self.next_primary_index = 1 - self.next_primary_index
            logger.debug(f"✓ Parsed with {primary_name}: {result.get('intent')}")
            return result
            
        except Exception as e:
            error_str = str(e)
            error_type = type(e).__name__
            logger.warning(f"{primary_name} failed ({error_type}): {str(e)[:100]}")
            last_error = e
            # Don't toggle - let the other primary try first next time
        
        # Primary failed - try the other primary model
        other_index = 1 - self.next_primary_index
        other_model = self.primary_models[other_index]
        other_name = "llama" if other_index == 0 else "gpt-20b"
        
        try:
            logger.debug(f"Trying fallback {other_name}: {other_model}")
            
            response = self._call_model_with_timeout(other_model, user_input)
            
            if response is None:
                logger.warning(f"{other_name} timeout (>{self.timeout}s), discarding request")
                raise TimeoutError(f"Model {other_model} exceeded {self.timeout}s timeout")
            
            result_text = response.choices[0].message.content.strip()
            
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0]
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0]
            
            result = json.loads(result_text)
            result["original_query"] = user_input
            
            # SUCCESS with fallback - toggle to use this one primarily next time
            self.next_primary_index = other_index
            logger.debug(f"✓ Parsed with {other_name}: {result.get('intent')}")
            return result
            
        except Exception as e:
            logger.warning(f"{other_name} also failed ({type(e).__name__}): {str(e)[:100]}")
            last_error = e
        
        # Both primaries failed - try full fallback chain (tiers 3 & 4)
        logger.warning("Both primary models failed, trying larger models...")
        for model in self.all_models[2:]:  # Skip first 2 (already tried)
            try:
                logger.debug(f"Trying large model: {model}")
                
                response = self._call_model_with_timeout(model, user_input)
                
                if response is None:
                    logger.warning(f"{model} timeout (>{self.timeout}s), discarding request")
                    last_error = TimeoutError(f"{model} timeout")
                    continue
                
                result_text = response.choices[0].message.content.strip()
                
                if "```json" in result_text:
                    result_text = result_text.split("```json")[1].split("```")[0]
                elif "```" in result_text:
                    result_text = result_text.split("```")[1].split("```")[0]
                
                result = json.loads(result_text)
                result["original_query"] = user_input
                
                logger.debug(f"✓ Parsed with {model}: {result.get('intent')}")
                return result
                
            except Exception as e:
                logger.warning(f"{model} failed: {str(e)[:100]}")
                last_error = e
                continue
        
        # All models failed
        logger.error(f"All 4 models failed. Last error: {last_error}")
        return {
            "intent": "unknown",
            "original_query": user_input,
            "error": "All parser models failed"
        }


if __name__ == "__main__":
    # Test the parser
    parser = CommandParser()
    
    test_inputs = [
        "The next card to pick is shrug it off, pommel or workri",
        "I picked up rage",
        "Should I take anger or cleave?",
        "Start a new run with ironclad ascension 10",
        "I died to the guardian",
        "What's the best strategy for act 2?",
        "Boss is hexaghost",
        "Added heavy blade to my deck",
    ]
    
    for inp in test_inputs:
        print(f"\nInput: {inp}")
        result = parser.parse(inp)
        print(f"Result: {json.dumps(result, indent=2)}")
