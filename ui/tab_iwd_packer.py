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

from helpers import get_map_list, get_missing_custom_assets_from_map, get_xmodel_dependencies

class IWDPackerTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.custom_files = set()  # Full paths to copy
        self.create_widgets()
        # Load maps immediately when tab is created
        self.refresh_packer_maps()

    def create_widgets(self):
        ttk.Label(self, text="IWD Packer - Collect & Pack Custom Assets", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(10, 20))

        self.status_label = ttk.Label(self, text="Select a map and click Analyze to find custom files", foreground="blue")
        self.status_label.pack(anchor="w", pady=10)

        # ── Independent Map Selector ──
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

        # ── Warning about potential missed files ──
        warning_text = (
            "This tool automatically collects most custom/non-stock files, but it may miss some content.\n"
            "Examples: manually added sounds not in soundaliases.csv, scripts not called from main.gsc,\n"
            "external IWD dependencies, or raw overrides not referenced in .map files.\n\n"
            "Always verify the resulting .iwd contains everything your map needs!"
        )
        warning_lbl = ttk.Label(self, text=warning_text, foreground="#d9534f", justify="left", wraplength=700)
        warning_lbl.pack(anchor="w", pady=(0, 15))

        # ── Buttons ──
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", pady=10)
        self.analyze_btn = ttk.Button(btn_frame, text="Analyze Custom Files", command=self.analyze_custom_files)
        self.analyze_btn.pack(side="left", padx=10)

        self.pack_btn = ttk.Button(btn_frame, text="Pack to IWD", command=self.pack_to_iwd, state="disabled")
        self.pack_btn.pack(side="left", padx=10)

        # ── File List ──
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

        project_root = Path(__file__).parent.parent  # ui/ → project root
        cod2_path = Path(self.app.cod2_path.get())
        if not cod2_path.exists():
            messagebox.showerror("Path Error", "CoD2 path not valid")
            return

        self.custom_files.clear()
        for item in self.file_tree.get_children():
            self.file_tree.delete(item)

        self.status_label.config(text="Analyzing custom + generated map files...", foreground="orange")

        try:
            # ── 1. Custom assets from .map source (xmodels, materials, textures) ──
            asset_result = get_missing_custom_assets_from_map(
                str(cod2_path),
                mapname,
                xmodel_json=str(project_root / "lists" / "xmodel_list.json"),
                material_json=str(project_root / "lists" / "materials.json")
            )

            for xmodel in asset_result["missing_xmodels"]:
                self.add_file(cod2_path / "main" / "xmodel" / xmodel)
                deps = get_xmodel_dependencies(str(cod2_path), xmodel)
                for surf in deps["surfs"]:
                    self.add_file(cod2_path / "main" / "xmodelsurfs" / surf)
                self.add_file(cod2_path / "main" / "xmodelparts" / deps["parts"])

            for mat in asset_result["missing_materials"]:
                raw_mat = cod2_path / "raw" / "materials" / mat
                main_mat = cod2_path / "main" / "materials" / mat
                self.add_file(raw_mat if raw_mat.exists() else main_mat)

            for tex in asset_result["missing_textures"]:
                tex_path = cod2_path / "main" / "images" / tex
                self.add_file(tex_path)
                if not tex_path.exists():
                    found = list((cod2_path / "main" / "images").rglob(f"{tex}.iwi"))
                    if found:
                        self.add_file(found[0])

            # ── 2. Core map files (always include if they exist) ──
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

            # ── 3. Loadscreen: CSV → material → texture .iwi + pack material itself ──
            if csv_path.exists():
                try:
                    with open(csv_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                        match = re.search(r'levelBriefing\s*,\s*(load(?:ing)?screen_[^\s,]+)', content, re.IGNORECASE)
                        if match:
                            mat_name = match.group(1).strip()
                            print(f"[IWD Packer] Found loadscreen material reference: {mat_name}")

                            mat_file = None
                            for base in ["raw", "main"]:
                                candidate = cod2_path / base / "materials" / mat_name
                                if candidate.exists():
                                    mat_file = candidate
                                    break

                            if mat_file:
                                print(f"[IWD Packer] Located material file: {mat_file}")
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

                                print(f"[DEBUG Material] Candidates found: {candidates}")

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
                                    else:
                                        print(f"[IWD Packer] Loadscreen texture missing: {iwi_path}")
                                else:
                                    print(f"[IWD Packer] No valid texture name found in material {mat_name}")
                            else:
                                print(f"[IWD Packer] Loadscreen material file not found: {mat_name}")
                except Exception as e:
                    print(f"[IWD Packer] Failed to process loadscreen CSV/material: {e}")

            # ── 4. Custom FX – IMPROVED PARSING ────────────────────────────────────────
            fx_gsc = base_mp / f"{mapname}_fx.gsc"
            if fx_gsc.exists():
                fx_content = fx_gsc.read_text(encoding="utf-8", errors="ignore")

                # ── IMPROVED: Catch loadfx() with OR without .efx extension ──
                fx_paths = re.findall(
                    r'loadfx\s*\(\s*"([^"]+)"\s*\)',
                    fx_content,
                    re.IGNORECASE
                )

                print(f"[DEBUG FX] All loadfx calls found: {fx_paths}")

                stock_fx = set()
                fx_json_path = project_root / "lists" / "fx_files.json"
                if fx_json_path.is_file():
                    try:
                        with open(fx_json_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            stock_fx = {
                                str(item.get("path", "")).strip().replace("\\", "/").removeprefix("fx/").strip().lower()
                                for item in data if isinstance(item, dict) and "path" in item
                            }
                    except Exception as e:
                        print(f"[DEBUG FX] JSON load error: {e}")

                added_fx = 0
                for fx_path_raw in fx_paths:
                    # Clean and normalize
                    clean_path = fx_path_raw.strip().replace("\\", "/").removeprefix("fx/").strip()
                    norm_lower = clean_path.lower()

                    # Always ensure .efx for disk lookup (game adds it if missing)
                    if clean_path.lower().endswith('.efx'):
                        game_path = f"fx/{clean_path}"
                        disk_path_no_ext = clean_path[:-4]  # remove .efx for comparison if needed
                    else:
                        game_path = f"fx/{clean_path}.efx"
                        disk_path_no_ext = clean_path

                    print(f"[DEBUG FX] Checking: '{fx_path_raw}' → game path: '{game_path}' (norm: '{norm_lower}')")

                    if norm_lower in stock_fx or disk_path_no_ext in stock_fx:
                        print(f"   → MATCHED stock → skipping")
                        continue

                    full_disk_path = cod2_path / "main" / game_path
                    if full_disk_path.exists():
                        self.add_file(full_disk_path)
                        added_fx += 1
                        print(f"      Added custom FX: {game_path}")
                    else:
                        print(f"      Custom FX missing on disk: {full_disk_path}")

                print(f"[IWD Packer] Total custom FX added: {added_fx}")
            else:
                print("[IWD Packer] No _fx.gsc found")

            # ── 5. Custom sounds from soundaliases csv ──
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

            # ── 6. Custom scripts from main.gsc includes ──
            main_gsc = base_mp / f"{mapname}.gsc"
            if main_gsc.exists():
                gsc_content = main_gsc.read_text(encoding="utf-8", errors="ignore")
                script_calls = re.findall(r'maps\\mp\\([^:]+)::[^;]+;', gsc_content)
                for path_part in script_calls:
                    script_file = path_part.strip() + ".gsc"
                    full_path = base_mp / script_file
                    self.add_file(full_path)

            # ── Finalize UI list ──
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
        """Add file if it exists (prefer raw/ for overrides)"""
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
                    print(f"[IWD Packer] Skipped missing file: {src_path}")
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
                print(f"[IWD Packer] Copied → {rel}")

            zip_path = Path(save_path)
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, _, files in os.walk(main_temp):
                    for file in files:
                        file_path = Path(root) / file
                        arcname = file_path.relative_to(main_temp)
                        zipf.write(file_path, arcname)

            shutil.rmtree(temp_dir)

            messagebox.showinfo("Success", f"Packed {copied} files into IWD:\n{zip_path}\n\n"
                                          f"Verify inside IWD (rename to .zip and open):\n"
                                          f"- Paths start with maps/, soundaliases/, images/, materials/, etc.")

        except Exception as e:
            messagebox.showerror("Pack Error", str(e))

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
