## ui/main_window.py
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

from config import DEFAULT_COD2_PATH, load_config, save_config, MINIMAL_MAIN_GSC
from helpers import get_map_list, ensure_directories
from .tab_basic import BasicFilesTab
from .tab_main_gsc import MainGSCTab
from .tab_fx_gsc import FXGSCTab
from .tab_sun import SunTab
from .tab_soundaliases import SoundAliasesTab
from .tab_model_viewer import ModelViewerTab
from .tab_tools_setup import ToolsSetupTab
from .tab_iwd_packer import IWDPackerTab

class MapScriptGeneratorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CoD2 MP Mapping tools")
        self.root.geometry("1200x950")
        self.root.minsize(1100, 800)

        self.config = load_config()
        self.cod2_path = tk.StringVar(value=self.config.get("last_cod2_path", str(DEFAULT_COD2_PATH)))
        self.map_name = tk.StringVar(value=self.config.get("last_selected_map", ""))

        self.create_widgets()
        self.refresh_maps()

        if "window_geometry" in self.config:
            self.root.geometry(self.config["window_geometry"])

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding=12)
        main_frame.pack(fill="both", expand=True)

        # TOP-LEVEL NOTEBOOK WITH TWO MAIN TABS
        top_notebook = ttk.Notebook(main_frame)
        top_notebook.pack(fill="both", expand=True, pady=8)

        # ==================== SCRIPT TOOLS TAB ====================
        script_tab = ttk.Frame(top_notebook)
        top_notebook.add(script_tab, text=" Script Tools ")

        # Path selection (only visible in Script Tools tab)
        path_frame = ttk.LabelFrame(script_tab, text=" Call of Duty 2 Location ", padding=10)
        path_frame.pack(fill="x", pady=(0, 12))

        ttk.Label(path_frame, text="CoD2 folder:").grid(row=0, column=0, sticky="w", padx=4)
        ttk.Entry(path_frame, textvariable=self.cod2_path, width=70).grid(row=0, column=1, padx=8)
        ttk.Button(path_frame, text="Browse", command=self.browse_cod2).grid(row=0, column=2)

        # Map selection (only visible in Script Tools tab)
        map_frame = ttk.LabelFrame(script_tab, text=" Map Selection ", padding=10)
        map_frame.pack(fill="x", pady=(0, 12))

        ttk.Label(map_frame, text="Map name:").grid(row=0, column=0, sticky="w", padx=4)
        self.map_combo = ttk.Combobox(
            map_frame, textvariable=self.map_name, state="readonly", width=35
        )
        self.map_combo.grid(row=0, column=1, sticky="w", padx=8)
        ttk.Button(map_frame, text="Refresh", command=self.refresh_maps).grid(row=0, column=2)

        # Existing sub-notebook (all your current tabs)
        self.notebook = ttk.Notebook(script_tab)
        self.notebook.pack(fill="both", expand=True, pady=8)

        self.tab_main_gsc = MainGSCTab(self.notebook, self)
        self.notebook.add(self.tab_main_gsc, text="  Main GSC  ")

        self.tab_fx = FXGSCTab(self.notebook, self)
        self.notebook.add(self.tab_fx, text="  FX GSC  ")

        self.tab_sun = SunTab(self.notebook, self)
        self.notebook.add(self.tab_sun, text="  SUN File  ")

        self.tab_soundaliases = SoundAliasesTab(self.notebook, self)
        self.notebook.add(self.tab_soundaliases, text="  Sound Aliases  ")

        self.tab_basic = BasicFilesTab(self.notebook, self)
        self.notebook.add(self.tab_basic, text="  Basic Files (csv + arena)  ")

        # Bottom buttons (only visible in Script Tools tab)
        btn_frame = ttk.Frame(script_tab)
        btn_frame.pack(fill="x", pady=12)
        ttk.Button(btn_frame, text="Generate / Save All Files", command=self.generate_files).pack(side="left", padx=20)

        # ==================== MODEL VIEWER TAB ====================
        model_tab = ttk.Frame(top_notebook)
        top_notebook.add(model_tab, text=" Model Viewer ")

        self.model_viewer = ModelViewerTab(model_tab)
        self.model_viewer.pack(fill="both", expand=True)

        tools_setup_tab = ttk.Frame(top_notebook)
        top_notebook.add(tools_setup_tab, text=" Tools Setup ")

        self.tools_setup = ToolsSetupTab(tools_setup_tab, self)
        self.tools_setup.pack(fill="both", expand=True)

                # ==================== IWD PACKER TAB (NEW) ====================
        packer_tab = ttk.Frame(top_notebook)
        top_notebook.add(packer_tab, text=" IWD Packer ")

        self.iwd_packer = IWDPackerTab(packer_tab, self)
        self.iwd_packer.pack(fill="both", expand=True)


    def browse_cod2(self):
        path = filedialog.askdirectory()
        if path:
            self.cod2_path.set(path)
            self.refresh_maps()
            config = load_config()
            config["last_cod2_path"] = path
            save_config(config)

    def refresh_maps(self):
        path = self.cod2_path.get().strip()
        if not path or not Path(path).is_dir():
            return

        maps = get_map_list(path)
        self.map_combo["values"] = maps

        prev = self.map_name.get()
        if prev in maps:
            self.map_combo.set(prev)
        elif maps:
            self.map_combo.current(0)
        else:
            self.map_name.set("")

        # IMPORTANT: Notify EVERY tab about the map change
        # This triggers update_missing_status() in all tabs
        print(f"[DEBUG] Map changed/refresh - notifying all tabs for '{self.map_name.get()}'")
        self.tab_main_gsc.update_missing_status()
        self.tab_fx.update_missing_status()
        self.tab_sun.update_missing_status()
        self.tab_soundaliases.update_missing_status()
        self.tab_basic.update_missing_status()

    def create_file_if_missing(self):
        mapname = self.app.map_name.get().strip()
        if not mapname:
            messagebox.showwarning("No Map", "Select a map first!")
            return

        cod2 = Path(self.app.cod2_path.get())
        path = cod2 / "main" / "maps" / "mp" / f"{mapname}.gsc"

        if path.exists():
            messagebox.showinfo("Already Exists", "Main GSC file already exists.")
            return

        # Use your minimal template from config
        content = MINIMAL_MAIN_GSC.format(mapname=mapname, mapname_short=mapname)

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

        messagebox.showinfo("Created", f"Created basic main GSC file:\n{path}")
        self.update_missing_status()

    def generate_files(self):
        mapname = self.map_name.get().strip()
        if not mapname:
            messagebox.showwarning("Error", "Select a map first!")
            return

        cod2 = Path(self.cod2_path.get())
        try:
            ensure_directories(str(cod2), mapname)
            self.tab_main_gsc.save_files(cod2, mapname)
            self.tab_fx.save_files(cod2, mapname)
            self.tab_sun.save_files(cod2, mapname)
            self.tab_soundaliases.save_files(cod2, mapname)
            self.tab_basic.save_files(cod2, mapname)

            messagebox.showinfo("Success", f"Files updated for {mapname}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def on_closing(self):
        config_data = {
            "last_cod2_path": self.cod2_path.get(),
            "last_selected_map": self.map_name.get(),
            "window_geometry": f"{self.root.winfo_width()}x{self.root.winfo_height()}+{self.root.winfo_x()}+{self.root.winfo_y()}"
        }
        save_config(config_data)
        self.root.destroy()

    def check_missing_files(self, cod2_path: Path, mapname: str) -> dict:
        # Check both possible locations: with and without 'main' subdirectory
        base_mp = cod2_path / "main" / "maps" / "mp"
        base_mp_alt = cod2_path / "maps" / "mp"
        base_mp_dir = cod2_path / "main" / "mp"
        base_mp_dir_alt = cod2_path / "mp"
        base_sun = cod2_path / "main" / "sun"
        base_sun_alt = cod2_path / "sun"
        base_sound = cod2_path / "main" / "soundaliases"

        # Use the locations that exist
        if not base_mp.exists():
            base_mp = base_mp_alt
        if not base_mp_dir.exists():
            base_mp_dir = base_mp_dir_alt
        if not base_sun.exists():
            base_sun = base_sun_alt

        files = {
            "main_gsc": base_mp / f"{mapname}.gsc",
            "fx_gsc":   base_mp / f"{mapname}_fx.gsc",
            "sun":      base_sun / f"{mapname}.sun",
            "csv":      base_mp / f"{mapname}.csv",
            "arena":    base_mp_dir / f"{mapname}.arena",
            "soundaliases_csv": base_sound / f"{mapname}.csv",
        }
        return {k: {"path": v, "exists": v.is_file()} for k, v in files.items()}