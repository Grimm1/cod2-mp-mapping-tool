# ui/tab_sun.py
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path

from presets import (
    get_sun_presets,
    get_sun_preset_names,
    get_sun_preset_by_name
)

class SunTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.sun_presets = get_sun_presets()   # Load once here
        self.create_widgets()
        self.update_missing_status()

    def create_widgets(self):
        # Missing file status
        self.missing_label = ttk.Label(self, text="", foreground="red", font=("Segoe UI", 10, "bold"))
        self.missing_label.pack(anchor="w", pady=6)

        self.create_btn = ttk.Button(self, text="Create mp_XXXX.sun", command=self.create_file_if_missing)
        self.create_btn.pack(anchor="w", pady=6)
        self.create_btn.state(["disabled"])

        ttk.Label(self, text="SUN File: sun/mp_mapname.sun", font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=12)

        # Presets section
        preset_frame = ttk.LabelFrame(self, text=" Presets ", padding=10)
        preset_frame.pack(fill="x", padx=20, pady=10)

        ttk.Label(preset_frame, text="Load a preset:").pack(anchor="w", pady=4)
        self.preset_var = tk.StringVar(value="")
        self.preset_combo = ttk.Combobox(
            preset_frame,
            textvariable=self.preset_var,
            values=get_sun_preset_names(),  # ← Imported
            state="readonly",
            width=40
        )
        self.preset_combo.pack(anchor="w", pady=4)

        ttk.Button(preset_frame, text="Load Preset", command=self.load_preset).pack(anchor="w", pady=4)

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

        # Create 2-column layout with fixed widths
        row_frames = []
        for idx, (name, default, desc) in enumerate(fields):
            # Create a new row frame for each pair
            col = idx % 2
            if col == 0:
                row = ttk.Frame(frame)
                row.pack(fill="x", pady=3)
                row_frames.append(row)
            else:
                row = row_frames[-1]
            
            # Create column container with fixed width
            col_frame = ttk.Frame(row)
            col_frame.pack(side="left", fill="both", expand=True, padx=(0, 20) if col == 0 else (0, 0))
            
            # Fixed width for labels to align inputs
            ttk.Label(col_frame, text=f"{name}:", width=22).pack(side="left", padx=(0, 4))
            entry = ttk.Entry(col_frame, width=18)
            entry.insert(0, default)
            entry.pack(side="left", padx=(0, 4), fill="x", expand=True)
            ttk.Label(col_frame, text=desc, foreground="gray", font=("Segoe UI", 8), width=30).pack(side="left", padx=(0, 2))

            self.sun_entries[name] = entry
        
        # Add Generate button in a footer section
        button_frame = ttk.Frame(scrollable_frame)
        button_frame.pack(fill="x", pady=(15, 0))
        ttk.Button(button_frame, text="Generate SUN File", command=self.save_now).pack(side="left", padx=15)

    def load_preset(self):
        preset_name = self.preset_var.get()
        if not preset_name:
            messagebox.showwarning("No Selection", "Please select a preset first.")
            return

        preset = get_sun_preset_by_name(preset_name)
        if not preset:
            messagebox.showerror("Preset Not Found", f"Preset '{preset_name}' not found.")
            return

        # Apply all values from preset to entries
        for name, entry in self.sun_entries.items():
            value = preset.get(name, "")
            entry.delete(0, tk.END)
            entry.insert(0, value)

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
        # Same logic as save_now but without dialog
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

        # Load existing data if file exists
        self.load_from_file(Path(self.app.cod2_path.get()), mapname)

    def load_from_file(self, cod2_path: Path, mapname: str):
        """Parse and load existing SUN file"""
        sun_path = cod2_path / "main" / "sun" / f"{mapname}.sun"
        if not sun_path.exists():
            sun_path = cod2_path / "sun" / f"{mapname}.sun"

        if sun_path.exists():
            try:
                sun_content = sun_path.read_text(encoding="utf-8")
                # Parse sun file and populate entries
                for line in sun_content.split('\n'):
                    line = line.strip()
                    if not line or line.startswith('//'):
                        continue

                    # Parse "key value" format
                    parts = line.split(None, 1)
                    if len(parts) == 2:
                        key, value = parts
                        if key in self.sun_entries:
                            self.sun_entries[key].delete(0, tk.END)
                            self.sun_entries[key].insert(0, value)
            except Exception as e:
                print(f"[DEBUG SUN] Load error: {e}")
                pass

    def create_file_if_missing(self):
        mapname = self.app.map_name.get().strip()
        if not mapname:
            return

        cod2_path = Path(self.app.cod2_path.get())
        path = cod2_path / "main" / "sun" / f"{mapname}.sun"
        if path.exists():
            return

        lines = ["// Generated SUN file"]
        for name, entry in self.sun_entries.items():
            value = entry.get().strip()
            if value:
                lines.append(f"{name} {value}")

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        messagebox.showinfo("Created", f"Created basic file:\n{path}")
        self.update_missing_status()