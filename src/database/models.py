"""
SQLAlchemy models for Slay the Spire knowledge database

Includes:
- Game data models (Card, Relic, Keyword, etc.)
- Run tracking models (Run, RunCard, RunRelic, etc.)
- Enemy data with Ascension modifiers
"""

from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Integer, Text, Float, Boolean, ForeignKey, DateTime, Table, Column, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

if TYPE_CHECKING:
    pass


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


# ============================================================================
# ASSOCIATION TABLES
# ============================================================================

card_keywords = Table(
    "card_keywords",
    Base.metadata,
    Column("card_id", Integer, ForeignKey("cards.id"), primary_key=True),
    Column("keyword_id", Integer, ForeignKey("keywords.id"), primary_key=True),
)

card_synergies = Table(
    "card_synergies",
    Base.metadata,
    Column("card_id", Integer, ForeignKey("cards.id"), primary_key=True),
    Column("synergy_card_id", Integer, ForeignKey("cards.id"), primary_key=True),
)

relic_card_synergies = Table(
    "relic_card_synergies",
    Base.metadata,
    Column("relic_id", Integer, ForeignKey("relics.id"), primary_key=True),
    Column("card_id", Integer, ForeignKey("cards.id"), primary_key=True),
)


class Card(Base):
    """Model for Slay the Spire cards."""
    
    __tablename__ = "cards"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    
    # Basic info from API
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    flavor_text: Mapped[Optional[str]] = mapped_column(Text)
    
    # Card attributes
    color: Mapped[Optional[str]] = mapped_column(String(50))  # RED, GREEN, BLUE, PURPLE, COLORLESS, CURSE
    rarity: Mapped[Optional[str]] = mapped_column(String(50), index=True)  # BASIC, COMMON, UNCOMMON, RARE, CURSE, SPECIAL
    card_type: Mapped[Optional[str]] = mapped_column(String(50), index=True)  # ATTACK, SKILL, POWER, STATUS, CURSE
    
    # Cost
    cost: Mapped[Optional[int]] = mapped_column(Integer)
    cost_upgraded: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Stats
    damage: Mapped[Optional[int]] = mapped_column(Integer)
    damage_upgraded: Mapped[Optional[int]] = mapped_column(Integer)
    block: Mapped[Optional[int]] = mapped_column(Integer)
    block_upgraded: Mapped[Optional[int]] = mapped_column(Integer)
    magic_number: Mapped[Optional[int]] = mapped_column(Integer)  # For special effects
    magic_number_upgraded: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Upgraded description
    description_upgraded: Mapped[Optional[str]] = mapped_column(Text)
    
    # Strategic metadata (to be enriched)
    tier_rating: Mapped[Optional[float]] = mapped_column(Float)  # 1-5 rating
    pick_priority: Mapped[Optional[int]] = mapped_column(Integer)  # Lower = pick earlier
    archetype_tags: Mapped[Optional[str]] = mapped_column(String(500))  # Comma-separated: "strength,exhaust,block"
    strategy_notes: Mapped[Optional[str]] = mapped_column(Text)
    
    # Flags
    is_innate: Mapped[bool] = mapped_column(Boolean, default=False)
    is_ethereal: Mapped[bool] = mapped_column(Boolean, default=False)
    exhausts: Mapped[bool] = mapped_column(Boolean, default=False)
    targets_all: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Metadata
    image_url: Mapped[Optional[str]] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    keywords: Mapped[list["Keyword"]] = relationship(
        secondary=card_keywords, back_populates="cards"
    )
    
    def __repr__(self) -> str:
        return f"<Card(name='{self.name}', color='{self.color}', rarity='{self.rarity}')>"


class Relic(Base):
    """Model for Slay the Spire relics."""
    
    __tablename__ = "relics"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    
    # Basic info from API
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    flavor_text: Mapped[Optional[str]] = mapped_column(Text)
    
    # Relic attributes
    rarity: Mapped[Optional[str]] = mapped_column(String(50), index=True)  # STARTER, COMMON, UNCOMMON, RARE, BOSS, SHOP, EVENT, SPECIAL
    pool: Mapped[Optional[str]] = mapped_column(String(50))  # Which character pool: IRONCLAD, SILENT, DEFECT, WATCHER, SHARED
    
    # Strategic metadata (to be enriched)
    tier_rating: Mapped[Optional[float]] = mapped_column(Float)  # 1-5 rating
    pick_priority: Mapped[Optional[int]] = mapped_column(Integer)
    strategy_notes: Mapped[Optional[str]] = mapped_column(Text)
    synergy_tags: Mapped[Optional[str]] = mapped_column(String(500))  # "strength,attack,scaling"
    
    # Metadata
    image_url: Mapped[Optional[str]] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self) -> str:
        return f"<Relic(name='{self.name}', rarity='{self.rarity}')>"


class Keyword(Base):
    """Model for Slay the Spire game keywords/mechanics."""
    
    __tablename__ = "keywords"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    
    # Relationships
    cards: Mapped[list["Card"]] = relationship(
        secondary=card_keywords, back_populates="keywords"
    )
    
    def __repr__(self) -> str:
        return f"<Keyword(name='{self.name}')>"


class Archetype(Base):
    """Model for deck archetypes and strategies."""
    
    __tablename__ = "archetypes"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    character: Mapped[Optional[str]] = mapped_column(String(50))  # IRONCLAD, SILENT, etc.
    description: Mapped[Optional[str]] = mapped_column(Text)
    key_cards: Mapped[Optional[str]] = mapped_column(Text)  # Comma-separated card names
    key_relics: Mapped[Optional[str]] = mapped_column(Text)  # Comma-separated relic names
    strategy_guide: Mapped[Optional[str]] = mapped_column(Text)
    difficulty_rating: Mapped[Optional[int]] = mapped_column(Integer)  # 1-5
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    def __repr__(self) -> str:
        return f"<Archetype(name='{self.name}', character='{self.character}')>"


class StrategicTip(Base):
    """Model for general strategic tips and advice."""
    
    __tablename__ = "strategic_tips"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    
    category: Mapped[str] = mapped_column(String(50), index=True)  # "card_pick", "pathing", "boss", "elite", etc.
    context: Mapped[Optional[str]] = mapped_column(String(200))  # "act1", "low_hp", "rich", etc.
    tip: Mapped[str] = mapped_column(Text)
    priority: Mapped[Optional[int]] = mapped_column(Integer)  # For ordering/importance
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    def __repr__(self) -> str:
        return f"<StrategicTip(category='{self.category}')>"


# ============================================================================
# ENEMY / CREATURE MODELS
# ============================================================================

class Enemy(Base):
    """Model for enemies/creatures in the game."""
    
    __tablename__ = "enemies"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    
    name: Mapped[str] = mapped_column(String(100), index=True)
    enemy_type: Mapped[Optional[str]] = mapped_column(String(50))  # NORMAL, ELITE, BOSS, MINION
    
    # Base stats (Ascension 0)
    base_hp_min: Mapped[Optional[int]] = mapped_column(Integer)
    base_hp_max: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Act where this enemy appears
    act: Mapped[Optional[int]] = mapped_column(Integer)  # 1, 2, 3, or None for all
    
    # Move patterns and abilities (JSON for flexibility)
    move_pattern: Mapped[Optional[str]] = mapped_column(Text)  # JSON description of moves
    abilities: Mapped[Optional[str]] = mapped_column(Text)  # JSON list of abilities
    
    # Strategic notes
    strategy_notes: Mapped[Optional[str]] = mapped_column(Text)
    danger_rating: Mapped[Optional[int]] = mapped_column(Integer)  # 1-5, how dangerous
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    def __repr__(self) -> str:
        return f"<Enemy(name='{self.name}', type='{self.enemy_type}')>"


class AscensionModifier(Base):
    """Model for Ascension level modifiers.
    
    Ascension levels add cumulative difficulty modifiers:
    - A1: Elites spawn more often
    - A2: Normal enemies deal more damage
    - A3: Elites are harder
    - A4: Start with a curse (Ascender's Bane)
    - A5: Heal less at rest sites
    - A6: Start with less gold
    - A7: Bosses are harder
    - A8: Harder boss fights
    - A9: Unfavorable events
    - A10: Start with 10 less HP
    - A11: Start with Ascender's Bane
    - A12: Upgraded cards appear less in rewards
    - A13: Bosses drop harder relics
    - A14: More elites on floor 2
    - A15: Enemies have more HP
    - A16: More damage from enemies
    - A17: Harder act 1/2 bosses
    - A18: Elites have more HP
    - A19: Heart fight has extra mechanics
    - A20: Double boss in act 3
    """
    
    __tablename__ = "ascension_modifiers"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    
    ascension_level: Mapped[int] = mapped_column(Integer, unique=True, index=True)  # 1-20
    description: Mapped[str] = mapped_column(Text)  # Human-readable description
    
    # Specific modifiers (cumulative from previous levels)
    enemy_hp_percent: Mapped[Optional[float]] = mapped_column(Float)  # HP multiplier (1.0 = normal)
    enemy_damage_percent: Mapped[Optional[float]] = mapped_column(Float)  # Damage multiplier
    elite_hp_percent: Mapped[Optional[float]] = mapped_column(Float)
    boss_hp_percent: Mapped[Optional[float]] = mapped_column(Float)
    starting_hp_modifier: Mapped[Optional[int]] = mapped_column(Integer)  # -10 at A10
    starting_gold: Mapped[Optional[int]] = mapped_column(Integer)  # 99 normally, less at high ascension
    rest_heal_percent: Mapped[Optional[float]] = mapped_column(Float)  # 30% normally, less at A5+
    
    # Flags
    has_ascenders_bane: Mapped[bool] = mapped_column(Boolean, default=False)  # A4+
    unfavorable_events: Mapped[bool] = mapped_column(Boolean, default=False)  # A9+
    double_boss: Mapped[bool] = mapped_column(Boolean, default=False)  # A20
    
    def __repr__(self) -> str:
        return f"<AscensionModifier(level={self.ascension_level})>"


# ============================================================================
# RUN TRACKING MODELS
# ============================================================================

class Run(Base):
    """Model for tracking a single run through the Spire.
    
    A run tracks the player's progress through all acts, including:
    - Character and ascension level
    - Current state (HP, gold, floor, etc.)
    - Deck composition (via RunCard)
    - Relics collected (via RunRelic)
    - Key decisions and events
    """
    
    __tablename__ = "runs"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    
    # Run identification
    run_id: Mapped[Optional[str]] = mapped_column(String(100), unique=True, index=True)  # Optional external ID
    
    # Character and difficulty
    character: Mapped[str] = mapped_column(String(50), index=True)  # IRONCLAD, SILENT, DEFECT, WATCHER
    ascension_level: Mapped[int] = mapped_column(Integer, default=0)  # 0-20
    
    # Current state
    current_act: Mapped[int] = mapped_column(Integer, default=1)  # 1, 2, 3, 4 (heart)
    current_floor: Mapped[int] = mapped_column(Integer, default=0)  # 0-57 typically
    current_hp: Mapped[int] = mapped_column(Integer)
    max_hp: Mapped[int] = mapped_column(Integer)
    gold: Mapped[int] = mapped_column(Integer, default=99)
    
    # Potion slots
    potion_slots: Mapped[int] = mapped_column(Integer, default=3)
    potions: Mapped[Optional[str]] = mapped_column(Text)  # JSON list of current potions
    
    # Run status
    status: Mapped[str] = mapped_column(String(50), default="IN_PROGRESS")  # IN_PROGRESS, VICTORY, DEFEAT, ABANDONED
    
    # Keys collected (for Act 4)
    has_ruby_key: Mapped[bool] = mapped_column(Boolean, default=False)
    has_emerald_key: Mapped[bool] = mapped_column(Boolean, default=False)
    has_sapphire_key: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Statistics
    cards_played: Mapped[int] = mapped_column(Integer, default=0)
    damage_dealt: Mapped[int] = mapped_column(Integer, default=0)
    damage_taken: Mapped[int] = mapped_column(Integer, default=0)
    gold_earned: Mapped[int] = mapped_column(Integer, default=0)
    gold_spent: Mapped[int] = mapped_column(Integer, default=0)
    
    # Final result (if completed)
    final_floor: Mapped[Optional[int]] = mapped_column(Integer)
    victory: Mapped[bool] = mapped_column(Boolean, default=False)
    killed_by: Mapped[Optional[str]] = mapped_column(String(100))  # Enemy that killed you
    
    # Timestamps
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Relationships
    deck: Mapped[list["RunCard"]] = relationship(back_populates="run", cascade="all, delete-orphan")
    relics: Mapped[list["RunRelic"]] = relationship(back_populates="run", cascade="all, delete-orphan")
    events: Mapped[list["RunEvent"]] = relationship(back_populates="run", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Run(character='{self.character}', A{self.ascension_level}, floor={self.current_floor}, status='{self.status}')>"
    
    @property
    def deck_size(self) -> int:
        """Return the number of cards in the deck."""
        return len(self.deck)
    
    @property
    def relic_count(self) -> int:
        """Return the number of relics collected."""
        return len(self.relics)


class RunCard(Base):
    """Model for a card in a run's deck.
    
    Tracks each card instance including:
    - Whether it's upgraded
    - When it was obtained
    - How it was obtained
    """
    
    __tablename__ = "run_cards"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    
    # Foreign keys
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"), index=True)
    card_id: Mapped[Optional[int]] = mapped_column(ForeignKey("cards.id"))  # Reference to base card
    
    # Card info (denormalized for quick access)
    card_name: Mapped[str] = mapped_column(String(100))
    is_upgraded: Mapped[bool] = mapped_column(Boolean, default=False)
    upgrade_count: Mapped[int] = mapped_column(Integer, default=0)  # For Searing Blow
    
    # How/when obtained
    obtained_floor: Mapped[Optional[int]] = mapped_column(Integer)
    obtained_from: Mapped[Optional[str]] = mapped_column(String(100))  # "combat_reward", "shop", "event", "starter", etc.
    
    # Stats for this card in this run
    times_played: Mapped[int] = mapped_column(Integer, default=0)
    
    # Timestamp
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    run: Mapped["Run"] = relationship(back_populates="deck")
    card: Mapped[Optional["Card"]] = relationship()
    
    def __repr__(self) -> str:
        upgraded = "+" if self.is_upgraded else ""
        return f"<RunCard(name='{self.card_name}{upgraded}')>"


class RunRelic(Base):
    """Model for a relic collected in a run."""
    
    __tablename__ = "run_relics"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    
    # Foreign keys
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"), index=True)
    relic_id: Mapped[Optional[int]] = mapped_column(ForeignKey("relics.id"))
    
    # Relic info (denormalized)
    relic_name: Mapped[str] = mapped_column(String(100))
    
    # How/when obtained
    obtained_floor: Mapped[Optional[int]] = mapped_column(Integer)
    obtained_from: Mapped[Optional[str]] = mapped_column(String(100))  # "boss", "elite", "shop", "event", "starter", etc.
    
    # Relic-specific counters (some relics track usage)
    counter: Mapped[Optional[int]] = mapped_column(Integer)  # e.g., Pen Nib counts attacks
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)  # Some relics can be disabled
    
    # Timestamp
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    run: Mapped["Run"] = relationship(back_populates="relics")
    relic: Mapped[Optional["Relic"]] = relationship()
    
    def __repr__(self) -> str:
        return f"<RunRelic(name='{self.relic_name}')>"


class RunEvent(Base):
    """Model for tracking events/decisions during a run.
    
    Records key moments like:
    - Combat encounters and outcomes
    - Card picks/skips
    - Shop purchases
    - Event choices
    - Rest site decisions
    """
    
    __tablename__ = "run_events"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    
    # Foreign key
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"), index=True)
    
    # Event info
    floor: Mapped[int] = mapped_column(Integer)
    event_type: Mapped[str] = mapped_column(String(50), index=True)
    # Types: COMBAT, ELITE, BOSS, SHOP, REST, EVENT, TREASURE, CARD_REWARD, BOSS_RELIC
    
    # Event details (JSON for flexibility)
    event_name: Mapped[Optional[str]] = mapped_column(String(200))  # Enemy name, event name, etc.
    details: Mapped[Optional[str]] = mapped_column(Text)  # JSON with additional details
    
    # State snapshot at this event
    hp_before: Mapped[Optional[int]] = mapped_column(Integer)
    hp_after: Mapped[Optional[int]] = mapped_column(Integer)
    gold_before: Mapped[Optional[int]] = mapped_column(Integer)
    gold_after: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Decision made (for card picks, event choices, etc.)
    decision: Mapped[Optional[str]] = mapped_column(String(200))  # What was chosen
    alternatives: Mapped[Optional[str]] = mapped_column(Text)  # JSON list of what wasn't chosen
    
    # Combat-specific
    damage_dealt: Mapped[Optional[int]] = mapped_column(Integer)
    damage_taken: Mapped[Optional[int]] = mapped_column(Integer)
    turns_taken: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Timestamp
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    run: Mapped["Run"] = relationship(back_populates="events")
    
    def __repr__(self) -> str:
        return f"<RunEvent(floor={self.floor}, type='{self.event_type}', name='{self.event_name}')>"


class Potion(Base):
    """Model for potions in the game."""
    
    __tablename__ = "potions"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    rarity: Mapped[Optional[str]] = mapped_column(String(50))  # COMMON, UNCOMMON, RARE
    description: Mapped[Optional[str]] = mapped_column(Text)
    
    # Strategic metadata
    tier_rating: Mapped[Optional[float]] = mapped_column(Float)
    strategy_notes: Mapped[Optional[str]] = mapped_column(Text)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    def __repr__(self) -> str:
        return f"<Potion(name='{self.name}')>"


# ============================================================================
# MAP / PATHING MODELS
# ============================================================================

class MapNode(Base):
    """Model for a node on the map (for a specific run).
    
    Used to track/analyze pathing decisions.
    """
    
    __tablename__ = "map_nodes"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"), index=True)
    
    floor: Mapped[int] = mapped_column(Integer)
    x_position: Mapped[int] = mapped_column(Integer)  # Column position
    node_type: Mapped[str] = mapped_column(String(50))  # MONSTER, ELITE, REST, SHOP, EVENT, TREASURE, BOSS
    
    # Was this node visited?
    visited: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Connected nodes (JSON list of node IDs or coordinates)
    connections: Mapped[Optional[str]] = mapped_column(Text)
    
    def __repr__(self) -> str:
        return f"<MapNode(floor={self.floor}, type='{self.node_type}', visited={self.visited})>"
