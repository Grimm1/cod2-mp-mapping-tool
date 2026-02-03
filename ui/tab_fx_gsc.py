# ui/tab_fx_gsc.py
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
import re

class FXGSCTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.precache_entries = []      # (name, fx_path)
        self.scr_sound_entries = []     # (key, value)
        self.usage_calls = []           # (effect_name_or_alias, func_type, params_string)
        self.create_widgets()
        self.update_missing_status()

    def create_widgets(self):
        self.missing_label = ttk.Label(self, text="", foreground="red", font=("Segoe UI", 10, "bold"))
        self.missing_label.pack(anchor="w", pady=6)

        self.create_btn = ttk.Button(self, text="Create mp_XXXX_fx.gsc", command=self.create_file_if_missing)
        self.create_btn.pack(anchor="w", pady=6)
        self.create_btn.state(["disabled"])

        # Single big scrollable canvas for the whole tab
        canvas = tk.Canvas(self)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Two-column layout inside scrollable frame
        columns = ttk.Frame(scrollable_frame)
        columns.pack(fill="both", expand=True, padx=20, pady=10)

        # Left column: Preview + Precache + scr_sound
        left = ttk.Frame(columns, width=750)
        left.pack(side="left", fill="y", expand=False, padx=(0, 20))
        left.pack_propagate(False)

        # Preview at top-left
        ttk.Label(left, text="Full FX Script Preview (read-only)", font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0, 4))
        self.preview_text = tk.Text(left, height=12, width=80, font=("Consolas", 10), state="disabled")
        self.preview_text.pack(fill="both", expand=True, pady=(0, 12))

        # PrecacheFX - compact
        ttk.Label(left, text="PrecacheFX() - Define Effects", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 6))

        precache_input = ttk.Frame(left)
        precache_input.pack(fill="x", pady=4)

        ttk.Label(precache_input, text="Effect Name:").pack(side="left", padx=(0, 4))
        self.effect_name_entry = ttk.Entry(precache_input, width=25)
        self.effect_name_entry.pack(side="left", padx=4)

        ttk.Label(precache_input, text="FX File Path:").pack(side="left", padx=(12, 4))
        self.fx_path_entry = ttk.Entry(precache_input, width=35)
        self.fx_path_entry.pack(side="left", fill="x", expand=True, padx=4)

        ttk.Button(precache_input, text="Browse...", command=self.browse_fx).pack(side="left", padx=(8, 4))

        ttk.Button(precache_input, text="Add Effect", command=self.add_precache_effect).pack(side="left", padx=(12, 0))

        self.precache_list = tk.Listbox(left, height=5, font=("Consolas", 10))
        self.precache_list.pack(fill="both", expand=False, pady=(6, 4))

        ttk.Button(left, text="Remove Selected Effect", command=self.remove_precache).pack(anchor="w", pady=4)

        # scr_sound - compact
        ttk.Label(left, text="scr_sound References (for scripted playable sounds)", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(12, 4))
        ttk.Label(left, text="These define aliases that can be played elsewhere (e.g. via playSoundOnPlayers).",
                  foreground="gray", font=("Segoe UI", 8), justify="left").pack(anchor="w", pady=(0, 8))

        scr_input = ttk.Frame(left)
        scr_input.pack(fill="x", pady=4)

        ttk.Label(scr_input, text="Key:").pack(side="left", padx=(0, 4))
        self.scr_key_entry = ttk.Entry(scr_input, width=25)
        self.scr_key_entry.pack(side="left", padx=4)

        ttk.Label(scr_input, text="Value:").pack(side="left", padx=(12, 4))
        self.scr_value_entry = ttk.Entry(scr_input, width=35)
        self.scr_value_entry.pack(side="left", fill="x", expand=True, padx=4)

        ttk.Button(scr_input, text="Add scr_sound", command=self.add_scr_sound).pack(side="left", padx=(12, 0))

        self.scr_sound_list = tk.Listbox(left, height=5, font=("Consolas", 10))
        self.scr_sound_list.pack(fill="both", expand=False, pady=(6, 4))

        ttk.Button(left, text="Remove Selected scr_sound", command=self.remove_scr_sound).pack(anchor="w", pady=4)

        # Right column: Usage Calls + Table
        right = ttk.Frame(columns)
        right.pack(side="right", fill="both", expand=True)

        ttk.Label(right, text="AmbientFX() / Usage Calls (Visual & Positional Audio Effects)", font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0, 6))

        usage_frame = ttk.LabelFrame(right, text="Add Usage Call", padding=10)
        usage_frame.pack(fill="x", pady=6)

        ttk.Label(usage_frame, text="Select Effect:").pack(anchor="w")
        self.effect_choice = ttk.Combobox(usage_frame, width=50, state="readonly")
        self.effect_choice.pack(fill="x", pady=4)

        ttk.Label(usage_frame, text="Function Type:").pack(anchor="w", pady=(8, 0))
        self.func_type = ttk.Combobox(
            usage_frame,
            width=50,
            values=["loopfx", "OneShotfx", "soundfx", "gunfireloopfx", "GrenadeExplosionfx"],
            state="readonly"
        )
        self.func_type.set("loopfx")
        self.func_type.pack(fill="x", pady=4)
        self.func_type.bind("<<ComboboxSelected>>", self.rebuild_param_inputs)

        # Dynamic parameters frame (will be rebuilt)
        self.param_container = ttk.Frame(usage_frame)
        self.param_container.pack(fill="x", pady=(12, 0))

        # Initial build
        self.param_widgets = {}
        self.rebuild_param_inputs()

        ttk.Button(usage_frame, text="Add Usage Call", command=self.add_usage_call).pack(anchor="w", pady=12)

        # Usage table
        ttk.Label(right, text="Current Usage Calls (select to remove)", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(12, 4))
        self.usage_table = ttk.Treeview(right, columns=("effect", "type", "params"), show="headings", height=12)
        self.usage_table.heading("effect", text="Effect Name / Alias")
        self.usage_table.heading("type", text="Function")
        self.usage_table.heading("params", text="Parameters")
        self.usage_table.column("effect", width=200)
        self.usage_table.column("type", width=140)
        self.usage_table.column("params", width=500)
        self.usage_table.pack(fill="both", expand=True, pady=4)

        button_frame = ttk.Frame(right)
        button_frame.pack(anchor="w", pady=4, fill="x")
        ttk.Button(button_frame, text="Edit Selected Usage", command=self.edit_usage_call).pack(side="left", padx=(0, 4))
        ttk.Button(button_frame, text="Remove Selected Usage", command=self.remove_usage_call).pack(side="left")

    # ------------------------------------------------------------------
    # Browse FX method
    # ------------------------------------------------------------------
    def browse_fx(self):
        cod2_path_str = self.app.cod2_path.get().strip()
        if not cod2_path_str:
            messagebox.showwarning("No CoD2 Path", "Please set the Call of Duty 2 location first (in the Script Tools tab).")
            return

        initial_dir = Path(cod2_path_str) / "main" / "fx"

        selected = filedialog.askopenfilename(
            title="Select FX Effect File (.efx)",
            initialdir=str(initial_dir) if initial_dir.exists() else str(Path(cod2_path_str)),
            filetypes=[("FX Effect Files", "*.efx"), ("All Files", "*.*")]
        )

        if selected:
            try:
                full_path = Path(selected)
                base_path = Path(cod2_path_str) / "main"
                rel_path = full_path.relative_to(base_path)
                fx_path = str(rel_path.with_suffix("")).replace("\\", "/")
                self.fx_path_entry.delete(0, tk.END)
                self.fx_path_entry.insert(0, fx_path)
            except ValueError:
                messagebox.showwarning("Invalid Path", "The selected file must be inside the CoD2 'main' folder.")
            except Exception as e:
                messagebox.showerror("Error", f"Unexpected error processing path: {e}")

    # ------------------------------------------------------------------
    # Dynamic parameter inputs
    # ------------------------------------------------------------------
    def rebuild_param_inputs(self, event=None):
        for widget in self.param_container.winfo_children():
            widget.destroy()
        self.param_widgets.clear()

        func = self.func_type.get()

        if func == "soundfx":
            # Special case: sound alias + origin
            alias_frame = ttk.Frame(self.param_container)
            alias_frame.pack(fill="x", pady=(0, 8))
            ttk.Label(alias_frame, text="Sound Alias (must exist in soundaliases csv):").pack(side="left", padx=(0, 8))
            alias_entry = ttk.Entry(alias_frame, width=40)
            alias_entry.pack(side="left", fill="x", expand=True)
            self.param_widgets["sound_alias"] = alias_entry

            ttk.Label(self.param_container,
                      text="Reminder: Define this alias in the Sound Aliases tab first!",
                      foreground="orange", font=("Segoe UI", 9, "italic")).pack(anchor="w", pady=(0, 8))

            origin_frame = ttk.LabelFrame(self.param_container, text="Origin (x, y, z) - Required")
            origin_frame.pack(fill="x", pady=(0, 8))
            self.create_vector_inputs(origin_frame, "origin")

        else:
            # Common origin for all other functions
            origin_frame = ttk.LabelFrame(self.param_container, text="Origin (x, y, z) - Required")
            origin_frame.pack(fill="x", pady=(0, 8))
            self.create_vector_inputs(origin_frame, "origin")

            if func in ["loopfx", "OneShotfx"]:
                delay_frame = ttk.Frame(self.param_container)
                delay_frame.pack(fill="x", pady=4)
                label_text = "Delay between shots (seconds)" if func == "loopfx" else "Pre-delay (seconds before effect)"
                ttk.Label(delay_frame, text=label_text + ":").grid(row=0, column=0, sticky="w", padx=(0, 8))
                delay_entry = ttk.Entry(delay_frame, width=15)
                delay_entry.insert(0, "0.3" if func == "loopfx" else "0")
                delay_entry.grid(row=0, column=1, sticky="w")
                self.param_widgets["delay"] = delay_entry

                fwd_var = tk.BooleanVar()
                fwd_check = ttk.Checkbutton(self.param_container, text="Add optional forward vector (for directional FX)", variable=fwd_var)
                fwd_check.pack(anchor="w", pady=(8, 0))
                fwd_frame = ttk.Frame(self.param_container)
                fwd_frame.pack(fill="x", pady=(4, 0))
                self.create_vector_inputs(fwd_frame, "forward")
                fwd_frame.pack_forget()
                def toggle_fwd(*args):
                    if fwd_var.get():
                        fwd_frame.pack(fill="x", pady=(4, 12))
                    else:
                        fwd_frame.pack_forget()
                fwd_var.trace("w", toggle_fwd)
                self.param_widgets["fwd_var"] = fwd_var
                self.param_widgets["fwd_frame"] = fwd_frame

            elif func == "gunfireloopfx":
                gf_frame = ttk.LabelFrame(self.param_container, text="Gunfire Parameters")
                gf_frame.pack(fill="x", pady=(0, 12))

                pairs = [
                    ("Shots (min, max)", "10", "15"),
                    ("Shot delay (min, max)", "0.1", "0.3"),
                    ("Between sets (min, max)", "2.5", "9")
                ]
                for i, (label, def_min, def_max) in enumerate(pairs):
                    ttk.Label(gf_frame, text=label + ":").grid(row=i, column=0, sticky="w", padx=(0, 8), pady=4)
                    min_entry = ttk.Entry(gf_frame, width=12)
                    min_entry.insert(0, def_min)
                    min_entry.grid(row=i, column=1, padx=4)
                    max_entry = ttk.Entry(gf_frame, width=12)
                    max_entry.insert(0, def_max)
                    max_entry.grid(row=i, column=2, padx=4)
                    self.param_widgets[f"gf_min_{i}"] = min_entry
                    self.param_widgets[f"gf_max_{i}"] = max_entry

            elif func == "GrenadeExplosionfx":
                ttk.Label(self.param_container, text="Only origin required – creates explosion FX with view jitter", foreground="gray").pack(anchor="w", pady=8)

    def create_vector_inputs(self, parent, prefix):
        frame = ttk.Frame(parent)
        frame.pack(fill="x", pady=4)
        ttk.Label(frame, text=f"{prefix.capitalize()} X:").grid(row=0, column=0, sticky="e", padx=(0, 4))
        x_entry = ttk.Entry(frame, width=12)
        x_entry.grid(row=0, column=1, padx=4)
        ttk.Label(frame, text="Y:").grid(row=0, column=2, sticky="e", padx=(20, 4))
        y_entry = ttk.Entry(frame, width=12)
        y_entry.grid(row=0, column=3, padx=4)
        ttk.Label(frame, text="Z:").grid(row=0, column=4, sticky="e", padx=(20, 4))
        z_entry = ttk.Entry(frame, width=12)
        z_entry.grid(row=0, column=5, padx=4)
        self.param_widgets[f"{prefix}_x"] = x_entry
        self.param_widgets[f"{prefix}_y"] = y_entry
        self.param_widgets[f"{prefix}_z"] = z_entry

    # ------------------------------------------------------------------
    # Validation & param string construction
    # ------------------------------------------------------------------
    def build_params_string(self):
        func = self.func_type.get()
        parts = []

        if func == "soundfx":
            alias = self.param_widgets["sound_alias"].get().strip()
            if not alias:
                messagebox.showwarning("Missing Alias", "Sound alias name is required for soundfx.")
                return None
            parts.append(f"\"{alias}\"")

            try:
                ox = float(self.param_widgets["origin_x"].get().strip() or 0)
                oy = float(self.param_widgets["origin_y"].get().strip() or 0)
                oz = float(self.param_widgets["origin_z"].get().strip() or 0)
                origin_str = f"({ox}, {oy}, {oz})"
                parts.append(origin_str)
            except ValueError:
                messagebox.showwarning("Invalid Origin", "Origin X/Y/Z must be valid numbers.")
                return None

        else:
            try:
                ox = float(self.param_widgets["origin_x"].get().strip() or 0)
                oy = float(self.param_widgets["origin_y"].get().strip() or 0)
                oz = float(self.param_widgets["origin_z"].get().strip() or 0)
                origin_str = f"({ox}, {oy}, {oz})"
                parts.append(origin_str)
            except ValueError:
                messagebox.showwarning("Invalid Origin", "Origin X/Y/Z must be valid numbers.")
                return None

            if func in ["loopfx", "OneShotfx"]:
                try:
                    delay = float(self.param_widgets["delay"].get().strip())
                    parts.append(str(delay))
                except ValueError:
                    messagebox.showwarning("Invalid Delay", "Delay must be a number.")
                    return None

                if "fwd_var" in self.param_widgets and self.param_widgets["fwd_var"].get():
                    try:
                        fx = float(self.param_widgets["forward_x"].get().strip())
                        fy = float(self.param_widgets["forward_y"].get().strip())
                        fz = float(self.param_widgets["forward_z"].get().strip())
                        parts.append(f"({fx}, {fy}, {fz})")
                    except ValueError:
                        messagebox.showwarning("Invalid Forward Vector", "Forward vector X/Y/Z must be valid numbers.")
                        return None

            elif func == "gunfireloopfx":
                try:
                    shots_min = int(self.param_widgets["gf_min_0"].get().strip())
                    shots_max = int(self.param_widgets["gf_max_0"].get().strip())
                    delay_min = float(self.param_widgets["gf_min_1"].get().strip())
                    delay_max = float(self.param_widgets["gf_max_1"].get().strip())
                    set_min = float(self.param_widgets["gf_min_2"].get().strip())
                    set_max = float(self.param_widgets["gf_max_2"].get().strip())
                    parts.extend([str(shots_min), str(shots_max), str(delay_min), str(delay_max), str(set_min), str(set_max)])
                except ValueError:
                    messagebox.showwarning("Invalid Gunfire Params", "All gunfire values must be valid numbers.")
                    return None

        return ", ".join(parts)

    # ------------------------------------------------------------------
    # Add / Remove / Preview
    # ------------------------------------------------------------------
    def add_usage_call(self):
        func_type = self.func_type.get().strip()

        if func_type != "soundfx":
            effect_name = self.effect_choice.get().strip()
            if not effect_name:
                messagebox.showwarning("No Effect", "Select a precached effect first.")
                return
            display_effect = effect_name
        else:
            display_effect = "(sound alias)"

        params = self.build_params_string()
        if params is None:
            return

        # Check if we're editing an existing call
        sel = self.usage_table.selection()
        if sel:
            # Update existing
            item = sel[0]
            idx = self.usage_table.index(item)
            self.usage_calls[idx] = (display_effect, func_type, params)
            self.usage_table.item(item, values=(display_effect, func_type, params))
        else:
            # Add new
            self.usage_calls.append((display_effect, func_type, params))
            self.usage_table.insert("", "end", values=(display_effect, func_type, params))

        self.update_preview()

        # Clear fields
        for key in ["origin_x", "origin_y", "origin_z"]:
            if key in self.param_widgets:
                self.param_widgets[key].delete(0, tk.END)
        if func_type in ["loopfx", "OneShotfx"]:
            self.param_widgets["delay"].delete(0, tk.END)
            self.param_widgets["delay"].insert(0, "0.3" if func_type == "loopfx" else "0")
        if func_type == "soundfx" and "sound_alias" in self.param_widgets:
            self.param_widgets["sound_alias"].delete(0, tk.END)

    def remove_usage_call(self):
        sel = self.usage_table.selection()
        if not sel:
            return

        for item in sel:
            idx = self.usage_table.index(item)
            del self.usage_calls[idx]
            self.usage_table.delete(item)

        self.update_preview()

    def edit_usage_call(self):
        sel = self.usage_table.selection()
        if not sel:
            messagebox.showwarning("No Selection", "Please select a usage call to edit.")
            return

        if len(sel) > 1:
            messagebox.showwarning("Multiple Selected", "Please select only one usage call to edit.")
            return

        item = sel[0]
        idx = self.usage_table.index(item)
        display_effect, func_type, params = self.usage_calls[idx]

        # Set the function type
        self.func_type.set(func_type)
        self.rebuild_param_inputs()

        # Set the effect choice if not a sound alias
        if display_effect != "(sound alias)":
            self.effect_choice.set(display_effect)

        # Parse and populate parameters
        self.populate_params_from_string(params, func_type, display_effect)

        # Scroll to the top to show the input fields
        self.master.master.yview_moveto(0)

    def populate_params_from_string(self, params: str, func_type: str, display_effect: str):
        """Parse parameters string and populate the input fields."""
        try:
            # Helper to extract coordinates from "(x, y, z)" format
            def extract_coords(coord_str):
                coord_str = coord_str.strip()
                if coord_str.startswith("(") and coord_str.endswith(")"):
                    coord_str = coord_str[1:-1]
                parts = [p.strip() for p in coord_str.split(",")]
                return parts if len(parts) == 3 else ["0", "0", "0"]

            if func_type == "soundfx":
                # Extract sound alias from params like: "alias_name", (x, y, z)
                match = re.match(r'"([^"]+)"\s*,\s*(.+)', params)
                if match:
                    alias = match.group(1)
                    origin_str = match.group(2)
                    self.param_widgets["sound_alias"].delete(0, tk.END)
                    self.param_widgets["sound_alias"].insert(0, alias)
                    coords = extract_coords(origin_str)
                    self.param_widgets["origin_x"].delete(0, tk.END)
                    self.param_widgets["origin_x"].insert(0, coords[0])
                    self.param_widgets["origin_y"].delete(0, tk.END)
                    self.param_widgets["origin_y"].insert(0, coords[1])
                    self.param_widgets["origin_z"].delete(0, tk.END)
                    self.param_widgets["origin_z"].insert(0, coords[2])

            elif func_type in ["loopfx", "OneShotfx"]:
                # Format: (x, y, z), delay [, (fx, fy, fz)]
                parts = [p.strip() for p in params.split(",")]
                # Extract origin (first coord triple)
                if len(parts) >= 3:
                    origin_parts = [parts[0].lstrip("("), parts[1], parts[2].rstrip(")")]
                    self.param_widgets["origin_x"].delete(0, tk.END)
                    self.param_widgets["origin_x"].insert(0, origin_parts[0])
                    self.param_widgets["origin_y"].delete(0, tk.END)
                    self.param_widgets["origin_y"].insert(0, origin_parts[1])
                    self.param_widgets["origin_z"].delete(0, tk.END)
                    self.param_widgets["origin_z"].insert(0, origin_parts[2])

                # Extract delay
                if len(parts) >= 4:
                    self.param_widgets["delay"].delete(0, tk.END)
                    self.param_widgets["delay"].insert(0, parts[3])

                # Extract forward vector if present (remaining parts after delay)
                if len(parts) > 4:
                    fwd_parts = [p.strip() for p in " ".join(parts[4:]).split(",")]
                    if len(fwd_parts) >= 3:
                        self.param_widgets["fwd_var"].set(True)
                        fwd_frame = self.param_widgets.get("fwd_frame")
                        if fwd_frame:
                            fwd_frame.pack(fill="x", pady=(4, 12))
                        self.param_widgets["forward_x"].delete(0, tk.END)
                        self.param_widgets["forward_x"].insert(0, fwd_parts[0].lstrip("("))
                        self.param_widgets["forward_y"].delete(0, tk.END)
                        self.param_widgets["forward_y"].insert(0, fwd_parts[1])
                        self.param_widgets["forward_z"].delete(0, tk.END)
                        self.param_widgets["forward_z"].insert(0, fwd_parts[2].rstrip(")"))

            elif func_type == "gunfireloopfx":
                # Format: (x, y, z), shots_min, shots_max, delay_min, delay_max, set_min, set_max
                parts = [p.strip() for p in params.split(",")]
                if len(parts) >= 9:
                    # Origin
                    origin_parts = [parts[0].lstrip("("), parts[1], parts[2].rstrip(")")]
                    self.param_widgets["origin_x"].delete(0, tk.END)
                    self.param_widgets["origin_x"].insert(0, origin_parts[0])
                    self.param_widgets["origin_y"].delete(0, tk.END)
                    self.param_widgets["origin_y"].insert(0, origin_parts[1])
                    self.param_widgets["origin_z"].delete(0, tk.END)
                    self.param_widgets["origin_z"].insert(0, origin_parts[2])

                    # Gunfire params
                    for i in range(3):
                        min_key = f"gf_min_{i}"
                        max_key = f"gf_max_{i}"
                        if min_key in self.param_widgets:
                            self.param_widgets[min_key].delete(0, tk.END)
                            self.param_widgets[min_key].insert(0, parts[3 + i * 2])
                        if max_key in self.param_widgets:
                            self.param_widgets[max_key].delete(0, tk.END)
                            self.param_widgets[max_key].insert(0, parts[4 + i * 2])

            elif func_type == "GrenadeExplosionfx":
                # Only origin required
                parts = [p.strip() for p in params.split(",")]
                if len(parts) >= 3:
                    origin_parts = [parts[0].lstrip("("), parts[1], parts[2].rstrip(")")]
                    self.param_widgets["origin_x"].delete(0, tk.END)
                    self.param_widgets["origin_x"].insert(0, origin_parts[0])
                    self.param_widgets["origin_y"].delete(0, tk.END)
                    self.param_widgets["origin_y"].insert(0, origin_parts[1])
                    self.param_widgets["origin_z"].delete(0, tk.END)
                    self.param_widgets["origin_z"].insert(0, origin_parts[2])

        except Exception as e:
            messagebox.showwarning("Parse Error", f"Could not fully parse parameters:\n{e}")

    def add_precache_effect(self):
        name = self.effect_name_entry.get().strip()
        fx_path = self.fx_path_entry.get().strip()

        if not name or not fx_path:
            messagebox.showwarning("Missing Input", "Both effect name and FX file path are required.")
            return

        self.precache_entries.append((name, fx_path))
        self.precache_list.insert(tk.END, f"{name} → {fx_path}")

        self.effect_choice["values"] = [n for n, _ in self.precache_entries]
        self.update_preview()

        self.effect_name_entry.delete(0, tk.END)
        self.fx_path_entry.delete(0, tk.END)
        self.effect_name_entry.focus()

    def remove_precache(self):
        sel = self.precache_list.curselection()
        if not sel:
            return

        idx = sel[0]
        del self.precache_entries[idx]
        self.precache_list.delete(idx)

        self.effect_choice["values"] = [n for n, _ in self.precache_entries]
        self.update_preview()

    def add_scr_sound(self):
        key = self.scr_key_entry.get().strip()
        value = self.scr_value_entry.get().strip()

        if not key or not value:
            messagebox.showwarning("Missing Input", "Both key and value are required for scr_sound.")
            return

        self.scr_sound_entries.append((key, value))
        self.scr_sound_list.insert(tk.END, f"{key} → {value}")

        self.update_preview()

        self.scr_key_entry.delete(0, tk.END)
        self.scr_value_entry.delete(0, tk.END)
        self.scr_key_entry.focus()

    def remove_scr_sound(self):
        sel = self.scr_sound_list.curselection()
        if not sel:
            return

        idx = sel[0]
        del self.scr_sound_entries[idx]
        self.scr_sound_list.delete(idx)

        self.update_preview()

    def update_preview(self):
        mapname = self.app.map_name.get().strip() or "mapname"

        lines = [
            f"// FX script for mp_{mapname}",
            "// Generated by CoD2 Map Script Generator",
            "",
            "main()",
            "{",
            "    level thread precacheFX();",
            "    level thread ambientFX();",
            "}",
            "",
            "precacheFX()",
            "{"
        ]

        for name, path in self.precache_entries:
            lines.append(f"    level._effect[\"{name}\"] = loadfx(\"{path}\");")

        for key, value in self.scr_sound_entries:
            lines.append(f'    level.scr_sound["{key}"] = "{value}";')

        lines.append("}")
        lines.append("")
        lines.append("ambientFX()")
        lines.append("{")

        for display_effect, func, params in self.usage_calls:
            if func == "soundfx":
                lines.append(f"    maps\\mp\\_fx::soundfx({params});")
            else:
                lines.append(f"    maps\\mp\\_fx::{func}(\"{display_effect}\", {params});")

        lines.append("}")

        content = "\n".join(lines)

        self.preview_text.config(state="normal")
        self.preview_text.delete("1.0", tk.END)
        self.preview_text.insert("1.0", content)
        self.preview_text.config(state="disabled")

    # ------------------------------------------------------------------
    # File handling
    # ------------------------------------------------------------------
    def save_files(self, cod2_path: Path, mapname: str):
        path = cod2_path / "main" / "maps" / "mp" / f"{mapname}_fx.gsc"
        content = self.preview_text.get("1.0", tk.END).strip()
        if not content:
            content = f"""// FX script for mp_{mapname}
// Generated by CoD2 Map Script Generator

main()
{{
    level thread precacheFX();
    level thread ambientFX();
}}

precacheFX()
{{
}}

ambientFX()
{{
}}
"""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content + "\n", encoding="utf-8")
        print(f"[DEBUG FX] Saved to {path}")

    def update_missing_status(self):
        mapname = self.app.map_name.get().strip()
        if not mapname:
            self.missing_label.config(text="")
            self.create_btn.state(["disabled"])
            return

        status = self.app.check_missing_files(Path(self.app.cod2_path.get()), mapname)
        fx_key = "fx_gsc"
        exists = status.get(fx_key, {}).get("exists", False)

        if exists:
            self.missing_label.config(text="FX GSC file exists ✓", foreground="green")
            self.create_btn.state(["disabled"])
            self.load_from_file(Path(self.app.cod2_path.get()), mapname)
        else:
            self.missing_label.config(text=f"File missing: {mapname}_fx.gsc", foreground="red")
            self.create_btn.config(text=f"Create {mapname}_fx.gsc")
            self.create_btn.state(["!disabled"])

    def load_from_file(self, cod2_path: Path, mapname: str):
        fx_path = cod2_path / "main" / "maps" / "mp" / f"{mapname}_fx.gsc"
        if not fx_path.exists():
            fx_path = cod2_path / "maps" / "mp" / f"{mapname}_fx.gsc"

        if fx_path.exists():
            try:
                content = fx_path.read_text(encoding="utf-8")

                # Clear all data
                self.precache_entries.clear()
                self.scr_sound_entries.clear()
                self.usage_calls.clear()
                self.precache_list.delete(0, tk.END)
                self.scr_sound_list.delete(0, tk.END)
                for item in self.usage_table.get_children():
                    self.usage_table.delete(item)

                # Parse precacheFX()
                precache_pattern = r'level\._effect\s*\[\s*"([^"]+)"\s*\]\s*=\s*loadfx\s*\(\s*"([^"]+)"\s*\)\s*;?'
                for match in re.finditer(precache_pattern, content, re.IGNORECASE):
                    name, path = match.groups()
                    name = name.strip()
                    path = path.strip()
                    self.precache_entries.append((name, path))
                    self.precache_list.insert(tk.END, f"{name} → {path}")

                self.effect_choice["values"] = [n for n, _ in self.precache_entries]

                # Parse scr_sound
                scr_sound_pattern = r'level\.scr_sound\s*\[\s*"([^"]+)"\s*\]\s*=\s*"([^"]+)"\s*;?'
                for match in re.finditer(scr_sound_pattern, content, re.IGNORECASE):
                    key, value = match.groups()
                    key = key.strip()
                    value = value.strip()
                    self.scr_sound_entries.append((key, value))
                    self.scr_sound_list.insert(tk.END, f"{key} → {value}")

                # Parse usage calls
                lines = content.splitlines()
                in_ambient = False
                for line in lines:
                    stripped = line.strip()
                    if not stripped or stripped.startswith('//'):
                        continue

                    if 'ambientFX()' in stripped:
                        in_ambient = True
                        continue

                    if in_ambient:
                        # Match any _fx function
                        match = re.match(r'^\s*maps\s*\\\s*mp\s*\\\s*_fx\s*::\s*(\w+)\s*\(\s*(?:"([^"]+)"\s*,\s*)?(.*)\);?', stripped, re.IGNORECASE)
                        if match:
                            func_type = match.group(1).strip()
                            effect_or_alias = match.group(2).strip() if match.group(2) else "(sound alias)"
                            remaining_params = match.group(3) if match.group(3) else ""

                            # For soundfx, the first param is the alias in quotes, no effect name
                            if func_type.lower() == "soundfx":
                                # Re-parse specifically for soundfx
                                sound_match = re.match(r'^\s*maps\s*\\\s*mp\s*\\\s*_fx\s*::\s*soundfx\s*\(\s*"([^"]+)"\s*,\s*(.*)\);?', stripped, re.IGNORECASE)
                                if sound_match:
                                    alias = sound_match.group(1)
                                    params = f'"{alias}", {sound_match.group(2)}'
                                    self.usage_calls.append(("(sound alias)", "soundfx", params))
                                    self.usage_table.insert("", "end", values=("(sound alias)", "soundfx", params))
                                    continue

                            # For visual effects
                            params = remaining_params.strip()
                            if params.endswith(','):
                                params = params[:-1].strip()
                            self.usage_calls.append((effect_or_alias, func_type, params))
                            self.usage_table.insert("", "end", values=(effect_or_alias, func_type, params))

                self.preview_text.config(state="normal")
                self.preview_text.delete("1.0", tk.END)
                self.preview_text.insert("1.0", content)
                self.preview_text.config(state="disabled")

                print(f"[DEBUG FX] Loaded and parsed from {fx_path}")
                self.update_preview()

            except Exception as e:
                print(f"[DEBUG FX] Load/parse error: {e}")
                messagebox.showwarning("FX Load Warning", f"File loaded but parsing incomplete:\n{e}")

    def create_file_if_missing(self):
        mapname = self.app.map_name.get().strip()
        if not mapname:
            return

        path = Path(self.app.cod2_path.get()) / "main" / "maps" / "mp" / f"{mapname}_fx.gsc"
        if path.exists():
            return

        content = f"""// FX script for mp_{mapname}
// Generated by CoD2 Map Script Generator

main()
{{
    level thread precacheFX();
    level thread ambientFX();
}}

precacheFX()
{{
}}

ambientFX()
{{
}}
"""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        messagebox.showinfo("Created", f"Created basic FX GSC file:\n{path}")
        self.update_missing_status()