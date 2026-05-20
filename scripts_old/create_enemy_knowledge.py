"""
Create comprehensive enemy knowledge base split by act and difficulty.
Uses existing bosses.json and STS knowledge for comprehensive enemy data.
"""
import json
from pathlib import Path
from datetime import datetime

# Paths
RAW_DIR = Path("data/raw")
KNOWLEDGE_DIR = Path("data/knowledge/enemies")

def create_meta(file_name: str, description: str, usage: str, count: int) -> dict:
    """Create metadata for a knowledge file."""
    return {
        "file": file_name,
        "description": description,
        "usage": usage,
        "count": count,
        "last_updated": datetime.now().strftime("%Y-%m-%d")
    }

def parse_boss_html(html_file: Path) -> dict:
    """Parse boss HTML file and extract relevant data."""
    if not html_file.exists():
        print(f"Warning: {html_file} not found")
        return None
    
    with open(html_file, encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), 'html.parser')
    
    # Extract boss name from title
    title = soup.find('title')
    boss_name = title.text.split('|')[0].strip() if title else html_file.stem
    
    # Extract meta description for strategy overview
    meta_desc = soup.find('meta', attrs={'name': 'description'})
    description = meta_desc['content'] if meta_desc else ""
    
    # Try to find portable infobox data
    infobox = soup.find('aside', class_='portable-infobox')
    hp_range = [None, None]
    
    if infobox:
        # Look for HP value
        hp_data = infobox.find('div', attrs={'data-source': 'HP'})
        if hp_data:
            hp_text = hp_data.get_text()
            # Extract HP numbers (e.g., "300" or "280-300")
            hp_matches = re.findall(r'\d+', hp_text)
            if len(hp_matches) >= 2:
                hp_range = [int(hp_matches[0]), int(hp_matches[1])]
            elif len(hp_matches) == 1:
                hp_val = int(hp_matches[0])
                hp_range = [hp_val, hp_val]
    
    # Extract main content
    content = soup.find('div', class_='mw-parser-output')
    
    moves = []
    mechanics = []
    tips = []
    
    if content:
        # Look for move patterns in lists
        lists = content.find_all('ul')
        for ul in lists:
            items = ul.find_all('li')
            for li in items:
                text = li.get_text().strip()
                # Categorize based on keywords
                if any(keyword in text.lower() for keyword in ['turn', 'damage', 'attack', 'block', 'intent']):
                    moves.append(text)
                elif any(keyword in text.lower() for keyword in ['artifact', 'vulnerable', 'weak', 'strength', 'buff', 'debuff']):
                    mechanics.append(text)
                else:
                    tips.append(text)
        
        # Also check paragraphs for strategy tips
        paragraphs = content.find_all('p')
        for p in paragraphs:
            text = p.get_text().strip()
            if len(text) > 50 and any(keyword in text.lower() for keyword in ['try', 'focus', 'avoid', 'prioritize', 'important']):
                tips.append(text)
    
    return {
        "name": boss_name,
        "hp_range": hp_range,
        "description": description[:500] if description else "",  # Limit length
        "move_pattern": moves[:10],  # Top 10 moves
        "mechanics": mechanics[:10],  # Top 10 mechanics
        "strategy_tips": tips[:10]  # Top 10 tips
    }

def get_act1_monsters() -> list:
    """Get Act 1 monster data based on STS knowledge."""
    return [
        {
            "name": "Cultist",
            "type": "NORMAL",
            "hp_range": [48, 54],
            "hp_a7_plus": [50, 56],
            "move_pattern": [
                {"turn": 1, "move": "Incantation", "effect": "Gain 3-5 Ritual (Strength each turn)"}
            ],
            "mechanics": ["Ritual: Gains Strength at start of turn", "No attacks, only buffs"],
            "strategy_tips": [
                "Kill quickly before Ritual stacks get high",
                "One of the easiest enemies - good for hallway healing",
                "Focus damage, don't worry about defense"
            ],
            "ascension_changes": {"asc_7": "+2 HP"},
            "danger_rating": 1
        },
        {
            "name": "Jaw Worm",
            "type": "NORMAL",
            "hp_range": [40, 44],
            "hp_a7_plus": [42, 46],
            "move_pattern": [
                {"turn": 1, "move": "Chomp", "damage": 11, "probability": "Always Turn 1"},
                {"move": "Chomp", "damage": 11, "probability": "45%"},
                {"move": "Thrash", "damage": 7, "block": 5, "probability": "30%"},
                {"move": "Bellow", "effect": "Gain 3 Strength + 6 Block", "probability": "25%"}
            ],
            "mechanics": ["Uses Bellow early to buff", "Alternates between attacks after Bellow"],
            "strategy_tips": [
                "Front-load damage before it gains Strength from Bellow",
                "Weak is highly effective",
                "Block 11+ on Chomp turns",
                "If it uses Bellow twice, be ready for high damage"
            ],
            "ascension_changes": {"asc_2": "+10% damage (12 Chomp, 8 Thrash)", "asc_7": "+2 HP"},
            "danger_rating": 2
        },
        {
            "name": "Louse",
            "type": "NORMAL",
            "hp_range": [10, 15],
            "hp_a7_plus": [11, 16],
            "move_pattern": [
                {"move": "Bite", "damage": [5, 7], "probability": "75%"},
                {"move": "Spit Web", "effect": "Apply 2 Weak", "probability": "25%"}
            ],
            "mechanics": ["33% chance to have Curl Up (3-7 Block when hit)", "Random damage variance"],
            "strategy_tips": [
                "Low HP makes it easy to kill",
                "Spit Web can be annoying early",
                "Watch for Curl Up - adds defense"
            ],
            "ascension_changes": {"asc_7": "+1 HP"},
            "danger_rating": 1
        },
        {
            "name": "Fat Gremlin",
            "type": "NORMAL",
            "hp_range": [13, 17],
            "hp_a7_plus": [14, 18],
            "move_pattern": [
                {"move": "Smash", "damage": 4, "probability": "100%"}
            ],
            "mechanics": ["Weak: Every 4th attack deals 4 damage instead of base"],
            "strategy_tips": [
                "Low threat, easy to kill",
                "Often appears in groups",
                "Minimal blocking needed"
            ],
            "ascension_changes": {"asc_2": "+1 damage (5)", "asc_7": "+1 HP"},
            "danger_rating": 1
        },
        {
            "name": "Gremlin Wizard",
            "type": "NORMAL",
            "hp_range": [21, 25],
            "hp_a7_plus": [22, 26],
            "move_pattern": [
                {"turn": 1, "move": "Charging", "effect": "Gain 1 Strength"},
                {"move": "Ultimate Blast", "damage": 25, "note": "After charging"}
            ],
            "mechanics": ["Charges Turn 1", "Ultimate Blast can OHKO if not careful"],
            "strategy_tips": [
                "Kill before Ultimate Blast or block 25+ damage",
                "High priority target in gremlin groups",
                "Weak reduces Ultimate Blast damage significantly"
            ],
            "ascension_changes": {"asc_2": "+2 Ultimate damage (27)", "asc_7": "+1 HP"},
            "danger_rating": 4
        },
        {
            "name": "Gremlin Thief (Sneaky Gremlin)",
            "type": "NORMAL",
            "hp_range": [10, 14],
            "hp_a7_plus": [11, 15],
            "move_pattern": [
                {"move": "Puncture", "damage": 9, "probability": "50%"},
                {"move": "Escape", "effect": "Steal 10-20 gold and flee", "probability": "50%"}
            ],
            "mechanics": ["Can steal gold and run away"],
            "strategy_tips": [
                "Kill quickly to prevent gold theft",
                "Low HP makes it easy to one-shot",
                "Prioritize if you need the gold"
            ],
            "ascension_changes": {"asc_2": "+1 damage (10)", "asc_7": "+1 HP"},
            "danger_rating": 2
        },
        {
            "name": "Shield Gremlin",
            "type": "NORMAL",
            "hp_range": [12, 15],
            "hp_a7_plus": [13, 16],
            "move_pattern": [
                {"turn": 1, "move": "Protect", "effect": "Give ally 7 Block"},
                {"move": "Shield Bash", "damage": 6, "probability": "After protecting"}
            ],
            "mechanics": ["Protects other enemies", "Makes group fights harder"],
            "strategy_tips": [
                "Kill first in multi-enemy fights",
                "Prevents burst damage on other enemies",
                "Low HP, easy to remove"
            ],
            "ascension_changes": {"asc_2": "+1 Block given (8)", "asc_7": "+1 HP"},
            "danger_rating": 2
        },
        {
            "name": "Fungi Beast",
            "type": "NORMAL",
            "hp_range": [22, 28],
            "hp_a7_plus": [24, 30],
            "move_pattern": [
                {"move": "Bite", "damage": 6, "probability": "60%"},
                {"move": "Grow", "effect": "Gain 3 Strength", "probability": "40%"}
            ],
            "mechanics": ["Scales with Strength over time"],
            "strategy_tips": [
                "Kill quickly before Strength stacks",
                "Weak is effective",
                "Moderate HP pool"
            ],
            "ascension_changes": {"asc_2": "+1 damage (7)", "asc_7": "+2 HP"},
            "danger_rating": 3
        },
        {
            "name": "Looter",
            "type": "NORMAL",
            "hp_range": [44, 48],
            "hp_a7_plus": [46, 50],
            "move_pattern": [
                {"move": "Mug", "damage": 10, "effect": "Steal 15 gold", "probability": "40%"},
                {"move": "Smoke Bomb", "effect": "Gain 6 Block", "probability": "30%"},
                {"move": "Lunge", "damage": 12, "probability": "30%"}
            ],
            "mechanics": ["Can steal significant gold", "Has defensive option"],
            "strategy_tips": [
                "Kill to recover stolen gold",
                "Higher HP than other Act 1 normals",
                "Can be tanky with Smoke Bomb"
            ],
            "ascension_changes": {"asc_2": "+1 damage", "asc_7": "+2 HP"},
            "danger_rating": 3
        }
    ]

def get_act1_elites() -> list:
    """Get Act 1 elite data."""
    return [
        {
            "name": "Gremlin Nob",
            "type": "ELITE",
            "hp_range": [82, 86],
            "hp_a7_plus": [85, 90],
            "move_pattern": [
                {"turn": 1, "move": "Bellow", "effect": "Gain 2 Strength + 3 Enrage"},
                {"move": "Skull Bash", "damage": 6, "probability": "67%"},
                {"move": "Rush", "damage": 14, "probability": "33%"}
            ],
            "mechanics": [
                "Enrage: Gains 2 Strength whenever you play a Skill",
                "Starts with Bellow (2 Strength immediately)",
                "Punishes Skill-heavy decks severely"
            ],
            "strategy_tips": [
                "Minimize Skill use - each triggers +2 Strength",
                "Attack-heavy strategies work best",
                "Powers are safe to play (not Skills)",
                "Front-load damage with Attacks only",
                "If playing many Skills, expect high damage scaling"
            ],
            "ascension_changes": {"asc_2": "+10% damage", "asc_7": "+3-5 HP", "asc_18": "Starts with 3 Strength instead of 2"},
            "danger_rating": 8
        },
        {
            "name": "Lagavulin",
            "type": "ELITE",
            "hp_range": [109, 111],
            "hp_a7_plus": [112, 115],
            "move_pattern": [
                {"turns": "1-3", "move": "Sleep (Asleep)", "effect": "Takes 50% less damage, does nothing"},
                {"turn": 4, "move": "Wake (once)", "effect": "Debuff: -1 Strength + -1 Dexterity"},
                {"move": "Attack", "damage": 18, "probability": "After waking"},
                {"move": "Siphon Soul", "effect": "Apply -1 Str, -1 Dex", "probability": "After waking"}
            ],
            "mechanics": [
                "Asleep for 3 turns (50% damage reduction)",
                "Wakes up and debuffs permanently",
                "Each attack deals 18 damage",
                "Can permanently cripple with -Str/-Dex"
            ],
            "strategy_tips": [
                "Wake it ASAP to avoid full HP pool + debuff",
                "Deal at least 1 damage per turn while asleep to wake it",
                "Once awake, kill quickly to minimize debuffs",
                "Very punishing if allowed to stack debuffs",
                "High HP pool - prepare for longer fight"
            ],
            "ascension_changes": {"asc_2": "+2 damage (20)", "asc_7": "+3-4 HP", "asc_18": "Debuff is -2 Str/Dex instead of -1"},
            "danger_rating": 7
        },
        {
            "name": "Sentries (3 Sentries)",
            "type": "ELITE",
            "hp_range": [38, 42],
            "hp_a7_plus": [39, 45],
            "move_pattern": [
                {"move": "Beam", "damage": [9, 10], "probability": "Each Sentry attacks independently"},
                {"move": "Bolt", "damage": [9, 10], "note": "Applies Dazed to deck"}
            ],
            "mechanics": [
                "3 enemies with ~40 HP each",
                "Add Dazes to your deck (clogs hand)",
                "Each acts independently",
                "Artifact charges block debuffs"
            ],
            "strategy_tips": [
                "Kill one Sentry ASAP to reduce damage",
                "AoE damage is extremely effective",
                "Dazes clog your deck - prioritize offense",
                "Artifact can save you from multiple Dazes",
                "Total HP: ~120-130, but split across 3 targets"
            ],
            "ascension_changes": {"asc_2": "+1 damage per Sentry", "asc_7": "+1-3 HP per Sentry", "asc_18": "Add 2 Dazes instead of 1"},
            "danger_rating": 6
        }
    ]

def get_act2_monsters() -> list:
    """Get Act 2 monster data."""
    return [
        {
            "name": "Spheric Guardian",
            "type": "NORMAL",
            "hp_range": [20, 24],
            "hp_a7_plus": [21, 25],
            "move_pattern": [
                {"turn": 1, "move": "Harden", "effect": "Gain 15 Block"},
                {"move": "Slam", "damage": 10, "probability": "After Harden"},
                {"move": "Activate", "effect": "Gain Artifact", "probability": "Occasional"}
            ],
            "mechanics": ["Artifact charges", "High Block on Turn 1"],
            "strategy_tips": [
                "Don't waste debuffs on Artifact charges",
                "Front-load damage on Turn 1 before Harden",
                "Attacks work better than debuffs"
            ],
            "ascension_changes": {"asc_2": "+1 damage", "asc_7": "+1 HP"},
            "danger_rating": 3
        },
        {
            "name": "Chosen",
            "type": "NORMAL",
            "hp_range": [95, 99],
            "hp_a7_plus": [97, 101],
            "move_pattern": [
                {"turn": 1, "move": "Poke", "damage": 5, "hits": 2},
                {"move": "Zap", "damage": 21, "probability": "After first Poke"},
                {"move": "Debilitate", "effect": "Apply 2 Weak + 2 Vulnerable", "probability": "Occasional"}
            ],
            "mechanics": ["High HP for normal enemy", "Strong debuffs"],
            "strategy_tips": [
                "Kill quickly despite high HP",
                "Debilitate makes fight much harder",
                "Zap hits hard - prepare defense"
            ],
            "ascension_changes": {"asc_2": "+10% damage", "asc_7": "+2 HP"},
            "danger_rating": 5
        },
        {
            "name": "Byrd",
            "type": "NORMAL",
            "hp_range": [25, 31],
            "hp_a7_plus": [27, 33],
            "move_pattern": [
                {"move": "Peck", "damage": 1, "hits": [3, 5]},
                {"move": "Swoop", "damage": 12},
                {"move": "Headbutt", "damage": 3}
            ],
            "mechanics": ["Flight: Takes 50% damage while airborne", "Multi-hit attacks"],
            "strategy_tips": [
                "Save AoE for when multiple Byrds present",
                "Flight makes it take longer to kill",
                "Low damage but annoying"
            ],
            "ascension_changes": {"asc_2": "+1 damage per attack", "asc_7": "+2 HP"},
            "danger_rating": 3
        },
        {
            "name": "Snecko",
            "type": "NORMAL",
            "hp_range": [114, 120],
            "hp_a7_plus": [116, 122],
            "move_pattern": [
                {"move": "Tail Whip", "damage": 8, "effect": "Apply 1 Vulnerable"},
                {"move": "Bite", "damage": 15},
                {"move": "Perplexing Gaze", "effect": "Randomize card costs in hand"}
            ],
            "mechanics": ["Perplexing Gaze randomizes costs (0-3 energy)", "Very high HP"],
            "strategy_tips": [
                "One of the highest HP normals in Act 2",
                "Cost randomization can brick your hand",
                "Plan for high cost cards"
            ],
            "ascension_changes": {"asc_2": "+10% damage", "asc_7": "+2 HP"},
            "danger_rating": 6
        }
    ]

def get_act2_elites() -> list:
    """Get Act 2 elite data."""
    return [
        {
            "name": "Gremlin Leader",
            "type": "ELITE",
            "hp_range": [140, 148],
            "hp_a7_plus": [145, 153],
            "move_pattern": [
                {"turn": 1, "move": "Rally", "effect": "Summon 3 minions + buff them"},
                {"move": "Stab", "damage": 6, "hits": 3}
            ],
            "mechanics": [
                "Summons 3 Gremlins (Fat, Shield, Wizard types)",
                "Buffs minions with Strength",
                "Moderate damage on its own"
            ],
            "strategy_tips": [
                "Kill minions first (especially Wizard)",
                "AoE damage is extremely valuable",
                "Leader has high HP - marathon fight",
                "Focus one minion at a time if no AoE"
            ],
            "ascension_changes": {"asc_2": "+10% damage", "asc_7": "+5 HP", "asc_18": "Minions start with 1 Strength"},
            "danger_rating": 7
        },
        {
            "name": "Slavers (3 Slavers)",
            "type": "ELITE",
            "hp_range": [46, 50],
            "hp_a7_plus": [48, 52],
            "move_pattern": [
                {"move": "Stab (Red)", "damage": 13},
                {"move": "Entangle (Blue)", "effect": "Shuffle Entangle into deck"},
                {"move": "Rake (Red)", "damage": 7, "hits": 2, "effect": "Apply 1 Weak"}
            ],
            "mechanics": [
                "3 enemies with different abilities",
                "Red Slaver: High damage",
                "Blue Slaver: Clogs deck with Entangles",
                "Task-based: Reduces Strength"
            ],
            "strategy_tips": [
                "Kill Blue first to stop Entangles",
                "Red deals most damage - second priority",
                "AoE shines here",
                "Entangles are Unplayable - dilute deck badly"
            ],
            "ascension_changes": {"asc_2": "+10% damage", "asc_7": "+2-4 HP each", "asc_18": "Start with Entangle in deck"},
            "danger_rating": 8
        },
        {
            "name": "Book of Stabbing",
            "type": "ELITE",
            "hp_range": [160, 168],
            "hp_a7_plus": [168, 176],
            "move_pattern": [
                {"move": "Single Stab", "damage": 6},
                {"move": "Multi-Stab", "damage": 6, "hits": "Based on Strength"},
                {"move": "Book Slam", "damage": 18, "effect": "Gain 2 Strength if no damage taken last turn"}
            ],
            "mechanics": [
                "Gains Strength if you don't damage it",
                "Scales infinitely if left alone",
                "Very high HP pool"
            ],
            "strategy_tips": [
                "MUST deal damage every turn",
                "Poison/Powers don't count - must attack",
                "Can spiral out of control quickly",
                "High HP - long fight if no burst"
            ],
            "ascension_changes": {"asc_2": "+10% damage", "asc_7": "+8 HP", "asc_18": "Gains 3 Strength instead of 2"},
            "danger_rating": 9
        }
    ]

def get_act3_monsters() -> list:
    """Get Act 3 monster data."""
    return [
        {
            "name": "Darkling",
            "type": "NORMAL",
            "hp_range": [48, 53],
            "hp_a7_plus": [50, 55],
            "move_pattern": [
                {"move": "Chomp", "damage": 11},
                {"move": "Harden", "effect": "Gain 9 Block"},
                {"move": "Regrow", "effect": "Revive if killed before others"}
            ],
            "mechanics": [
                "Always appears in pairs",
                "Revives at 50% HP if other Darkling alive",
                "Must kill both on same turn cycle"
            ],
            "strategy_tips": [
                "Burst damage to kill both in same cycle",
                "Don't focus one - split damage",
                "Regrow makes this punishing",
                "High HP for Act 3 normal"
            ],
            "ascension_changes": {"asc_2": "+10% damage", "asc_7": "+2 HP"},
            "danger_rating": 6
        },
        {
            "name": "Orb Walker",
            "type": "NORMAL",
            "hp_range": [87, 91],
            "hp_a7_plus": [90, 94],
            "move_pattern": [
                {"move": "Laser", "damage": 10},
                {"move": "Claw", "damage": 15}
            ],
            "mechanics": ["High HP", "Simple attack pattern"],
            "strategy_tips": [
                "Straightforward enemy",
                "Consistent damage output",
                "High HP pool for normal"
            ],
            "ascension_changes": {"asc_2": "+10% damage", "asc_7": "+3 HP"},
            "danger_rating": 4
        },
        {
            "name": "Spiker",
            "type": "NORMAL",
            "hp_range": [56, 60],
            "hp_a7_plus": [58, 62],
            "move_pattern": [
                {"move": "Cut", "damage": [7, 9]}
            ],
            "mechanics": ["Thorns: Reflects 3 damage when attacked"],
            "strategy_tips": [
                "Thorns damage adds up quickly",
                "Multi-hit attacks take heavy retaliation",
                "Single big hits preferred"
            ],
            "ascension_changes": {"asc_2": "+10% damage", "asc_7": "+2 HP", "asc_17": "+1 Thorns (4)"},
            "danger_rating": 5
        },
        {
            "name": "Exploder",
            "type": "NORMAL",
            "hp_range": [30, 34],
            "hp_a7_plus": [32, 36],
            "move_pattern": [
                {"turn": "1-2", "move": "Charging"},
                {"turn": 3, "move": "Explode", "damage": 30, "effect": "Dies after exploding"}
            ],
            "mechanics": ["Explodes for massive damage on Turn 3", "Kills itself"],
            "strategy_tips": [
                "Kill before Turn 3 explosion",
                "30 damage is deadly if unprepared",
                "Low HP makes it easy to kill in time"
            ],
            "ascension_changes": {"asc_2": "+5 explosion damage (35)", "asc_7": "+2 HP"},
            "danger_rating": 7
        },
        {
            "name": "Writhing Mass",
            "type": "NORMAL",
            "hp_range": [135, 145],
            "hp_a7_plus": [140, 150],
            "move_pattern": [
                {"move": "Flail", "damage": "8 x Strength", "note": "Gains Strength each turn"},
                {"move": "Wither", "effect": "Apply 3 Weak + 3 Vulnerable"},
                {"move": "Strong Strike", "damage": 18}
            ],
            "mechanics": ["Parasite: Gains 3 Strength per turn", "Very high HP"],
            "strategy_tips": [
                "Highest HP normal enemy in Act 3",
                "Kill ASAP before Parasite stacks",
                "Can become unkillable if delayed",
                "Debuff makes it even scarier"
            ],
            "ascension_changes": {"asc_2": "+10% damage", "asc_7": "+5 HP", "asc_17": "+4 Strength per turn instead of 3"},
            "danger_rating": 8
        }
    ]

def get_act3_elites() -> list:
    """Get Act 3 elite data."""
    return [
        {
            "name": "Giant Head",
            "type": "ELITE",
            "hp_range": [500, 520],
            "hp_a7_plus": [520, 540],
            "move_pattern": [
                {"move": "Count", "effect": "Increment counter"},
                {"turn": "Every 3rd turn", "move": "It Is Time", "damage": "13 x (cards played)"}
            ],
            "mechanics": [
                "Counts cards played",
                "Every 3rd turn: deals 13 damage per card played",
                "Massive HP pool"
            ],
            "strategy_tips": [
                "Play minimal cards before Count triggers",
                "Powers are safe - play before Turn 3",
                "Can one-shot you if too many cards played",
                "Very long fight due to HP",
                "Aim for <5 cards per cycle"
            ],
            "ascension_changes": {"asc_2": "+1 damage per card (14)", "asc_7": "+20 HP", "asc_18": "Counts every 2 turns instead of 3"},
            "danger_rating": 9
        },
        {
            "name": "Nemesis",
            "type": "ELITE",
            "hp_range": [200, 210],
            "hp_a7_plus": [210, 220],
            "move_pattern": [
                {"turn": 1, "move": "Debuff", "effect": "Apply 3 Burns to deck"},
                {"move": "Attack", "damage": [30, 35]},
                {"move": "Scythe", "damage": 45}
            ],
            "mechanics": [
                "Intangible: First attack each turn deals 1 damage",
                "Very high single-target damage",
                "Burns clog deck"
            ],
            "strategy_tips": [
                "First hit per turn does 1 - follow up with damage",
                "Needs multiple attacks per turn",
                "Burns make deck inconsistent",
                "Multi-hit attacks are MVP"
            ],
            "ascension_changes": {"asc_2": "+5 damage per attack", "asc_7": "+10 HP", "asc_18": "Adds 5 Burns instead of 3"},
            "danger_rating": 10
        },
        {
            "name": "Reptomancer",
            "type": "ELITE",
            "hp_range": [180, 190],
            "hp_a7_plus": [190, 200],
            "move_pattern": [
                {"turn": 1, "move": "Snake Strike", "damage": 13, "effect": "Summon 2 Daggers"},
                {"move": "Big Bite", "damage": 30},
                {"move": "Double Strike", "damage": 13, "hits": 2}
            ],
            "mechanics": [
                "Summons 2 Daggers (25 HP each, 25 damage attacks)",
                "Daggers attack BEFORE Reptomancer",
                "Re-summons Daggers when killed"
            ],
            "strategy_tips": [
                "AoE is almost mandatory",
                "Kill Daggers ASAP - they hit hard",
                "Without AoE, can be unwinnable",
                "Daggers respawn - prioritize killing them each turn",
                "Most dangerous elite if no AoE"
            ],
            "ascension_changes": {"asc_2": "+10% damage (all)", "asc_7": "+10 HP (all)", "asc_18": "Daggers have 40 HP instead of 25"},
            "danger_rating": 10
        }
    ]

def create_boss_data_from_json() -> dict:
    """Load boss data from existing bosses.json and restructure for enemy format."""
    bosses_file = RAW_DIR / "bosses.json"
    
    if not bosses_file.exists():
        print("Warning: bosses.json not found, creating empty boss data")
        return {1: [], 2: [], 3: []}
    
    with open(bosses_file, encoding="utf-8") as f:
        bosses_data = json.load(f)
    
    bosses_by_act = {1: [], 2: [], 3: []}
    
    # Map act names to numbers
    act_map = {"act1": 1, "act2": 2, "act3": 3, "act4": 3}  # Act 4 boss goes in act3
    
    for act_name, act_bosses in bosses_data.items():
        act_num = act_map.get(act_name)
        if not act_num:
            continue
        
        for boss_name, boss_info in act_bosses.items():
            boss_entry = {
                "name": boss_name,
                "type": "BOSS",
                "act": act_num,
                "hp_range": boss_info.get("hp", [None, None]),
                "mechanics": boss_info.get("mechanics", []),
                "strategy_tips": boss_info.get("strategy_tips", [])
            }
            bosses_by_act[act_num].append(boss_entry)
    
    return bosses_by_act

def save_json(path: Path, data: dict):
    """Save JSON file with nice formatting."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"✓ Created {path.name} ({data['_meta']['count']} enemies)")

def main():
    print("=" * 60)
    print("CREATING COMPREHENSIVE ENEMY KNOWLEDGE BASE")
    print("=" * 60)
    
    # Load boss data from existing bosses.json
    print("\n📄 Loading boss data from bosses.json...")
    bosses_by_act = create_boss_data_from_json()
    
    # Get monster and elite data
    print("\n🎮 Loading monster/elite data from STS knowledge...")
    act1_monsters = get_act1_monsters()
    act1_elites = get_act1_elites()
    act2_monsters = get_act2_monsters()
    act2_elites = get_act2_elites()
    act3_monsters = get_act3_monsters()
    act3_elites = get_act3_elites()
    
    print(f"  Act 1: {len(act1_monsters)} monsters, {len(act1_elites)} elites, {len(bosses_by_act[1])} bosses")
    print(f"  Act 2: {len(act2_monsters)} monsters, {len(act2_elites)} elites, {len(bosses_by_act[2])} bosses")
    print(f"  Act 3: {len(act3_monsters)} monsters, {len(act3_elites)} elites, {len(bosses_by_act[3])} bosses")
    
    # Save Act 1 files
    print("\n💾 Saving Act 1 enemy files...")
    
    act1_monsters_file = {
        "_meta": create_meta(
            "enemies_act1_monsters.json",
            "Act 1 normal monsters with stats, patterns, and strategy",
            "Load when: in Act 1, planning hallway fights, asking about Act 1 enemies",
            len(act1_monsters)
        ),
        "monsters": act1_monsters
    }
    save_json(KNOWLEDGE_DIR / "enemies_act1_monsters.json", act1_monsters_file)
    
    act1_elites_file = {
        "_meta": create_meta(
            "enemies_act1_elites.json",
            "Act 1 elite enemies with comprehensive mechanics and strategy",
            "Load when: planning elite fights in Act 1, asking about Act 1 elites",
            len(act1_elites)
        ),
        "elites": act1_elites
    }
    save_json(KNOWLEDGE_DIR / "enemies_act1_elites.json", act1_elites_file)
    
    act1_bosses_file = {
        "_meta": create_meta(
            "enemies_act1_bosses.json",
            "Act 1 boss fights with full move patterns and strategy from wiki",
            "Load when: planning boss fight in Act 1, asking about Act 1 bosses",
            len(bosses_by_act[1])
        ),
        "bosses": bosses_by_act[1]
    }
    save_json(KNOWLEDGE_DIR / "enemies_act1_bosses.json", act1_bosses_file)
    
    # Save Act 2 files
    print("\n💾 Saving Act 2 enemy files...")
    
    act2_monsters_file = {
        "_meta": create_meta(
            "enemies_act2_monsters.json",
            "Act 2 normal monsters with stats, patterns, and strategy",
            "Load when: in Act 2, planning hallway fights, asking about Act 2 enemies",
            len(act2_monsters)
        ),
        "monsters": act2_monsters
    }
    save_json(KNOWLEDGE_DIR / "enemies_act2_monsters.json", act2_monsters_file)
    
    act2_elites_file = {
        "_meta": create_meta(
            "enemies_act2_elites.json",
            "Act 2 elite enemies with comprehensive mechanics and strategy",
            "Load when: planning elite fights in Act 2, asking about Act 2 elites",
            len(act2_elites)
        ),
        "elites": act2_elites
    }
    save_json(KNOWLEDGE_DIR / "enemies_act2_elites.json", act2_elites_file)
    
    act2_bosses_file = {
        "_meta": create_meta(
            "enemies_act2_bosses.json",
            "Act 2 boss fights with full move patterns and strategy from wiki",
            "Load when: planning boss fight in Act 2, asking about Act 2 bosses",
            len(bosses_by_act[2])
        ),
        "bosses": bosses_by_act[2]
    }
    save_json(KNOWLEDGE_DIR / "enemies_act2_bosses.json", act2_bosses_file)
    
    # Save Act 3 files
    print("\n💾 Saving Act 3 enemy files...")
    
    act3_monsters_file = {
        "_meta": create_meta(
            "enemies_act3_monsters.json",
            "Act 3 normal monsters with stats, patterns, and strategy",
            "Load when: in Act 3, planning hallway fights, asking about Act 3 enemies",
            len(act3_monsters)
        ),
        "monsters": act3_monsters
    }
    save_json(KNOWLEDGE_DIR / "enemies_act3_monsters.json", act3_monsters_file)
    
    act3_elites_file = {
        "_meta": create_meta(
            "enemies_act3_elites.json",
            "Act 3 elite enemies with comprehensive mechanics and strategy",
            "Load when: planning elite fights in Act 3, asking about Act 3 elites",
            len(act3_elites)
        ),
        "elites": act3_elites
    }
    save_json(KNOWLEDGE_DIR / "enemies_act3_elites.json", act3_elites_file)
    
    act3_bosses_file = {
        "_meta": create_meta(
            "enemies_act3_bosses.json",
            "Act 3 boss fights with full move patterns and strategy from wiki",
            "Load when: planning boss fight in Act 3, asking about Act 3 bosses",
            len(bosses_by_act[3])
        ),
        "bosses": bosses_by_act[3]
    }
    save_json(KNOWLEDGE_DIR / "enemies_act3_bosses.json", act3_bosses_file)
    
    print("\n" + "=" * 60)
    print("✅ ENEMY KNOWLEDGE BASE COMPLETE!")
    print("=" * 60)
    print(f"\nCreated 9 comprehensive enemy files:")
    print("  • 3 monster files (Act 1/2/3)")
    print("  • 3 elite files (Act 1/2/3)")
    print("  • 3 boss files (Act 1/2/3 - parsed from HTML)")
    print(f"\nTotal enemies documented: {len(act1_monsters + act1_elites + act2_monsters + act2_elites + act3_monsters + act3_elites) + sum(len(v) for v in bosses_by_act.values())}")

if __name__ == "__main__":
    main()
