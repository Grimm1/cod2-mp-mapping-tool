# ui/tab_iwd_packer.py

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
import shutil
import zipfile
import tempfile
import re
import json
import os

from helpers import get_map_list, get_missing_custom_assets_from_map, get_xmodel_dependencies, get_textures_from_material

class IWDPackerTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.custom_files = set()  # Full paths to copy
        self.create_widgets()
        self.refresh_packer_maps()

    def create_widgets(self):
        ttk.Label(self, text="IWD Packer - Collect & Pack Custom Assets", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(10, 20))
        ttk.Label(self, text="**If you have called custom assets in a script they will not be automatically detected. please add these manually after iwd creation**", font=("Segoe UI", 10, "bold"), foreground="red").pack(anchor="w", pady=(15, 20))
        self.status_label = ttk.Label(self, text="Select a map and click Analyze to find custom files", foreground="blue")
        self.status_label.pack(anchor="w", pady=10)

        map_select_frame = ttk.LabelFrame(self, text="Map to Pack", padding=10)
        map_select_frame.pack(fill="x", pady=(0, 15))

        ttk.Label(map_select_frame, text="Select map:").pack(side="left", padx=(0, 8))

        self.packer_map_var = tk.StringVar(value="")
        self.packer_map_combo = ttk.Combobox(
            map_select_frame,
            textvariable=self.packer_map_var,
            state="readonly",
            width=40
        )
        self.packer_map_combo.pack(side="left", padx=8)

        ttk.Button(map_select_frame, text="Refresh Maps", command=self.refresh_packer_maps).pack(side="left")

        warning_text = (
            "This tool automatically collects most custom/non-stock files, but it may miss some content.\n"
            "Examples: manually added sounds not in soundaliases.csv, scripts not called from main.gsc,\n"
            "external IWD dependencies, or raw overrides not referenced in .map files.\n\n"
            "Always verify the resulting .iwd contains everything your map needs!"
        )
        warning_lbl = ttk.Label(self, text=warning_text, foreground="#d9534f", justify="left", wraplength=700)
        warning_lbl.pack(anchor="w", pady=(0, 15))

        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", pady=10)
        self.analyze_btn = ttk.Button(btn_frame, text="Analyze Custom Files", command=self.analyze_custom_files)
        self.analyze_btn.pack(side="left", padx=10)

        self.pack_btn = ttk.Button(btn_frame, text="Pack to IWD", command=self.pack_to_iwd, state="disabled")
        self.pack_btn.pack(side="left", padx=10)

        list_frame = ttk.Frame(self)
        list_frame.pack(fill="both", expand=True, pady=10)

        self.file_tree = ttk.Treeview(list_frame, columns=("path",), show="headings")
        self.file_tree.heading("path", text="Custom File Path (relative to main/)")
        self.file_tree.column("path", width=600)
        self.file_tree.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.file_tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.file_tree.configure(yscrollcommand=scrollbar.set)

        self.count_label = ttk.Label(self, text="", foreground="green")
        self.count_label.pack(anchor="w", pady=10)

    def refresh_packer_maps(self):
        cod2_path_str = self.app.cod2_path.get().strip()
        if not cod2_path_str or not Path(cod2_path_str).is_dir():
            messagebox.showwarning("No CoD2 Path", "Set CoD2 path first (in Script Tools tab)")
            self.packer_map_combo["values"] = []
            self.packer_map_var.set("")
            return

        maps = get_map_list(cod2_path_str)
        self.packer_map_combo["values"] = maps

        current = self.packer_map_var.get()
        if current in maps:
            self.packer_map_combo.set(current)
        elif maps:
            self.packer_map_combo.current(0)
            self.packer_map_var.set(maps[0])
        else:
            self.packer_map_var.set("No maps found")

    def analyze_custom_files(self):
        mapname = self.packer_map_var.get().strip()
        if not mapname:
            messagebox.showwarning("No Map Selected", "Please select a map in the IWD Packer tab first!")
            return

        project_root = Path(__file__).parent.parent
        cod2_path = Path(self.app.cod2_path.get())
        if not cod2_path.exists():
            messagebox.showerror("Path Error", "CoD2 path not valid")
            return

        self.custom_files.clear()
        for item in self.file_tree.get_children():
            self.file_tree.delete(item)

        self.status_label.config(text="Analyzing custom + generated map files...", foreground="orange")

        try:
            # ── 1. Parse .map for xmodels, materials, textures + hidden FX ──
            asset_result = get_missing_custom_assets_from_map(
                str(cod2_path),
                mapname,
                xmodel_json=str(project_root / "lists" / "xmodel_list.json"),
                material_json=str(project_root / "lists" / "materials.json")
            )

            # XModels
            for xmodel in asset_result["missing_xmodels"]:
                self.add_file(cod2_path / "main" / "xmodel" / xmodel)
                deps = get_xmodel_dependencies(str(cod2_path), xmodel)
                for surf in deps["surfs"]:
                    self.add_file(cod2_path / "main" / "xmodelsurfs" / surf)
                self.add_file(cod2_path / "main" / "xmodelparts" / deps["parts"])

            # Materials
            for mat in asset_result["missing_materials"]:
                raw_mat = cod2_path / "raw" / "materials" / mat
                main_mat = cod2_path / "main" / "materials" / mat
                self.add_file(raw_mat if raw_mat.exists() else main_mat)

            # Textures
            for tex in asset_result["missing_textures"]:
                tex_path = cod2_path / "main" / "images" / tex
                self.add_file(tex_path)
                if not tex_path.exists():
                    found = list((cod2_path / "main" / "images").rglob(f"{tex}.iwi"))
                    if found:
                        self.add_file(found[0])

            # ── Hidden FX from .map entities ──
            added_hidden_fx = 0
            stock_fx = set()
            fx_json_path = project_root / "lists" / "fx_files.json"
            if fx_json_path.is_file():
                try:
                    with open(fx_json_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        stock_fx = {
                            str(item.get("path", "")).strip().replace("\\", "/")
                            .removeprefix("fx/").strip()
                            .removesuffix(".efx").removesuffix(".EFX").lower()
                            for item in data if isinstance(item, dict) and "path" in item
                        }
                except Exception as e:
                    print(f"[DEBUG FX] JSON load error: {e}")

            for fx_ref in asset_result.get("hidden_fx_paths", []):
                clean_path = fx_ref.removeprefix("fx/").removesuffix(".efx").strip()
                norm_lower = clean_path.lower()

                if norm_lower in stock_fx:
                    print(f"   → Hidden FX is stock → skipping: fx/{clean_path}")
                    continue

                full_game_path = f"fx/{clean_path}.efx"
                full_disk_path = cod2_path / "main" / full_game_path

                if full_disk_path.exists():
                    self.add_file(full_disk_path)
                    added_hidden_fx += 1
                    print(f"      Added hidden custom FX from .map: {full_game_path}")
                else:
                    print(f"      Hidden FX missing: {full_disk_path}")

            print(f"[IWD Packer] Total hidden FX added from map: {added_hidden_fx}")

            # ── NEW: Parse ALL custom .efx files (GSC + map entities) for shaders & textures ──
            custom_efx_files = [
                p for p in self.custom_files
                if p.suffix.lower() == '.efx'
                and "fx" in str(p).lower()
            ]

            print(f"[IWD Packer] Parsing {len(custom_efx_files)} custom EFX files for shaders...")

            stock_materials = set()
            materials_json = project_root / "lists" / "materials.json"
            if materials_json.is_file():
                try:
                    with open(materials_json, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        stock_materials = {item["name"].lower() for item in data if "name" in item}
                except Exception as e:
                    print(f"[DEBUG] Failed to load stock materials: {e}")

            added_shaders = 0
            added_textures = 0

            for efx_path in custom_efx_files:
                try:
                    content = efx_path.read_text(encoding="utf-8", errors="ignore")

                    # Find all shaders[] blocks
                    shader_blocks = re.findall(
                        r'shaders\s*\[\s*([^]]*)\s*\]',
                        content,
                        re.IGNORECASE | re.DOTALL
                    )

                    for block in shader_blocks:
                        shaders = [
                            s.strip().strip('"').strip()
                            for s in re.split(r'[\r\n,]+', block)
                            if s.strip().strip('"').strip()
                        ]

                        for shader_name in shaders:
                            if not shader_name:
                                continue

                            shader_lower = shader_name.lower()
                            if shader_lower in stock_materials:
                                continue

                            print(f"   → Found custom shader in {efx_path.name}: {shader_name}")

                            # Locate material file
                            mat_file = None
                            for base in ["raw", "main"]:
                                candidate = cod2_path / base / "materials" / shader_name
                                if candidate.is_file():
                                    mat_file = candidate
                                    break

                            if mat_file:
                                self.add_file(mat_file)
                                added_shaders += 1
                                print(f"      Added custom material: {mat_file.relative_to(cod2_path / 'main')}")

                                # Parse material for textures
                                tex_bases = get_textures_from_material(str(cod2_path), shader_name)
                                for tex_base in tex_bases:
                                    iwi_path = cod2_path / "main" / "images" / f"{tex_base}.iwi"
                                    if iwi_path.exists():
                                        self.add_file(iwi_path)
                                        added_textures += 1
                                        print(f"         Added texture: images/{tex_base}.iwi")
                                    else:
                                        print(f"         Texture missing: images/{tex_base}.iwi")

                except Exception as e:
                    print(f"[IWD Packer] Failed to parse EFX {efx_path.name}: {e}")

            print(f"[IWD Packer] Added {added_shaders} custom shaders and {added_textures} textures from EFX files")

            # ── 2. Core map files ──
            base_mp = cod2_path / "main" / "maps" / "mp"
            base_sound = cod2_path / "main" / "soundaliases"
            base_sun = cod2_path / "main" / "sun"
            base_mp_dir = cod2_path / "main" / "mp"

            self.add_file(base_mp / f"{mapname}.gsc")
            self.add_file(base_mp / f"{mapname}_fx.gsc")
            csv_path = base_mp / f"{mapname}.csv"
            self.add_file(csv_path)
            self.add_file(base_mp / f"{mapname}.d3dbsp")
            self.add_file(base_mp_dir / f"{mapname}.arena")
            self.add_file(base_sound / f"{mapname}.csv")
            self.add_file(base_sun / f"{mapname}.sun")

            # ── 3. Loadscreen processing (unchanged) ──
            if csv_path.exists():
                try:
                    with open(csv_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                        match = re.search(r'levelBriefing\s*,\s*(load(?:ing)?screen_[^\s,]+)', content, re.IGNORECASE)
                        if match:
                            mat_name = match.group(1).strip()
                            print(f"[IWD Packer] Found loadscreen material: {mat_name}")

                            mat_file = None
                            for base in ["raw", "main"]:
                                candidate = cod2_path / base / "materials" / mat_name
                                if candidate.exists():
                                    mat_file = candidate
                                    break

                            if mat_file:
                                self.add_file(mat_file)
                                data = mat_file.read_bytes()
                                pos = 0
                                candidates = []
                                while pos < len(data):
                                    start = pos
                                    while pos < len(data) and data[pos] != 0:
                                        pos += 1
                                    if pos > start:
                                        s = data[start:pos].decode('ascii', errors='ignore').strip()
                                        if s and re.match(r'^[a-zA-Z0-9_~/\.&\-]+$', s):
                                            candidates.append(s)
                                    pos += 1

                                tex_base = None
                                for s in candidates:
                                    base_name = Path(s).stem
                                    if base_name.startswith(("loadingscreen_", "loadscreen_")) and base_name != mat_name:
                                        tex_base = base_name
                                        break

                                if not tex_base and candidates:
                                    for s in reversed(candidates):
                                        base_name = Path(s).stem
                                        if base_name not in {mat_name, "colorMap", "normalMap"}:
                                            tex_base = base_name
                                            break

                                if tex_base:
                                    iwi_path = cod2_path / "main" / "images" / f"{tex_base}.iwi"
                                    if iwi_path.exists():
                                        self.add_file(iwi_path)
                                        print(f"[IWD Packer] Added loadscreen texture: {tex_base}.iwi")

                except Exception as e:
                    print(f"[IWD Packer] Loadscreen processing error: {e}")

            # ── 4. Custom FX from _fx.gsc (unchanged) ──
            fx_gsc = base_mp / f"{mapname}_fx.gsc"
            if fx_gsc.exists():
                fx_content = fx_gsc.read_text(encoding="utf-8", errors="ignore")
                fx_paths = re.findall(r'loadfx\s*\(\s*"([^"]+)"\s*\)', fx_content, re.IGNORECASE)

                added_fx = 0
                for fx_path_raw in fx_paths:
                    clean_path = fx_path_raw.strip().replace("\\", "/").removeprefix("fx/").strip()
                    norm_lower = clean_path.lower().removesuffix(".efx").removesuffix(".EFX")

                    full_game_path = f"fx/{clean_path}.efx" if not clean_path.lower().endswith('.efx') else f"fx/{clean_path}"
                    full_disk_path = cod2_path / "main" / full_game_path

                    if norm_lower in stock_fx:
                        continue

                    if full_disk_path.exists():
                        self.add_file(full_disk_path)
                        added_fx += 1
                    else:
                        print(f"[IWD Packer] FX missing: {full_disk_path}")

                print(f"[IWD Packer] Total custom FX from GSC: {added_fx}")

            # ── 5. Sounds from soundaliases.csv (unchanged) ──
            sound_csv = base_sound / f"{mapname}.csv"
            if sound_csv.exists():
                content = sound_csv.read_text(encoding="utf-8", errors="ignore")
                lines = content.splitlines()
                for line in lines:
                    if line.startswith('#') or not line.strip():
                        continue
                    parts = [p.strip() for p in line.split(',')]
                    if len(parts) > 2 and parts[2]:
                        sound_path = parts[2]
                        if not sound_path.lower().endswith(('.wav', '.mp3')):
                            continue
                        full_path = cod2_path / "main" / "sound" / sound_path
                        self.add_file(full_path)

            # ── 6. Custom scripts from main.gsc (unchanged) ──
            main_gsc = base_mp / f"{mapname}.gsc"
            if main_gsc.exists():
                gsc_content = main_gsc.read_text(encoding="utf-8", errors="ignore")
                script_calls = re.findall(r'maps\\mp\\([^:]+)::[^;]+;', gsc_content)
                for path_part in script_calls:
                    script_file = path_part.strip() + ".gsc"
                    full_path = base_mp / script_file
                    self.add_file(full_path)

            # ── Finalize UI ──
            relative_files = sorted([
                str(p.relative_to(cod2_path / "main"))
                for p in self.custom_files if p.exists()
            ])

            for rel in relative_files:
                self.file_tree.insert("", "end", values=(rel,))

            count = len(relative_files)
            self.count_label.config(text=f"Found {count} files to pack")
            self.status_label.config(text="Analysis complete!", foreground="green")

            if count > 0:
                self.pack_btn.state(["!disabled"])
            else:
                self.pack_btn.state(["disabled"])
                messagebox.showinfo("No Files", "No custom or map files detected.")

        except Exception as e:
            messagebox.showerror("Analysis Error", str(e))
            self.status_label.config(text="Analysis failed", foreground="red")

    def add_file(self, full_path: Path):
        if full_path.exists():
            self.custom_files.add(full_path)
        else:
            print(f"[IWD Packer] Skipped missing file: {full_path}")

    def pack_to_iwd(self):
        if not self.custom_files:
            messagebox.showwarning("Nothing to Pack", "No custom files found")
            return

        save_path = filedialog.asksaveasfilename(
            title="Save Custom IWD",
            defaultextension=".iwd",
            filetypes=[("IWD File", "*.iwd"), ("All Files", "*.*")],
            initialfile=f"zz_custom_{self.packer_map_var.get() or 'map'}.iwd"
        )
        if not save_path:
            return

        try:
            temp_dir = tempfile.mkdtemp()
            main_temp = Path(temp_dir) / "main"
            main_temp.mkdir(parents=True)

            copied = 0
            for src_path in self.custom_files:
                if not src_path.exists():
                    continue

                if "raw" in src_path.parts:
                    idx = src_path.parts.index("raw")
                    rel = Path(*src_path.parts[idx+1:])
                elif "main" in src_path.parts:
                    idx = src_path.parts.index("main")
                    rel = Path(*src_path.parts[idx+1:])
                else:
                    rel = src_path.name

                dest = main_temp / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_path, dest)
                copied += 1

            zip_path = Path(save_path)
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, _, files in os.walk(main_temp):
                    for file in files:
                        file_path = Path(root) / file
                        arcname = file_path.relative_to(main_temp)
                        zipf.write(file_path, arcname)

            shutil.rmtree(temp_dir)

            messagebox.showinfo("Success", f"Packed {copied} files into IWD:\n{zip_path}")

        except Exception as e:
            messagebox.showerror("Pack Error", str(e))

    def refresh_packer_maps(self):
        cod2_path_str = self.app.cod2_path.get().strip()
        if not cod2_path_str or not Path(cod2_path_str).is_dir():
            messagebox.showwarning("No CoD2 Path", "Set CoD2 path first")
            self.packer_map_combo["values"] = []
            self.packer_map_var.set("")
            return

        maps = get_map_list(cod2_path_str)
        self.packer_map_combo["values"] = maps

        current = self.packer_map_var.get()
        if current in maps:
            self.packer_map_combo.set(current)
        elif maps:
            self.packer_map_combo.current(0)
            self.packer_map_var.set(maps[0])
        else:
            self.packer_map_var.set("No maps found")
