# ui/tab_main_gsc.py
import tkinter as tk
from tkinter import ttk, messagebox, colorchooser
from pathlib import Path

from config import MINIMAL_MAIN_GSC

class Tooltip:
    """Simple tooltip widget for hover help"""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        self.widget.bind("<Enter>", self.show_tip)
        self.widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event=None):
        if self.tipwindow or not self.text:
            return
        x = self.widget.winfo_rootx() + 10
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, background="#ffffe0", relief="solid", borderwidth=1,
                        font=("Segoe UI", 8), wraplength=300, justify="left")
        label.pack()

    def hide_tip(self, event=None):
        if self.tipwindow:
            self.tipwindow.destroy()
            self.tipwindow = None

class MainGSCTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.faction_presets = self.get_faction_presets()
        self.create_widgets()
        self.update_missing_status()

    def get_faction_presets(self):
        # No longer used as dropdown - now using individual controls
        return []

    def get_soldier_types_for_allies(self, allies):
        """Return available soldier types based on allies faction"""
        if allies == "american":
            return ["normandy"]
        elif allies == "british":
            return ["normandy", "africa"]
        elif allies == "russian":
            return ["coats", "padded"]
        return []

    def on_allies_changed(self, event=None):
        """Update allies soldier type options when allies faction changes"""
        allies = self.allies_combo.get()
        soldier_types = self.get_soldier_types_for_allies(allies)
        self.allies_soldiertype_combo["values"] = soldier_types
        if soldier_types:
            self.allies_soldiertype_combo.set(soldier_types[0])
        else:
            self.allies_soldiertype_combo.set("")


    def create_widgets(self):
        # Missing status + create button (top)
        self.missing_label = ttk.Label(self, text="", foreground="red", font=("Segoe UI", 10, "bold"))
        self.missing_label.pack(anchor="w", pady=6)

        self.create_btn = ttk.Button(self, text="Create mp_XXXX.gsc", command=self.create_file_if_missing)
        self.create_btn.pack(anchor="w", pady=6)
        self.create_btn.state(["disabled"])

        # ── FIXED SCROLLABLE CONTAINER WITH FULL-HEIGHT/WIDTH SCROLLBARS ──
        scroll_container = ttk.Frame(self)
        scroll_container.pack(fill="both", expand=True, pady=10)

        # Enable resizing for the canvas area
        scroll_container.grid_rowconfigure(0, weight=1)
        scroll_container.grid_columnconfigure(0, weight=1)

        canvas = tk.Canvas(scroll_container, background="#f0f0f0")  # Dark background to match theme
        v_scroll = tk.Scrollbar(scroll_container, orient="vertical", command=canvas.yview,
                                width=24, bg="#666666", troughcolor="#1e1e1e",
                                activebackground="#888888")
        h_scroll = tk.Scrollbar(scroll_container, orient="horizontal", command=canvas.xview,
                                width=24, bg="#666666", troughcolor="#1e1e1e",
                                activebackground="#888888")

        # Grid layout — ensures full height/width spanning and proper corner handling
        canvas.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")

        canvas.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        scrollable_frame = ttk.Frame(canvas)
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

        # Mouse wheel bindings (directly on canvas for reliability)
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def _on_shift_mousewheel(event):
            canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind("<MouseWheel>", _on_mousewheel)
        canvas.bind("<Shift-MouseWheel>", _on_shift_mousewheel)

        # Linux support
        canvas.bind("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))
        canvas.bind("<Button-5>", lambda e: canvas.yview_scroll(1, "units"))
        canvas.bind("<Shift-Button-4>", lambda e: canvas.xview_scroll(-1, "units"))
        canvas.bind("<Shift-Button-5>", lambda e: canvas.xview_scroll(1, "units"))

        # ── CONTENT LAYOUT (unchanged — now inside scrollable_frame) ──
        columns_frame = ttk.Frame(scrollable_frame)
        columns_frame.pack(fill="both", expand=True, padx=15, pady=10)

        # Left column
        left_frame = ttk.Frame(columns_frame, width=550)
        left_frame.pack(side="left", fill="y", expand=False, padx=(0, 20))
        left_frame.pack_propagate(False)

        # Right column
        right_frame = ttk.Frame(columns_frame)
        right_frame.pack(side="right", fill="both", expand=True)

        # ── LEFT COLUMN CONTENT ───────────────────────────────────────────────────────
        amb_frame = ttk.LabelFrame(left_frame, text="Ambient Sound", padding=10)
        amb_frame.pack(fill="x", pady=(0, 12))
        self.ambient_enabled = tk.BooleanVar(value=False)
        ambient_check = ttk.Checkbutton(amb_frame, text="Enable ambientPlay()", variable=self.ambient_enabled)
        ambient_check.pack(anchor="w")
        Tooltip(ambient_check, "Plays ambient background sound for the map")

        self.ambient_combo = ttk.Combobox(amb_frame, width=40, values=[
            "ambient_mp_carentan", "ambient_mp_dawnville", "ambient_mp_toujane",
            "ambient_mp_burgundy", "ambient_mp_railyard", "ambient_mp_harbor",
            "ambient_mp_farmhouse", "ambient_mp_matmata", "ambient_mp_brecourt"
        ])
        self.ambient_combo.pack(anchor="w", pady=6)
        Tooltip(self.ambient_combo, "Select the ambient sound alias to play")

        faction_frame = ttk.LabelFrame(left_frame, text="Factions & Soldier Types", padding=10)
        faction_frame.pack(fill="x", pady=12)

        # Allies Faction
        allies_frame = ttk.Frame(faction_frame)
        allies_frame.pack(fill="x", pady=4)
        allies_label = ttk.Label(allies_frame, text="Allies:", width=15)
        allies_label.pack(side="left")
        Tooltip(allies_label, "Choose the allied nation for this map")
        self.allies_combo = ttk.Combobox(allies_frame, values=["british", "american", "russian"],
                                        state="readonly", width=20)
        self.allies_combo.pack(side="left", padx=4)
        self.allies_combo.set("british")
        self.allies_combo.bind("<<ComboboxSelected>>", self.on_allies_changed)
        Tooltip(self.allies_combo, "Allies faction (affects available soldier types)")

        # Axis (always German, no choice)
        axis_frame = ttk.Frame(faction_frame)
        axis_frame.pack(fill="x", pady=4)
        axis_label = ttk.Label(axis_frame, text="Axis:", width=15)
        axis_label.pack(side="left")
        Tooltip(axis_label, "Axis faction is always German")
        ttk.Label(axis_frame, text="german (fixed)", foreground="gray").pack(side="left", padx=4)
        self.axis_var = tk.StringVar(value="german")

        # Defenders
        defenders_frame = ttk.Frame(faction_frame)
        defenders_frame.pack(fill="x", pady=4)
        defenders_label = ttk.Label(defenders_frame, text="Defenders:", width=15)
        defenders_label.pack(side="left")
        Tooltip(defenders_label, "Which side defends the objectives")
        self.defenders_combo = ttk.Combobox(defenders_frame, values=["allies", "axis"],
                                            state="readonly", width=20)
        self.defenders_combo.pack(side="left", padx=4)
        self.defenders_combo.set("axis")
        Tooltip(self.defenders_combo, "Defending team for this map")

        # Attackers
        attackers_frame = ttk.Frame(faction_frame)
        attackers_frame.pack(fill="x", pady=4)
        attackers_label = ttk.Label(attackers_frame, text="Attackers:", width=15)
        attackers_label.pack(side="left")
        Tooltip(attackers_label, "Which side attacks the objectives")
        self.attackers_combo = ttk.Combobox(attackers_frame, values=["allies", "axis"],
                                            state="readonly", width=20)
        self.attackers_combo.pack(side="left", padx=4)
        self.attackers_combo.set("allies")
        Tooltip(self.attackers_combo, "Attacking team for this map")

        # German Soldier Type
        german_st_frame = ttk.Frame(faction_frame)
        german_st_frame.pack(fill="x", pady=4)
        german_label = ttk.Label(german_st_frame, text="German Troops:", width=15)
        german_label.pack(side="left")
        Tooltip(german_label, "Soldier appearance/uniform for German forces")
        self.german_soldiertype_combo = ttk.Combobox(german_st_frame,
                                                    values=["winterlight", "winterdark", "normandy", "africa"],
                                                    state="readonly", width=20)
        self.german_soldiertype_combo.pack(side="left", padx=4)
        self.german_soldiertype_combo.set("normandy")
        Tooltip(self.german_soldiertype_combo, "German soldier uniform variant")

        # Allies Soldier Type (dynamically updated based on allies choice)
        allies_st_frame = ttk.Frame(faction_frame)
        allies_st_frame.pack(fill="x", pady=4)
        allies_st_label = ttk.Label(allies_st_frame, text="Allied Troops:", width=15)
        allies_st_label.pack(side="left")
        Tooltip(allies_st_label, "Soldier appearance/uniform for allied forces")
        self.allies_soldiertype_combo = ttk.Combobox(allies_st_frame, state="readonly", width=20)
        self.allies_soldiertype_combo.pack(side="left", padx=4)
        Tooltip(self.allies_soldiertype_combo, "Soldier variant based on allied faction selection")
        self.on_allies_changed()  # Initialize with default allies selection

        # ── SCRIPTS SECTION ────────────────────────────────────────────────────────────
        script_title = ttk.Label(left_frame, text="Scripts, required scripts are added automatically", font=("Segoe UI", 10, "bold"))
        script_title.pack(anchor="w", pady=(12, 4))
        Tooltip(script_title, "Add custom script calls to execute in main()")
        
        ttk.Label(left_frame, text="Enter path from maps/mp/ and function name.\n"
                                    "Will build: maps\\mp\\PATH::FUNCTION();\n"
                                    "Examples:\n  Path: _myscript     Function: main\n  Path: myfolder/_script     Function: init",
                foreground="gray", font=("Segoe UI", 8), justify="left").pack(anchor="w", pady=(0, 6))

        script_input_frame = ttk.Frame(left_frame)
        script_input_frame.pack(fill="x", pady=4)

        path_label = ttk.Label(script_input_frame, text="Path:")
        path_label.pack(side="left", padx=(0, 4))
        Tooltip(path_label, "Script path relative to maps/mp/")
        self.script_path_entry = ttk.Entry(script_input_frame, width=30)
        self.script_path_entry.pack(side="left", fill="x", expand=True, padx=4)
        Tooltip(self.script_path_entry, "e.g., _myscript or myfolder/_script")

        ttk.Label(script_input_frame, text="::").pack(side="left", padx=2)

        func_label = ttk.Label(script_input_frame, text="Function:")
        func_label.pack(side="left", padx=(8, 4))
        Tooltip(func_label, "Function name to call")
        self.script_func_entry = ttk.Entry(script_input_frame, width=30)
        self.script_func_entry.pack(side="left", fill="x", expand=True, padx=4)
        Tooltip(self.script_func_entry, "e.g., main or init")

        add_call_btn = ttk.Button(script_input_frame, text="Add Call", width=10,
                command=self.add_script_call)
        add_call_btn.pack(side="left", padx=(12, 0))
        Tooltip(add_call_btn, "Add this script call to the list")

        self.threads_text = tk.Text(left_frame, height=5, width=60, font=("Consolas", 10))
        self.threads_text.pack(fill="both", expand=True, pady=6)
        self.threads_text.insert("1.0", "# Example calls (will be added in main()):\n"
                                    "# maps\\mp\\_myscript::main();\n"
                                    "# maps\\mp\\_load::main();\n"
                                    "# maps\\mp\\myfolder/_script::init();")

        # ── FOG SETTINGS (moved to left, below scripts) ─────────────────────────────────
        fog_frame = ttk.LabelFrame(left_frame, text="Fog Settings", padding=10)
        fog_frame.pack(fill="x", pady=12)

        ttk.Label(fog_frame, text="Hint: setExpFog is exponential fog, setcullfog is linear fog",
                foreground="gray", font=("Segoe UI", 8), wraplength=400, justify="left").pack(anchor="w", pady=(0, 8))

        # Exp Fog settings
        self.expfog_enabled = tk.BooleanVar(value=False)
        expfog_check = ttk.Checkbutton(fog_frame, text="Enable setExpFog", variable=self.expfog_enabled,
                    command=self.toggle_expfog_fields)
        expfog_check.pack(anchor="w", pady=4)
        Tooltip(expfog_check, "Exponential fog: fog density increases exponentially with distance")

        # Exp Fog Start Distance
        expfog_start_frame = ttk.Frame(fog_frame)
        expfog_start_frame.pack(fill="x", pady=4, padx=(20, 0))
        start_label = ttk.Label(expfog_start_frame, text="Start Distance:", width=18)
        start_label.pack(side="left")
        Tooltip(start_label, "Distance (in world units) where fog begins")
        self.expfog_start_entry = ttk.Entry(expfog_start_frame, width=30, state="disabled")
        self.expfog_start_entry.insert(0, "0.0001144")
        self.expfog_start_entry.pack(side="left", padx=4)

        # Exp Fog Halfway Distance
        expfog_halfway_frame = ttk.Frame(fog_frame)
        expfog_halfway_frame.pack(fill="x", pady=4, padx=(20, 0))
        halfway_label = ttk.Label(expfog_halfway_frame, text="Halfway Distance:", width=18)
        halfway_label.pack(side="left")
        Tooltip(halfway_label, "Distance beyond startDist where the scene is 50% fogged")
        self.expfog_halfway_entry = ttk.Entry(expfog_halfway_frame, width=30, state="disabled")
        self.expfog_halfway_entry.insert(0, "0.51")
        self.expfog_halfway_entry.pack(side="left", padx=4)

        # Exp Fog Color with Color Picker
        expfog_color_frame = ttk.Frame(fog_frame)
        expfog_color_frame.pack(fill="x", pady=4, padx=(20, 0))
        color_label = ttk.Label(expfog_color_frame, text="Color (R, G, B):", width=18)
        color_label.pack(side="left")
        Tooltip(color_label, "Fog color in RGB format (0.0 to 1.0 per channel)")
        self.expfog_color_entry = ttk.Entry(expfog_color_frame, width=30, state="disabled")
        self.expfog_color_entry.insert(0, "0.51, 0.45, 0.28")
        self.expfog_color_entry.pack(side="left", padx=4)
        ttk.Button(expfog_color_frame, text="Pick", width=6,
                command=lambda: self.pick_color(self.expfog_color_entry)).pack(side="left", padx=2)

        # Exp Fog Transition Time
        expfog_time_frame = ttk.Frame(fog_frame)
        expfog_time_frame.pack(fill="x", pady=4, padx=(20, 0))
        time_label = ttk.Label(expfog_time_frame, text="Transition Time:", width=18)
        time_label.pack(side="left")
        Tooltip(time_label, "Duration in seconds for fog transition")
        self.expfog_time_entry = ttk.Entry(expfog_time_frame, width=30, state="disabled")
        self.expfog_time_entry.insert(0, "0")
        self.expfog_time_entry.pack(side="left", padx=4)

        # Cull Fog settings
        self.cullfog_enabled = tk.BooleanVar(value=False)
        cullfog_check = ttk.Checkbutton(fog_frame, text="Enable setcullfog", variable=self.cullfog_enabled,
                    command=self.toggle_cullfog_fields)
        cullfog_check.pack(anchor="w", pady=4)
        Tooltip(cullfog_check, "Linear fog: fog increases linearly from near to far distance")

        # Cull Fog Near Distance
        cullfog_near_frame = ttk.Frame(fog_frame)
        cullfog_near_frame.pack(fill="x", pady=4, padx=(20, 0))
        near_label = ttk.Label(cullfog_near_frame, text="Near Distance:", width=18)
        near_label.pack(side="left")
        Tooltip(near_label, "Distance from camera where fog starts")
        self.cullfog_near_entry = ttk.Entry(cullfog_near_frame, width=30, state="disabled")
        self.cullfog_near_entry.insert(0, "0")
        self.cullfog_near_entry.pack(side="left", padx=4)

        # Cull Fog Far Distance
        cullfog_far_frame = ttk.Frame(fog_frame)
        cullfog_far_frame.pack(fill="x", pady=4, padx=(20, 0))
        far_label = ttk.Label(cullfog_far_frame, text="Far Distance:", width=18)
        far_label.pack(side="left")
        Tooltip(far_label, "Distance from camera where full occlusion occurs")
        self.cullfog_far_entry = ttk.Entry(cullfog_far_frame, width=30, state="disabled")
        self.cullfog_far_entry.insert(0, "16500")
        self.cullfog_far_entry.pack(side="left", padx=4)

        # Cull Fog Color with Color Picker
        cullfog_color_frame = ttk.Frame(fog_frame)
        cullfog_color_frame.pack(fill="x", pady=4, padx=(20, 0))
        cull_color_label = ttk.Label(cullfog_color_frame, text="Color (R, G, B):", width=18)
        cull_color_label.pack(side="left")
        Tooltip(cull_color_label, "Fog color in RGB format (0.0 to 1.0 per channel)")
        self.cullfog_color_entry = ttk.Entry(cullfog_color_frame, width=30, state="disabled")
        self.cullfog_color_entry.insert(0, "0.7, 0.85, 1.0")
        self.cullfog_color_entry.pack(side="left", padx=4)
        ttk.Button(cullfog_color_frame, text="Pick", width=6,
                command=lambda: self.pick_color(self.cullfog_color_entry)).pack(side="left", padx=2)

        # Cull Fog Transition Time
        cullfog_time_frame = ttk.Frame(fog_frame)
        cullfog_time_frame.pack(fill="x", pady=4, padx=(20, 0))
        cull_time_label = ttk.Label(cullfog_time_frame, text="Transition Time:", width=18)
        cull_time_label.pack(side="left")
        Tooltip(cull_time_label, "Duration in seconds for fog transition")
        self.cullfog_time_entry = ttk.Entry(cullfog_time_frame, width=30, state="disabled")
        self.cullfog_time_entry.insert(0, "0")
        self.cullfog_time_entry.pack(side="left", padx=4)

        # ── RIGHT COLUMN CONTENT ──────────────────────────────────────────────────────
        hq_frame = ttk.LabelFrame(right_frame, text="HQ Radio Locations (level.radio[])", padding=10)
        hq_frame.pack(fill="x", pady=(0, 12))
        Tooltip(hq_frame, "Define radio spawn points for HQ gametype")

        hq_input_frame = ttk.Frame(hq_frame)
        hq_input_frame.pack(fill="x", pady=(0, 8))

        pos_label = ttk.Label(hq_input_frame, text="Position:")
        pos_label.pack(side="left", padx=(0, 4))
        Tooltip(pos_label, "X, Y, Z coordinates for radio spawn location")
        self.hq_pos_entry = ttk.Entry(hq_input_frame, width=32)
        self.hq_pos_entry.pack(side="left", padx=4)
        Tooltip(self.hq_pos_entry, "e.g., 100 200 50")

        angles_label = ttk.Label(hq_input_frame, text="Angles:")
        angles_label.pack(side="left", padx=(12, 4))
        Tooltip(angles_label, "Pitch, Yaw, Roll rotation angles")
        self.hq_angles_entry = ttk.Entry(hq_input_frame, width=24)
        self.hq_angles_entry.pack(side="left", padx=4)
        Tooltip(self.hq_angles_entry, "e.g., 0 90 0")

        add_hq_btn = ttk.Button(hq_input_frame, text="Add", width=8,
                command=self.add_hq_location_inline)
        add_hq_btn.pack(side="left", padx=(12, 0))
        Tooltip(add_hq_btn, "Add this position/angle pair to the radio list")

        ttk.Label(hq_frame, text="Format: x, y, z    |    Angles: pitch, yaw, roll",
                foreground="gray", font=("Segoe UI", 8)).pack(anchor="w", pady=(0, 4))

        self.hq_list = ttk.Treeview(hq_frame, columns=("location", "angles"), show="headings", height=8)
        self.hq_list.heading("location", text="Position (x, y, z)")
        self.hq_list.heading("angles", text="Angles (pitch, yaw, roll)")
        self.hq_list.column("location", width=280)
        self.hq_list.column("angles", width=220)
        self.hq_list.pack(fill="x", pady=4)

        remove_hq_btn = ttk.Button(hq_frame, text="Remove selected", command=self.remove_hq_location)
        remove_hq_btn.pack(anchor="w", pady=4)
        Tooltip(remove_hq_btn, "Remove selected radio location from list")

        kt_frame = ttk.LabelFrame(right_frame, text="Kill Triggers (level.killtriggers[])", padding=10)
        kt_frame.pack(fill="x", pady=12)
        Tooltip(kt_frame, "Define kill trigger volumes that eliminate players touching them")

        kt_input_frame = ttk.Frame(kt_frame)
        kt_input_frame.pack(fill="x", pady=(0, 8))

        origin_label = ttk.Label(kt_input_frame, text="Origin:")
        origin_label.pack(side="left", padx=(0, 4))
        Tooltip(origin_label, "X, Y, Z center point of kill trigger volume")
        self.kt_origin_entry = ttk.Entry(kt_input_frame, width=32)
        self.kt_origin_entry.pack(side="left", padx=4)
        Tooltip(self.kt_origin_entry, "e.g., 100 200 50")

        radius_label = ttk.Label(kt_input_frame, text="Radius:")
        radius_label.pack(side="left", padx=(12, 4))
        Tooltip(radius_label, "Horizontal radius of cylindrical kill trigger")
        self.kt_radius_entry = ttk.Entry(kt_input_frame, width=12)
        self.kt_radius_entry.pack(side="left", padx=4)
        Tooltip(self.kt_radius_entry, "e.g., 100")

        height_label = ttk.Label(kt_input_frame, text="Height:")
        height_label.pack(side="left", padx=(8, 4))
        Tooltip(height_label, "Vertical height of kill trigger volume")
        self.kt_height_entry = ttk.Entry(kt_input_frame, width=12)
        self.kt_height_entry.pack(side="left", padx=4)
        Tooltip(self.kt_height_entry, "e.g., 100")

        add_kt_btn = ttk.Button(kt_input_frame, text="Add", width=8,
                command=self.add_killtrigger_inline)
        add_kt_btn.pack(side="left", padx=(12, 0))
        Tooltip(add_kt_btn, "Add this kill trigger configuration to the list")

        ttk.Label(kt_frame, text="Format: x, y, z    |    Radius & Height: numbers",
                foreground="gray", font=("Segoe UI", 8)).pack(anchor="w", pady=(0, 4))

        self.killtrigger_list = ttk.Treeview(kt_frame, columns=("origin", "radius", "height"), show="headings", height=8)
        self.killtrigger_list.heading("origin", text="Origin (x, y, z)")
        self.killtrigger_list.heading("radius", text="Radius")
        self.killtrigger_list.heading("height", text="Height")
        self.killtrigger_list.column("origin", width=280)
        self.killtrigger_list.column("radius", width=100)
        self.killtrigger_list.column("height", width=100)
        self.killtrigger_list.pack(fill="x", pady=4)

        kt_btn_frame = ttk.Frame(kt_frame)
        kt_btn_frame.pack(fill="x", pady=6)

        self.kt_enabled = tk.BooleanVar(value=False)
        kt_check = ttk.Checkbutton(kt_btn_frame, text="Enable killtriggers (adds thread call)",
                        variable=self.kt_enabled)
        kt_check.pack(side="left", padx=4)
        Tooltip(kt_check, "When checked, enables kill triggers and adds thread call")
        
        remove_kt_btn = ttk.Button(kt_btn_frame, text="Remove selected", command=self.remove_killtrigger)
        remove_kt_btn.pack(side="left", padx=8)
        Tooltip(remove_kt_btn, "Remove selected kill trigger from list")

        # ── GLOW/BLOOM SECTION (with sliders) ─────────────────────────────────────────
        glow_frame = ttk.LabelFrame(right_frame, text="Glow/Bloom Settings", padding=10)
        glow_frame.pack(fill="x", pady=12)

        ttk.Label(glow_frame, text="Hint: r_glowbloomintensity controls bloom strength, r_glowskybleedintensity controls sky bleed",
                foreground="gray", font=("Segoe UI", 8), wraplength=500, justify="left").pack(anchor="w", pady=(0, 8))

        # r_glowbloomintensity0 (0.2 - 1.0)
        self.glow_bloom0_enabled = tk.BooleanVar(value=False)
        glow_bloom0_check = ttk.Checkbutton(glow_frame, text="Enable r_glowbloomintensity0 (0.2 - 1.0)", 
                    variable=self.glow_bloom0_enabled, command=self.toggle_glow_bloom0_field)
        glow_bloom0_check.pack(anchor="w", pady=4)
        Tooltip(glow_bloom0_check, "Controls primary bloom/glow intensity (0.2-1.0)")

        glow_frame1 = ttk.Frame(glow_frame)
        glow_frame1.pack(fill="x", pady=4, padx=(20, 0))
        self.glow_bloom0_slider = ttk.Scale(glow_frame1, from_=0.2, to=1.0, orient="horizontal", 
                                           command=self.update_glow_bloom0_display, state="disabled")
        self.glow_bloom0_slider.set(0.25)
        self.glow_bloom0_slider.pack(side="left", fill="x", expand=True, padx=4)
        Tooltip(self.glow_bloom0_slider, "Slide to adjust bloom intensity (0.2 to 1.0)")
        self.glow_bloom0_value = ttk.Label(glow_frame1, text="0.25", width=8)
        self.glow_bloom0_value.pack(side="left", padx=4)

        # r_glowbloomintensity1 (0.1 - 0.7)
        self.glow_bloom1_enabled = tk.BooleanVar(value=False)
        glow_bloom1_check = ttk.Checkbutton(glow_frame, text="Enable r_glowbloomintensity1 (0.1 - 0.7)", 
                    variable=self.glow_bloom1_enabled, command=self.toggle_glow_bloom1_field)
        glow_bloom1_check.pack(anchor="w", pady=4)
        Tooltip(glow_bloom1_check, "Controls secondary bloom intensity (0.1-0.7)")

        glow_frame2 = ttk.Frame(glow_frame)
        glow_frame2.pack(fill="x", pady=4, padx=(20, 0))
        self.glow_bloom1_slider = ttk.Scale(glow_frame2, from_=0.1, to=0.7, orient="horizontal",
                                           command=self.update_glow_bloom1_display, state="disabled")
        self.glow_bloom1_slider.set(0.25)
        self.glow_bloom1_slider.pack(side="left", fill="x", expand=True, padx=4)
        Tooltip(self.glow_bloom1_slider, "Slide to adjust secondary bloom (0.1 to 0.7)")
        self.glow_bloom1_value = ttk.Label(glow_frame2, text="0.25", width=8)
        self.glow_bloom1_value.pack(side="left", padx=4)

        # r_glowskybleedintensity0 (0.1 - 0.5)
        self.glow_skybleed0_enabled = tk.BooleanVar(value=False)
        glow_skybleed_check = ttk.Checkbutton(glow_frame, text="Enable r_glowskybleedintensity0 (0.1 - 0.5)", 
                    variable=self.glow_skybleed0_enabled, command=self.toggle_glow_skybleed0_field)
        glow_skybleed_check.pack(anchor="w", pady=4)
        Tooltip(glow_skybleed_check, "Controls sky color bleed into scene (0.1-0.5)")

        glow_frame3 = ttk.Frame(glow_frame)
        glow_frame3.pack(fill="x", pady=4, padx=(20, 0))
        self.glow_skybleed0_slider = ttk.Scale(glow_frame3, from_=0.1, to=0.5, orient="horizontal",
                                              command=self.update_glow_skybleed0_display, state="disabled")
        self.glow_skybleed0_slider.set(0.3)
        self.glow_skybleed0_slider.pack(side="left", fill="x", expand=True, padx=4)
        Tooltip(self.glow_skybleed0_slider, "Slide to adjust sky bleed (0.1 to 0.5)")
        self.glow_skybleed0_value = ttk.Label(glow_frame3, text="0.30", width=8)
        self.glow_skybleed0_value.pack(side="left", padx=4)

    def add_script_call(self):
        path_part = self.script_path_entry.get().strip()
        func_part = self.script_func_entry.get().strip()

        if not path_part or not func_part:
            messagebox.showwarning("Missing Input", "Please enter both path and function name.")
            return

        path_part = path_part.replace("/", "\\").strip("\\")
        full_call = f"maps\\mp\\{path_part}::{func_part}();"

        current = self.threads_text.get("1.0", tk.END).strip()
        if current:
            self.threads_text.insert(tk.END, f"\n{full_call}")
        else:
            self.threads_text.insert("1.0", full_call)

        self.script_path_entry.delete(0, tk.END)
        self.script_func_entry.delete(0, tk.END)
        self.script_path_entry.focus()

    def pick_color(self, target_entry):
        """Open color picker and update entry with normalized RGB values"""
        color = colorchooser.askcolor(title="Pick Color")
        if color[0]:  # color[0] is RGB tuple, color[1] is hex
            r, g, b = color[0]
            # Normalize to 0-1 range (divide by 255) and format with 2 decimal places
            r_norm = round(r / 255.0, 2)
            g_norm = round(g / 255.0, 2)
            b_norm = round(b / 255.0, 2)
            target_entry.delete(0, tk.END)
            target_entry.insert(0, f"{r_norm}, {g_norm}, {b_norm}")

    def update_glow_bloom0_display(self, value):
        """Update display for r_glowbloomintensity0 slider"""
        val = round(float(value), 2)
        self.glow_bloom0_value.config(text=f"{val:.2f}")

    def update_glow_bloom1_display(self, value):
        """Update display for r_glowbloomintensity1 slider"""
        val = round(float(value), 2)
        self.glow_bloom1_value.config(text=f"{val:.2f}")

    def update_glow_skybleed0_display(self, value):
        """Update display for r_glowskybleedintensity0 slider"""
        val = round(float(value), 2)
        self.glow_skybleed0_value.config(text=f"{val:.2f}")

    # ── Other methods (unchanged except for clear_all_ui) ────────────────────────
    def toggle_expfog_fields(self):
        """Enable/disable expfog fields based on checkbox state"""
        state = "normal" if self.expfog_enabled.get() else "disabled"
        self.expfog_start_entry.config(state=state)
        self.expfog_halfway_entry.config(state=state)
        self.expfog_color_entry.config(state=state)
        self.expfog_time_entry.config(state=state)

    def toggle_cullfog_fields(self):
        """Enable/disable cullfog fields based on checkbox state"""
        state = "normal" if self.cullfog_enabled.get() else "disabled"
        self.cullfog_near_entry.config(state=state)
        self.cullfog_far_entry.config(state=state)
        self.cullfog_color_entry.config(state=state)
        self.cullfog_time_entry.config(state=state)

    def toggle_glow_bloom0_field(self):
        """Enable/disable glow bloom0 slider based on checkbox state"""
        state = "normal" if self.glow_bloom0_enabled.get() else "disabled"
        self.glow_bloom0_slider.config(state=state)

    def toggle_glow_bloom1_field(self):
        """Enable/disable glow bloom1 slider based on checkbox state"""
        state = "normal" if self.glow_bloom1_enabled.get() else "disabled"
        self.glow_bloom1_slider.config(state=state)

    def toggle_glow_skybleed0_field(self):
        """Enable/disable glow skybleed0 slider based on checkbox state"""
        state = "normal" if self.glow_skybleed0_enabled.get() else "disabled"
        self.glow_skybleed0_slider.config(state=state)

    def update_missing_status(self):
        mapname = self.app.map_name.get().strip()
        print(f"[DEBUG MainGSC] Updating for map: '{mapname}'")

        if not mapname:
            self.missing_label.config(text="")
            self.create_btn.state(["disabled"])
            self.clear_all_ui()
            return

        self.clear_all_ui()

        cod2_path = Path(self.app.cod2_path.get())
        status = self.app.check_missing_files(cod2_path, mapname)

        if not status.get("main_gsc", {}).get("exists", False):
            self.missing_label.config(text=f"File missing: {mapname}.gsc", foreground="red")
            self.create_btn.config(text=f"Create {mapname}.gsc")
            self.create_btn.state(["!disabled"])
        else:
            self.missing_label.config(text="Main GSC file exists ✓", foreground="green")
            self.create_btn.state(["disabled"])
            self.load_from_file(cod2_path, mapname)

    def load_from_file(self, cod2_path: Path, mapname: str):
        gsc_path = cod2_path / "main" / "maps" / "mp" / f"{mapname}.gsc"
        if not gsc_path.exists():
            gsc_path = cod2_path / "maps" / "mp" / f"{mapname}.gsc"

        if not gsc_path.exists():
            print(f"[DEBUG MainGSC] File not found: {gsc_path}")
            return

        try:
            content = gsc_path.read_text(encoding="utf-8")
            lines = content.splitlines()

            # Reset UI
            self.threads_text.delete("1.0", tk.END)
            self.hq_list.delete(*self.hq_list.get_children())
            self.killtrigger_list.delete(*self.killtrigger_list.get_children())
            self.ambient_enabled.set(False)
            self.ambient_combo.set("")

            # Reset faction controls
            self.allies_combo.set("british")
            self.axis_var.set("german")
            self.defenders_combo.set("axis")
            self.attackers_combo.set("allies")
            self.german_soldiertype_combo.set("normandy")
            self.allies_soldiertype_combo.set("")

            self.kt_enabled.set(False)
            self.expfog_enabled.set(False)
            self.cullfog_enabled.set(False)
            self.glow_bloom0_enabled.set(False)
            self.glow_bloom1_enabled.set(False)
            self.glow_skybleed0_enabled.set(False)

            hq_temp = {}
            kt_temp = {}

            for line in lines:
                stripped = line.strip()
                if not stripped or stripped.startswith('//'):
                    continue

                if 'ambientPlay(' in stripped:
                    self.ambient_enabled.set(True)
                    try:
                        alias = stripped.split('"')[1]
                        self.ambient_combo.set(alias)
                    except:
                        pass

                elif 'game["' in stripped and '"] = "' in stripped:
                    try:
                        key = stripped.split('game["')[1].split('"')[0]
                        val = stripped.split('"] = "')[1].split('"')[0]

                        # Parse individual faction variables
                        if key == "allies":
                            self.allies_combo.set(val)
                            self.on_allies_changed()  # Update soldier type options
                        elif key == "axis":
                            self.axis_var.set(val)
                        elif key == "defenders":
                            self.defenders_combo.set(val)
                        elif key == "attackers":
                            self.attackers_combo.set(val)
                        elif key == "german_soldiertype":
                            self.german_soldiertype_combo.set(val)
                        elif key == "american_soldiertype":
                            self.allies_soldiertype_combo.set(val)
                        elif key == "british_soldiertype":
                            self.allies_soldiertype_combo.set(val)
                        elif key == "russian_soldiertype":
                            self.allies_soldiertype_combo.set(val)
                    except:
                        pass

                # HQ parsing - improved stripping
                # HQ parsing - much more accurate position extraction
                elif 'level.radio[' in stripped:
                    try:
                        idx = stripped.split('[')[1].split(']')[0].strip()

                        if 'spawn("script_model"' in stripped:
                            # Find the exact start of the position tuple after "script_model",
                            start_pos = stripped.find('(', stripped.find('"script_model"')) + 1
                            if start_pos == 0:
                                start_pos = stripped.find('(', stripped.find('spawn')) + 1

                            # Find matching closing ) by balancing parentheses
                            paren_count = 1
                            end_pos = start_pos
                            while end_pos < len(stripped):
                                if stripped[end_pos] == '(':
                                    paren_count += 1
                                elif stripped[end_pos] == ')':
                                    paren_count -= 1
                                    if paren_count == 0:
                                        break
                                end_pos += 1

                            if paren_count == 0:
                                pos = stripped[start_pos:end_pos].strip()
                                # Clean up: remove any leading/trailing junk
                                pos = pos.lstrip('("script_model", ')
                                pos = pos.rstrip(' "')
                                hq_temp[idx] = pos
                            else:
                                print(f"[DEBUG HQ] Unbalanced parens in pos: {stripped}")

                        elif '.angles =' in stripped:
                            # Extract angles after =
                            angles_start = stripped.find('=') + 1
                            angles = stripped[angles_start:].strip().rstrip(';')
                            # Strip outer parentheses if present
                            angles = angles.strip('() ')
                            if idx in hq_temp:
                                self.hq_list.insert("", "end", values=(hq_temp[idx], angles))
                                del hq_temp[idx]
                    except Exception as e:
                        print(f"[DEBUG HQ] Parse error: {e} | Line: {stripped}")

                elif 'level.killtriggers[' in stripped:
                    if 'spawnstruct()' in stripped:
                        self.kt_enabled.set(True)

                # Fog parsing
                elif 'setExpFog(' in stripped:
                    try:
                        self.expfog_enabled.set(True)
                        # Extract parameters from setExpFog(startDist, halfwayDist, r, g, b, transitionTime)
                        params_str = stripped.split('setExpFog(')[1].split(')')[0]
                        params = [p.strip() for p in params_str.split(',')]
                        if len(params) >= 6:
                            self.expfog_start_entry.delete(0, tk.END)
                            self.expfog_start_entry.insert(0, params[0])
                            self.expfog_halfway_entry.delete(0, tk.END)
                            self.expfog_halfway_entry.insert(0, params[1])
                            self.expfog_color_entry.delete(0, tk.END)
                            self.expfog_color_entry.insert(0, f"{params[2]}, {params[3]}, {params[4]}")
                            self.expfog_time_entry.delete(0, tk.END)
                            self.expfog_time_entry.insert(0, params[5])
                    except Exception as e:
                        print(f"[DEBUG Fog] Parse error: {e}")

                elif 'setcullfog(' in stripped:
                    try:
                        self.cullfog_enabled.set(True)
                        # Extract parameters from setcullfog(nearDist, farDist, r, g, b, transitionTime)
                        params_str = stripped.split('setcullfog(')[1].split(')')[0]
                        params = [p.strip() for p in params_str.split(',')]
                        if len(params) >= 6:
                            self.cullfog_near_entry.delete(0, tk.END)
                            self.cullfog_near_entry.insert(0, params[0])
                            self.cullfog_far_entry.delete(0, tk.END)
                            self.cullfog_far_entry.insert(0, params[1])
                            self.cullfog_color_entry.delete(0, tk.END)
                            self.cullfog_color_entry.insert(0, f"{params[2]}, {params[3]}, {params[4]}")
                            self.cullfog_time_entry.delete(0, tk.END)
                            self.cullfog_time_entry.insert(0, params[5])
                    except Exception as e:
                        print(f"[DEBUG Cull Fog] Parse error: {e}")

                # Glow parsing
                elif 'r_glowbloomintensity0' in stripped:
                    try:
                        self.glow_bloom0_enabled.set(True)
                        val = stripped.split('"')[3] if len(stripped.split('"')) > 3 else ""
                        if val:
                            self.glow_bloom0_slider.set(float(val))
                    except Exception as e:
                        print(f"[DEBUG Glow] Parse error: {e}")

                elif 'r_glowbloomintensity1' in stripped:
                    try:
                        self.glow_bloom1_enabled.set(True)
                        val = stripped.split('"')[3] if len(stripped.split('"')) > 3 else ""
                        if val:
                            self.glow_bloom1_slider.set(float(val))
                    except Exception as e:
                        print(f"[DEBUG Glow] Parse error: {e}")

                elif 'r_glowskybleedintensity0' in stripped:
                    try:
                        self.glow_skybleed0_enabled.set(True)
                        val = stripped.split('"')[3] if len(stripped.split('"')) > 3 else ""
                        if val:
                            self.glow_skybleed0_slider.set(float(val))
                    except Exception as e:
                        print(f"[DEBUG Sky Bleed] Parse error: {e}")

                # Add only NON-standard calls to threads_text
                elif '::' in stripped and stripped.endswith(';'):
                    call = stripped.rstrip(';').strip()
                    # Skip standard ones to prevent duplication
                    if any(x in call for x in [f"{mapname}_fx::main", "_load::main"]):
                        continue
                    current = self.threads_text.get("1.0", tk.END).strip()
                    if current:
                        self.threads_text.insert(tk.END, f"\n{call}")
                    else:
                        self.threads_text.insert("1.0", call)

            # Update field states for fog and glow
            self.toggle_expfog_fields()
            self.toggle_cullfog_fields()
            self.toggle_glow_bloom0_field()
            self.toggle_glow_bloom1_field()
            self.toggle_glow_skybleed0_field()

            print("[DEBUG MainGSC] Parsing completed successfully")

        except Exception as e:
            print(f"[DEBUG MainGSC] Load error: {e}")
            messagebox.showwarning("Partial Load", "Some parts of the GSC could not be parsed.")

    def save_files(self, cod2_path: Path, mapname: str):
        path = cod2_path / "main" / "maps" / "mp" / f"{mapname}.gsc"

        lines = []

        lines.append("main()")
        lines.append("{")

        # Standard loads first
        lines.append(f"    maps\\mp\\{mapname}_fx::main();")
        lines.append("    maps\\mp\\_load::main();")
        lines.append("")

        # Custom script calls (from threads_text) - placed BEFORE ambient
        calls = self.threads_text.get("1.0", tk.END).strip().splitlines()
        for call in calls:
            stripped = call.strip()
            if stripped:
                if not stripped.endswith(';'):
                    stripped += ';'
                lines.append(f"    {stripped}")
        if calls:
            lines.append("")

        # Ambient
        if self.ambient_enabled.get():
            alias = self.ambient_combo.get().strip()
            if alias:
                lines.append(f"    ambientPlay(\"{alias}\");")
            lines.append("")

        # Factions
        allies = self.allies_combo.get()
        axis = self.axis_var.get()
        defenders = self.defenders_combo.get()
        attackers = self.attackers_combo.get()
        german_st = self.german_soldiertype_combo.get()
        allies_st = self.allies_soldiertype_combo.get()

        lines.append(f'    game["allies"] = "{allies}";')
        lines.append(f'    game["axis"] = "{axis}";')
        lines.append(f'    game["defenders"] = "{defenders}";')
        lines.append(f'    game["attackers"] = "{attackers}";')
        lines.append(f'    game["german_soldiertype"] = "{german_st}";')

        # Set appropriate soldier type key based on allies selection
        if allies == "american":
            lines.append(f'    game["american_soldiertype"] = "{allies_st}";')
        elif allies == "british":
            lines.append(f'    game["british_soldiertype"] = "{allies_st}";')
        elif allies == "russian":
            lines.append(f'    game["russian_soldiertype"] = "{allies_st}";')

        lines.append("")

        # HQ
        hq_items = list(self.hq_list.get_children())
        if hq_items:
            lines.append("")
            lines.append('    if (getcvar("g_gametype") == "hq")')
            lines.append("    {")
            lines.append("        level.radio = [];")
            for idx, item in enumerate(hq_items):
                pos, angles = self.hq_list.item(item)["values"]
                # Use stored strings directly (already normalized)
                lines.append(f"        level.radio[{idx}] = spawn(\"script_model\", ({pos}));")
                lines.append(f"        level.radio[{idx}].angles = ({angles});")
            lines.append("    }")
            lines.append("")

        # Kill Triggers
        kt_items = list(self.killtrigger_list.get_children())
        if kt_items and self.kt_enabled.get():
            lines.append("    level.killtriggers = [];")
            for idx, item in enumerate(kt_items):
                origin, radius, height = self.killtrigger_list.item(item)["values"]
                lines.append(f"    level.killtriggers[{idx}] = spawnstruct();")
                lines.append(f"    level.killtriggers[{idx}].origin = ({origin});")
                lines.append(f"    level.killtriggers[{idx}].radius = {radius};")
                lines.append(f"    level.killtriggers[{idx}].height = {height};")
            lines.append("    thread maps\\mp\\_killtriggers::init();")
            lines.append("")

        # Fog
        if self.expfog_enabled.get():
            lines.append("    // Fog Settings - setExpFog")
            start_dist = self.expfog_start_entry.get().strip()
            halfway_dist = self.expfog_halfway_entry.get().strip()
            expfog_color = self.expfog_color_entry.get().strip()
            expfog_time = self.expfog_time_entry.get().strip()
            if start_dist and halfway_dist:
                lines.append(f"    setExpFog({start_dist}, {halfway_dist}, {expfog_color}, {expfog_time});")
            lines.append("")

        if self.cullfog_enabled.get():
            lines.append("    // Fog Settings - setcullfog")
            cullfog_near = self.cullfog_near_entry.get().strip()
            cullfog_far = self.cullfog_far_entry.get().strip()
            cullfog_color = self.cullfog_color_entry.get().strip()
            cullfog_time = self.cullfog_time_entry.get().strip()
            lines.append(f"    setcullfog({cullfog_near}, {cullfog_far}, {cullfog_color}, {cullfog_time});")
            lines.append("")

        # Glow/Bloom
        if self.glow_bloom0_enabled.get():
            bloom0 = round(self.glow_bloom0_slider.get(), 2)
            lines.append(f"    setcvar(\"r_glowbloomintensity0\", \"{bloom0:.2f}\");")

        if self.glow_bloom1_enabled.get():
            bloom1 = round(self.glow_bloom1_slider.get(), 2)
            lines.append(f"    setcvar(\"r_glowbloomintensity1\", \"{bloom1:.2f}\");")

        if self.glow_skybleed0_enabled.get():
            skybleed0 = round(self.glow_skybleed0_slider.get(), 2)
            lines.append(f"    setcvar(\"r_glowskybleedintensity0\", \"{skybleed0:.2f}\");")

        if any([self.glow_bloom0_enabled.get(), self.glow_bloom1_enabled.get(), self.glow_skybleed0_enabled.get()]):
            lines.append("")

        lines.append("}")

        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"[DEBUG MainGSC] Saved to: {path}")

    def clear_all_ui(self):
        self.threads_text.delete("1.0", tk.END)
        self.hq_list.delete(*self.hq_list.get_children())
        self.killtrigger_list.delete(*self.killtrigger_list.get_children())
        self.ambient_enabled.set(False)
        self.ambient_combo.set("")

        # Clear faction controls
        self.allies_combo.set("british")
        self.axis_var.set("german")
        self.defenders_combo.set("axis")
        self.attackers_combo.set("allies")
        self.german_soldiertype_combo.set("normandy")
        self.allies_soldiertype_combo.set("")

        self.kt_enabled.set(False)

        # Clear fog and glow - disable all
        self.expfog_enabled.set(False)
        self.cullfog_enabled.set(False)
        self.glow_bloom0_enabled.set(False)
        self.glow_bloom1_enabled.set(False)
        self.glow_skybleed0_enabled.set(False)
        self.toggle_expfog_fields()
        self.toggle_cullfog_fields()
        self.toggle_glow_bloom0_field()
        self.toggle_glow_bloom1_field()
        self.toggle_glow_skybleed0_field()

        print("[DEBUG MainGSC] UI cleared")

    def add_script_call(self):
        path_part = self.script_path_entry.get().strip()
        func_part = self.script_func_entry.get().strip()

        if not path_part or not func_part:
            messagebox.showwarning("Missing Input", "Please enter both path and function name.")
            return

        path_part = path_part.replace("/", "\\").strip("\\")
        full_call = f"maps\\mp\\{path_part}::{func_part}();"

        current = self.threads_text.get("1.0", tk.END).strip()
        if current:
            self.threads_text.insert(tk.END, f"\n{full_call}")
        else:
            self.threads_text.insert("1.0", full_call)

        self.script_path_entry.delete(0, tk.END)
        self.script_func_entry.delete(0, tk.END)
        self.script_path_entry.focus()

    def add_hq_location_inline(self):
        pos = self.hq_pos_entry.get().strip()
        angles = self.hq_angles_entry.get().strip()

        if not pos or not angles:
            return

        # Normalize: replace multiple spaces with single comma, remove extra spaces
        pos = ' '.join(pos.split())          # collapse spaces
        pos = pos.replace(' ', ', ')         # space → comma + space
        pos = pos.replace(',,', ',')         # cleanup double commas if any

        angles = ' '.join(angles.split())
        angles = angles.replace(' ', ', ')

        # Optional: strip any outer parentheses user might have pasted
        pos = pos.strip('() ')
        angles = angles.strip('() ')

        self.hq_list.insert("", "end", values=(pos, angles))
        self.hq_pos_entry.delete(0, tk.END)
        self.hq_angles_entry.delete(0, tk.END)
        self.hq_pos_entry.focus()

    def add_killtrigger_inline(self):
        origin = self.kt_origin_entry.get().strip()
        radius = self.kt_radius_entry.get().strip()
        height = self.kt_height_entry.get().strip()

        if not origin or not radius or not height:
            return

        # Normalize origin (same as above)
        origin = ' '.join(origin.split())
        origin = origin.replace(' ', ', ')
        origin = origin.strip('() ')

        self.killtrigger_list.insert("", "end", values=(origin, radius, height))
        self.kt_origin_entry.delete(0, tk.END)
        self.kt_radius_entry.delete(0, tk.END)
        self.kt_height_entry.delete(0, tk.END)
        self.kt_origin_entry.focus()

    def remove_hq_location(self):
        sel = self.hq_list.selection()
        if sel:
            self.hq_list.delete(sel)

    def remove_killtrigger(self):
        sel = self.killtrigger_list.selection()
        if sel:
            self.killtrigger_list.delete(sel)

    def create_file_if_missing(self):
        mapname = self.app.map_name.get().strip()
        if not mapname:
            messagebox.showwarning("No Map Selected", "Please select a map first!")
            return

        cod2_path = Path(self.app.cod2_path.get())

        path = cod2_path / "main" / "maps" / "mp" / f"{mapname}.gsc"
        if not path.parent.exists():
            path = cod2_path / "maps" / "mp" / f"{mapname}.gsc"

        if path.exists():
            messagebox.showinfo("File Exists", f"Main GSC file already exists:\n{path}")
            return

        try:
            content = MINIMAL_MAIN_GSC.format(mapname=mapname, mapname_short=mapname)
        except KeyError as e:
            messagebox.showerror("Template Error", f"Error formatting minimal GSC template: {e}")
            return

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

        messagebox.showinfo("Created", f"Created basic main GSC file:\n{path}")

        self.update_missing_status()