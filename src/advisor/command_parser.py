"""
Command parser using fast LLM for intent classification and entity extraction.

Uses llama-3.1-8b-instant (14,400 requests/day) to:
1. Classify user intent (question vs command)
2. Extract entities (card names, numbers)
3. Normalize misspelled names from speech-to-text
"""

import os
import json
from typing import Optional, Dict, Any
from groq import Groq
from dotenv import load_dotenv
from loguru import logger

load_dotenv()


class CommandParser:
    """Fast command parser using llama-3.1-8b-instant."""
    
    SYSTEM_PROMPT = """You are a command parser for a Slay the Spire voice assistant.
Your job is to classify user intent and extract entities.

RESPOND ONLY WITH JSON, no other text.

INTENTS:
- "card_choice": User is asking which card to pick from MULTIPLE options (at least 2 cards)
- "card_removal": User is at a card removal event (shop, event) and wants advice on which card to REMOVE from their deck
- "followup": User is asking a follow-up question about a previous choice (e.g., "why not X?", "what about Y?", "explain your reasoning")
- "add_card": User explicitly says they picked/added/took a specific card
- "remove_card": User manually removes a card from tracking (already decided)
- "add_relic": User got a new relic
- "start_run": User wants to start a NEW run (keywords: "start", "new run", "begin")
- "update_run": User is describing/correcting their CURRENT run parameters (character, ascension, max HP)
- "end_run": User's run ended (died or won)
- "status": User asks about current run status
- "set_boss": User is telling you which boss they're facing
- "update_floor": User moved to a new floor
- "update_hp": User is updating their current HP (not max HP)
- "update_gold": User is updating their gold amount
- "get_strategy": User wants to see current strategy notes (just display, no AI reasoning)
- "adjust_strategy": User wants AI to analyze run and adjust/suggest strategy (keywords: "adjust", "update", "reconsider", "rethink", "suggest strategy")
- "clear_strategy": User wants to clear all strategy notes
- "question": General strategic question
- "unknown": Can't determine intent

IMPORTANT DISTINCTIONS:
- "should I pick A, B, or C?" → card_choice (multiple options)
- "I can remove a card from my deck" → card_removal (at removal event)
- "which card should I remove?" → card_removal (wants advice on removal)
- "at the shop, can remove a card" → card_removal
- "I removed Strike" → remove_card (already decided, just tracking)
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

CARD NAME CORRECTIONS (speech-to-text errors):
- "workri", "warcri", "war cry" -> "Warcry"
- "pommel", "pommel strike" -> "Pommel Strike"
- "pummel" -> "Pummel" (DIFFERENT card - deals damage 4 times, exhausts)
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

OUTPUT FORMAT:
{
  "intent": "card_choice|add_card|remove_card|add_relic|start_run|update_run|end_run|status|set_boss|update_floor|update_hp|update_gold|question|unknown",
  "cards": ["Card Name 1", "Card Name 2"],  // Corrected card names
  "relics": ["Relic Name"],
  "character": "ironclad|silent|defect|watcher|null",
  "ascension": null or number,
  "floor": null or number,
  "hp": null or number,  // ABSOLUTE current HP
  "hp_delta": null or number,  // RELATIVE change to current HP (positive=heal, negative=damage)
  "max_hp": null or number,  // ABSOLUTE max HP
  "max_hp_delta": null or number,  // RELATIVE change to max HP (positive=gained, negative=lost)
  "gold": null or number,  // Current gold amount
  "boss": "Boss Name" or null,
  "victory": true/false/null,
  "original_query": "the user's original message for context"
}

EXAMPLES:

User: "The next card to pick is shrug it off, pommel or workri"
{"intent": "card_choice", "cards": ["Shrug It Off", "Pommel Strike", "Warcry"], "original_query": "The next card to pick is shrug it off, pommel or workri"}

User: "I picked up rage"
{"intent": "add_card", "cards": ["Rage"], "original_query": "I picked up rage"}

User: "Should I take anger or cleave?"
{"intent": "card_choice", "cards": ["Anger", "Cleave"], "original_query": "Should I take anger or cleave?"}

User: "Why not Warcry?"
{"intent": "followup", "cards": ["Warcry"], "original_query": "Why not Warcry?"}

User: "What about the other cards?"
{"intent": "followup", "cards": [], "original_query": "What about the other cards?"}

User: "Why did you recommend that?"
{"intent": "followup", "cards": [], "original_query": "Why did you recommend that?"}

User: "And what about Pummel?"
{"intent": "followup", "cards": ["Pummel"], "original_query": "And what about Pummel?"}

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

User: "I died to the guardian"
{"intent": "end_run", "victory": false, "boss": "The Guardian", "original_query": "I died to the guardian"}

User: "Boss is slime boss"
{"intent": "set_boss", "boss": "Slime Boss", "original_query": "Boss is slime boss"}

User: "What's good against time eater?"
{"intent": "question", "boss": "Time Eater", "original_query": "What's good against time eater?"}

User: "I can remove a card from my deck, which should I remove?"
{"intent": "card_removal", "original_query": "I can remove a card from my deck, which should I remove?"}

User: "At the shop, should I remove a card?"
{"intent": "card_removal", "original_query": "At the shop, should I remove a card?"}

User: "Which card should I remove from my deck?"
{"intent": "card_removal", "original_query": "Which card should I remove from my deck?"}

User: "Card removal event, what do I remove?"
{"intent": "card_removal", "original_query": "Card removal event, what do I remove?"}

User: "I removed a Strike"
{"intent": "remove_card", "cards": ["Strike"], "original_query": "I removed a Strike"}"""

    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not found")
        
        self.client = Groq(api_key=api_key)
        self.model = "llama-3.1-8b-instant"
        logger.info(f"Command parser initialized with {self.model}")
    
    def parse(self, user_input: str) -> Dict[str, Any]:
        """Parse user input and return structured command."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": user_input}
                ],
                temperature=0.1,  # Low temp for consistent parsing
                max_completion_tokens=500,
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Try to extract JSON from response
            # Sometimes model wraps in markdown code blocks
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0]
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0]
            
            result = json.loads(result_text)
            result["original_query"] = user_input
            
            logger.debug(f"Parsed command: {result}")
            return result
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON: {e}, raw: {result_text}")
            return {
                "intent": "question",
                "original_query": user_input,
                "cards": [],
                "relics": []
            }
        except Exception as e:
            logger.error(f"Command parser error: {e}")
            return {
                "intent": "unknown",
                "original_query": user_input,
                "error": str(e)
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
