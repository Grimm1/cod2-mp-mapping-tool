# helpers.py (COMPLETE FINAL VERSION - with hidden FX extraction)

from pathlib import Path
import os
import re
import json
from typing import List, Dict, Set

def get_map_list(cod2_path: str) -> list[str]:
    """Returns list of map names from map_source folder"""
    map_source = Path(cod2_path) / "map_source"
    if not map_source.is_dir():
        return []

    maps = []
    for file in map_source.glob("*.map"):
        name = file.stem
        if name.startswith("mp_") or name.startswith("dupe_"):
            maps.append(name)
    return sorted(maps)


def ensure_directories(cod2_path: str, mapname: str):
    """Creates necessary folders under maps/mp, sun, mp"""
    base = Path(cod2_path)
    
    folders = [
        base / "maps" / "mp",
        base / "sun",
        base / "mp"
    ]
    
    for folder in folders:
        folder.mkdir(parents=True, exist_ok=True)


def read_file_if_exists(path: Path) -> str:
    if path.is_file():
        try:
            return path.read_text(encoding="utf-8", errors="replace")
        except:
            return "# Error reading file"
    return ""


def write_file(path: Path, content: str, overwrite: bool = False):
    if path.exists() and not overwrite:
        raise FileExistsError(f"File already exists: {path}\nUse overwrite mode.")
    
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")


def get_xmodel_dependencies(cod2_path: str, model_name: str) -> dict[str, any]:
    """
    Parses a CoD2 xmodel file and returns the required dependencies.
    """
    xmodel_path = Path(cod2_path) / "main" / "xmodel" / model_name

    suggested_parts = model_name + "0"

    if not xmodel_path.is_file():
        return {
            "surfs": [],
            "materials": [],
            "parts": suggested_parts
        }

    data = xmodel_path.read_bytes()

    pos = 0
    candidates = []
    while pos < len(data):
        start = pos
        while pos < len(data) and data[pos] != 0:
            pos += 1
        if pos > start:
            try:
                s = data[start:pos].decode('ascii', errors='ignore').strip()
                if s:
                    candidates.append(s)
            except:
                pass
        pos += 1

    pattern = re.compile(r'^[a-z0-9_]+$')
    filtered = []
    for s in candidates:
        if (len(s) >= 6 and
            pattern.match(s) and
            ('_' in s or any(c.isdigit() for c in s))):
            filtered.append(s)

    materials = []
    surfs = []
    seen_mat = set()
    seen_surf = set()

    for name in filtered:
        if name.startswith('mtl_'):
            if name not in seen_mat:
                materials.append(name)
                seen_mat.add(name)
        else:
            if name not in seen_surf:
                surfs.append(name)
                seen_surf.add(name)

    return {
        "surfs": surfs,
        "materials": materials,
        "parts": suggested_parts
    }


def parse_map_entities(file_path: Path) -> List[Dict[str, str]]:
    """Parses only keyvalue entities (ignores brushes/patches for speed)"""
    if not file_path.is_file():
        return []

    text = file_path.read_text(encoding="latin1", errors="replace")
    lines = [line.rstrip() for line in text.splitlines()]

    entities = []
    current = None
    for line in lines:
        stripped = line.strip()
        if stripped == "{":
            current = {}
        elif stripped == "}":
            if current is not None:
                entities.append(current)
                current = None
        elif current is not None and not stripped.startswith("//"):
            match = re.match(r'\s*"([^"]+)"\s*"([^"]*)"\s*', line)
            if match:
                key, value = match.groups()
                current[key] = value
    return entities


def get_textures_from_material(cod2_path: str, material_name: str) -> set[str]:
    """
    Parses a binary material file (NO extension) and extracts referenced texture base names (without .iwi).
    Allows '&' and '-' in names for specular maps, etc.
    """
    cod2 = Path(cod2_path)

    possible_paths = [
        cod2 / "raw" / "materials" / material_name,
        cod2 / "main" / "materials" / material_name
    ]

    material_path = None
    for p in possible_paths:
        if p.is_file():
            material_path = p
            break

    if not material_path:
        print(f"  [DEBUG] No material file found for {material_name}")
        return set()

    print(f"  [DEBUG] Parsing material: {material_path.name}")

    data = material_path.read_bytes()

    pos = 0
    candidates = []
    while pos < len(data):
        start = pos
        while pos < len(data) and data[pos] != 0:
            pos += 1
        if pos > start:
            try:
                s = data[start:pos].decode('ascii', errors='ignore').strip()
                if s:
                    candidates.append(s)
            except:
                pass
        pos += 1

    exclude_keys = {
        "colorMap", "normalMap", "specularMap", "detailMap", "detailScale",
        "wallpaper", "phong_replace_detail", "specularColorMap", "alphaMap",
        "alphaTest", "phong_alphatest_spec", "specularFactor", "glossScale",
        "bumpMap", "heightMap", "lightMap", "diffuseMap", "emissiveMap",
        "qer_editorimage", "qer_trans", "surfaceparm", "nomipmaps"
    }

    textures = set()
    for s in candidates:
        if (len(s) > 3 and
            re.match(r'^[a-zA-Z0-9_~/\.&\-]+$', s) and
            s not in exclude_keys and
            not s.startswith(("phong_", "mtl_", "qer_", "surfaceparm"))):

            base = Path(s).stem
            if base:
                textures.add(base)

    if textures:
        print(f"  → Textures extracted: {', '.join(sorted(textures))}")
    else:
        print(f"  → No textures found")

    return textures


def get_missing_custom_assets_from_map(
    cod2_path: str,
    map_name: str,
    xmodel_json: str = "lists/xmodel_list.json",
    material_json: str = "lists/materials.json"
) -> dict:
    """
    Parses map + prefabs → finds custom xmodels, materials, textures, and hidden FX references.

    Returns:
        dict with:
            missing_xmodels: list[str]
            missing_materials: list[str]
            missing_textures: list[str]     # .iwi filenames
            hidden_fx_paths: list[str]      # NEW: full "fx/..." paths (with .efx)
            dropped_xmodels: int
            dropped_materials: int
            total_xmodels: int
            total_materials: int
            prefabs_processed: list[str]
    """
    cod2 = Path(cod2_path)
    main_map_path = cod2 / "map_source" / f"{map_name}.map"
    prefab_dir = cod2 / "map_source" / "prefabs"

    if not main_map_path.is_file():
        raise FileNotFoundError(f"Main map not found: {main_map_path}")

    known_xmodels: Set[str] = set()
    xjson_path = Path(xmodel_json)
    if xjson_path.is_file():
        try:
            with open(xjson_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                known_xmodels = {item["name"] for item in data if isinstance(item, dict) and "name" in item}
        except Exception as e:
            print(f"[WARNING] Failed to load {xmodel_json}: {e}")

    known_materials: Set[str] = set()
    mjson_path = Path(material_json)
    if mjson_path.is_file():
        try:
            with open(mjson_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                known_materials = {item["name"] for item in data if isinstance(item, dict) and "name" in item}
        except Exception as e:
            print(f"[WARNING] Failed to load {material_json}: {e}")

    used_xmodels: Set[str] = set()
    used_materials: Set[str] = set()
    hidden_fx_paths: Set[str] = set()
    prefabs_processed: List[str] = []
    visited: Set[str] = set()

    brush_mat_regex = re.compile(r'\)\s*\)\s*\)\s*([a-z0-9_/]+)')
    cm_mat_regex = re.compile(r'(?:curve|mesh|patchDef2)\s*\{\s*([a-z0-9_/]+)')

    def recurse(map_path: Path):
        print(f"  Parsing: {map_path.name}")
        text = map_path.read_text(encoding="latin1", errors="replace")

        # Materials from brushes/curves
        used_materials.update(brush_mat_regex.findall(text))
        for match in cm_mat_regex.finditer(text):
            used_materials.add(match.group(1))

        # Entities
        entities = parse_map_entities(map_path)
        for ent in entities:
            classname = ent.get("classname", "").lower()

            # XModels from misc_model
            if classname == "misc_model":
                model = ent.get("model", "")
                if model.startswith("xmodel/"):
                    name = model[len("xmodel/"):].strip()
                    if name:
                        used_xmodels.add(name)

            # Hidden FX from various keys
            for key in ["script_noteworthy", "fx", "effect", "corona", "script_fx", "targetname"]:
                if key in ent:
                    val = ent[key].strip()
                    if "fx/" in val.lower() or val.lower().startswith("fx/"):
                        # Normalize
                        fx_path = val.replace("\\", "/").strip()
                        if not fx_path.lower().endswith(".efx"):
                            fx_path += ".efx"
                        hidden_fx_paths.add(fx_path)

            # Prefab recursion
            if classname == "misc_prefab":
                prefab_raw = ent.get("model", "")
                if prefab_raw and prefab_raw.endswith(".map"):
                    prefab_rel = prefab_raw.removeprefix("prefabs/")
                    prefab_path = prefab_dir / prefab_rel
                    key = str(prefab_path.resolve())
                    if prefab_path.is_file() and key not in visited:
                        visited.add(key)
                        prefabs_processed.append(prefab_path.name)
                        recurse(prefab_path)

    recurse(main_map_path)

    missing_xmodels = sorted(used_xmodels - known_xmodels)
    missing_materials = sorted(used_materials - known_materials)

    dropped_xmodels = len(used_xmodels & known_xmodels)
    dropped_materials = len(used_materials & known_materials)

    total_xmodels = len(used_xmodels)
    total_materials = len(used_materials)

    missing_textures = set()
    print(f"\nParsing {len(missing_materials)} missing materials for textures...")
    for mat in missing_materials:
        tex_bases = get_textures_from_material(cod2_path, mat)
        missing_textures.update(tex_bases)

    missing_iwis = sorted([t + ".iwi" for t in missing_textures])

    # Final hidden FX list (deduped, sorted)
    hidden_fx_list = sorted(hidden_fx_paths)

    return {
        "missing_xmodels": missing_xmodels,
        "missing_materials": missing_materials,
        "missing_textures": missing_iwis,
        "hidden_fx_paths": hidden_fx_list,          # ← NEW
        "dropped_xmodels": dropped_xmodels,
        "dropped_materials": dropped_materials,
        "total_xmodels": total_xmodels,
        "total_materials": total_materials,
        "prefabs_processed": prefabs_processed
    }
