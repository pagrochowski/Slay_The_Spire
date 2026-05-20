#!/usr/bin/env python
"""
Voice-Controlled Run Status Recorder.

This script tracks Slay the Spire run state via voice commands:
- Groq API for intent parsing (4-tier fallback)
- Groq Whisper API for speech-to-text
- Edge TTS for voice confirmations
- Persistent run storage in JSON

Usage:
    python scripts/voice_advisor.py

Controls:
    - Press and hold SPACE to speak
    - Release to process command
    - Press ESC to exit
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from src_old.advisor.status_recorder import StatusRecorder
from src_old.voice.voice_interface import VoiceInterface, VoiceConfig
from src_old.advisor.command_parser import CommandParser
import argparse
from loguru import logger
from datetime import datetime

# Configure logging to file
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)
log_file = log_dir / f"voice_recorder_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logger.add(log_file, rotation="10 MB", retention="7 days", level="DEBUG")
logger.info(f"Voice recorder logging to: {log_file}")


def create_command_handler(recorder: StatusRecorder, parser: CommandParser):
    """Create the command handler function with intent parsing."""
    
    def validate_card_names(cards: list) -> list:
        """Return canonical names for cards when KB matches, otherwise keep original.
        NOTE: do not filter here; use `filter_matched_card_names` to drop unknowns.
        """
        if not cards:
            return []

        validated = []
        for card_name in cards:
            matches = recorder.kb.find_cards(card_name, limit=1)
            if matches:
                validated.append(matches[0][2]["name"])
            else:
                validated.append(card_name)
        return validated

    def filter_matched_card_names(cards: list) -> list:
        """Return only those card names that have a match in the KB (canonicalized)."""
        out = []
        for card_name in cards:
            matches = recorder.kb.find_cards(card_name, limit=1)
            if matches:
                out.append(matches[0][2]["name"])
        return out
    
    def validate_relic_names(relics: list) -> list:
        """Validate and correct relic names using knowledge base."""
        if not relics:
            return []
        
        validated = []
        for relic_name in relics:
            matches = recorder.kb.find_relics(relic_name, limit=1)
            if matches:
                validated.append(matches[0][2]["name"])
            else:
                validated.append(relic_name)
        return validated
    
    def handle_command(text: str) -> str:
        """Process voice commands."""
        
        # Refresh from save file before processing command
        recorder.refresh_from_save()
        
        # Parse intent (may return None on model failures)
        parsed = parser.parse(text) or {"intent": "unknown", "cards": [], "relics": []}
        intent = parsed.get("intent", "unknown")
        
        # If parser missed items, supplement using KB mention extraction
        try:
            mentions = recorder.kb.extract_mentioned_items(text)
        except Exception:
            mentions = {"cards": [], "relics": []}

        # Normalize parser-returned cards and detect upgrade hints
        raw_parsed_cards = parsed.get("cards", []) or []
        upgrades = {}
        normalized_parsed = []
        import re
        text_lower = (text or "").lower()
        for p in raw_parsed_cards:
            if not p:
                continue
            pl = p.strip()
            # "Upgraded Recursion" -> mark upgrade
            m = re.match(r"^upgrad(?:ed|e)?\s+(.+)", pl, flags=re.I)
            if m:
                base = m.group(1).strip()
                upgrades[base.lower().rstrip('+').strip()] = True
                normalized_parsed.append(base)
                continue
            # Trailing + markers
            if pl.endswith('+'):
                base = pl.rstrip('+').strip()
                upgrades[base.lower()] = True
                normalized_parsed.append(base)
                continue
            normalized_parsed.append(pl)

        # Merge KB-detected cards (longest-first already returned by KB)
        for c in mentions.get("cards", []):
            # If original text indicates upgrade for this mention
            upgraded = False
            if re.search(r"\bupgrad(?:ed|e)?\s+" + re.escape(c) + r"\b", text_lower):
                upgraded = True
            if re.search(re.escape(c) + r"\s*\+", text_lower):
                upgraded = True
            if c not in [x.lower() for x in normalized_parsed]:
                normalized_parsed.append(recorder.kb.cards.get(c, {}).get("name", c))
            if upgraded:
                upgrades[c] = True

        parsed["cards"] = normalized_parsed

        # Validate card and relic names against knowledge base
        if "cards" in parsed and parsed["cards"]:
            # Validate names against KB (returns canonical names)
            validated = validate_card_names(parsed["cards"])
            # Reapply upgrade markers based on detected hints
            validated_with_upgrades = []
            for name in validated:
                base = name.lower().rstrip('+').strip()
                if upgrades.get(base):
                    validated_with_upgrades.append(name + "+")
                else:
                    validated_with_upgrades.append(name)

            # Post-process: remove noise tokens and deduplicate while preserving order
            stop_tokens = {"card choice", "cardchoice", "choice", "card"}
            seen = set()
            cleaned = []
            for c in validated_with_upgrades:
                if not c:
                    continue
                cl = c.strip().lower()
                if cl in stop_tokens:
                    continue
                base = cl.rstrip('+').strip()
                if base in seen:
                    continue
                seen.add(base)
                cleaned.append(c)
            parsed["cards"] = cleaned
        # Validate relic names against KB; if parser returned none, use KB mention fallback
        if "relics" in parsed and parsed["relics"]:
            parsed["relics"] = validate_relic_names(parsed["relics"])
        else:
            # Fall back to KB-detected relic mentions when parser omitted them
            kb_relics = mentions.get("relics", [])
            if kb_relics:
                parsed["relics"] = validate_relic_names(kb_relics)
        
        logger.info(f"Parsed intent: {intent}, cards: {parsed.get('cards', [])}")
        # Fallback: if intent unknown but we detected card mentions, treat appropriately
        if intent == "unknown":
            # Use parser cards first, then KB mentions
            detected = parsed.get("cards", []) or mentions.get("cards", [])
            if detected:
                # Always treat detected cards as a choice (single or multiple)
                return recorder.set_card_choice(detected)

        # Treat legacy/alternate intents as choices
        if intent == "add_card":
            intent = "card_choice"

        # Handle based on intent
        if intent == "status":
            return recorder.get_run_status()
        
        elif intent == "summary":
            return recorder.create_summary_file()
        
        elif intent == "sync" or intent == "refresh":
            return recorder.refresh_from_save()
        
        elif intent == "card_choice":
            options = parsed.get("cards", [])
            # Attempt to canonicalize and filter to KB-matched cards
            if options:
                # First, reapply validation (may keep originals)
                validated = validate_card_names(options)
                # Reapply upgrade markers from earlier detection
                validated_with_upgrades = []
                for name in validated:
                    base = name.lower().rstrip('+').strip()
                    if upgrades.get(base):
                        validated_with_upgrades.append(name + "+")
                    else:
                        validated_with_upgrades.append(name)

                # Keep only the KB-matched canonical names
                matched = filter_matched_card_names(validated_with_upgrades)
                # If none matched but original parser had entries, try KB mention fallback
                if not matched:
                    mentions_cards = mentions.get("cards", [])
                    if mentions_cards:
                        matched = filter_matched_card_names(mentions_cards)

                # If we have at least one matched card, record it (single or multiple)
                if matched:
                    return recorder.set_card_choice(matched)

            return "What are your card options?"

        # Note: adding cards is done by reading the save file; no add_card handler here
        
        elif intent == "relic_choice":
            # Prefer parser relics, then KB mentions; always validate and clean before recording
            options = parsed.get("relics", []) or mentions.get("relics", [])
            options = validate_relic_names(options)

            # Deduplicate and remove empty/noise tokens while preserving order
            seen = set()
            cleaned = []
            for r in options:
                if not r:
                    continue
                rl = r.strip()
                key = rl.lower()
                if key in seen:
                    continue
                seen.add(key)
                cleaned.append(rl)

            if len(cleaned) >= 2:
                return recorder.set_relic_choice(cleaned)
            return "What are your relic options?"
        
        elif intent == "clear_choice":
            return recorder.clear_choice()
        
        # Unknown or unsupported intents
        else:
            return "Sorry, I didn't understand that command."
    
    return handle_command


def create_choice_handler(recorder: StatusRecorder):
    """Create a handler that takes free-form text and appends validated
    card or relic names to the current choice in the summary file.

    Behavior:
    - Split incoming text on commas or line breaks to get candidate names.
    - For each candidate, try to match against cards and relics via KB.
    - If matches are primarily cards, add as card options; if relics, add as relic options.
    - Append to existing `current_choice` options and update summary.
    """

    def _split_candidates(text: str) -> list:
        parts = []
        if not text:
            return parts
        # Split on commas, ' or ', ' / ', and newlines
        for seg in [s.strip() for s in text.replace('\n', ',').replace(' or ', ',').replace(' / ', ',').split(',')]:
            if seg:
                parts.append(seg)
        return parts
    
    def _extract_all_items(text: str, kb) -> list:
        """Extract all card/relic names from text using KB, regardless of delimiters."""
        extracted = kb.extract_mentioned_items(text)
        return extracted.get('cards', []) + extracted.get('relics', [])

    def handle_choice_input(text: str) -> str:
        if not recorder.current_run:
            return "No active run found. Start a run first."

        # Special commands to clear or manage choice
        text_lower = text.lower().strip()
        if text_lower in ["clear", "clear choice", "reset", "reset choice", "start over"]:
            recorder.clear_choice()
            return "Choice cleared."

        # Get current character for filtering
        current_char = recorder.current_run.get('character', '').upper()
        # Map character names to color codes
        char_to_color = {
            'IRONCLAD': 'RED',
            'SILENT': 'GREEN',
            'DEFECT': 'BLUE',
            'WATCHER': 'PURPLE'
        }
        current_color = char_to_color.get(current_char, current_char)
        
        # FIRST: Try to extract all items from KB, regardless of delimiters
        candidates = _extract_all_items(text, recorder.kb)
        logger.debug(f"KB-extracted candidates: {candidates}")
        
        # Only add individual tokens if KB extraction found nothing
        # This prevents "eye" from matching when "Snecko Eye" was already extracted
        if not candidates:
            import re
            clean_text = re.sub(r'[^\w\s]', '', text.lower())
            tokens = [t.strip() for t in re.split(r'[, ]+', clean_text) if t.strip()]
            logger.debug(f"No KB extraction, using input tokens: {tokens}")
            candidates = tokens
        else:
            logger.debug(f"Using KB-extracted candidates only (no token splitting)")

        logger.debug(f"Final candidates for matching: {candidates}")

        # If extraction didn't find anything, try fuzzy matching the whole phrase
        if not candidates:
            # Try fuzzy matching against all cards for current character
            fuzzy_matches = recorder.kb.find_cards(text, limit=3)
            if fuzzy_matches:
                # Filter by character and pick best match
                char_matches = [m for m in fuzzy_matches if m[2].get('color', '').upper() == current_color or m[2].get('color', '').upper() == 'COLORLESS']
                if char_matches:
                    best = char_matches[0]
                    logger.debug(f"Fuzzy matched whole phrase '{text}' -> '{best[2]['name']}'")
                    candidates = [best[1]]

        if not candidates:
            return "No items detected in input."

        card_matches = []
        relic_matches = []

        # Validate each candidate against KB with fuzzy matching
        # Priority: Cards (with character filtering) > Relics
        for c in candidates:
            # First try exact/fuzzy card match (with character filtering)
            cm = recorder.kb.find_cards(c, limit=3)
            if cm:
                # Filter by character class
                valid_cards = [m for m in cm if m[2].get('color', '').upper() == current_color or m[2].get('color', '').upper() == 'COLORLESS']
                # Also check if the match score is good enough (>= 0.8 for reliable matches)
                if valid_cards and valid_cards[0][0] >= 0.8:
                    matched_name = valid_cards[0][2].get('name')
                    logger.debug(f"Card match: '{c}' -> '{matched_name}' (score: {valid_cards[0][0]}, color: {current_color})")
                    card_matches.append(matched_name)
                    continue
                elif valid_cards:
                    # Low score match - log but don't use
                    logger.debug(f"Low-score card match rejected: '{c}' -> '{valid_cards[0][2]['name']}' (score: {valid_cards[0][0]})")
                else:
                    # Found a card but not for this character
                    if cm[0][2].get('color'):
                        wrong_color = cm[0][2].get('color', 'unknown')
                        logger.debug(f"Skipped '{c}' -> '{cm[0][2]['name']}' (wrong color: {wrong_color}, current: {current_color})")
                    # Don't continue - try relics below
            
            # Only try relics if no valid card was found
            # Use good threshold for relics (0.75)
            rm = recorder.kb.find_relics(c, limit=1)
            if rm and rm[0][0] >= 0.75:  # Only accept good matches
                matched_name = rm[0][2].get('name')
                logger.debug(f"Relic match: '{c}' -> '{matched_name}' (score: {rm[0][0]})")
                relic_matches.append(matched_name)
                continue
            
            # If still no match, try aggressive fuzzy match for cards
            logger.debug(f"No direct match for '{c}', trying aggressive fuzzy match")
            # Get all cards for current character and try fuzzy match
            all_char_cards = [
                (name, card) for name, card in recorder.kb.cards.items()
                if card.get('color', '').upper() == current_color or card.get('color', '').upper() == 'COLORLESS'
            ]
            # Try fuzzy matching using Levenshtein distance (better for speech-to-text errors)
            def levenshtein_distance(s1: str, s2: str) -> int:
                if len(s1) < len(s2):
                    return levenshtein_distance(s2, s1)
                
                if len(s2) == 0:
                    return len(s1)
                
                previous_row = range(len(s2) + 1)
                for i, c1 in enumerate(s1):
                    current_row = [i + 1]
                    for j, c2 in enumerate(s2):
                        insertions = previous_row[j + 1] + 1
                        deletions = current_row[j] + 1
                        substitutions = previous_row[j] + (c1 != c2)
                        current_row.append(min(insertions, deletions, substitutions))
                    previous_row = current_row
                
                return previous_row[-1]
            
            best_match = None
            min_distance = float('inf')
            for name, card in all_char_cards:
                distance = levenshtein_distance(c.lower(), name.lower())
                if distance < min_distance:
                    min_distance = distance
                    best_match = name
                elif distance == min_distance and best_match is not None:
                    # If distances are equal, prefer shorter name or name with same starting letter
                    if len(name) < len(best_match):
                        best_match = name
                    elif len(name) == len(best_match) and name.lower()[0] == c.lower()[0]:
                        best_match = name
            
            # Only accept matches with reasonable distance
            max_acceptable_distance = 2
            if best_match is not None and min_distance <= max_acceptable_distance:
                logger.debug(f"Fuzzy match: '{c}' -> '{best_match}' (distance: {min_distance})")
                card_matches.append(best_match)
            else:
                logger.debug(f"No match for '{c}', best was '{best_match}' (distance: {min_distance})")
        
        # Clean up matches: remove duplicates and redundant items
        # For card matches: keep only unique items, and if a longer card contains a shorter one, keep longer
        unique_card_matches = []
        seen = set()
        # First pass: deduplicate
        for match in card_matches:
            if match not in seen:
                seen.add(match)
                unique_card_matches.append(match)
        # Second pass: remove redundant items (if item A is contained in item B, remove A)
        final_card_matches = []
        for i, match1 in enumerate(unique_card_matches):
            keep = True
            for j, match2 in enumerate(unique_card_matches):
                if i != j and match1.lower() in match2.lower():
                    keep = False
                    break
            if keep:
                final_card_matches.append(match1)
        card_matches = final_card_matches
        logger.debug(f"Final card matches (cleaned): {card_matches}")
        
        # Clean up relic matches too: remove duplicates and redundant items
        # For relic matches: keep only unique items, and if a longer relic contains a shorter one, keep longer
        unique_relic_matches = []
        seen_relics = set()
        # First pass: deduplicate
        for match in relic_matches:
            if match not in seen_relics:
                seen_relics.add(match)
                unique_relic_matches.append(match)
        # Second pass: remove redundant items (if item A is contained in item B, remove A)
        final_relic_matches = []
        for i, match1 in enumerate(unique_relic_matches):
            keep = True
            for j, match2 in enumerate(unique_relic_matches):
                if i != j and match1.lower() in match2.lower():
                    keep = False
                    break
            if keep:
                final_relic_matches.append(match1)
        relic_matches = final_relic_matches
        logger.debug(f"Final relic matches (cleaned): {relic_matches}")

        # Heuristic: default to cards (more common)
        # Only treat as relics if ALL matches are relics (no card matches at all)
        if relic_matches and not card_matches:
            # Pure relic input - all matches were relics
            new_opts = list(dict.fromkeys(relic_matches))
            recorder.set_relic_choice(new_opts)
            return f"Set {len(new_opts)} relic(s) as current choice."
        else:
            # Default to cards (including mixed input or pure card input)
            new_opts = list(dict.fromkeys(card_matches))
            recorder.set_card_choice(new_opts)
            return f"Set {len(new_opts)} card(s) as current choice."

    return handle_choice_input


def main():
    """Main entry point."""
    print("=" * 60)
    print("Slay the Spire Run Status Recorder")
    print("=" * 60)
    print("\nInitializing...")
    
    # Initialize components
    parser = CommandParser()
    recorder = StatusRecorder()

    # CLI: allow choice-only mode
    argp = argparse.ArgumentParser(add_help=False)
    argp.add_argument('--choice-mode', action='store_true', help='Enable choice-only mode: any speech appends validated items to current choice')
    args, _ = argp.parse_known_args()

    if args.choice_mode:
        handler = create_choice_handler(recorder)
    else:
        handler = create_command_handler(recorder, parser)
    
    # Check if we found an active game
    startup_message = "Voice advisor ready"
    if recorder.current_run:
        r = recorder.current_run
        char = r['character']
        asc = r['ascension']
        act = r['act']
        hp = r['hp']
        max_hp = r['max_hp']
        
        print(f"\n✓ Found active game: {char} A{asc}, Act {act}")
        print(f"  HP: {hp}/{max_hp}")
        startup_message = f"Resuming {char} run"
    else:
        print("\n⚠ No active game found in save file")
        print("  Start a game in Slay the Spire, then use voice commands")
        startup_message = "Current game not found"
    
    # Configure voice interface
    config = VoiceConfig(
        push_to_talk_key='f1',
        tts_engine='edge-tts',
        tts_voice=os.getenv("TTS_VOICE", "en-US-AriaNeural"),
        whisper_backend='groq',
        whisper_model=os.getenv("WHISPER_MODEL", "whisper-large-v3"),
        whisper_fallback_model=os.getenv("WHISPER_FALLBACK", "whisper-large-v3-turbo")
    )
    
    voice = VoiceInterface(config)
    voice.on_command = handler
    voice.startup_message = startup_message
    
    print("\n✓ Ready!")
    print("\nControls:")
    print("  - Hold F1 to speak")
    print("  - Release to process")
    print("  - Press ESC to exit")
    print("\nListening for commands...\n")
    
    # Start the voice interface loop
    voice.run()


if __name__ == "__main__":
    main()
