"""
Gemini API advisor for Slay the Spire.

Uses Google's Gemini API for fast, high-quality responses while
keeping run tracking and database queries local.
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Suppress deprecation warning for now (google.generativeai still works)
import warnings
warnings.filterwarnings("ignore", category=FutureWarning, module="google.generativeai")

import google.generativeai as genai
from dotenv import load_dotenv
from loguru import logger


class GeminiAdvisor:
    """Slay the Spire advisor powered by Gemini API."""
    
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment. Add it to .env file.")
        
        # Configure Gemini
        genai.configure(api_key=api_key)
        
        # Use Gemini 2.5 Flash Lite (better free tier availability)
        self.model = genai.GenerativeModel(
            model_name="gemini-2.5-flash-lite",
            generation_config={
                "temperature": 0.7,
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 500,  # Keep responses concise for voice
            },
            system_instruction=self._get_system_prompt()
        )
        
        # Start a chat session for conversation history
        self.chat = self.model.start_chat(history=[])
        
        # Run tracking (simple in-memory for now)
        self.active_run = None
        
        logger.info("Gemini Advisor initialized with gemini-2.5-flash-lite")
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for the advisor."""
        return """You are an expert Slay the Spire advisor and coach. You have deep knowledge of:
- All 4 characters: Ironclad, Silent, Defect, and Watcher
- All cards, relics, potions, and their synergies
- Boss patterns, elite fights, and enemy mechanics
- Optimal pathing, card evaluation, and deck building strategies
- Ascension-specific challenges and adaptations

Your role is to:
1. Give concise, actionable strategic advice
2. Help with card picks by evaluating synergies with current deck
3. Guide pathing decisions (when to take elites, campfires, shops, etc.)
4. Explain boss patterns and how to handle them
5. Help optimize deck building for the current run

IMPORTANT: Keep responses BRIEF and conversational since they will be spoken aloud. 
Aim for 2-3 sentences unless the user asks for detailed explanation.
Do NOT use lists or bullet points - speak naturally.
Never say you're an AI or that you can't play the game."""

    def chat_message(self, message: str) -> str:
        """Send a message and get a response."""
        try:
            # Build context from active run if any
            if self.active_run:
                context = f"[Current run: {self.active_run['character']} A{self.active_run['ascension']}, Floor {self.active_run.get('floor', 1)}]\n"
                message = context + message
            
            # Get response from Gemini
            response = self.chat.send_message(message)
            return response.text.strip()
            
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return f"Sorry, I encountered an error: {str(e)}"
    
    def start_run(self, character: str, ascension: int = 0) -> str:
        """Start tracking a new run."""
        character = character.lower()
        if character not in ["ironclad", "silent", "defect", "watcher"]:
            return f"Unknown character: {character}. Choose Ironclad, Silent, Defect, or Watcher."
        
        self.active_run = {
            "character": character.title(),
            "ascension": ascension,
            "floor": 1,
            "cards": [],
            "relics": [],
        }
        
        # Get starter info
        starter_relics = {
            "ironclad": ("Burning Blood", 80),
            "silent": ("Ring of the Snake", 70),
            "defect": ("Cracked Core", 75),
            "watcher": ("Pure Water", 72)
        }
        relic_name, max_hp = starter_relics[character]
        
        # Adjust HP for ascension
        if ascension >= 14:
            max_hp -= 4
        if ascension >= 10:
            max_hp -= 10
        
        self.active_run["hp"] = max_hp
        self.active_run["max_hp"] = max_hp
        self.active_run["relics"].append(relic_name)
        
        logger.info(f"Started new run: {character.title()} A{ascension}")
        
        return f"New run started! {character.title()} Ascension {ascension}. Starting HP: {max_hp}. Starter relic: {relic_name}. Let's climb the Spire!"
    
    def add_card(self, card_name: str) -> str:
        """Add a card to the current run's deck."""
        if not self.active_run:
            return "No active run. Start one with 'new run [character] [ascension]'"
        
        self.active_run["cards"].append(card_name)
        logger.info(f"Added card: {card_name}")
        return f"Added {card_name} to deck. You now have {len(self.active_run['cards'])} non-starter cards."
    
    def add_relic(self, relic_name: str) -> str:
        """Add a relic to the current run."""
        if not self.active_run:
            return "No active run. Start one with 'new run [character] [ascension]'"
        
        self.active_run["relics"].append(relic_name)
        logger.info(f"Added relic: {relic_name}")
        return f"Added {relic_name}. You now have {len(self.active_run['relics'])} relics."
    
    def update_state(self, floor: int = None, hp: int = None) -> str:
        """Update the current run state."""
        if not self.active_run:
            return "No active run."
        
        if floor:
            self.active_run["floor"] = floor
        if hp:
            self.active_run["hp"] = hp
        
        return f"Updated. Floor {self.active_run['floor']}, HP {self.active_run['hp']}/{self.active_run['max_hp']}."
    
    def get_run_status(self) -> str:
        """Get current run status."""
        if not self.active_run:
            return "No active run. Say 'start a new run with [character]' to begin!"
        
        r = self.active_run
        return f"Playing {r['character']} Ascension {r['ascension']}. Floor {r.get('floor', 1)}. HP {r.get('hp', r['max_hp'])}/{r['max_hp']}. Deck has {len(r['cards'])} added cards. Relics: {', '.join(r['relics'])}."
    
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


if __name__ == "__main__":
    print("Testing Gemini Advisor...")
    print("-" * 50)
    
    try:
        advisor = GeminiAdvisor()
        
        # Test chat
        response = advisor.chat_message("What's the best starter card for Ironclad?")
        print(f"Q: What's the best starter card for Ironclad?")
        print(f"A: {response}")
        print("-" * 50)
        
        # Test run tracking
        print(advisor.start_run("Silent", 5))
        print("-" * 50)
        
        print(advisor.get_run_status())
        print("-" * 50)
        
        # Test strategic advice with run context
        response = advisor.chat_message("I just got offered Noxious Fumes. Should I take it?")
        print(f"Q: I just got offered Noxious Fumes. Should I take it?")
        print(f"A: {response}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
