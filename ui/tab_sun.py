# ui/tab_sun.py
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from pathlib import Path
import json

class SunTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.json_path = Path(__file__).parent.parent / "presets" / "sun_presets.json"
        self.sun_presets = self.load_sun_presets()  # Load from JSON
        self.create_widgets()
        self.update_missing_status()

    def load_sun_presets(self):
        """Load sun presets from JSON file"""
        if not self.json_path.is_file():
            print(f"[SunTab] Presets JSON not found: {self.json_path}")
            messagebox.showwarning(
                "Presets Missing",
                f"Sun presets file not found:\n{self.json_path}\n\n"
                "Using default/empty preset list.\n"
                "Create presets by adjusting values and clicking 'Save Current as Preset'."
            )
            return {}

        try:
            with open(self.json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                presets = {}
                for p in data.get("presets", []):
                    name = p.get("name")
                    if name:
                        presets[name] = p.get("values", {})
                print(f"[SunTab] Loaded {len(presets)} sun presets from JSON")
                return presets
        except json.JSONDecodeError as e:
            print(f"[SunTab] JSON decode error: {e}")
            messagebox.showerror("Presets Error", f"Invalid JSON in presets file:\n{e}")
            return {}
        except Exception as e:
            print(f"[SunTab] Failed to load presets JSON: {e}")
            messagebox.showerror("Presets Error", f"Could not load sun presets:\n{e}")
            return {}

    def save_preset_to_json(self, name: str, values: dict) -> bool:
        """Append or update preset in JSON file"""
        data = {"presets": []}
        if self.json_path.is_file():
            try:
                with open(self.json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except:
                pass  # corrupt? start fresh with empty

        # Check if name exists → warn and confirm overwrite
        existing = next((p for p in data["presets"] if p["name"] == name), None)
        if existing:
            if not messagebox.askyesno(
                "Overwrite Preset?",
                f"Preset '{name}' already exists.\nOverwrite it?"
            ):
                return False

        # Remove old version if exists
        data["presets"] = [p for p in data["presets"] if p["name"] != name]

        # Add new/updated preset
        data["presets"].append({
            "name": name,
            "values": values
        })

        # Sort alphabetically by name
        data["presets"].sort(key=lambda p: p["name"].lower())

        try:
            self.json_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"[SunTab] Saved preset '{name}' to {self.json_path}")
            return True
        except Exception as e:
            messagebox.showerror("Save Failed", f"Could not save preset:\n{e}")
            return False

    def create_widgets(self):
        # Missing file status
        self.missing_label = ttk.Label(self, text="", foreground="red", font=("Segoe UI", 10, "bold"))
        self.missing_label.pack(anchor="w", pady=6)

        self.create_btn = ttk.Button(self, text="Create mp_XXXX.sun", command=self.create_file_if_missing)
        self.create_btn.pack(anchor="w", pady=6)
        self.create_btn.state(["disabled"])

        ttk.Label(self, text="SUN File: sun/mp_mapname.sun", font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=12)

        # Presets section with Load + Save
        preset_frame = ttk.LabelFrame(self, text=" Presets ", padding=10)
        preset_frame.pack(fill="x", padx=20, pady=10)

        load_frame = ttk.Frame(preset_frame)
        load_frame.pack(fill="x", pady=(0, 8))

        ttk.Label(load_frame, text="Load preset:").pack(side="left", padx=(0, 8))
        self.preset_var = tk.StringVar(value="")
        self.preset_combo = ttk.Combobox(
            load_frame,
            textvariable=self.preset_var,
            values=list(self.sun_presets.keys()),
            state="readonly",
            width=40
        )
        self.preset_combo.pack(side="left", padx=8)

        ttk.Button(load_frame, text="Load", command=self.load_preset).pack(side="left")

        # Save button
        ttk.Button(preset_frame, text="Save Current as New Preset...", command=self.save_current_preset).pack(anchor="w", pady=8)

        # Scrollable frame for sun parameters
        canvas = tk.Canvas(self)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True, padx=20, pady=10)
        scrollbar.pack(side="right", fill="y")

        frame = ttk.LabelFrame(scrollable_frame, text=" Sun Parameters ", padding=15)
        frame.pack(fill="both", expand=True)

        self.sun_entries = {}

        # All sun parameters with descriptions
        fields = [
            ("r_sunsprite_shader", "sun_trainyard", "Sun sprite shader name"),
            ("r_sunsprite_size", "109.722", "Size of the sun sprite"),
            ("r_sunflare_shader", "sun_flare_trainyard", "Sun flare shader name"),
            ("r_sunflare_min_size", "390.1", "Minimum sun flare size"),
            ("r_sunflare_min_angle", "82.3608", "Minimum angle for flare visibility"),
            ("r_sunflare_max_size", "889.3", "Maximum sun flare size"),
            ("r_sunflare_max_angle", "0", "Maximum angle for flare visibility"),
            ("r_sunflare_max_alpha", "0.45622", "Maximum alpha/opacity of flare"),
            ("r_sunflare_fadein", "0.2604", "Fade in speed for flare"),
            ("r_sunflare_fadeout", "0.2992", "Fade out speed for flare"),
            ("r_sunblind_min_angle", "62.4258", "Minimum angle for sun blindness effect"),
            ("r_sunblind_max_angle", "14.6015", "Maximum angle for sun blindness effect"),
            ("r_sunblind_max_darken", "0.23165", "Maximum darkening from blindness"),
            ("r_sunblind_fadein", "0.5", "Fade in for blindness effect"),
            ("r_sunblind_fadeout", "1", "Fade out for blindness effect"),
            ("r_sunglare_min_angle", "20.7108", "Minimum angle for glare effect"),
            ("r_sunglare_max_angle", "5.7933", "Maximum angle for glare effect"),
            ("r_sunglare_max_lighten", "0.0930199", "Maximum lightening from glare"),
            ("r_sunglare_fadein", "0.7758", "Fade in for glare effect"),
            ("r_sunglare_fadeout", "3", "Fade out for glare effect"),
            ("r_sun_fx_position", "-38.6856 -53.8224 0", "Sun FX position (x y z)"),
        ]

        # Create 2-column layout
        row_frames = []
        for idx, (name, default, desc) in enumerate(fields):
            col = idx % 2
            if col == 0:
                row = ttk.Frame(frame)
                row.pack(fill="x", pady=3)
                row_frames.append(row)
            else:
                row = row_frames[-1]

            col_frame = ttk.Frame(row)
            col_frame.pack(side="left", fill="both", expand=True, padx=(0, 20) if col == 0 else (0, 0))

            ttk.Label(col_frame, text=f"{name}:", width=22).pack(side="left", padx=(0, 4))
            entry = ttk.Entry(col_frame, width=18)
            entry.insert(0, default)
            entry.pack(side="left", padx=(0, 4), fill="x", expand=True)
            ttk.Label(col_frame, text=desc, foreground="gray", font=("Segoe UI", 8), width=30).pack(side="left", padx=(0, 2))

            self.sun_entries[name] = entry

        # Generate button
        button_frame = ttk.Frame(scrollable_frame)
        button_frame.pack(fill="x", pady=(15, 0))
        ttk.Button(button_frame, text="Generate SUN File", command=self.save_now).pack(side="left", padx=15)

    def save_current_preset(self):
        """Prompt for name and save current sun settings as preset"""
        # Check if anything is set (prevent saving empty)
        if not any(entry.get().strip() for entry in self.sun_entries.values()):
            messagebox.showwarning("Nothing to Save", "No sun settings have been changed.")
            return

        name = simpledialog.askstring(
            "Save Preset",
            "Enter a name for this preset (e.g. 'My Desert Noon'):",
            parent=self
        )
        if not name or not name.strip():
            return

        name = name.strip()

        # Collect current values
        current_values = {}
        for key, entry in self.sun_entries.items():
            val = entry.get().strip()
            if val:
                current_values[key] = val

        if self.save_preset_to_json(name, current_values):
            # Reload presets to update UI
            self.sun_presets = self.load_sun_presets()
            self.preset_combo["values"] = list(self.sun_presets.keys())
            self.preset_var.set(name)  # select the newly saved one
            messagebox.showinfo("Saved", f"Preset '{name}' saved successfully!\nYou can now load it anytime.")

    def load_preset(self):
        preset_name = self.preset_var.get()
        if not preset_name or preset_name not in self.sun_presets:
            messagebox.showwarning("No Preset", "Please select a valid preset first.")
            return

        values = self.sun_presets[preset_name]
        for name, entry in self.sun_entries.items():
            value = values.get(name, "")
            entry.delete(0, tk.END)
            entry.insert(0, str(value))

        messagebox.showinfo("Preset Loaded", f"Loaded preset: {preset_name}")

    def save_now(self):
        mapname = self.app.map_name.get().strip()
        if not mapname:
            messagebox.showwarning("No map", "Select a map first")
            return

        cod2 = Path(self.app.cod2_path.get())
        path = cod2 / "main" / "sun" / f"{mapname}.sun"

        lines = ["// Generated SUN file"]
        for name, entry in self.sun_entries.items():
            value = entry.get().strip()
            if value:
                lines.append(f"{name} {value}")

        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            messagebox.showinfo("Success", f"Saved:\n{path}")
            self.update_missing_status()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def save_files(self, cod2_path: Path, mapname: str):
        path = cod2_path / "main" / "sun" / f"{mapname}.sun"
        lines = ["// Generated SUN file"]
        for name, entry in self.sun_entries.items():
            value = entry.get().strip()
            if value:
                lines.append(f"{name} {value}")

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def update_missing_status(self):
        mapname = self.app.map_name.get().strip()
        if not mapname:
            self.missing_label.config(text="")
            self.create_btn.state(["disabled"])
            return

        status = self.app.check_missing_files(Path(self.app.cod2_path.get()), mapname)
        if not status.get("sun", {}).get("exists", False):
            self.missing_label.config(text=f"File missing: {mapname}.sun", foreground="red")
            self.create_btn.config(text=f"Create {mapname}.sun")
            self.create_btn.state(["!disabled"])
        else:
            self.missing_label.config(text="SUN file exists ✓", foreground="green")
            self.create_btn.state(["disabled"])

        self.load_from_file(Path(self.app.cod2_path.get()), mapname)

    def load_from_file(self, cod2_path: Path, mapname: str):
        sun_path = cod2_path / "main" / "sun" / f"{mapname}.sun"
        if not sun_path.exists():
            sun_path = cod2_path / "sun" / f"{mapname}.sun"

        if sun_path.exists():
            try:
                sun_content = sun_path.read_text(encoding="utf-8")
                for line in sun_content.split('\n'):
                    line = line.strip()
                    if not line or line.startswith('//'):
                        continue
                    parts = line.split(None, 1)
                    if len(parts) == 2:
                        key, value = parts
                        if key in self.sun_entries:
                            self.sun_entries[key].delete(0, tk.END)
                            self.sun_entries[key].insert(0, value)
            except Exception as e:
                print(f"[DEBUG SUN] Load error: {e}")

    def create_file_if_missing(self):
        mapname = self.app.map_name.get().strip()
        if not mapname:
            return

        cod2 = Path(self.app.cod2_path.get())
        path = cod2 / "main" / "sun" / f"{mapname}.sun"
        if path.exists():
            return

        lines = ["// Generated SUN file"]
        for name, entry in self.sun_entries.items():
            value = entry.get().strip()
            if value:
                lines.append(f"{name} {value}")

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        messagebox.showinfo("Created", f"Created basic SUN file:\n{path}")
        self.update_missing_status()
