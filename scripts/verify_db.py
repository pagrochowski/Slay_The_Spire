#!/usr/bin/env python
"""
Verify the database setup and test run tracking functionality.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import DatabaseManager


def verify_database():
    """Verify database contents and test run tracking."""
    db = DatabaseManager()
    
    with db.get_session() as session:
        # Print statistics
        stats = db.get_stats(session)
        print("\n" + "=" * 50)
        print("DATABASE VERIFICATION")
        print("=" * 50)
        
        print("\n📊 Database Statistics:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
        
        # Verify card data
        print("\n🃏 Sample Cards (Ironclad):")
        ironclad_cards = db.get_cards_by_color(session, "RED")[:5]
        for card in ironclad_cards:
            cost = card.cost if card.cost is not None else "X"
            print(f"  - {card.name} ({cost} cost, {card.card_type}, {card.rarity})")
        
        # Verify relic data
        print("\n💎 Sample Relics:")
        relics = db.get_all_relics(session)[:5]
        for relic in relics:
            print(f"  - {relic.name} ({relic.rarity}, {relic.pool})")
        
        # Verify enemy data
        print("\n👹 Sample Enemies:")
        bosses = db.get_enemies_by_type(session, "BOSS")[:5]
        for enemy in bosses:
            hp = f"{enemy.base_hp_min}-{enemy.base_hp_max}" if enemy.base_hp_min else "?"
            print(f"  - {enemy.name} ({enemy.enemy_type}, HP: {hp})")
        
        # Verify ascension modifiers
        print("\n⬆️ Ascension Modifiers:")
        ascensions = db.get_all_ascension_modifiers(session)
        for asc in ascensions[:5]:
            print(f"  - A{asc.ascension_level}: {asc.description[:50]}...")
        print(f"  ... and {len(ascensions) - 5} more")
        
        # Test run tracking
        print("\n" + "=" * 50)
        print("RUN TRACKING TEST")
        print("=" * 50)
        
        # Create a test run
        print("\n🎮 Creating test run (Ironclad A5)...")
        run = db.create_run(session, "IRONCLAD", ascension_level=5)
        session.commit()
        
        print(f"  Run ID: {run.id}")
        print(f"  Character: {run.character}")
        print(f"  Ascension: A{run.ascension_level}")
        print(f"  HP: {run.current_hp}/{run.max_hp}")
        print(f"  Gold: {run.gold}")
        print(f"  Status: {run.status}")
        
        # Get deck summary
        deck_summary = db.get_deck_summary(session, run.id)
        print(f"\n📚 Starting Deck ({deck_summary['total_cards']} cards):")
        for card in deck_summary['cards']:
            print(f"    - {card}")
        
        # Get relics
        relics = db.get_run_relics(session, run.id)
        print(f"\n💎 Starting Relics ({len(relics)}):")
        for relic in relics:
            print(f"    - {relic.relic_name}")
        
        # Simulate some gameplay
        print("\n🎯 Simulating gameplay...")
        
        # Add a card from combat
        db.add_card_to_run(session, run.id, "Anger", floor=2, source="combat_reward")
        session.commit()
        print("  Floor 2: Picked Anger from combat rewards")
        
        # Log combat event
        db.log_event(
            session, run.id,
            floor=2, event_type="COMBAT", event_name="2x Cultists",
            hp_before=80, hp_after=72, damage_dealt=28, damage_taken=8, turns_taken=3
        )
        session.commit()
        print("  Floor 2: Fought 2x Cultists (took 8 damage)")
        
        # Update run state
        db.update_run_state(session, run.id, floor=2, hp=72)
        session.commit()
        
        # Add a relic from elite
        db.add_relic_to_run(session, run.id, "Bag of Preparation", floor=6, source="elite")
        session.commit()
        print("  Floor 6: Got Bag of Preparation from Gremlin Nob")
        
        # Get run summary
        summary = db.get_run_summary(session, run.id)
        print("\n📋 Run Summary:")
        print(f"  Status: {summary['status']}")
        print(f"  Floor: {summary['current_floor']}")
        print(f"  HP: {summary['hp']}")
        print(f"  Deck size: {summary['deck']['total_cards']}")
        print(f"  Relics: {len(summary['relics'])}")
        print(f"  Events logged: {summary['event_count']}")
        
        # Clean up test run
        print("\n🗑️ Cleaning up test run...")
        for event in db.get_run_events(session, run.id):
            session.delete(event)
        for card in db.get_run_deck(session, run.id):
            session.delete(card)
        for relic in db.get_run_relics(session, run.id):
            session.delete(relic)
        session.delete(run)
        session.commit()
        print("  Test run deleted")
        
        print("\n" + "=" * 50)
        print("✅ ALL VERIFICATION PASSED!")
        print("=" * 50)


if __name__ == "__main__":
    verify_database()
