"""Configuration helpers for persistent application settings.

Provides load/save helpers for config.json and compile_settings.json,
plus default file templates used by the mapping tool.
"""

from pathlib import Path
import json

DEFAULT_COD2_PATH = r"C:\Program Files\Call of Duty 2"

CONFIG_FILE = Path(__file__).parent / "config.json"
COMPILE_SETTINGS_FILE = Path(__file__).parent / "compile_settings.json"

def load_config():
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_config(data):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def load_compile_settings() -> dict:
    """Load per-map compile tool settings. Structure: { "mapname": { ...settings... }, ... }"""
    if COMPILE_SETTINGS_FILE.exists():
        try:
            with open(COMPILE_SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
        except Exception:
            return {}
    return {}

def save_compile_settings(data: dict) -> None:
    """Save per-map compile tool settings."""
    with open(COMPILE_SETTINGS_FILE, "w", encoding="utf-8") as f:
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