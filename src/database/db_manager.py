"""
Database manager for Slay the Spire knowledge base
"""

from datetime import datetime
from pathlib import Path
from typing import Optional, Type, TypeVar
from sqlalchemy import create_engine, select, and_
from sqlalchemy.orm import Session, sessionmaker
from loguru import logger

from .models import (
    Base, Card, Relic, Keyword, Archetype, StrategicTip,
    Enemy, AscensionModifier, Run, RunCard, RunRelic, RunEvent, Potion
)


T = TypeVar("T", bound=Base)


class DatabaseManager:
    """Manager for database operations."""
    
    def __init__(self, db_path: str = "db/sts_knowledge.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.engine = create_engine(f"sqlite:///{self.db_path}", echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)
        
    def create_tables(self) -> None:
        """Create all database tables."""
        logger.info("Creating database tables...")
        Base.metadata.create_all(self.engine)
        logger.info("Database tables created successfully")
    
    def drop_tables(self) -> None:
        """Drop all database tables."""
        logger.warning("Dropping all database tables...")
        Base.metadata.drop_all(self.engine)
        logger.info("Database tables dropped")
    
    def get_session(self) -> Session:
        """Get a new database session."""
        return self.SessionLocal()
    
    # Card operations
    def add_card(self, session: Session, card_data: dict) -> Card:
        """Add a card to the database."""
        card = Card(**card_data)
        session.add(card)
        return card
    
    def get_card_by_name(self, session: Session, name: str) -> Optional[Card]:
        """Get a card by name."""
        return session.execute(
            select(Card).where(Card.name == name)
        ).scalar_one_or_none()
    
    def get_all_cards(self, session: Session) -> list[Card]:
        """Get all cards."""
        return list(session.execute(select(Card)).scalars().all())
    
    def get_cards_by_color(self, session: Session, color: str) -> list[Card]:
        """Get all cards for a specific character color."""
        return list(session.execute(
            select(Card).where(Card.color == color)
        ).scalars().all())
    
    # Relic operations
    def add_relic(self, session: Session, relic_data: dict) -> Relic:
        """Add a relic to the database."""
        relic = Relic(**relic_data)
        session.add(relic)
        return relic
    
    def get_relic_by_name(self, session: Session, name: str) -> Optional[Relic]:
        """Get a relic by name."""
        return session.execute(
            select(Relic).where(Relic.name == name)
        ).scalar_one_or_none()
    
    def get_all_relics(self, session: Session) -> list[Relic]:
        """Get all relics."""
        return list(session.execute(select(Relic)).scalars().all())
    
    # Keyword operations
    def add_keyword(self, session: Session, keyword_data: dict) -> Keyword:
        """Add a keyword to the database."""
        keyword = Keyword(**keyword_data)
        session.add(keyword)
        return keyword
    
    def get_keyword_by_name(self, session: Session, name: str) -> Optional[Keyword]:
        """Get a keyword by name."""
        return session.execute(
            select(Keyword).where(Keyword.name == name)
        ).scalar_one_or_none()
    
    def get_all_keywords(self, session: Session) -> list[Keyword]:
        """Get all keywords."""
        return list(session.execute(select(Keyword)).scalars().all())
    
    # Archetype operations
    def add_archetype(self, session: Session, archetype_data: dict) -> Archetype:
        """Add an archetype to the database."""
        archetype = Archetype(**archetype_data)
        session.add(archetype)
        return archetype
    
    def get_all_archetypes(self, session: Session) -> list[Archetype]:
        """Get all archetypes."""
        return list(session.execute(select(Archetype)).scalars().all())
    
    # Strategic tip operations
    def add_tip(self, session: Session, tip_data: dict) -> StrategicTip:
        """Add a strategic tip to the database."""
        tip = StrategicTip(**tip_data)
        session.add(tip)
        return tip
    
    def get_tips_by_category(self, session: Session, category: str) -> list[StrategicTip]:
        """Get tips by category."""
        return list(session.execute(
            select(StrategicTip).where(StrategicTip.category == category)
        ).scalars().all())
    
    # Bulk operations
    def bulk_add(self, session: Session, model: Type[T], items: list[dict]) -> list[T]:
        """Bulk add items to the database."""
        objects = [model(**item) for item in items]
        session.add_all(objects)
        return objects
    
    def count(self, session: Session, model: Type[Base]) -> int:
        """Count items of a model type."""
        return session.query(model).count()
    
    def get_stats(self, session: Session) -> dict:
        """Get database statistics."""
        return {
            "cards": self.count(session, Card),
            "relics": self.count(session, Relic),
            "keywords": self.count(session, Keyword),
            "archetypes": self.count(session, Archetype),
            "tips": self.count(session, StrategicTip),
            "enemies": self.count(session, Enemy),
            "potions": self.count(session, Potion),
            "runs": self.count(session, Run),
        }
    
    # ========================================================================
    # ENEMY OPERATIONS
    # ========================================================================
    
    def add_enemy(self, session: Session, enemy_data: dict) -> Enemy:
        """Add an enemy to the database."""
        enemy = Enemy(**enemy_data)
        session.add(enemy)
        return enemy
    
    def get_enemy_by_name(self, session: Session, name: str) -> Optional[Enemy]:
        """Get an enemy by name."""
        return session.execute(
            select(Enemy).where(Enemy.name == name)
        ).scalar_one_or_none()
    
    def get_enemies_by_type(self, session: Session, enemy_type: str) -> list[Enemy]:
        """Get enemies by type (NORMAL, ELITE, BOSS)."""
        return list(session.execute(
            select(Enemy).where(Enemy.enemy_type == enemy_type)
        ).scalars().all())
    
    # ========================================================================
    # POTION OPERATIONS
    # ========================================================================
    
    def add_potion(self, session: Session, potion_data: dict) -> Potion:
        """Add a potion to the database."""
        potion = Potion(**potion_data)
        session.add(potion)
        return potion
    
    def get_potion_by_name(self, session: Session, name: str) -> Optional[Potion]:
        """Get a potion by name."""
        return session.execute(
            select(Potion).where(Potion.name == name)
        ).scalar_one_or_none()
    
    # ========================================================================
    # ASCENSION OPERATIONS
    # ========================================================================
    
    def add_ascension_modifier(self, session: Session, data: dict) -> AscensionModifier:
        """Add an ascension modifier."""
        modifier = AscensionModifier(**data)
        session.add(modifier)
        return modifier
    
    def get_ascension_modifier(self, session: Session, level: int) -> Optional[AscensionModifier]:
        """Get ascension modifier for a specific level."""
        return session.execute(
            select(AscensionModifier).where(AscensionModifier.ascension_level == level)
        ).scalar_one_or_none()
    
    def get_all_ascension_modifiers(self, session: Session) -> list[AscensionModifier]:
        """Get all ascension modifiers ordered by level."""
        return list(session.execute(
            select(AscensionModifier).order_by(AscensionModifier.ascension_level)
        ).scalars().all())
    
    # ========================================================================
    # RUN TRACKING OPERATIONS
    # ========================================================================
    
    def create_run(
        self,
        session: Session,
        character: str,
        ascension_level: int = 0,
        run_id: Optional[str] = None,
    ) -> Run:
        """Create a new run.
        
        Args:
            session: Database session
            character: Character name (IRONCLAD, SILENT, DEFECT, WATCHER)
            ascension_level: Ascension level (0-20)
            run_id: Optional external identifier
            
        Returns:
            New Run object
        """
        # Get starting HP based on character
        base_hp = {
            "IRONCLAD": 80,
            "SILENT": 70,
            "DEFECT": 75,
            "WATCHER": 72,
        }.get(character.upper(), 75)
        
        # Apply ascension HP penalty (A10+: -10 max HP)
        hp_penalty = 0
        if ascension_level >= 10:
            hp_penalty = 10
        
        # Apply ascension gold penalty (A6+: less starting gold)
        starting_gold = 99
        if ascension_level >= 6:
            starting_gold = 99  # Actually gold varies by A6, kept simple for now
        
        run = Run(
            run_id=run_id,
            character=character.upper(),
            ascension_level=ascension_level,
            current_hp=base_hp - hp_penalty,
            max_hp=base_hp - hp_penalty,
            gold=starting_gold,
        )
        session.add(run)
        session.flush()  # Get the ID
        
        # Add starter relic based on character
        starter_relics = {
            "IRONCLAD": "Burning Blood",
            "SILENT": "Ring of the Snake",
            "DEFECT": "Cracked Core",
            "WATCHER": "Pure Water",
        }
        starter_relic = starter_relics.get(character.upper())
        if starter_relic:
            self.add_relic_to_run(session, run.id, starter_relic, floor=0, source="starter")
        
        # Add starter deck
        starter_decks = {
            "IRONCLAD": [("Strike", 5), ("Defend", 4), ("Bash", 1)],
            "SILENT": [("Strike", 5), ("Defend", 5), ("Survivor", 1), ("Neutralize", 1)],
            "DEFECT": [("Strike", 4), ("Defend", 4), ("Zap", 1), ("Dualcast", 1)],
            "WATCHER": [("Strike", 4), ("Defend", 4), ("Eruption", 1), ("Vigilance", 1)],
        }
        starter_cards = starter_decks.get(character.upper(), [])
        for card_name, count in starter_cards:
            for _ in range(count):
                self.add_card_to_run(session, run.id, card_name, floor=0, source="starter")
        
        logger.info(f"Created new run: {character} A{ascension_level}")
        return run
    
    def get_run(self, session: Session, run_id: int) -> Optional[Run]:
        """Get a run by ID."""
        return session.get(Run, run_id)
    
    def get_run_by_external_id(self, session: Session, external_id: str) -> Optional[Run]:
        """Get a run by external ID."""
        return session.execute(
            select(Run).where(Run.run_id == external_id)
        ).scalar_one_or_none()
    
    def get_active_runs(self, session: Session) -> list[Run]:
        """Get all runs that are in progress."""
        return list(session.execute(
            select(Run).where(Run.status == "IN_PROGRESS")
        ).scalars().all())
    
    def get_runs_by_character(self, session: Session, character: str) -> list[Run]:
        """Get all runs for a specific character."""
        return list(session.execute(
            select(Run).where(Run.character == character.upper())
        ).scalars().all())
    
    def update_run_state(
        self,
        session: Session,
        run_id: int,
        floor: Optional[int] = None,
        hp: Optional[int] = None,
        max_hp: Optional[int] = None,
        gold: Optional[int] = None,
        act: Optional[int] = None,
        potions: Optional[str] = None,
    ) -> Optional[Run]:
        """Update the current state of a run."""
        run = session.get(Run, run_id)
        if not run:
            return None
        
        if floor is not None:
            run.current_floor = floor
        if hp is not None:
            run.current_hp = hp
        if max_hp is not None:
            run.max_hp = max_hp
        if gold is not None:
            run.gold = gold
        if act is not None:
            run.current_act = act
        if potions is not None:
            run.potions = potions
        
        run.updated_at = datetime.utcnow()
        return run
    
    def end_run(
        self,
        session: Session,
        run_id: int,
        victory: bool,
        killed_by: Optional[str] = None,
    ) -> Optional[Run]:
        """Mark a run as ended."""
        run = session.get(Run, run_id)
        if not run:
            return None
        
        run.status = "VICTORY" if victory else "DEFEAT"
        run.victory = victory
        run.final_floor = run.current_floor
        run.killed_by = killed_by
        run.ended_at = datetime.utcnow()
        
        logger.info(f"Run ended: {'Victory!' if victory else f'Defeated by {killed_by}'}")
        return run
    
    def collect_key(self, session: Session, run_id: int, key_type: str) -> Optional[Run]:
        """Record collecting a key (for Act 4 access)."""
        run = session.get(Run, run_id)
        if not run:
            return None
        
        key_type = key_type.lower()
        if key_type in ("ruby", "red"):
            run.has_ruby_key = True
        elif key_type in ("emerald", "green"):
            run.has_emerald_key = True
        elif key_type in ("sapphire", "blue"):
            run.has_sapphire_key = True
        
        return run
    
    # ========================================================================
    # RUN CARD OPERATIONS
    # ========================================================================
    
    def add_card_to_run(
        self,
        session: Session,
        run_id: int,
        card_name: str,
        floor: int = 0,
        source: str = "unknown",
        upgraded: bool = False,
    ) -> RunCard:
        """Add a card to a run's deck."""
        # Try to find the base card
        base_card = self.get_card_by_name(session, card_name.rstrip("+"))
        
        run_card = RunCard(
            run_id=run_id,
            card_id=base_card.id if base_card else None,
            card_name=card_name,
            is_upgraded=upgraded or card_name.endswith("+"),
            obtained_floor=floor,
            obtained_from=source,
        )
        session.add(run_card)
        return run_card
    
    def remove_card_from_run(self, session: Session, run_card_id: int) -> bool:
        """Remove a card from a run's deck."""
        run_card = session.get(RunCard, run_card_id)
        if run_card:
            session.delete(run_card)
            return True
        return False
    
    def upgrade_card_in_run(self, session: Session, run_card_id: int) -> Optional[RunCard]:
        """Upgrade a card in a run's deck."""
        run_card = session.get(RunCard, run_card_id)
        if run_card:
            run_card.is_upgraded = True
            run_card.upgrade_count += 1
            if not run_card.card_name.endswith("+"):
                run_card.card_name += "+"
        return run_card
    
    def get_run_deck(self, session: Session, run_id: int) -> list[RunCard]:
        """Get all cards in a run's deck."""
        return list(session.execute(
            select(RunCard).where(RunCard.run_id == run_id)
        ).scalars().all())
    
    def get_deck_summary(self, session: Session, run_id: int) -> dict:
        """Get a summary of the run's deck."""
        deck = self.get_run_deck(session, run_id)
        
        summary = {
            "total_cards": len(deck),
            "by_type": {},
            "by_rarity": {},
            "upgraded_count": 0,
            "cards": [],
        }
        
        for run_card in deck:
            # Count by type and rarity if we have base card info
            if run_card.card:
                card_type = run_card.card.card_type or "UNKNOWN"
                rarity = run_card.card.rarity or "UNKNOWN"
                summary["by_type"][card_type] = summary["by_type"].get(card_type, 0) + 1
                summary["by_rarity"][rarity] = summary["by_rarity"].get(rarity, 0) + 1
            
            if run_card.is_upgraded:
                summary["upgraded_count"] += 1
            
            summary["cards"].append(run_card.card_name)
        
        return summary
    
    # ========================================================================
    # RUN RELIC OPERATIONS
    # ========================================================================
    
    def add_relic_to_run(
        self,
        session: Session,
        run_id: int,
        relic_name: str,
        floor: int = 0,
        source: str = "unknown",
    ) -> RunRelic:
        """Add a relic to a run."""
        base_relic = self.get_relic_by_name(session, relic_name)
        
        run_relic = RunRelic(
            run_id=run_id,
            relic_id=base_relic.id if base_relic else None,
            relic_name=relic_name,
            obtained_floor=floor,
            obtained_from=source,
        )
        session.add(run_relic)
        return run_relic
    
    def get_run_relics(self, session: Session, run_id: int) -> list[RunRelic]:
        """Get all relics in a run."""
        return list(session.execute(
            select(RunRelic).where(RunRelic.run_id == run_id)
        ).scalars().all())
    
    def update_relic_counter(
        self,
        session: Session,
        run_relic_id: int,
        counter: int,
    ) -> Optional[RunRelic]:
        """Update a relic's counter (e.g., Pen Nib, Nunchaku)."""
        run_relic = session.get(RunRelic, run_relic_id)
        if run_relic:
            run_relic.counter = counter
        return run_relic
    
    # ========================================================================
    # RUN EVENT OPERATIONS
    # ========================================================================
    
    def log_event(
        self,
        session: Session,
        run_id: int,
        floor: int,
        event_type: str,
        event_name: Optional[str] = None,
        details: Optional[str] = None,
        hp_before: Optional[int] = None,
        hp_after: Optional[int] = None,
        gold_before: Optional[int] = None,
        gold_after: Optional[int] = None,
        decision: Optional[str] = None,
        alternatives: Optional[str] = None,
        damage_dealt: Optional[int] = None,
        damage_taken: Optional[int] = None,
        turns_taken: Optional[int] = None,
    ) -> RunEvent:
        """Log an event during a run."""
        event = RunEvent(
            run_id=run_id,
            floor=floor,
            event_type=event_type.upper(),
            event_name=event_name,
            details=details,
            hp_before=hp_before,
            hp_after=hp_after,
            gold_before=gold_before,
            gold_after=gold_after,
            decision=decision,
            alternatives=alternatives,
            damage_dealt=damage_dealt,
            damage_taken=damage_taken,
            turns_taken=turns_taken,
        )
        session.add(event)
        return event
    
    def get_run_events(self, session: Session, run_id: int) -> list[RunEvent]:
        """Get all events for a run."""
        return list(session.execute(
            select(RunEvent)
            .where(RunEvent.run_id == run_id)
            .order_by(RunEvent.floor, RunEvent.timestamp)
        ).scalars().all())
    
    def get_run_combats(self, session: Session, run_id: int) -> list[RunEvent]:
        """Get all combat events for a run."""
        return list(session.execute(
            select(RunEvent)
            .where(and_(
                RunEvent.run_id == run_id,
                RunEvent.event_type.in_(["COMBAT", "ELITE", "BOSS"])
            ))
            .order_by(RunEvent.floor)
        ).scalars().all())
    
    # ========================================================================
    # RUN ANALYSIS / SUMMARY
    # ========================================================================
    
    def get_run_summary(self, session: Session, run_id: int) -> Optional[dict]:
        """Get a comprehensive summary of a run."""
        run = self.get_run(session, run_id)
        if not run:
            return None
        
        deck_summary = self.get_deck_summary(session, run_id)
        relics = self.get_run_relics(session, run_id)
        events = self.get_run_events(session, run_id)
        
        return {
            "run_id": run.id,
            "character": run.character,
            "ascension": run.ascension_level,
            "status": run.status,
            "current_floor": run.current_floor,
            "current_act": run.current_act,
            "hp": f"{run.current_hp}/{run.max_hp}",
            "gold": run.gold,
            "keys": {
                "ruby": run.has_ruby_key,
                "emerald": run.has_emerald_key,
                "sapphire": run.has_sapphire_key,
            },
            "deck": deck_summary,
            "relics": [r.relic_name for r in relics],
            "potions": run.potions,
            "event_count": len(events),
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "victory": run.victory,
            "killed_by": run.killed_by,
        }
