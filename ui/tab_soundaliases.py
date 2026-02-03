import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
import csv

class SoundAliasesTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.entries = {}
        self.current_edit_iid = None
        self.create_widgets()
        self.update_missing_status()

    def create_widgets(self):
        self.missing_label = ttk.Label(self, text="", foreground="red", font=("Segoe UI", 10, "bold"))
        self.missing_label.pack(anchor="w", pady=6)

        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", pady=6)
        self.create_btn = ttk.Button(
            btn_frame,
            text="Create missing soundaliases csv",
            command=self.create_file_if_missing
        )
        self.create_btn.pack(side="left")
        self.create_btn.state(["disabled"])

        ttk.Separator(self, orient="horizontal").pack(fill="x", pady=10)

        ttk.Label(self, text="Sound Alias Entries", font=("Segoe UI", 11, "bold")).pack(anchor="w")

        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill="both", expand=True, pady=(4, 0))

        xscroll = ttk.Scrollbar(tree_frame, orient="horizontal")
        xscroll.pack(side="bottom", fill="x")

        yscroll = ttk.Scrollbar(tree_frame, orient="vertical")
        yscroll.pack(side="right", fill="y")

        self.tree = ttk.Treeview(
            tree_frame,
            columns=self.get_column_names(),
            show="headings",
            height=10,
            xscrollcommand=xscroll.set,
            yscrollcommand=yscroll.set
        )
        self.tree.pack(side="left", fill="both", expand=True)

        xscroll.config(command=self.tree.xview)
        yscroll.config(command=self.tree.yview)

        for col in self.get_column_names():
            self.tree.heading(col, text=col)
            self.tree.column(col, width=110, anchor="w")

        self.tree.column("name", width=180)
        self.tree.column("file", width=240)
        self.tree.column("loadspec", width=140)

        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

        form_frame = ttk.LabelFrame(self, text="Add / Edit Sound Alias", padding=12)
        form_frame.pack(fill="x", pady=10)

        self.create_form(form_frame)

        btns = ttk.Frame(self)
        btns.pack(fill="x", pady=(5, 10))

        ttk.Button(btns, text="Add / Update", command=self.add_or_update_entry).pack(side="left", padx=6)
        ttk.Button(btns, text="Clear Form", command=self.clear_form).pack(side="left", padx=6)
        ttk.Button(btns, text="Remove Selected", command=self.remove_selected).pack(side="right", padx=6)

    def get_column_names(self):
        return [
            "name", "sequence", "file", "vol_min", "vol_max", "vol_mod",
            "pitch_min", "pitch_max", "dist_min", "dist_max", "channel",
            "type", "probability", "loop", "masterslave", "loadspec",
            "subtitle", "compression", "secondaryaliasname", "volumefalloffcurve",
            "startdelay", "speakermap", "reverb", "lfe percentage"
        ]

    def create_form(self, parent):
        columns = self.get_column_names()
        channel_values = ["", "local", "announce", "mission", "voice", "music", "voicechat", "effects"]
        type_values = ["", "streamed", "loaded"]
        loop_values = ["", "looping", "oneshot"]
        compression_values = ["", "pc", "xb"]

        row = 0
        field_col = 0

        for col_name in columns:
            ttk.Label(parent, text=f"{col_name}:", width=18, anchor="e") \
                .grid(row=row, column=field_col * 3, sticky="e", padx=(0, 4), pady=4)

            if col_name == "channel":
                widget = ttk.Combobox(parent, values=channel_values, width=22, state="readonly")
                widget.set("local")
            elif col_name == "type":
                widget = ttk.Combobox(parent, values=type_values, width=22, state="readonly")
                widget.set("streamed")
            elif col_name == "loop":
                widget = ttk.Combobox(parent, values=loop_values, width=22, state="readonly")
                widget.set("looping")
            elif col_name == "compression":
                widget = ttk.Combobox(parent, values=compression_values, width=22, state="readonly")
            elif col_name in ("vol_min", "vol_max", "pitch_min", "pitch_max", "startdelay"):
                widget = tk.Spinbox(parent, from_=0.0, to=2.0, increment=0.01, width=10)
            elif col_name in ("dist_min", "dist_max"):
                widget = tk.Spinbox(parent, from_=0, to=20000, increment=50, width=10)
            elif col_name in ("probability", "lfe percentage"):
                widget = tk.Spinbox(parent, from_=0, to=100, increment=5, width=10)
            else:
                widget = ttk.Entry(parent, width=26)

            widget.grid(row=row, column=field_col * 3 + 1, sticky="w", padx=4, pady=4)
            self.entries[col_name] = widget

            field_col += 1
            if field_col >= 3:
                field_col = 0
                row += 1

            mapname = self.app.map_name.get().strip() or "mapname"
            if col_name == "name":
                widget.insert(0, f"ambient_mp_{mapname}")
            elif col_name == "file":
                widget.insert(0, f"ambient/amb_{mapname}_01.mp3")
            elif col_name == "loadspec":
                widget.insert(0, f"mp_{mapname}")
            elif col_name in ("vol_min", "vol_max"):
                widget.delete(0, tk.END)
                widget.insert(0, "0.65")

    def add_or_update_entry(self):
        values = [self.entries[col].get().strip() or "" for col in self.get_column_names()]

        if not values[0]:
            messagebox.showwarning("Missing Name", "Alias name is required!")
            return
        if not values[2]:
            messagebox.showwarning("Missing File", "Sound file path is required!")
            return

        if self.current_edit_iid:
            self.tree.item(self.current_edit_iid, values=values)
            self.current_edit_iid = None
        else:
            self.tree.insert("", "end", values=values)

        self.clear_form()

    def on_tree_select(self, event):
        sel = self.tree.selection()
        if not sel:
            return

        self.current_edit_iid = sel[0]
        values = self.tree.item(sel[0])["values"]

        self.clear_form()
        for i, col in enumerate(self.get_column_names()):
            if i < len(values):
                val = values[i]
                widget = self.entries[col]
                if isinstance(widget, ttk.Combobox):
                    widget.set(val)
                elif isinstance(widget, (tk.Spinbox, ttk.Entry)):
                    widget.delete(0, tk.END)
                    widget.insert(0, val)

    def clear_form(self):
        for widget in self.entries.values():
            if isinstance(widget, (ttk.Entry, tk.Spinbox)):
                widget.delete(0, tk.END)
            elif isinstance(widget, ttk.Combobox):
                widget.set("")
        self.current_edit_iid = None

    def remove_selected(self):
        sel = self.tree.selection()
        if sel:
            self.tree.delete(sel)
            self.clear_form()

    def clear_all_ui(self):
        self.tree.delete(*self.tree.get_children())
        self.clear_form()
        self.current_edit_iid = None

    def load_from_file(self, cod2_path: Path, mapname: str):
        path = cod2_path / "main" / "soundaliases" / f"{mapname}.csv"
        if not path.exists():
            path = cod2_path / "soundaliases" / f"{mapname}.csv"

        self.tree.delete(*self.tree.get_children())

        if path.exists():
            try:
                with open(path, 'r', encoding="utf-8") as f:
                    reader = csv.reader(f)
                    skipped_header = False

                    for row in reader:
                        if not row or all(not cell.strip() for cell in row):
                            continue

                        first_cell = (row[0] or "").strip()

                        if first_cell.startswith('#'):
                            continue

                        if not skipped_header and (
                            first_cell.lower() == "name" or
                            "sequence" in first_cell.lower() or
                            "file" in first_cell.lower() or
                            "vol_min" in ','.join(row).lower()
                        ):
                            skipped_header = True
                            continue

                        if len(row) >= 3 and first_cell and not first_cell.startswith('#'):
                            padded = row + [""] * (len(self.get_column_names()) - len(row))
                            self.tree.insert("", "end", values=padded[:len(self.get_column_names())])

                print(f"[DEBUG Sound] Loaded CSV from {path} - skipped header/comments")
            except Exception as e:
                print(f"[DEBUG Sound] CSV load error: {e}")
                messagebox.showerror("CSV Load Error", str(e))

    def save_files(self, cod2_path: Path, mapname: str):
        path = cod2_path / "main" / "soundaliases" / f"{mapname}.csv"
        path.parent.mkdir(parents=True, exist_ok=True)

        header = ",".join(self.get_column_names())
        lines = ["# Generated by CoD2 Map Script Generator", header]

        for item in self.tree.get_children():
            values = self.tree.item(item)["values"]
            safe_values = [str(v).replace(",", "_") for v in values]  # prevent CSV break
            lines.append(",".join(safe_values))

        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"[DEBUG Sound] Saved to: {path}")

    def update_missing_status(self):
        mapname = self.app.map_name.get().strip()
        print(f"[DEBUG Sound] Updating for map: '{mapname}'")

        if not mapname:
            self.missing_label.config(text="")
            self.create_btn.state(["disabled"])
            self.clear_all_ui()
            print("[DEBUG Sound] No map - cleared")
            return

        self.clear_all_ui()
        print("[DEBUG Sound] UI cleared")

        cod2 = Path(self.app.cod2_path.get())
        status = self.app.check_missing_files(cod2, mapname)

        sound_key = "soundaliases_csv"
        file_status = status.get(sound_key, {})
        file_path = file_status.get("path")
        exists = file_status.get("exists", False)

        print(f"[DEBUG Sound] Path: {file_path} | Exists: {exists}")

        if exists:
            print(f"[DEBUG Sound] Loading existing file: {file_path}")
            try:
                self.load_from_file(cod2, mapname)
                print("[DEBUG Sound] Load successful")

                # ── FIXED: Now properly update UI when file exists ──
                self.missing_label.config(
                    text=f"Soundaliases exists ✓ ({mapname}.csv)",
                    foreground="green"
                )
                self.create_btn.state(["disabled"])

            except Exception as e:
                print(f"[DEBUG Sound] Load failed: {e}")
                messagebox.showerror("Load Error", f"Failed to load soundaliases:\n{e}")
                self.missing_label.config(text="Error loading file", foreground="red")
                self.create_btn.state(["disabled"])  # prevent edits on broken file

        else:
            print("[DEBUG Sound] No file exists - using defaults")
            self.missing_label.config(
                text=f"Missing: soundaliases/{mapname}.csv",
                foreground="red"
            )
            self.create_btn.config(text=f"Create {mapname}.csv")
            self.create_btn.state(["!disabled"])

    def create_file_if_missing(self):
        mapname = self.app.map_name.get().strip()
        if not mapname:
            return

        cod2 = Path(self.app.cod2_path.get())
        path = cod2 / "main" / "soundaliases" / f"{mapname}.csv"

        if path.exists():
            messagebox.showinfo("Exists", "File already exists.")
            return

        header = ",".join(self.get_column_names())
        default_lines = [
            "# Generated by CoD2 Map Script Generator",
            header,
            f"ambient_mp_{mapname},,ambient/amb_{mapname}_01.mp3,0.65,,,,,,,local,streamed,,looping,,mp_{mapname},,,,",
        ]

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(default_lines) + "\n", encoding="utf-8")

        self.load_from_file(cod2, mapname)
        messagebox.showinfo("Created", f"Created basic soundaliases file:\n{path}")
        self.update_missing_status()