"""Utility helpers for file resolution, parsing, and game asset management.

This module contains shared helper functions used across the UI and
packaging tools for working with CoD2 map files, FX assets, materials,
and configuration paths.
"""

from pathlib import Path
import os
import re
import json
from typing import List, Dict, Set, Optional, Any


def get_map_list(cod2_path: str) -> list[str]:
    """Returns map names based ONLY on .map files directly in map_source/ folder."""
    base = Path(cod2_path)
    map_source_dir = base / "map_source"

    if not map_source_dir.is_dir():
        return []

    candidates = set()
    for map_file in map_source_dir.glob("*.map"):
        name = map_file.stem
        if name.startswith(("mp_", "dupe_")):
            candidates.add(name)

    return sorted(candidates)


def ensure_directories(cod2_path: str, mapname: str):
    """Creates necessary folders under maps/mp, sun, mp"""
    base = Path(cod2_path)
    folders = [
        base / "maps" / "mp",
        base / "sun",
        base / "mp",
    ]
    for folder in folders:
        folder.mkdir(parents=True, exist_ok=True)


def resolve_cod2_install_root(cod2_path: str | os.PathLike[str]) -> Path:
    """Return the actual CoD2 install root for either the root folder or the main/ subfolder."""
    base = Path(cod2_path).expanduser()
    if not base.exists():
        return base
    if base.name.lower() == "main":
        return base.parent
    if (base / "main").exists():
        return base
    return base


def resolve_cod2_path(cod2_path: str | os.PathLike[str], *parts: str) -> Path:
    """Resolve the first existing file/dir from the common CoD2 layouts, falling back to preferred (main/)."""
    base = resolve_cod2_install_root(cod2_path)
    preferred = base / "main" / Path(*parts)
    fallback = base / Path(*parts)
    if preferred.exists():
        return preferred
    if fallback.exists():
        return fallback
    return preferred


def preferred_write_path(cod2_path: str | os.PathLike[str], *parts: str) -> Path:
    """Always prefer writing under main/."""
    base = resolve_cod2_install_root(cod2_path)
    return base / "main" / Path(*parts)


def map_gsc_path(
    cod2_path: str | os.PathLike[str],
    mapname: str,
    *,
    fx: bool = False,
    for_write: bool = False,
) -> Path:
    name = f"{mapname}_fx.gsc" if fx else f"{mapname}.gsc"
    if for_write:
        return preferred_write_path(cod2_path, "maps", "mp", name)
    return resolve_cod2_path(cod2_path, "maps", "mp", name)


def map_csv_path(
    cod2_path: str | os.PathLike[str],
    mapname: str,
    *,
    for_write: bool = False,
) -> Path:
    name = f"{mapname}.csv"
    if for_write:
        return preferred_write_path(cod2_path, "maps", "mp", name)
    return resolve_cod2_path(cod2_path, "maps", "mp", name)


def map_arena_path(
    cod2_path: str | os.PathLike[str],
    mapname: str,
    *,
    for_write: bool = False,
) -> Path:
    name = f"{mapname}.arena"
    if for_write:
        return preferred_write_path(cod2_path, "mp", name)
    return resolve_cod2_path(cod2_path, "mp", name)


def map_sun_path(
    cod2_path: str | os.PathLike[str],
    mapname: str,
    *,
    for_write: bool = False,
) -> Path:
    name = f"{mapname}.sun"
    if for_write:
        return preferred_write_path(cod2_path, "sun", name)
    return resolve_cod2_path(cod2_path, "sun", name)


def map_soundaliases_path(
    cod2_path: str | os.PathLike[str],
    mapname: str,
    *,
    for_write: bool = False,
) -> Path:
    name = f"{mapname}.csv"
    if for_write:
        return preferred_write_path(cod2_path, "soundaliases", name)
    return resolve_cod2_path(cod2_path, "soundaliases", name)


def material_path(cod2_path: str | os.PathLike[str], material_name: str) -> Optional[Path]:
    """Return first existing material file under raw/ or main/."""
    base = resolve_cod2_install_root(cod2_path)
    for root_name in ("raw", "main"):
        p = base / root_name / "materials" / material_name
        if p.is_file():
            return p
    return None


def fx_file_path(cod2_path: str | os.PathLike[str], fx_ref: str) -> Optional[Path]:
    """Resolve an FX reference to an on-disk .efx path if it exists."""
    base = resolve_cod2_install_root(cod2_path)
    key = fx_lookup_key(fx_ref)
    if not key:
        return None
    candidate = base / "main" / "fx" / f"{key}.efx"
    return candidate if candidate.is_file() else None


def read_file_if_exists(path: Path) -> str:
    if path.is_file():
        try:
            return path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return "# Error reading file"
    return ""


def write_file(path: Path, content: str, overwrite: bool = False):
    if path.exists() and not overwrite:
        raise FileExistsError(f"File already exists: {path}\nUse overwrite mode.")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")


def parse_number(value: str) -> int | float:
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return float(value)


def normalize_gsc_vectors(content: str) -> str:
    """Normalize double parentheses like ((x, y, z)) before regex parsing."""
    return re.sub(
        r"\(\(\s*([\-\d\.]+)\s*,\s*([\-\d\.]+)\s*,\s*([\-\d\.]+)\s*\)\)",
        r"(\1, \2, \3)",
        content,
    )


def extract_ascii_cstrings(data: bytes) -> list[str]:
    """Extract null-terminated ASCII strings from binary data."""
    candidates: list[str] = []
    pos = 0
    while pos < len(data):
        start = pos
        while pos < len(data) and data[pos] != 0:
            pos += 1
        if pos > start:
            try:
                s = data[start:pos].decode("ascii", errors="ignore").strip()
                if s:
                    candidates.append(s)
            except Exception:
                pass
        pos += 1
    return candidates


def load_json_name_set(json_path: str | Path, key: str = "name") -> set[str]:
    """Load a JSON list of objects and return a set of string values for `key`."""
    path = Path(json_path)
    if not path.is_file():
        return set()
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            return set()
        result: set[str] = set()
        for item in data:
            if isinstance(item, dict) and key in item:
                val = str(item[key]).strip()
                if val:
                    result.add(val)
        return result
    except Exception as e:
        print(f"[WARNING] Failed to load {json_path}: {e}")
        return set()


def load_stock_fx_keys(json_path: str | Path) -> set[str]:
    """Load stock FX list and return normalized lookup keys (no fx/ prefix, no .efx)."""
    path = Path(json_path)
    if not path.is_file():
        return set()
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        keys: set[str] = set()
        if not isinstance(data, list):
            return keys
        for item in data:
            if isinstance(item, dict) and "path" in item:
                keys.add(fx_lookup_key(str(item["path"])))
            elif isinstance(item, str):
                keys.add(fx_lookup_key(item))
        return {k for k in keys if k}
    except Exception as e:
        print(f"[WARNING] Failed to load stock FX from {json_path}: {e}")
        return set()


def normalize_fx_ref(ref: str) -> str:
    """Return a normalized 'fx/foo/bar.efx' style path."""
    fx_path = (ref or "").replace("\\", "/").strip()
    if not fx_path:
        return ""
    lower = fx_path.lower()
    if not lower.startswith("fx/"):
        fx_path = "fx/" + fx_path.lstrip("/")
    if not fx_path.lower().endswith(".efx"):
        fx_path += ".efx"
    return fx_path


def fx_lookup_key(ref: str) -> str:
    """Lowercased stem path without leading fx/ or trailing .efx for stock comparisons."""
    p = (ref or "").replace("\\", "/").strip().lower()
    p = p.removeprefix("fx/").removeprefix("/")
    p = p.removesuffix(".efx")
    return p.strip()


def relative_to_asset_root(path: Path) -> Path:
    """Strip leading .../main or .../raw so the remainder is the IWD-relative layout."""
    parts = path.parts
    for root_name in ("raw", "main"):
        if root_name in parts:
            idx = parts.index(root_name)
            return Path(*parts[idx + 1 :])
    return Path(path.name)


def parse_gsc_hq_locations(content: str) -> list[tuple[tuple[float, float, float], tuple[float, float, float]]]:
    """Parse level.radio script_model spawn positions and angles from a GSC file."""
    normalized = normalize_gsc_vectors(content)
    spawn_re = re.compile(
        r'level\.radio\[(\d+)\]\s*=\s*spawn\(\s*"script_model"\s*,\s*\(\s*([\-\d\.]+)\s*,\s*([\-\d\.]+)\s*,\s*([\-\d\.]+)\s*\)\s*\)\s*;',
        re.IGNORECASE,
    )
    angles_re = re.compile(
        r'level\.radio\[(\d+)\]\.angles\s*=\s*\(\s*([\-\d\.]+)\s*,\s*([\-\d\.]+)\s*,\s*([\-\d\.]+)\s*\)\s*;',
        re.IGNORECASE,
    )

    entries: dict[int, dict[str, tuple]] = {}
    for match in spawn_re.finditer(normalized):
        idx = int(match.group(1))
        pos = (parse_number(match.group(2)), parse_number(match.group(3)), parse_number(match.group(4)))
        entries.setdefault(idx, {})["pos"] = pos
    for match in angles_re.finditer(normalized):
        idx = int(match.group(1))
        angles = (parse_number(match.group(2)), parse_number(match.group(3)), parse_number(match.group(4)))
        entries.setdefault(idx, {})["angles"] = angles

    results = []
    for idx in sorted(entries):
        data = entries[idx]
        if "pos" in data and "angles" in data:
            results.append((data["pos"], data["angles"]))
    return results


def parse_gsc_kill_triggers(content: str) -> list[tuple[tuple[float, float, float], float, float]]:
    """Parse kill trigger origin, radius, and height values from a GSC file."""
    normalized = normalize_gsc_vectors(content)
    trigger_re = re.compile(r'level\.killtriggers\[(\d+)\]\s*=\s*spawnstruct\(\s*\)\s*;?', re.IGNORECASE)
    origin_re = re.compile(
        r'level\.killtriggers\[(\d+)\]\.origin\s*=\s*\(\s*([\-\d\.]+)\s*,\s*([\-\d\.]+)\s*,\s*([\-\d\.]+)\s*\)\s*;?',
        re.IGNORECASE,
    )
    radius_re = re.compile(r'level\.killtriggers\[(\d+)\]\.radius\s*=\s*([\-\d\.]+)\s*;?', re.IGNORECASE)
    height_re = re.compile(r'level\.killtriggers\[(\d+)\]\.height\s*=\s*([\-\d\.]+)\s*;?', re.IGNORECASE)

    entries: dict[int, dict[str, Any]] = {}
    for match in trigger_re.finditer(content):
        idx = int(match.group(1))
        entries.setdefault(idx, {})
    for match in origin_re.finditer(normalized):
        idx = int(match.group(1))
        origin = (parse_number(match.group(2)), parse_number(match.group(3)), parse_number(match.group(4)))
        entries.setdefault(idx, {})["origin"] = origin
    for match in radius_re.finditer(content):
        idx = int(match.group(1))
        entries.setdefault(idx, {})["radius"] = parse_number(match.group(2))
    for match in height_re.finditer(content):
        idx = int(match.group(1))
        entries.setdefault(idx, {})["height"] = parse_number(match.group(2))

    results = []
    for idx in sorted(entries):
        data = entries[idx]
        if "origin" in data and "radius" in data and "height" in data:
            results.append((data["origin"], data["radius"], data["height"]))
    return results


def parse_gsc_script_calls(content: str) -> list[str]:
    """Extract script call paths from a GSC file's maps\\mp\\...:: calls."""
    call_re = re.compile(r'maps\\mp\\([^:;\r\n]+)::', re.IGNORECASE)
    results: list[str] = []
    seen: set[str] = set()
    for match in call_re.finditer(content):
        path = match.group(1).replace("\\", "/").strip()
        if not path or path in seen:
            continue
        seen.add(path)
        results.append(path)
    return results


def parse_gsc_loadfx(content: str) -> list[str]:
    """Extract loadfx(\"...\") paths from a GSC file."""
    return re.findall(r'loadfx\s*\(\s*"([^"]+)"\s*\)', content, re.IGNORECASE)


def extract_loadscreen_iwi_candidates(csv_content: str) -> list[Path]:
    """Extract loadscreen .iwi candidate paths from a CSV-style string."""
    candidates: list[Path] = []
    for line in csv_content.splitlines():
        fields = [field.strip().strip('"') for field in line.split(",") if field.strip()]
        if len(fields) < 2:
            continue
        value = fields[1].replace("\\", "/").strip()
        if not value:
            continue
        if not value.lower().endswith(".iwi"):
            value = value.removeprefix("images/").removeprefix("/")
            value = f"images/{value}.iwi"
        candidates.append(Path(value))
    return candidates


def get_xmodel_dependencies(cod2_path: str, model_name: str) -> dict[str, Any]:
    """Parses a CoD2 xmodel file and returns the required dependencies."""
    xmodel_path = Path(cod2_path) / "main" / "xmodel" / model_name
    suggested_parts = model_name + "0"

    if not xmodel_path.is_file():
        return {"surfs": [], "materials": [], "parts": suggested_parts}

    data = xmodel_path.read_bytes()
    candidates = extract_ascii_cstrings(data)

    pattern = re.compile(r"^[a-z0-9_]+$")
    filtered = []
    for s in candidates:
        if len(s) >= 6 and pattern.match(s) and ("_" in s or any(c.isdigit() for c in s)):
            filtered.append(s)

    materials: list[str] = []
    surfs: list[str] = []
    seen_mat: set[str] = set()
    seen_surf: set[str] = set()

    for name in filtered:
        if name.startswith("mtl_"):
            if name not in seen_mat:
                materials.append(name)
                seen_mat.add(name)
        else:
            if name not in seen_surf:
                surfs.append(name)
                seen_surf.add(name)

    return {"surfs": surfs, "materials": materials, "parts": suggested_parts}


def parse_map_entities(file_path: Path) -> List[Dict[str, str]]:
    """Parses only keyvalue entities (ignores brushes/patches for speed)."""
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
    material_file = material_path(cod2_path, material_name)
    if not material_file:
        print(f"  [DEBUG] No material file found for {material_name}")
        return set()

    print(f"  [DEBUG] Parsing material: {material_file.name}")
    data = material_file.read_bytes()
    candidates = extract_ascii_cstrings(data)

    exclude_keys = {
        "colorMap", "normalMap", "specularMap", "detailMap", "detailScale",
        "wallpaper", "phong_replace_detail", "specularColorMap", "alphaMap",
        "alphaTest", "phong_alphatest_spec", "specularFactor", "glossScale",
        "bumpMap", "heightMap", "lightMap", "diffuseMap", "emissiveMap",
        "qer_editorimage", "qer_trans", "surfaceparm", "nomipmaps",
    }

    textures: set[str] = set()
    for s in candidates:
        if (
            len(s) > 3
            and re.match(r"^[a-zA-Z0-9_~/\\.&\\-]+$", s)
            and s not in exclude_keys
            and not s.startswith(("phong_", "mtl_", "qer_", "surfaceparm"))
        ):
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
    material_json: str = "lists/materials.json",
) -> dict:
    """
    Parses map + prefabs → finds custom xmodels, materials, textures, and hidden FX references.
    """
    cod2 = Path(cod2_path)
    main_map_path = cod2 / "map_source" / f"{map_name}.map"
    prefab_dir = cod2 / "map_source" / "prefabs"

    if not main_map_path.is_file():
        raise FileNotFoundError(f"Main map not found: {main_map_path}")

    known_xmodels = load_json_name_set(xmodel_json, key="name")
    known_materials = load_json_name_set(material_json, key="name")

    used_xmodels: Set[str] = set()
    used_materials: Set[str] = set()
    hidden_fx_paths: Set[str] = set()
    prefabs_processed: List[str] = []
    visited: Set[str] = set()

    brush_mat_regex = re.compile(r"\)\s*\)\s*\)\s*([a-z0-9_/]+)")
    cm_mat_regex = re.compile(r"(?:curve|mesh|patchDef2)\s*\{\s*([a-z0-9_/]+)")

    def recurse(map_path: Path):
        print(f"  Parsing: {map_path.name}")
        text = map_path.read_text(encoding="latin1", errors="replace")

        used_materials.update(brush_mat_regex.findall(text))
        for match in cm_mat_regex.finditer(text):
            used_materials.add(match.group(1))

        entities = parse_map_entities(map_path)
        for ent in entities:
            classname = ent.get("classname", "").lower()

            if classname == "misc_model":
                model = ent.get("model", "")
                if model.startswith("xmodel/"):
                    name = model[len("xmodel/") :].strip()
                    if name:
                        used_xmodels.add(name)

            for key in ["script_noteworthy", "fx", "effect", "corona", "script_fx", "targetname"]:
                if key in ent:
                    val = ent[key].strip()
                    if "fx/" in val.lower() or val.lower().startswith("fx/"):
                        hidden_fx_paths.add(normalize_fx_ref(val))

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

    missing_textures: set[str] = set()
    print(f"\nParsing {len(missing_materials)} missing materials for textures...")
    for mat in missing_materials:
        tex_bases = get_textures_from_material(cod2_path, mat)
        missing_textures.update(tex_bases)

    missing_iwis = sorted([t + ".iwi" for t in missing_textures])
    hidden_fx_list = sorted(hidden_fx_paths)

    return {
        "missing_xmodels": missing_xmodels,
        "missing_materials": missing_materials,
        "missing_textures": missing_iwis,
        "hidden_fx_paths": hidden_fx_list,
        "dropped_xmodels": dropped_xmodels,
        "dropped_materials": dropped_materials,
        "total_xmodels": total_xmodels,
        "total_materials": total_materials,
        "prefabs_processed": prefabs_processed,
    }