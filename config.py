# config.py
from pathlib import Path
import json

DEFAULT_COD2_PATH = r"C:\Program Files\Call of Duty 2"

CONFIG_FILE = Path(__file__).parent / "config.json"

def load_config():
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_config(data):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

# Default CSV template - generates correct levelBriefing line
def DEFAULT_CSV_CONTENT(mapname: str) -> str:
    return f"levelBriefing,loadscreen_{mapname}\n"

# Minimal main.gsc template
MINIMAL_MAIN_GSC = """#include maps\\mp\\_utility;
#include maps\\mp\\_load;

main()
{{
    maps\\mp\\{mapname}_fx::main();
    maps\\mp\\_load::main();

    // ambientPlay("{mapname_short}");

    // Factions example
    game["allies"] = "british";
    game["axis"] = "german";
    game["attackers"] = "allies";
    game["defenders"] = "axis";
}}
"""