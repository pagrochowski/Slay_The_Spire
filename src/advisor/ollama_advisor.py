"""
Ollama API wrapper for the Slay the Spire advisor.

This module provides the interface between the LLM and the database.
"""

import json
from typing import Optional, Any
from pathlib import Path

import ollama
from loguru import logger

# Add project root to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import DatabaseManager


class STSAdvisor:
    """Slay the Spire advisor powered by local LLM via Ollama."""
    
    def __init__(self, model: str = "qwen2.5:7b", db_path: str = "db/sts_knowledge.db"):
        self.model = model
        self.db = DatabaseManager(db_path)
        self.conversation_history: list[dict] = []
        self.active_run_id: Optional[int] = None
        
        # Load system prompt
        self._load_system_prompt()
        
        logger.info(f"STS Advisor initialized with model: {model}")
    
    def _load_system_prompt(self) -> None:
        """Load the system prompt from file."""
        prompt_path = Path(__file__).parent.parent / "docs" / "system_prompt.md"
        context_path = Path(__file__).parent.parent / "docs" / "llm_context.md"
        
        system_content = ""
        
        if prompt_path.exists():
            system_content = prompt_path.read_text(encoding="utf-8")
        
        # Optionally load full context (can be large)
        # if context_path.exists():
        #     system_content += "\n\n" + context_path.read_text(encoding="utf-8")
        
        self.system_prompt = system_content or self._default_system_prompt()
    
    def _default_system_prompt(self) -> str:
        """Default system prompt if files not found."""
        return """You are an expert Slay the Spire game advisor. Help players make optimal decisions 
during runs by providing strategic advice on card picks, pathing, deck building, relic synergies, 
and combat strategies. Be concise but thorough. Explain your reasoning."""
    
    def chat(self, user_message: str) -> str:
        """Send a message and get a response from the advisor."""
        
        # Build messages
        messages = [{"role": "system", "content": self.system_prompt}]
        messages.extend(self.conversation_history)
        messages.append({"role": "user", "content": user_message})
        
        # Check for function triggers in the message
        context = self._gather_context(user_message)
        if context:
            # Inject context before user message
            messages[-1]["content"] = f"[Context: {context}]\n\n{user_message}"
        
        try:
            response = ollama.chat(
                model=self.model,
                messages=messages,
            )
            
            assistant_message = response["message"]["content"]
            
            # Update conversation history
            self.conversation_history.append({"role": "user", "content": user_message})
            self.conversation_history.append({"role": "assistant", "content": assistant_message})
            
            # Keep history manageable (last 20 turns)
            if len(self.conversation_history) > 40:
                self.conversation_history = self.conversation_history[-40:]
            
            return assistant_message
            
        except Exception as e:
            logger.error(f"Error calling Ollama: {e}")
            return f"Error: Could not get response from model. {str(e)}"
    
    def _gather_context(self, message: str) -> Optional[str]:
        """Gather relevant context from database based on message content."""
        context_parts = []
        message_lower = message.lower()
        
        with self.db.get_session() as session:
            # If there's an active run, include its state
            if self.active_run_id:
                summary = self.db.get_run_summary(session, self.active_run_id)
                if summary:
                    context_parts.append(f"Current run: {summary['character']} A{summary['ascension']}, "
                                        f"Floor {summary['current_floor']}, HP: {summary['hp']}, "
                                        f"Gold: {summary['gold']}, Deck: {summary['deck']['total_cards']} cards, "
                                        f"Relics: {', '.join(summary['relics'])}")
            
            # Look for card names mentioned
            for word in message.split():
                clean_word = word.strip(",.?!\"'()[]")
                if len(clean_word) > 2:
                    card = self.db.get_card_by_name(session, clean_word)
                    if card:
                        context_parts.append(f"Card '{card.name}': {card.description} "
                                           f"({card.card_type}, {card.rarity}, Cost: {card.cost})")
                    
                    relic = self.db.get_relic_by_name(session, clean_word)
                    if relic:
                        context_parts.append(f"Relic '{relic.name}': {relic.description}")
        
        return " | ".join(context_parts) if context_parts else None
    
    # =========================================================================
    # RUN MANAGEMENT
    # =========================================================================
    
    def start_run(self, character: str, ascension: int = 0) -> str:
        """Start a new run."""
        character = character.upper()
        if character not in ["IRONCLAD", "SILENT", "DEFECT", "WATCHER"]:
            return f"Unknown character: {character}. Choose from: Ironclad, Silent, Defect, Watcher"
        
        with self.db.get_session() as session:
            run = self.db.create_run(session, character, ascension)
            session.commit()
            self.active_run_id = run.id
            
            summary = self.db.get_run_summary(session, run.id)
        
        logger.info(f"Started new run: {character} A{ascension}, ID: {self.active_run_id}")
        
        return (f"New run started! {character} Ascension {ascension}. "
                f"Starting HP: {summary['hp']}, Gold: {summary['gold']}. "
                f"Starter relic: {summary['relics'][0] if summary['relics'] else 'None'}. "
                f"Ready to climb the Spire!")
    
    def add_relic(self, relic_name: str, floor: int = 0, source: str = "unknown") -> str:
        """Add a relic to the current run."""
        if not self.active_run_id:
            return "No active run. Start a run first with start_run()."
        
        with self.db.get_session() as session:
            self.db.add_relic_to_run(session, self.active_run_id, relic_name, floor, source)
            session.commit()
            
            # Get relic info for response
            relic = self.db.get_relic_by_name(session, relic_name)
            relic_desc = relic.description if relic else "Unknown relic"
        
        logger.info(f"Added relic: {relic_name}")
        return f"Added relic: {relic_name}. Effect: {relic_desc}"
    
    def add_card(self, card_name: str, floor: int = 0, source: str = "combat_reward", upgraded: bool = False) -> str:
        """Add a card to the current run's deck."""
        if not self.active_run_id:
            return "No active run. Start a run first with start_run()."
        
        with self.db.get_session() as session:
            self.db.add_card_to_run(session, self.active_run_id, card_name, floor, source, upgraded)
            session.commit()
        
        logger.info(f"Added card: {card_name}")
        return f"Added {card_name}{'+' if upgraded else ''} to deck."
    
    def update_state(self, floor: int = None, hp: int = None, gold: int = None, act: int = None) -> str:
        """Update the current run state."""
        if not self.active_run_id:
            return "No active run. Start a run first with start_run()."
        
        with self.db.get_session() as session:
            self.db.update_run_state(session, self.active_run_id, floor=floor, hp=hp, gold=gold, act=act)
            session.commit()
            
            summary = self.db.get_run_summary(session, self.active_run_id)
        
        updates = []
        if floor is not None:
            updates.append(f"Floor {floor}")
        if hp is not None:
            updates.append(f"HP {hp}")
        if gold is not None:
            updates.append(f"Gold {gold}")
        if act is not None:
            updates.append(f"Act {act}")
        
        return f"Updated: {', '.join(updates)}. Current state: Floor {summary['current_floor']}, {summary['hp']}, {summary['gold']} gold."
    
    def get_run_status(self) -> str:
        """Get the current run status."""
        if not self.active_run_id:
            return "No active run."
        
        with self.db.get_session() as session:
            summary = self.db.get_run_summary(session, self.active_run_id)
            
            if not summary:
                return "Run not found."
            
            deck_cards = summary['deck']['cards']
            deck_str = ', '.join(deck_cards[:10])
            if len(deck_cards) > 10:
                deck_str += f"... (+{len(deck_cards) - 10} more)"
        
        return (f"Run Status: {summary['character']} A{summary['ascension']}\n"
                f"Floor: {summary['current_floor']} | HP: {summary['hp']} | Gold: {summary['gold']}\n"
                f"Relics ({len(summary['relics'])}): {', '.join(summary['relics'])}\n"
                f"Deck ({summary['deck']['total_cards']}): {deck_str}")
    
    def end_run(self, victory: bool, killed_by: str = None) -> str:
        """End the current run."""
        if not self.active_run_id:
            return "No active run."
        
        with self.db.get_session() as session:
            self.db.end_run(session, self.active_run_id, victory, killed_by)
            session.commit()
        
        result = "Victory! Congratulations!" if victory else f"Defeated by {killed_by or 'unknown'}."
        self.active_run_id = None
        
        return f"Run ended. {result}"
    
    # =========================================================================
    # QUERY FUNCTIONS
    # =========================================================================
    
    def query_card(self, card_name: str) -> str:
        """Look up a card by name."""
        with self.db.get_session() as session:
            card = self.db.get_card_by_name(session, card_name)
            
            if not card:
                return f"Card '{card_name}' not found."
            
            return (f"{card.name} ({card.color}, {card.rarity}, {card.card_type})\n"
                    f"Cost: {card.cost if card.cost is not None else 'X'}\n"
                    f"Effect: {card.description}")
    
    def query_relic(self, relic_name: str) -> str:
        """Look up a relic by name."""
        with self.db.get_session() as session:
            relic = self.db.get_relic_by_name(session, relic_name)
            
            if not relic:
                return f"Relic '{relic_name}' not found."
            
            return (f"{relic.name} ({relic.rarity}, {relic.pool})\n"
                    f"Effect: {relic.description}")
    
    def query_enemy(self, enemy_name: str) -> str:
        """Look up an enemy by name."""
        with self.db.get_session() as session:
            enemy = self.db.get_enemy_by_name(session, enemy_name)
            
            if not enemy:
                return f"Enemy '{enemy_name}' not found."
            
            hp_str = f"{enemy.base_hp_min}-{enemy.base_hp_max}" if enemy.base_hp_min else "?"
            return (f"{enemy.name} ({enemy.enemy_type})\n"
                    f"HP: {hp_str}\n"
                    f"Notes: {enemy.strategy_notes or 'No strategy notes available.'}")
    
    def clear_history(self) -> None:
        """Clear conversation history."""
        self.conversation_history = []
        logger.info("Conversation history cleared")


def test_advisor():
    """Quick test of the advisor."""
    advisor = STSAdvisor()
    
    print("\n" + "=" * 60)
    print("STS ADVISOR TEST")
    print("=" * 60)
    
    # Test card query
    print("\n📋 Testing card query...")
    print(advisor.query_card("Demon Form"))
    
    # Test relic query
    print("\n💎 Testing relic query...")
    print(advisor.query_relic("Dead Branch"))
    
    # Test starting a run
    print("\n🎮 Starting a run...")
    print(advisor.start_run("Silent", 5))
    
    # Test adding a relic
    print("\n➕ Adding Specimen relic...")
    print(advisor.add_relic("Specimen", floor=0, source="boss_swap"))
    
    # Get run status
    print("\n📊 Run status...")
    print(advisor.get_run_status())
    
    # Test chat with context
    print("\n💬 Testing chat...")
    response = advisor.chat("I got Specimen as my boss swap relic. What build path should I follow?")
    print(f"Advisor: {response}")
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    test_advisor()
