# ui/tab_basic.py
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path

from config import DEFAULT_CSV_CONTENT

class BasicFilesTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.create_widgets()
        self.update_missing_status()

    def create_widgets(self):
        self.missing_label = ttk.Label(self, text="", foreground="red", font=("Segoe UI", 10, "bold"))
        self.missing_label.pack(anchor="w", pady=6)

        self.create_btn = ttk.Button(self, text="Create missing files", command=self.create_missing_files)
        self.create_btn.pack(anchor="w", pady=6)
        self.create_btn.state(["disabled"])

        ttk.Label(self, text="CSV File (maps/mp/mp_mapname.csv)", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(10,4))
        ttk.Label(self, text="Loadscreen initialization – format: levelBriefing,loadscreen_<mapname>",
                  foreground="gray", font=("Segoe UI", 8)).pack(anchor="w", pady=(0, 4))
        self.csv_text = tk.Text(self, height=3, width=80, wrap="word")
        self.csv_text.pack(fill="x", pady=6)

        ttk.Separator(self, orient="horizontal").pack(fill="x", pady=20)

        ttk.Label(self, text="Arena File (mp/mp_mapname.arena)", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(10,4))

        ttk.Label(self, text="Display name (shown in server browser):").pack(anchor="w")
        self.longname_entry = ttk.Entry(self, width=70)
        self.longname_entry.pack(fill="x", pady=4)

        ttk.Label(self, text="Supported gametypes:").pack(anchor="w", pady=(12,4))

        self.gametype_vars = {
            "dm":  tk.BooleanVar(value=True),
            "tdm": tk.BooleanVar(value=False),
            "sd":  tk.BooleanVar(value=False),
            "hq":  tk.BooleanVar(value=False),
            "ctf": tk.BooleanVar(value=False),
        }

        gt_frame = ttk.Frame(self)
        gt_frame.pack(anchor="w", pady=4)
        for gt, var in self.gametype_vars.items():
            ttk.Checkbutton(gt_frame, text=gt.upper(), variable=var).pack(side="left", padx=12)

    def save_files(self, cod2_path: Path, mapname: str):
        csv_content = self.csv_text.get("1.0", tk.END).strip()
        if not csv_content:
            csv_content = DEFAULT_CSV_CONTENT(mapname)
        csv_path = cod2_path / "main" / "maps" / "mp" / f"{mapname}.csv"
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        csv_path.write_text(csv_content + "\n", encoding="utf-8")

        longname = self.longname_entry.get().strip() or f"Map {mapname}"
        gametypes = " ".join(gt.upper() for gt, var in self.gametype_vars.items() if var.get())

        arena_content = f"""{{
    map			"{mapname}"
    longname	"{longname}"
    gametype	"{gametypes}"
}}
"""

        arena_path = cod2_path / "main" / "mp" / f"{mapname}.arena"
        arena_path.parent.mkdir(parents=True, exist_ok=True)
        arena_path.write_text(arena_content, encoding="utf-8")

        print(f"[DEBUG Basic] Saved CSV to {csv_path} and arena to {arena_path}")

    def update_missing_status(self):
        mapname = self.app.map_name.get().strip()
        print(f"[DEBUG Basic] Updating for map: '{mapname}'")

        if not mapname:
            self.missing_label.config(text="")
            self.create_btn.state(["disabled"])
            self.clear_all_ui()
            print("[DEBUG Basic] No map - UI cleared")
            return

        self.clear_all_ui()
        print("[DEBUG Basic] UI cleared")

        cod2 = Path(self.app.cod2_path.get())
        status = self.app.check_missing_files(cod2, mapname)

        missing_files = [k for k, v in status.items() if k in ["csv", "arena"] and not v.get("exists", False)]

        if missing_files:
            self.missing_label.config(text=f"Missing files: {', '.join(missing_files)}", foreground="red")
            self.create_btn.config(text="Create missing files")
            self.create_btn.state(["!disabled"])
            print(f"[DEBUG Basic] Missing: {missing_files}")
        else:
            self.missing_label.config(text="All files exist ✓", foreground="green")
            self.create_btn.state(["disabled"])
            print("[DEBUG Basic] All files exist")

        if status.get("csv", {}).get("exists", False) or status.get("arena", {}).get("exists", False):
            print("[DEBUG Basic] Loading existing data")
            try:
                self.load_from_files(cod2, mapname)  # ← This must match the method name below
                print("[DEBUG Basic] Load successful")
            except Exception as e:
                print(f"[DEBUG Basic] Load failed: {e}")
                messagebox.showerror("Load Error", f"Failed to load basic files:\n{e}")
        else:
            print("[DEBUG Basic] No files - using defaults")

    def load_from_files(self, cod2_path: Path, mapname: str):  # ← Renamed from load_from_file (plural)
        """Parse and load existing CSV and Arena files"""
        # Load CSV
        csv_path = cod2_path / "main" / "maps" / "mp" / f"{mapname}.csv"
        if not csv_path.exists():
            csv_path = cod2_path / "maps" / "mp" / f"{mapname}.csv"

        if csv_path.exists():
            try:
                csv_content = csv_path.read_text(encoding="utf-8").strip()
                self.csv_text.delete("1.0", tk.END)
                self.csv_text.insert("1.0", csv_content)
                print(f"[DEBUG Basic] Loaded CSV from {csv_path}")
            except Exception as e:
                print(f"[DEBUG Basic] CSV load error: {e}")

        # Load Arena
        arena_path = cod2_path / "main" / "mp" / f"{mapname}.arena"
        if not arena_path.exists():
            arena_path = cod2_path / "mp" / f"{mapname}.arena"

        if arena_path.exists():
            try:
                arena_content = arena_path.read_text(encoding="utf-8")
                for line in arena_content.split('\n'):
                    line = line.strip()
                    if line.startswith('longname'):
                        val = line.split('"')[1] if '"' in line else ""
                        self.longname_entry.delete(0, tk.END)
                        self.longname_entry.insert(0, val)
                    elif line.startswith('gametype'):
                        val = line.split('"')[1] if '"' in line else ""
                        for var in self.gametype_vars.values():
                            var.set(False)
                        for gt in val.split():
                            gt_lower = gt.lower()
                            if gt_lower in self.gametype_vars:
                                self.gametype_vars[gt_lower].set(True)
                print(f"[DEBUG Basic] Loaded arena from {arena_path}")
            except Exception as e:
                print(f"[DEBUG Basic] Arena load error: {e}")

    def create_missing_files(self):
        mapname = self.app.map_name.get().strip()
        if not mapname:
            return

        cod2 = Path(self.app.cod2_path.get())
        status = self.app.check_missing_files(cod2, mapname)

        if not status.get("csv", {}).get("exists", False):
            csv_path = cod2 / "main" / "maps" / "mp" / f"{mapname}.csv"
            csv_path.parent.mkdir(parents=True, exist_ok=True)
            csv_content = DEFAULT_CSV_CONTENT(mapname)
            csv_path.write_text(csv_content, encoding="utf-8")
            self.csv_text.delete("1.0", tk.END)
            self.csv_text.insert("1.0", csv_content)
            print(f"[DEBUG Basic] Created CSV: {csv_path}")

        if not status.get("arena", {}).get("exists", False):
            arena_path = cod2 / "main" / "mp" / f"{mapname}.arena"
            arena_path.parent.mkdir(parents=True, exist_ok=True)
            longname = f"Map {mapname}"
            arena_content = f"""{{
    map			"{mapname}"
    longname	"{longname}"
    gametype	"DM"
}}
"""
            arena_path.write_text(arena_content, encoding="utf-8")
            self.longname_entry.delete(0, tk.END)
            self.longname_entry.insert(0, longname)
            print(f"[DEBUG Basic] Created arena: {arena_path}")

        self.update_missing_status()
        messagebox.showinfo("Created", "Missing files created successfully")

    def clear_all_ui(self):
        """Clear all UI elements when switching maps"""
        self.csv_text.delete("1.0", tk.END)
        self.longname_entry.delete(0, tk.END)
        for var in self.gametype_vars.values():
            var.set(False)
        print("[DEBUG Basic] UI cleared")