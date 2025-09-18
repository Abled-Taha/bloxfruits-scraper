import json
from typing import Any, Dict

def read_file(FILE:str) -> Dict[str, Any]:
    """
    Read the file and return its contents as a dictionary.
    If the file does not exist or is empty, return an empty dictionary.
    """
    try:
        with open(FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
            elif isinstance(data, list):
                return data
            else:
                print(f"Warning: {FILE} does not contain a valid JSON object.")
                return {}
    except FileNotFoundError:
        print(f"Warning: {FILE} not found. Returning empty dictionary.")
        return {}
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from {FILE}: {e}")
        return {}
      
def write_file(FILE:str, data: Dict[str, Any]) -> None:
    """
    Write the given dictionary to the file.
    Creates the file if it does not exist as well as the directory.
    """
    import os
    os.makedirs(os.path.dirname(FILE), exist_ok=True)
    try:
        with open(FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except IOError as e:
        print(f"Error writing to {FILE}: {e}")
        
def check_file_validity(FILE:str, seconds:int=7200) -> bool:
    """
    Check when the file was last modified.
    Returns True if modified within the last 2 hours and not an empty object, False otherwise.
    """
    import os
    import time

    try:
        mod_time = os.path.getmtime(FILE)
        current_time = time.time()
        # Check if modified within the last 2 hours (7200 seconds) / given time
        return (current_time - mod_time) < seconds and os.path.getsize(FILE) > 2  # not empty {}
    except FileNotFoundError:
        print(f"Warning: {FILE} not found.")
        return False
      
def write_fruits_info_file() -> None:
    """
    Writes the fruit info JSON file.
    """
    FILE = "storage/info.json"
    fruits = [
        # Common Fruits
        {"name": "Rocket", "rarity": "Common", "type": "Natural", "image": "", "price": 5000, "robux_price": 50, "awakening": 0, "upgrading": [], "skins":[]},
        {"name": "Spin", "rarity": "Common", "type": "Natural", "image": "", "price": 7500, "robux_price": 75, "awakening": 0, "upgrading": [], "skins":[]},
        {"name": "Blade", "rarity": "Common", "type": "Natural", "image": "", "price": 30000, "robux_price": 100, "awakening": 0, "upgrading": [], "skins":[]},
        {"name": "Spring", "rarity": "Common", "type": "Natural", "image": "", "price": 60000, "robux_price": 180, "awakening": 0, "upgrading": [], "skins":[]},
        {"name": "Bomb", "rarity": "Common", "type": "Natural", "image": "", "price": 80000, "robux_price": 220, "awakening": 0, "upgrading": [], "skins":[]},
        {"name": "Smoke", "rarity": "Common", "type": "Elemental", "image": "", "price": 100000, "robux_price": 250, "awakening": 0, "upgrading": [], "skins":[]},
        {"name": "Spike", "rarity": "Common", "type": "Natural", "image": "", "price": 180000, "robux_price": 380, "awakening": 0, "upgrading": [], "skins":[]},
        # Uncommon Fruits
        {"name": "Flame", "rarity": "Uncommon", "type": "Elemental", "image": "", "price": 250000, "robux_price": 550, "awakening": 14500, "upgrading": [], "skins":[]},
        {"name": "Ice", "rarity": "Uncommon", "type": "Elemental", "image": "", "price": 350000, "robux_price": 750, "awakening": 14500, "upgrading": [], "skins":[]},
        {"name": "Sand", "rarity": "Uncommon", "type": "Elemental", "image": "", "price": 420000, "robux_price": 850, "awakening": 14500, "upgrading": [], "skins":[]},
        {"name": "Dark", "rarity": "Uncommon", "type": "Elemental", "image": "", "price": 500000, "robux_price": 950, "awakening": 14500, "upgrading": [], "skins":[]},
        {"name": "Eagle", "rarity": "Uncommon", "type": "Beast", "image": "", "price": 550000, "robux_price": 975, "awakening": 0, "upgrading": [{"name":"Fragments","amount":2600},{"name":"Fire Feather","amount":3},{"name":"Electric Wing","amount":5},{"name":"Fool's Gold","amount":2},{"name":"Angel Wings","amount":16}], "skins":[]},
        {"name": "Diamond", "rarity": "Uncommon", "type": "Natural", "image": "", "price": 600000, "robux_price": 1000, "awakening": 0, "upgrading": [], "skins":[{"name":"Emerald","rarity":"Uncommon","chromatic":True,"image":"","ingame_image":"","obtainment":"Was obtainable from the Summer Gacha for 500 Summer Tokens, in Update 27.2. Now obtainable only from trading."},{"name":"Rose Quartz","rarity":"Uncommon","chromatic":True,"image":"","ingame_image":"","obtainment":"Was obtainable from the Summer Gacha for 500 Summer Tokens, in Update 27.2. Now obtainable only from trading."},{"name":"Topaz","rarity":"Uncommon","chromatic":True,"image":"","ingame_image":"","obtainment":"Was obtainable from the Summer Gacha for 500 Summer Tokens, in Update 27.2. Now obtainable only from trading."},{"name":"Ruby","rarity":"Rare","chromatic":True,"image":"","ingame_image":"","obtainment":"Was obtainable from the Red Gacha for 250 Oni Tokens, in Update 27.2. Now obtainable only from trading."}]},
        # Rare Fruits
        {"name": "Light", "rarity": "Rare", "type": "Elemental", "image": "", "price": 650000, "robux_price": 1100, "awakening": 14500, "upgrading": [], "skins":[]},
        {"name": "Rubber", "rarity": "Rare", "type": "Natural", "image": "", "price": 750000, "robux_price": 1200, "awakening": 0, "upgrading": [], "skins":[]},
        {"name": "Ghost", "rarity": "Rare", "type": "Natural", "image": "", "price": 940000, "robux_price": 1275, "awakening": 0, "upgrading": [], "skins":[]},
        {"name": "Magma", "rarity": "Rare", "type": "Elemental", "image": "", "price": 960000, "robux_price": 1300, "awakening": 14500, "upgrading": [], "skins":[]},
        # Legendary Fruits
        {"name": "Quake", "rarity": "Legendary", "type": "Natural", "image": "", "price": 1000000, "robux_price": 1500, "awakening": 17000, "upgrading": [], "skins":[]},
        {"name": "Buddha", "rarity": "Legendary", "type": "Beast", "image": "", "price": 1200000, "robux_price": 1650, "awakening": 14500, "upgrading": [], "skins":[]},
        {"name": "Love", "rarity": "Legendary", "type": "Natural", "image": "", "price": 1300000, "robux_price": 1700, "awakening": 0, "upgrading": [], "skins":[]},
        {"name": "Creation", "rarity": "Legendary", "type": "Natural", "image": "", "price": 1400000, "robux_price": 1750, "awakening": 0, "upgrading": [], "skins":[]},
        {"name": "Spider", "rarity": "Legendary", "type": "Natural", "image": "", "price": 1500000, "robux_price": 1800, "awakening": 17300, "upgrading": [], "skins":[]},
        {"name": "Sound", "rarity": "Legendary", "type": "Natural", "image": "", "price": 1700000, "robux_price": 1900, "awakening": 0, "upgrading": [], "skins":[]},
        {"name": "Phoenix", "rarity": "Legendary", "type": "Beast", "image": "", "price": 1800000, "robux_price": 2000, "awakening": 18500, "upgrading": [], "skins":[]},
        {"name": "Portal", "rarity": "Legendary", "type": "Natural", "image": "", "price": 1900000, "robux_price": 2000, "awakening": 0, "upgrading": [], "skins":[]},
        {"name": "Lightning", "rarity": "Legendary", "type": "Elemental", "image": "", "price": 2100000, "robux_price": 2100, "awakening": 0, "upgrading": [{"name":"Fragments","amount":21500},{"name":"Volt Capsule","amount":4},{"name":"Electric Wing","amount":13},{"name":"Angel Wings","amount":3}], "skins":[{"name":"Purple","rarity":"Legendary","chromatic":True,"image":"","ingame_image":"","obtainment":"Was obtainable from the Summer Gacha for 500 Summer Tokens, in Update 27.1. Now obtainable only from trading."},{"name":"Yellow","rarity":"Legendary","chromatic":True,"image":"","ingame_image":"","obtainment":"Was obtainable from the Summer Gacha for 500 Summer Tokens, in Update 27.1. Now obtainable only from trading."},{"name":"Green","rarity":"Legendary","chromatic":True,"image":"","ingame_image":"","obtainment":"Was obtainable from the Summer Gacha for 500 Summer Tokens, in Update 27.1. Now obtainable only from trading."}]},
        {"name": "Pain", "rarity": "Legendary", "type": "Natural", "image": "", "price": 2300000, "robux_price": 2200, "awakening": 0, "upgrading": [{"name":"Fragments","amount":19000},{"name":"Nightmare Catcher","amount":4},{"name":"Ectoplasm","amount":16},{"name":"Magma Ore","amount":3}], "skins":[{"name":"Sadness","rarity":"Legendary","chromatic":True,"image":"","ingame_image":"","obtainment":"Was obtainable from the Summer Gacha for 500 Summer Tokens. Now obtainable only from trading."},{"name":"Torment","rarity":"Legendary","chromatic":True,"image":"","ingame_image":"","obtainment":"Was obtainable from the Summer Gacha for 500 Summer Tokens. Now obtainable only from trading."},{"name":"Frustration","rarity":"Legendary","chromatic":True,"image":"","ingame_image":"","obtainment":"Was obtainable from the Summer Gacha for 500 Summer Tokens. Now obtainable only from trading."},{"name":"Celestial","rarity":"Legendary","chromatic":True,"image":"","ingame_image":"","obtainment":"Was obtainable from the Celestial Gacha for 250 Celestial Tokens. Now obtainable only from trading."}]},
        {"name": "Blizzard", "rarity": "Legendary", "type": "Elemental", "image": "", "price": 2400000, "robux_price": 2250, "awakening": 0, "upgrading": [], "skins":[]},
        # Mythical Fruits
        {"name": "Gravity", "rarity": "Mythical", "type": "Natural", "image": "", "price": 2500000, "robux_price": 2300, "awakening": 0, "upgrading": [{"name":"Fragments","amount":19000},{"name":"Meteorite","amount":3},{"name":"Moonstone","amount":3},{"name":"Mystic Droplet","amount":15},{"name":"Radioactive Material","amount":12}], "skins":[]},
        {"name": "Mammoth", "rarity": "Mythical", "type": "Beast", "image": "", "price": 2700000, "robux_price": 2350, "awakening": 0, "upgrading": [], "skins":[]},
        {"name": "T-Rex", "rarity": "Mythical", "type": "Beast", "image": "", "price": 2700000, "robux_price": 2350, "awakening": 0, "upgrading": [], "skins":[]},
        {"name": "Dough", "rarity": "Mythical", "type": "Elemental", "image": "", "price": 2800000, "robux_price": 2400, "awakening": 18500, "upgrading": [], "skins":[]},
        {"name": "Shadow", "rarity": "Mythical", "type": "Natural", "image": "", "price": 2900000, "robux_price": 2425, "awakening": 0, "upgrading": [], "skins":[]},
        {"name": "Venom", "rarity": "Mythical", "type": "Natural", "image": "", "price": 3000000, "robux_price": 2450, "awakening": 0, "upgrading": [], "skins":[]},
        {"name": "Control", "rarity": "Mythical", "type": "Natural", "image": "", "price": 3200000, "robux_price": 2500, "awakening": 0, "upgrading": [], "skins":[]},
        {"name": "Gas", "rarity": "Mythical", "type": "Elemental", "image": "", "price": 3200000, "robux_price": 2500, "awakening": 0, "upgrading": [], "skins":[]},
        {"name": "Spirit", "rarity": "Mythical", "type": "Natural", "image": "", "price": 3400000, "robux_price": 2550, "awakening": 0, "upgrading": [], "skins":[]},
        {"name": "Leopard", "rarity": "Mythical", "type": "Beast", "image": "", "price": 5000000, "robux_price": 3000, "awakening": 0, "upgrading": [], "skins":[]},
        {"name": "Yeti", "rarity": "Mythical", "type": "Beast", "image": "", "price": 5000000, "robux_price": 3000, "awakening": 0, "upgrading": [], "skins":[]},
        {"name": "Kitsune", "rarity": "Mythical", "type": "Beast", "image": "", "price": 8000000, "robux_price": 4000, "awakening": 0, "upgrading": [], "skins":[]},
        {"name": "Dragon", "rarity": "Mythical", "type": "Beast", "image": "", "price": 15000000, "robux_price": 5000, "awakening": 0, "upgrading": [], "skins":[]},
    ]
    
    import os, json
    os.makedirs(os.path.dirname(FILE), exist_ok=True)
    try:
        with open(FILE, "w", encoding="utf-8") as f:
            json.dump(fruits, f, ensure_ascii=False, indent=2)
    except IOError as e:
        print(f"Error writing to {FILE}: {e}")
        return {}