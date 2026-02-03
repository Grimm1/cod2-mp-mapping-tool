#!/usr/bin/env python3
"""Debug script to check file paths"""
from pathlib import Path

# Read the config to get the CoD2 path
import json
config_file = Path(__file__).parent / "config.json"
if config_file.exists():
    with open(config_file) as f:
        config = json.load(f)
    cod2_path = Path(config.get("last_cod2_path", ""))
    mapname = config.get("last_selected_map", "")
    
    print(f"CoD2 Path: {cod2_path}")
    print(f"Map Name: {mapname}")
    print(f"CoD2 exists: {cod2_path.exists()}")
    print()
    
    if mapname:
        files = {
            "main_gsc": cod2_path / "maps" / "mp" / f"{mapname}.gsc",
            "fx_gsc":   cod2_path / "maps" / "mp" / f"{mapname}_fx.gsc",
            "sun":      cod2_path / "sun" / f"{mapname}.sun",
            "csv":      cod2_path / "maps" / "mp" / f"{mapname}.csv",
            "arena":    cod2_path / "mp" / f"{mapname}.arena",
        }
        
        for name, path in files.items():
            exists = "✓" if path.is_file() else "✗"
            print(f"{exists} {name:12} {path}")
            if not path.is_file():
                print(f"  Parent dir exists: {path.parent.exists()}")
                print(f"  Parent dir path: {path.parent}")
else:
    print("config.json not found")
