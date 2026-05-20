"""
LLM Name Corrector for Slay the Spire.

Uses Groq API with 4-model fallback chain to correct misspelled card/relic names
from voice transcription.
"""

import json
import threading
from typing import List, Dict, Optional, Tuple
from groq import Groq
from rapidfuzz import fuzz, process
from src.core.config import Config
from src.knowledge.knowledge_base import KnowledgeBase
from src.utils.logger import setup_logger, log_operation

# Initialize logger for this module
log = setup_logger("llm")


class NameCorrector:
    """Corrects card/relic names using LLM with 4-model fallback."""
    
    def __init__(
        self,
        knowledge_base: Optional[KnowledgeBase] = None,
        api_key: Optional[str] = None
    ):
        """
        Initialize name corrector.
        
        Args:
            knowledge_base: KnowledgeBase instance (creates new if None)
            api_key: Groq API key (default: from Config)
        """
        self.kb = knowledge_base or KnowledgeBase()
        self.api_key = api_key or Config.GROQ_API_KEY
        
        if not self.api_key:
            raise ValueError("GROQ_API_KEY not found in environment")
        
        self.client = Groq(api_key=self.api_key)
        self.models = Config.LLM_MODELS  # 4-model fallback chain
        self.timeout = Config.LLM_TIMEOUT
        
        # Track which primary model to use next (alternates between first two)
        self.next_primary_index = 0
        
        log.info("NameCorrector initialized")
        log_operation(log, "corrector_init", {
            "models": " → ".join(self.models),
            "timeout": f"{self.timeout}s"
        })
    
    def correct_names(
        self,
        transcribed_text: str,
        character: str,
        include_relics: bool = True
    ) -> Tuple[List[str], List[str]]:
        """
        Correct card/relic names from transcribed text.
        
        Args:
            transcribed_text: Text from voice transcription
            character: Character class (ironclad, silent, defect, watcher)
            include_relics: Whether to include relics in matching
            
        Returns:
            Tuple of (card_names, relic_names)
        """
        log.info(f"Correcting names from transcription")
        log_operation(log, "correct_names_start", {
            "text_length": len(transcribed_text),
            "character": character,
            "text_preview": transcribed_text[:100]
        })
        
        # Get available cards (exclude STATUS/CURSE) and relics
        available_cards = self.kb.get_choosable_cards_for_character(character)
        available_relics = self.kb.get_all_relics() if include_relics else []
        
        # Build prompt
        prompt = self._build_correction_prompt(
            transcribed_text,
            available_cards,
            available_relics
        )
        
        # Try models with fallback
        result = self._try_models_with_fallback(prompt)
        
        if result is None:
            log.error("All models failed to correct names")
            log_operation(log, "correct_names_failed", {
                "text": transcribed_text
            }, level="ERROR")
            return ([], [])
        
        # Parse result
        cards, relics = self._parse_correction_result(result)
        
        # Fallback: Use fuzzy matching for unmatched words
        cards, relics = self._fuzzy_fallback(
            transcribed_text,
            cards,
            relics,
            available_cards,
            available_relics
        )
        
        log.info(f"Name correction complete")
        log_operation(log, "correct_names_complete", {
            "cards_found": len(cards),
            "relics_found": len(relics),
            "cards": ", ".join(cards[:5]) if cards else "none",
            "relics": ", ".join(relics[:3]) if relics else "none"
        })
        
        return (cards, relics)
    
    def _build_correction_prompt(
        self,
        text: str,
        available_cards: List[str],
        available_relics: List[str]
    ) -> str:
        """Build the LLM prompt for name correction."""
        prompt = f"""You are a Slay the Spire card/relic name matcher. The user spoke card/relic names via voice, which were transcribed (possibly with errors).

TRANSCRIBED TEXT:
"{text}"

AVAILABLE CARDS:
{json.dumps(available_cards, indent=2)}

AVAILABLE RELICS:
{json.dumps(available_relics, indent=2)}

CRITICAL FUZZY MATCHING RULES:
1. "wrath" sounds like "wreath" - ALWAYS check for "Wreath of Flame" when you see "wrath of flame"
2. Single letter differences matter: "wrath" vs "wreath" (one letter 'e' difference)
3. Check EVERY word in the transcription - users often say multiple card names separated by commas
4. Use AGGRESSIVE fuzzy matching for speech-to-text errors:
   - "wrath of flame" → "Wreath of Flame" (wrath/wreath sound similar!)
   - "third eye wrath of flame weave" → ["Third Eye", "Wreath of Flame", "Weave"]
   - "study" → "Study"
   - "wheel kick" → "Wheel Kick"
   - "battle him" → "Battle Hymn"
5. Handle capitalization differences ("third eye" → "Third Eye")
6. Handle word variations ("a thousand cuts" → "A Thousand Cuts")
7. Only return names from the available lists above
8. Return ALL matches you find - don't stop at the first one

COMMON MISTAKES TO AVOID:
- "wrath" is NOT the same as "Wrath" stance - it's likely "Wreath of Flame" card
- Always check if a spoken word could be a slight mispronunciation

EXAMPLES:
- "Third Eye, Wrath of Flame, Weave" → {{"cards": ["Third Eye", "Wreath of Flame", "Weave"], "relics": []}}
- "wheel kick study wrath of flame" → {{"cards": ["Wheel Kick", "Study", "Wreath of Flame"], "relics": []}}
- "strike defend" → {{"cards": ["Strike", "Defend"], "relics": []}}
- "wrath of flame" → {{"cards": ["Wreath of Flame"], "relics": []}}

OUTPUT FORMAT (JSON only):
{{
  "cards": ["Exact Card Name 1", "Exact Card Name 2"],
  "relics": ["Exact Relic Name 1"]
}}

Return ONLY valid JSON matching the format above. No explanations."""
        
        return prompt
    
    def _try_models_with_fallback(self, prompt: str) -> Optional[str]:
        """
        Try models in order with fallback.
        
        First two models alternate, then fall back to tier 3 and 4.
        
        Args:
            prompt: LLM prompt
            
        Returns:
            LLM response text, or None if all models fail
        """
        # Determine primary models to try (alternate between first two)
        primary_1 = self.models[self.next_primary_index]
        primary_2 = self.models[1 - self.next_primary_index]
        
        # Alternate for next request
        self.next_primary_index = 1 - self.next_primary_index
        
        # Full model sequence: two primaries (alternating), then tier 3, then tier 4
        model_sequence = [primary_1, primary_2] + self.models[2:]
        
        log.debug(f"Model sequence: {' → '.join(model_sequence)}")
        
        for i, model in enumerate(model_sequence):
            log.debug(f"Trying model {i+1}/{len(model_sequence)}: {model}")
            
            result = self._call_model_with_timeout(model, prompt)
            
            if result is not None:
                log.info(f"Model {model} succeeded")
                log_operation(log, "model_success", {
                    "model": model,
                    "attempt": i + 1,
                    "response_length": len(result)
                })
                return result
            else:
                log.warning(f"Model {model} failed or timed out")
        
        # All models failed
        log.error("All models failed")
        return None
    
    def _call_model_with_timeout(self, model: str, prompt: str) -> Optional[str]:
        """
        Call LLM model with timeout using threading.
        
        Args:
            model: Model name
            prompt: LLM prompt
            
        Returns:
            Model response, or None if timeout/error
        """
        result = {"response": None, "error": None}
        
        def api_call():
            try:
                response = self.client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "You are a JSON-only response bot."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0,
                    max_tokens=500,
                    response_format={"type": "json_object"}
                )
                result["response"] = response.choices[0].message.content
            except Exception as e:
                result["error"] = str(e)
        
        # Start API call in thread
        thread = threading.Thread(target=api_call)
        thread.daemon = True
        thread.start()
        
        # Wait for timeout
        thread.join(timeout=self.timeout)
        
        # Check if thread finished
        if thread.is_alive():
            log.warning(f"Model {model} timed out after {self.timeout}s")
            return None
        
        # Check for errors
        if result["error"]:
            log.warning(f"Model {model} error: {result['error']}")
            return None
        
        return result["response"]
    
    def _parse_correction_result(self, response: str) -> Tuple[List[str], List[str]]:
        """
        Parse LLM response to extract card and relic names.
        
        Checks both card and relic pools for each name to handle LLM mis-categorization.
        
        Args:
            response: JSON response from LLM
            
        Returns:
            Tuple of (cards, relics)
        """
        try:
            data = json.loads(response)
            llm_cards = data.get("cards", [])
            llm_relics = data.get("relics", [])
            
            validated_cards = []
            validated_relics = []
            
            # Validate "cards" - check cards first, then relics if not found
            for name in llm_cards:
                if self.kb.get_card_data(name):
                    validated_cards.append(name)
                elif self.kb.get_relic_data(name):
                    # LLM mis-categorized a relic as a card
                    log.debug(f"Reclassified '{name}' from card to relic")
                    validated_relics.append(name)
                else:
                    log.debug(f"Not found in KB: {name}")
            
            # Validate "relics" - check relics first, then cards if not found
            for name in llm_relics:
                if self.kb.get_relic_data(name):
                    validated_relics.append(name)
                elif self.kb.get_card_data(name):
                    # LLM mis-categorized a card as a relic
                    log.debug(f"Reclassified '{name}' from relic to card")
                    validated_cards.append(name)
                else:
                    log.debug(f"Not found in KB: {name}")
            
            return (validated_cards, validated_relics)
            
        except json.JSONDecodeError as e:
            log.error(f"Failed to parse JSON response: {e}")
            log.debug(f"Response was: {response[:200]}...")
            return ([], [])
        except Exception as e:
            log.error(f"Failed to parse correction result: {e}")
            return ([], [])
    
    def _fuzzy_fallback(
        self,
        transcribed_text: str,
        llm_cards: List[str],
        llm_relics: List[str],
        available_cards: List[str],
        available_relics: List[str],
        threshold: int = 70
    ) -> Tuple[List[str], List[str]]:
        """
        Fuzzy match fallback for items LLM might have missed.
        
        Checks if any words in transcription weren't matched, then tries fuzzy matching.
        
        Args:
            transcribed_text: Original transcription
            llm_cards: Cards found by LLM
            llm_relics: Relics found by LLM
            available_cards: All available card names
            available_relics: All available relic names
            threshold: Minimum fuzzy match score (0-100), default 70
            
        Returns:
            Updated (cards, relics) with fallback matches added
        """
        import string
        
        # Clean transcription: lowercase, remove punctuation
        cleaned_text = transcribed_text.lower()
        cleaned_text = cleaned_text.translate(str.maketrans('', '', string.punctuation))
        
        # Extract words from cleaned transcription
        transcribed_words = set(cleaned_text.split())
        
        # Extract words from matched items
        matched_words = set()
        for item in llm_cards + llm_relics:
            matched_words.update(item.lower().split())
        
        # Find unmatched words
        unmatched_words = transcribed_words - matched_words
        
        if not unmatched_words:
            log.debug("All words matched by LLM, no fallback needed")
            return (llm_cards, llm_relics)
        
        log.debug(f"Unmatched words: {unmatched_words}")
        
        # Try to match unmatched portions to cards/relics
        fallback_cards = list(llm_cards)
        fallback_relics = list(llm_relics)
        
        # Build multi-word queries from unmatched words
        # Try as sorted list to maintain some order
        unmatched_list = sorted(list(unmatched_words))
        unmatched_text = " ".join(unmatched_list)
        
        log.debug(f"Trying multi-word match with: '{unmatched_text}'")
        
        # Try matching against cards with LOWER threshold for multi-word phrases
        if available_cards:
            card_matches = process.extract(
                unmatched_text,
                available_cards,
                scorer=fuzz.token_sort_ratio,
                limit=5
            )
            
            log.debug(f"Top card matches: {[(name, score) for name, score, _ in card_matches[:3]]}")
            
            for match_name, score, _ in card_matches:
                if score >= 60 and match_name not in fallback_cards:  # Lowered to 60 for multi-word
                    log.info(f"Fuzzy match (card): '{unmatched_text}' → '{match_name}' (score: {score})")
                    fallback_cards.append(match_name)
                    break  # Only add the best multi-word match
        
        # Try matching against relics
        if available_relics:
            relic_matches = process.extract(
                unmatched_text,
                available_relics,
                scorer=fuzz.token_sort_ratio,
                limit=5
            )
            
            log.debug(f"Top relic matches: {[(name, score) for name, score, _ in relic_matches[:3]]}")
            
            for match_name, score, _ in relic_matches:
                if score >= 60 and match_name not in fallback_relics:  # Lowered to 60 for multi-word
                    log.info(f"Fuzzy match (relic): '{unmatched_text}' → '{match_name}' (score: {score})")
                    fallback_relics.append(match_name)
                    break  # Only add the best multi-word match
        
        # Also try individual unmatched words
        for word in unmatched_words:
            if len(word) < 4:  # Skip short words (was 3, now 4)
                continue
            
            # Try cards
            if available_cards:
                best_card = process.extractOne(
                    word,
                    available_cards,
                    scorer=fuzz.ratio  # Changed from partial_ratio to ratio (more strict)
                )
                if best_card and best_card[1] >= 85 and best_card[0] not in fallback_cards:  # Increased threshold
                    log.info(f"Fuzzy match (card): '{word}' → '{best_card[0]}' (score: {best_card[1]})")
                    fallback_cards.append(best_card[0])
            
            # Try relics
            if available_relics:
                best_relic = process.extractOne(
                    word,
                    available_relics,
                    scorer=fuzz.ratio  # Changed from partial_ratio to ratio (more strict)
                )
                if best_relic and best_relic[1] >= 85 and best_relic[0] not in fallback_relics:  # Increased threshold
                    log.info(f"Fuzzy match (relic): '{word}' → '{best_relic[0]}' (score: {best_relic[1]})")
                    fallback_relics.append(best_relic[0])
        
        added_cards = len(fallback_cards) - len(llm_cards)
        added_relics = len(fallback_relics) - len(llm_relics)
        
        if added_cards > 0 or added_relics > 0:
            log.info(f"Fuzzy fallback added {added_cards} cards, {added_relics} relics")
        
        return (fallback_cards, fallback_relics)


if __name__ == "__main__":
    # Test the name corrector
    from datetime import datetime
    
    print("LLM Name Corrector Test")
    print("=" * 50)
    
    # Initialize corrector
    try:
        corrector = NameCorrector()
        print("\n1. NameCorrector initialized")
        print(f"   Models: {' → '.join(corrector.models)}")
        print(f"   Timeout: {corrector.timeout}s per model")
    except ValueError as e:
        print(f"\n❌ Failed to initialize: {e}")
        exit(1)
    
    # Test with various transcription errors
    test_cases = [
        ("I want shrug it off and pommel strike", "ironclad"),
        ("battle him and third eye", "watcher"),
        ("dead branch relic", "ironclad"),
    ]
    
    for i, (text, character) in enumerate(test_cases, 1):
        print(f"\n{i}. Testing transcription: '{text}'")
        print(f"   Character: {character}")
        
        cards, relics = corrector.correct_names(text, character)
        
        print(f"   → Cards: {cards if cards else 'none'}")
        print(f"   → Relics: {relics if relics else 'none'}")
    
    print("\n" + "=" * 50)
    print(f"Logs written to: {Config.LOGS_DIR / datetime.now().strftime('%Y-%m-%d')}")
