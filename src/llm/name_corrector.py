"""
LLM Name Corrector for Slay the Spire.

Uses Groq API with 4-model fallback chain to correct misspelled card/relic names
from voice transcription.
"""

import json
import re
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
        
        # Try to detect and split concatenated words (e.g., "sashwhipplus" → "sash whip plus")
        transcribed_text = self._try_split_concatenated_words(
            transcribed_text,
            available_cards,
            available_relics
        )
        
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
            
            # Emergency fallback: Use fuzzy matching directly when all LLMs fail
            log.warning("Attempting emergency fuzzy fallback with lower threshold")
            cards, relics = self._fuzzy_fallback(
                transcribed_text,
                [],  # No LLM results
                [],
                available_cards,
                available_relics,
                threshold=75  # Lower threshold for emergency mode
            )
            
            if cards or relics:
                log.info(f"Emergency fallback found {len(cards)} cards, {len(relics)} relics")
                log_operation(log, "emergency_fallback_success", {
                    "cards_found": len(cards),
                    "relics_found": len(relics),
                    "cards": ", ".join(cards[:3]) if cards else "none"
                })
                return (cards, relics)
            
            return ([], [])
        
        # Parse result
        cards, relics = self._parse_correction_result(result)
        
        # Second pass: If there are unmatched words, try again with focused prompt
        unmatched_words = self._get_unmatched_words(transcribed_text, cards, relics)
        
        # Filter out very short words (1-2 chars) - they cause too many false matches
        unmatched_words = {w for w in unmatched_words if len(w) >= 3}
        
        if unmatched_words:
            log.info(f"Second pass: Attempting to match {len(unmatched_words)} unmatched words")
            log_operation(log, "second_pass_start", {
                "unmatched_words": ", ".join(sorted(unmatched_words)),
                "unmatched_count": len(unmatched_words)
            })
            
            # Build focused second-pass prompt
            second_pass_prompt = self._build_second_pass_prompt(
                unmatched_words,
                available_cards,
                available_relics,
                cards,
                relics
            )
            
            # Try models again with focused prompt
            second_result = self._try_models_with_fallback(second_pass_prompt)
            
            if second_result:
                second_cards, second_relics = self._parse_correction_result(second_result)
                
                # Validate second-pass matches: Only accept if they contain part of unmatched words
                validated_cards = []
                validated_relics = []
                
                for card in second_cards:
                    if card not in cards:
                        if self._validate_second_pass_match(card, unmatched_words):
                            validated_cards.append(card)
                            log.info(f"Second pass matched: {card}")
                        else:
                            log.debug(f"Second pass rejected (no substring match): {card}")
                
                # Safety check: If too many cards matched, something went wrong
                MAX_SECOND_PASS_MATCHES = 5
                if len(validated_cards) > MAX_SECOND_PASS_MATCHES:
                    log.warning(f"Second pass matched {len(validated_cards)} cards - too many! Likely over-matching.")
                    log.warning(f"Unmatched words were: {unmatched_words}")
                    log.warning(f"Rejecting all second-pass matches as likely false positives")
                    validated_cards = []
                
                # Add validated cards to results
                for card in validated_cards:
                    cards.append(card)
                
                for relic in second_relics:
                    if relic not in relics:
                        if self._validate_second_pass_match(relic, unmatched_words):
                            relics.append(relic)
                            validated_relics.append(relic)
                            log.info(f"Second pass matched: {relic}")
                        else:
                            log.debug(f"Second pass rejected (no substring match): {relic}")
                
                log_operation(log, "second_pass_complete", {
                    "new_cards": len(validated_cards),
                    "new_relics": len(validated_relics),
                    "rejected": (len(second_cards) - len(validated_cards)) + (len(second_relics) - len(validated_relics))
                })
            else:
                log.warning("Second pass failed - no response from LLM")
        
        # Final fallback: Use fuzzy matching for any still-unmatched words
        cards, relics = self._fuzzy_fallback(
            transcribed_text,
            cards,
            relics,
            available_cards,
            available_relics
        )
        
        # Deduplicate lists while preserving order
        cards = list(dict.fromkeys(cards))
        relics = list(dict.fromkeys(relics))
        
        log.info(f"Name correction complete")
        log_operation(log, "correct_names_complete", {
            "cards_found": len(cards),
            "relics_found": len(relics),
            "cards": ", ".join(cards[:5]) if cards else "none",
            "relics": ", ".join(relics[:3]) if relics else "none"
        })
        
        return (cards, relics)

    def correct_relic_names(self, transcribed_text: str) -> List[str]:
        """
        Correct relic names only from transcribed text.

        Args:
            transcribed_text: Text from voice transcription

        Returns:
            List of corrected relic names
        """
        log.info("Correcting relic names from transcription")
        log_operation(log, "correct_relic_names_start", {
            "text_length": len(transcribed_text),
            "text_preview": transcribed_text[:100]
        })

        available_relics = self.kb.get_all_relics()
        transcribed_text = self._try_split_concatenated_words(
            transcribed_text,
            [],
            available_relics
        )

        prompt = self._build_relic_correction_prompt(transcribed_text, available_relics)
        result = self._try_models_with_fallback(prompt)

        if result is None:
            log.warning("Relic-only correction fell back to fuzzy matching")
            relics = self._relic_phrase_fallback(
                transcribed_text,
                [],
                available_relics
            )
            _, relics = self._fuzzy_fallback(
                transcribed_text,
                [],
                relics,
                [],
                available_relics,
                threshold=75
            )
            relics = list(dict.fromkeys(relics))
            return relics

        _, relics = self._parse_correction_result(result)
        relics = self._relic_phrase_fallback(
            transcribed_text,
            relics,
            available_relics
        )

        if not self._should_skip_phrase_level_relic_fuzzy_fallback(transcribed_text, relics):
            _, relics = self._fuzzy_fallback(
                transcribed_text,
                [],
                relics,
                [],
                available_relics
            )

        relics = list(dict.fromkeys(relics))

        log.info("Relic-only correction complete")
        log_operation(log, "correct_relic_names_complete", {
            "relics_found": len(relics),
            "relics": ", ".join(relics[:5]) if relics else "none"
        })

        return relics

    def _relic_phrase_fallback(
        self,
        transcribed_text: str,
        matched_relics: List[str],
        available_relics: List[str]
    ) -> List[str]:
        """Recover missed relics by matching comma-separated phrases token-by-token."""
        fallback_relics = list(matched_relics)

        for phrase in self._split_transcribed_phrases(transcribed_text):
            best_match = self._find_best_relic_phrase_match(phrase, available_relics)
            if best_match and best_match not in fallback_relics:
                log.info(f"Phrase fallback (relic): '{phrase}' → '{best_match}'")
                fallback_relics.append(best_match)

        return fallback_relics

    def _should_skip_phrase_level_relic_fuzzy_fallback(
        self,
        transcribed_text: str,
        matched_relics: List[str]
    ) -> bool:
        """Skip broad fuzzy relic matching when each spoken phrase already has a strong canonical match."""
        phrases = self._split_transcribed_phrases(transcribed_text)
        if not phrases or not matched_relics:
            return False

        for phrase in phrases:
            phrase_tokens = self._tokenize_phrase(phrase)
            best_match, score = self._find_best_relic_phrase_match_with_score(phrase, matched_relics)
            if best_match is None:
                return False

            relic_tokens = self._tokenize_phrase(best_match)
            if abs(len(phrase_tokens) - len(relic_tokens)) > 1:
                return False
            if score < 72:
                return False

        return True

    def _split_transcribed_phrases(self, transcribed_text: str) -> List[str]:
        """Split a transcription into likely spoken item phrases."""
        parts = re.split(r",|[.!?;\n]+|\band\b", transcribed_text, flags=re.IGNORECASE)
        phrases = []

        for part in parts:
            cleaned = re.sub(r"[^A-Za-z0-9\-\s]", " ", part)
            cleaned = re.sub(r"\s+", " ", cleaned).strip()
            if cleaned:
                phrases.append(cleaned)

        return phrases

    def _find_best_relic_phrase_match(
        self,
        phrase: str,
        available_relics: List[str]
    ) -> Optional[str]:
        """Find the best relic for a spoken phrase using token-position similarity."""
        best_match, best_score = self._find_best_relic_phrase_match_with_score(phrase, available_relics)
        if best_match and best_score >= 70:
            return best_match

        return None

    def _find_best_relic_phrase_match_with_score(
        self,
        phrase: str,
        available_relics: List[str]
    ) -> Tuple[Optional[str], float]:
        """Find the best relic for a spoken phrase and return its composite score."""
        phrase_tokens = self._tokenize_phrase(phrase)
        if not phrase_tokens or not available_relics:
            return (None, 0.0)

        best_match = None
        best_score = 0.0

        for relic_name in available_relics:
            relic_tokens = self._tokenize_phrase(relic_name)
            if not relic_tokens:
                continue

            full_score = fuzz.ratio(phrase.lower(), relic_name.lower())
            token_sort_score = fuzz.token_sort_ratio(phrase.lower(), relic_name.lower())

            prefix_bonus = 0.0
            if phrase_tokens[0] == relic_tokens[0]:
                prefix_bonus = 10.0

            compared = min(len(phrase_tokens), len(relic_tokens))
            position_score = 0.0
            if compared > 0:
                position_scores = [
                    fuzz.ratio(phrase_tokens[index], relic_tokens[index])
                    for index in range(compared)
                ]
                position_score = sum(position_scores) / compared

            composite_score = max(full_score, token_sort_score, position_score + prefix_bonus)

            if composite_score > best_score:
                best_score = composite_score
                best_match = relic_name

        return (best_match, best_score)

    def _tokenize_phrase(self, phrase: str) -> List[str]:
        """Normalize a spoken phrase into comparable lowercase tokens."""
        return [token for token in re.split(r"[^A-Za-z0-9]+", phrase.lower()) if token]
    
    def _try_split_concatenated_words(
        self,
        text: str,
        available_cards: List[str],
        available_relics: List[str]
    ) -> str:
        """
        Try to split concatenated words by finding card/relic names within them.
        
        Example: "sashwhipplus" → "sash whip plus"
        
        This is a heuristic to fix Whisper transcription errors where it omits spaces.
        
        Args:
            text: Transcribed text (may have concatenated words)
            available_cards: All available card names
            available_relics: All available relic names
            
        Returns:
            Text with spaces added where card/relic names were found
        """
        words = text.split()
        fixed_words = []
        
        for word in words:
            # If word is short or has spaces, keep as-is
            if len(word) < 6 or ' ' in word:
                fixed_words.append(word)
                continue
            
            # Try to find card/relic names in this word
            split_result = self._find_names_in_concatenated_word(
                word,
                available_cards + available_relics
            )
            
            if split_result:
                log.info(f"Split concatenated word: '{word}' → '{split_result}'")
                fixed_words.append(split_result)
            else:
                fixed_words.append(word)
        
        return ' '.join(fixed_words)
    
    def _find_names_in_concatenated_word(
        self,
        concatenated: str,
        available_names: List[str]
    ) -> Optional[str]:
        """
        Try to find card/relic names within a concatenated word.
        
        Example: "sashwhipplus" contains "sash whip" (a card name when spaces are added)
        
        Strategy:
        1. Normalize the concatenated word (lowercase, remove hyphens/spaces)
        2. For each card/relic, normalize it the same way
        3. Check if the normalized card name appears in the concatenated word
        4. If found, extract it and try to split the rest recursively
        
        Args:
            concatenated: Concatenated word to split
            available_names: List of card/relic names to look for
            
        Returns:
            Split string with spaces, or None if no split found
        """
        concat_lower = concatenated.lower().replace('-', '').replace(' ', '')
        
        # Try to find names that appear in the concatenated word
        best_match = None
        best_match_len = 0
        
        for name in available_names:
            name_normalized = name.lower().replace('-', '').replace(' ', '')
            
            # Check if this name appears in the concatenated word
            if name_normalized in concat_lower:
                if len(name_normalized) > best_match_len:
                    best_match = name
                    best_match_len = len(name_normalized)
        
        if best_match:
            # Found a match!
            name_normalized = best_match.lower().replace('-', '').replace(' ', '')
            
            # If the entire word matches (after normalization), just return the match
            if concat_lower == name_normalized:
                log.debug(f"Complete match: '{concatenated}' → '{best_match}'")
                return best_match
            
            # Otherwise, split the word
            # Find where it appears in the NORMALIZED concatenated word
            start_idx = concat_lower.find(name_normalized)
            
            # Calculate positions in the original word
            # This is tricky because normalization removes characters
            # Simpler approach: return the match + remaining parts
            before_normalized = concat_lower[:start_idx]
            after_normalized = concat_lower[start_idx + len(name_normalized):]
            
            # Build the result
            parts = []
            if before_normalized:
                parts.append(before_normalized)
            parts.append(best_match)
            if after_normalized:
                parts.append(after_normalized)
            
            result = ' '.join(parts)
            log.debug(f"Split: '{concatenated}' → '{result}'")
            return result
        
        return None
    
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
7. **MATCH PARTIAL WORDS TO FULL CARD NAMES**:
   - If you see "lucky", search the available cards for names containing "lucky"
   - "trust lucky" → "Just Lucky" (ignore "trust", match "lucky" to "Just Lucky")
   - "fist" alone could be "Empty Fist" or other cards with "Fist"
   - "follow up" → "Follow-Up" (match spaces to hyphens)
   - When a word appears IN a card name, return the FULL card name from the list
8. **HANDLE SPACE VARIATIONS**:
   - "war cry" (two words) → "Warcry" (one word) - users often add spaces
   - "warcry" (no space) → "Warcry" (correct)
   - Check both with and without spaces when matching
   - IMPORTANT: Prefer CARDS over RELICS when both match
9. Only return names from the available lists above - return EXACT names, not partial matches
10. Return ALL matches you find - don't stop at the first one

COMMON MISTAKES TO AVOID:
- "wrath" is NOT the same as "Wrath" stance - it's likely "Wreath of Flame" card
- Always check if a spoken word could be a slight mispronunciation
- NEVER return partial names like "Lucky" - always return the full name "Just Lucky"
- Check the available lists for the FULL card/relic name before returning

EXAMPLES:
- "Third Eye, Wrath of Flame, Weave" → {{"cards": ["Third Eye", "Wreath of Flame", "Weave"], "relics": []}}
- "wheel kick study wrath of flame" → {{"cards": ["Wheel Kick", "Study", "Wreath of Flame"], "relics": []}}
- "strike defend" → {{"cards": ["Strike", "Defend"], "relics": []}}
- "wrath of flame" → {{"cards": ["Wreath of Flame"], "relics": []}}
- "trust lucky tranquility" → {{"cards": ["Just Lucky", "Tranquility"], "relics": []}}
- "follow up brilliance" → {{"cards": ["Follow-Up", "Brilliance"], "relics": []}}
- "war cry" → {{"cards": ["Warcry"], "relics": []}} (NOT "War Paint" relic!)
- "pommel strike war cry" → {{"cards": ["Pommel Strike", "Warcry"], "relics": []}}

OUTPUT FORMAT (JSON only):
{{
  "cards": ["Exact Card Name 1", "Exact Card Name 2"],
  "relics": ["Exact Relic Name 1"]
}}

Return ONLY valid JSON matching the format above. No explanations."""
        
        return prompt

    def _build_relic_correction_prompt(
        self,
        text: str,
        available_relics: List[str]
    ) -> str:
        """Build the LLM prompt for relic-only name correction."""
        prompt = f"""You are a Slay the Spire relic name matcher. The user spoke relic names via voice, which were transcribed and may contain speech-to-text errors.

TRANSCRIBED TEXT:
\"{text}\"

AVAILABLE RELICS:
{json.dumps(available_relics, indent=2)}

RULES:
1. Match ONLY against the available relic names above.
2. Return the exact relic names from the list.
3. Handle spacing and punctuation differences, including hyphens.
4. Handle common speech-to-text mistakes and return every relic you can identify.
5. Do not invent new names.
6. Leave the cards list empty.

EXAMPLES:
- \"aka beko pen nib\" -> {{\"cards\": [], \"relics\": [\"Akabeko\", \"Pen Nib\"]}}
- \"dead branch\" -> {{\"cards\": [], \"relics\": [\"Dead Branch\"]}}
- \"oddly smooth stone\" -> {{\"cards\": [], \"relics\": [\"Oddly Smooth Stone\"]}}

OUTPUT FORMAT (JSON only):
{{
  \"cards\": [],
  \"relics\": [\"Exact Relic Name 1\", \"Exact Relic Name 2\"]
}}

Return ONLY valid JSON matching the format above. No explanations."""

        return prompt
    
    def _get_unmatched_words(
        self,
        transcribed_text: str,
        matched_cards: List[str],
        matched_relics: List[str]
    ) -> set:
        """
        Get words from transcription that weren't matched by LLM.
        
        Args:
            transcribed_text: Original transcription
            matched_cards: Cards matched in first pass
            matched_relics: Relics matched in first pass
            
        Returns:
            Set of unmatched words (lowercase)
        """
        import string
        
        # Clean transcription: lowercase, remove punctuation INCLUDING hyphens
        # This ensures "multicast" matches "Multi-Cast"
        cleaned_text = transcribed_text.lower()
        cleaned_text = cleaned_text.translate(str.maketrans('', '', string.punctuation))
        
        # Extract words from transcription
        transcribed_words = set(cleaned_text.split())
        
        # Extract words from matched items (normalize hyphens to spaces, remove punctuation)
        matched_words = set()
        for item in matched_cards + matched_relics:
            # Normalize hyphens and remove punctuation
            normalized = item.lower().replace('-', ' ')
            normalized = normalized.translate(str.maketrans('', '', string.punctuation))
            matched_words.update(normalized.split())
        
        # Also add the full matched item names (without hyphens/punctuation)
        # This catches cases like "multicast" matching "Multi-Cast"
        for item in matched_cards + matched_relics:
            normalized_full = item.lower().replace('-', '').replace(' ', '')
            normalized_full = normalized_full.translate(str.maketrans('', '', string.punctuation))
            if normalized_full:
                matched_words.add(normalized_full)
        
        # Find unmatched words
        unmatched = transcribed_words - matched_words
        
        return unmatched
        
        return unmatched
    
    def _validate_second_pass_match(
        self,
        match_name: str,
        unmatched_words: set
    ) -> bool:
        """
        Validate that a second-pass match actually contains part of the unmatched words.
        
        This prevents the LLM from hallucinating matches that have nothing to do with
        the input. For example, "sashwhipplus" should not match "Just Lucky" because
        "Just Lucky" doesn't contain "sash", "whip", "plus", or any substring of "sashwhipplus".
        
        Args:
            match_name: Card/relic name to validate
            unmatched_words: Set of unmatched words from transcription
            
        Returns:
            True if match contains a substring of unmatched words, False otherwise
        """
        match_lower = match_name.lower().replace('-', '').replace(' ', '')
        
        for word in unmatched_words:
            word_lower = word.lower().replace('-', '').replace(' ', '')
            
            # Check if the word appears in the match
            if word_lower in match_lower:
                log.debug(f"Validated: '{match_name}' contains '{word}'")
                return True
            
            # Check if the match appears in the word (for concatenated words like "sashwhipplus")
            if match_lower in word_lower:
                log.debug(f"Validated: '{word}' contains '{match_name}'")
                return True
            
            # Check for partial overlap (at least 4 characters)
            # Check substrings from unmatched word in match name
            for i in range(len(word_lower) - 3):
                substring = word_lower[i:i+4]
                if substring in match_lower:
                    log.debug(f"Validated: '{match_name}' contains substring '{substring}' from '{word}'")
                    return True
            
            # Check substrings from match name in unmatched word
            for i in range(len(match_lower) - 3):
                substring = match_lower[i:i+4]
                if substring in word_lower:
                    log.debug(f"Validated: '{word}' contains substring '{substring}' from '{match_name}'")
                    return True
        
        log.debug(f"Rejected: '{match_name}' has no substring match with {unmatched_words}")
        return False
    
    def _build_second_pass_prompt(
        self,
        unmatched_words: set,
        available_cards: List[str],
        available_relics: List[str],
        already_matched_cards: List[str],
        already_matched_relics: List[str]
    ) -> str:
        """
        Build focused second-pass prompt for unmatched words.
        
        This prompt is more aggressive about partial matching since we know
        these words weren't matched in the first pass.
        
        Args:
            unmatched_words: Words that weren't matched in first pass
            available_cards: All available card names
            available_relics: All available relic names
            already_matched_cards: Cards already matched (to avoid re-checking)
            already_matched_relics: Relics already matched
            
        Returns:
            Focused LLM prompt
        """
        unmatched_text = " ".join(sorted(unmatched_words))
        
        prompt = f"""You are a Slay the Spire card/relic name matcher doing a SECOND PASS focused match.

FIRST PASS RESULTS:
- Already matched cards: {json.dumps(already_matched_cards)}
- Already matched relics: {json.dumps(already_matched_relics)}

UNMATCHED WORDS FROM TRANSCRIPTION:
"{unmatched_text}"

These words were NOT matched in the first pass. Your job is to find cards/relics that contain these words or are close matches.

AVAILABLE CARDS:
{json.dumps(available_cards, indent=2)}

AVAILABLE RELICS:
{json.dumps(available_relics, indent=2)}

SECOND PASS MATCHING RULES (STRICTER SUBSTRING MATCHING):
1. **CRITICAL: Only match if the unmatched word is a SUBSTRING of the card/relic name**:
   - "lucky" IS a substring of "Just Lucky" → MATCH ✅
   - "fist" IS a substring of "Empty Fist" → MATCH ✅
   - "him" IS a substring of "Battle Hymn" (phonetically: him → hym) → MATCH ✅
   - "sashwhipplus" contains "sash" and "whip" which are in "Sash Whip" → MATCH ✅
   - BUT "lucky" is NOT a substring of "Follow-Up" → NO MATCH ❌
   
2. **Check both directions**:
   - Does the unmatched word appear IN the card name? ("lucky" in "Just Lucky")
   - Does the card name appear IN the unmatched word? ("Sash Whip" → "sashwhip" in "sashwhipplus")
   
3. **For concatenated words** (like "sashwhipplus"):
   - Try to find card names that appear when you remove spaces/hyphens
   - "sashwhip" (from "sashwhipplus") matches "Sash Whip" ✅
   
4. **Phonetic errors** (be conservative):
   - "him" sounds like "hymn" → "Battle Hymn" ✅
   - "wrath" sounds like "wreath" → "Wreath of Flame" ✅
   - But don't match random cards!
   
5. **Space variations**:
   - "war cry" (two words) → "Warcry" (one word)
   - Try removing spaces to find matches
   - CRITICAL: Prefer CARDS over RELICS when both match
   
6. **STRICT RULE**: If you can't find a clear substring or phonetic connection, DO NOT match
   
7. **Do NOT return items already matched in the first pass**

8. **Return FULL exact names from the available lists, not partial matches**

9. **PREFER CARDS OVER RELICS**: If both a card and relic match, return the CARD

EXAMPLES:
- Unmatched: "lucky" → {{"cards": ["Just Lucky"], "relics": []}}
  (Because "lucky" appears in "Just Lucky")
  
- Unmatched: "fist" → {{"cards": ["Empty Fist"], "relics": []}}
  (Because "fist" appears in "Empty Fist")
  
- Unmatched: "sashwhipplus" → {{"cards": ["Sash Whip"], "relics": []}}
  (Because "sashwhip" = normalized "Sash Whip")
  
- Unmatched: "trust" → {{"cards": [], "relics": []}}
  (No card contains "trust" - return empty!)
  
- Unmatched: "him" → {{"cards": ["Battle Hymn"], "relics": []}}
  (Phonetic match: "him" → "hym" in "Hymn")
  
- Unmatched: "war cry" → {{"cards": ["Warcry"], "relics": []}}
  (Space variation: "war cry" → "Warcry", prefer card over "War Paint" relic)

IMPORTANT: Return ONLY cards that have a clear substring relationship. Empty results are OK!

OUTPUT FORMAT (JSON only):
{{
  "cards": ["Exact Card Name 1"],
  "relics": ["Exact Relic Name 1"]
}}

Return ONLY valid JSON. Be STRICT - substring matching required."""
        
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
        # Use the same logic as _get_unmatched_words() to ensure consistency
        unmatched_words = self._get_unmatched_words(transcribed_text, llm_cards, llm_relics)
        
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
        
        # Try all two-word combinations (e.g., "steam barrier" → "Steam Barrier")
        unmatched_list = list(unmatched_words)
        for i in range(len(unmatched_list)):
            for j in range(i+1, len(unmatched_list)):
                pair = f"{unmatched_list[i]} {unmatched_list[j]}"
                
                # Try cards
                if available_cards:
                    card_matches = process.extract(
                        pair,
                        available_cards,
                        scorer=fuzz.token_sort_ratio,
                        limit=1
                    )
                    if card_matches and card_matches[0][1] >= 75 and card_matches[0][0] not in fallback_cards:
                        log.info(f"Fuzzy match (card pair): '{pair}' → '{card_matches[0][0]}' (score: {card_matches[0][1]})")
                        fallback_cards.append(card_matches[0][0])
                
                # Try relics
                if available_relics:
                    relic_matches = process.extract(
                        pair,
                        available_relics,
                        scorer=fuzz.token_sort_ratio,
                        limit=1
                    )
                    if relic_matches and relic_matches[0][1] >= 75 and relic_matches[0][0] not in fallback_relics:
                        log.info(f"Fuzzy match (relic pair): '{pair}' → '{relic_matches[0][0]}' (score: {relic_matches[0][1]})")
                        fallback_relics.append(relic_matches[0][0])
        
        # Also try individual unmatched words
        # Use threshold parameter for single-word matches (default 70)
        single_word_threshold = max(threshold, 75)  # At least 75 for single words
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
                if best_card and best_card[1] >= single_word_threshold and best_card[0] not in fallback_cards:
                    log.info(f"Fuzzy match (card): '{word}' → '{best_card[0]}' (score: {best_card[1]})")
                    fallback_cards.append(best_card[0])
            
            # Try relics
            if available_relics:
                best_relic = process.extractOne(
                    word,
                    available_relics,
                    scorer=fuzz.ratio  # Changed from partial_ratio to ratio (more strict)
                )
                if best_relic and best_relic[1] >= single_word_threshold and best_relic[0] not in fallback_relics:
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
