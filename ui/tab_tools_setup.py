# ui/tab_tools_setup.py
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
import subprocess
import zipfile
import os
import shutil

class ToolsSetupTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.cod2_path = None
        self.create_widgets()
        self.check_setup_status()

    def create_widgets(self):
        # Main container with scrollbar
        canvas = tk.Canvas(self)
        v_scroll = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=v_scroll.set)

        canvas.pack(side="top", fill="both", expand=True)
        v_scroll.pack(side="right", fill="y")

        # Enable mouse wheel scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # Main content frame
        main_frame = ttk.Frame(scrollable_frame, padding=20)
        main_frame.pack(fill="both", expand=True)

        # Title
        title_label = ttk.Label(main_frame, text="Tools Setup", font=("Segoe UI", 14, "bold"))
        title_label.pack(anchor="w", pady=(0, 12))

        # ── COD2 PATH SECTION ──────────────────────────────────────────────
        path_frame = ttk.LabelFrame(main_frame, text="COD2 Path", padding=15)
        path_frame.pack(fill="x", pady=12)

        path_info_frame = ttk.Frame(path_frame)
        path_info_frame.pack(fill="x", pady=(0, 8))
        ttk.Label(path_info_frame, text="Current Path:", font=("Segoe UI", 9, "bold")).pack(side="left")
        self.path_label = ttk.Label(path_info_frame, text="Not set", foreground="red")
        self.path_label.pack(side="left", padx=(8, 0))

        ttk.Button(path_frame, text="Set COD2 Path", command=self.set_cod2_path).pack(anchor="w")

        # ── XMODELS SECTION ───────────────────────────────────────────────
        xmodel_frame = ttk.LabelFrame(main_frame, text="XModels Extraction", padding=15)
        xmodel_frame.pack(fill="x", pady=12)

        xmodel_info_frame = ttk.Frame(xmodel_frame)
        xmodel_info_frame.pack(fill="x", pady=(0, 8))
        ttk.Label(xmodel_info_frame, text="Status:", font=("Segoe UI", 9, "bold")).pack(side="left")
        self.xmodel_status = ttk.Label(xmodel_info_frame, text="Checking...", foreground="gray")
        self.xmodel_status.pack(side="left", padx=(8, 0))

        ttk.Label(xmodel_frame, text="If xmodels folder doesn't exist, extracts from iw_13.iwd",
                  foreground="gray", font=("Segoe UI", 8)).pack(anchor="w", pady=(0, 8))

        ttk.Button(xmodel_frame, text="Extract/Fix XModels", command=self.extract_xmodels).pack(anchor="w")

        # ── FX EXTRACTION SECTION ──────────────────────────────────────────
        fx_frame = ttk.LabelFrame(main_frame, text="FX Extraction", padding=15)
        fx_frame.pack(fill="x", pady=12)

        fx_info_frame = ttk.Frame(fx_frame)
        fx_info_frame.pack(fill="x", pady=(0, 8))
        ttk.Label(fx_info_frame, text="Status:", font=("Segoe UI", 9, "bold")).pack(side="left")
        self.fx_status = ttk.Label(fx_info_frame, text="Checking...", foreground="gray")
        self.fx_status.pack(side="left", padx=(8, 0))

        ttk.Label(fx_frame, text="If fx folder doesn't exist, extracts from iw_07.iwd",
                  foreground="gray", font=("Segoe UI", 8)).pack(anchor="w", pady=(0, 8))

        ttk.Button(fx_frame, text="Extract/Fix FX", command=self.extract_fx).pack(anchor="w")

        # ── SHORTCUTS SECTION ──────────────────────────────────────────────
        shortcuts_frame = ttk.LabelFrame(main_frame, text="Tool Shortcuts", padding=15)
        shortcuts_frame.pack(fill="x", pady=12)

        ttk.Label(shortcuts_frame, text="Creates desktop shortcuts for these tools:",
                  foreground="gray", font=("Segoe UI", 8)).pack(anchor="w", pady=(0, 8))

        tools_list = ttk.Frame(shortcuts_frame)
        tools_list.pack(fill="x", pady=8)

        # Define tools with nice display names
        self.shortcut_tools = [
            ("CoD2Radiant.exe", "CoD2 Radiant"),
            ("CoD2CompileTools.exe", "CoD2 Compile Tools"),
            ("asset_manager.exe", "CoD2 Asset Manager"),
            ("CoD2_EffectsEd.exe", "CoD2 Effects Editor"),
        ]

        for _, display_name in self.shortcut_tools:
            tool_frame = ttk.Frame(tools_list)
            tool_frame.pack(fill="x", pady=2)
            ttk.Label(tool_frame, text=f"  • {display_name}", width=40).pack(side="left")

        ttk.Label(shortcuts_frame, text="⚠ Tools should be run as administrator for best results\n"
                                        "(Shortcuts will request admin privileges)",
                  foreground="orange", font=("Segoe UI", 8)).pack(anchor="w", pady=(8, 0))

        ttk.Button(shortcuts_frame, text="Create Desktop Shortcuts", command=self.create_shortcuts).pack(anchor="w", pady=(8, 0))

        # ── GRID BATCH FILE SECTION ────────────────────────────────────────
        grid_frame = ttk.LabelFrame(main_frame, text="Grid Batch File", padding=15)
        grid_frame.pack(fill="x", pady=12)

        grid_info_frame = ttk.Frame(grid_frame)
        grid_info_frame.pack(fill="x", pady=(0, 8))
        ttk.Label(grid_info_frame, text="Status:", font=("Segoe UI", 9, "bold")).pack(side="left")
        self.grid_status = ttk.Label(grid_info_frame, text="Checking...", foreground="gray")
        self.grid_status.pack(side="left", padx=(8, 0))

        ttk.Label(grid_frame, text="Fixes cod2compiletools_grid.bat in /bin folder",
                  foreground="gray", font=("Segoe UI", 8)).pack(anchor="w", pady=(0, 8))

        ttk.Button(grid_frame, text="Fix Grid Batch File", command=self.fix_grid_batch).pack(anchor="w")

    def check_setup_status(self):
        """Check current setup status"""
        self.cod2_path = self.app.cod2_path.get() if hasattr(self.app, 'cod2_path') else None
        
        if self.cod2_path:
            self.path_label.config(text=self.cod2_path, foreground="green")
            self.check_xmodels()
            self.check_fx()
            self.check_grid_batch()
        else:
            self.path_label.config(text="Not set", foreground="red")
            self.xmodel_status.config(text="Waiting for path", foreground="gray")
            self.fx_status.config(text="Waiting for path", foreground="gray")
            self.grid_status.config(text="Waiting for path", foreground="gray")

    def check_xmodels(self):
        """Check if xmodels folder exists"""
        if not self.cod2_path:
            return
        
        xmodels_path = Path(self.cod2_path) / "main" / "xmodel"
        if xmodels_path.exists():
            self.xmodel_status.config(text="✓ Exists", foreground="green")
        else:
            self.xmodel_status.config(text="✗ Missing (need to extract)", foreground="red")

    def check_fx(self):
        """Check if fx folder exists"""
        if not self.cod2_path:
            return
        
        fx_path = Path(self.cod2_path) / "main" / "fx"
        if fx_path.exists():
            self.fx_status.config(text="✓ Exists", foreground="green")
        else:
            self.fx_status.config(text="✗ Missing (need to extract)", foreground="red")

    def check_grid_batch(self):
        """Check if grid batch file exists and is correct"""
        if not self.cod2_path:
            return
        
        grid_path = Path(self.cod2_path) / "bin" / "cod2compiletools_grid.bat"
        if grid_path.exists():
            self.grid_status.config(text="✓ Exists", foreground="green")
        else:
            self.grid_status.config(text="✗ Missing", foreground="red")

    def set_cod2_path(self):
        """Allow user to set COD2 path"""
        path = filedialog.askdirectory(title="Select COD2 Directory")
        if path:
            self.app.cod2_path.set(path)
            self.cod2_path = path
            self.check_setup_status()

    def extract_xmodels(self):
        """Extract xmodels from iw_13.iwd if needed"""
        if not self.cod2_path:
            messagebox.showwarning("Path Not Set", "Please set COD2 path first")
            return

        cod2_path = Path(self.cod2_path)
        xmodels_path = cod2_path / "main" / "xmodel"
        
        if xmodels_path.exists():
            messagebox.showinfo("XModels", "XModels folder already exists!")
            return

        iwd_path = cod2_path / "main" / "iw_13.iwd"
        if not iwd_path.exists():
            messagebox.showerror("Error", "iw_13.iwd not found in /main folder")
            return

        try:
            with zipfile.ZipFile(iwd_path, 'r') as zip_ref:
                xmodel_members = [m for m in zip_ref.namelist() if m.startswith('xmodel/')]
                
                if not xmodel_members:
                    messagebox.showerror("Error", "No xmodel folder found in iw_13.iwd")
                    return

                for member in xmodel_members:
                    zip_ref.extract(member, cod2_path / "main")

            messagebox.showinfo("Success", "XModels extracted successfully!")
            self.check_xmodels()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to extract xmodels: {e}")

    def extract_fx(self):
        """Extract fx from iw_07.iwd if needed"""
        if not self.cod2_path:
            messagebox.showwarning("Path Not Set", "Please set COD2 path first")
            return

        cod2_path = Path(self.cod2_path)
        fx_path = cod2_path / "main" / "fx"
        
        if fx_path.exists():
            messagebox.showinfo("FX", "FX folder already exists!")
            return

        iwd_path = cod2_path / "main" / "iw_07.iwd"
        if not iwd_path.exists():
            messagebox.showerror("Error", "iw_07.iwd not found in /main folder")
            return

        try:
            with zipfile.ZipFile(iwd_path, 'r') as zip_ref:
                fx_members = [m for m in zip_ref.namelist() if m.startswith('fx')]
                
                if not fx_members:
                    messagebox.showerror("Error", "No fx folder found in iw_07.iwd")
                    return

                for member in fx_members:
                    zip_ref.extract(member, cod2_path / "main")

            messagebox.showinfo("Success", "FX extracted successfully!")
            self.check_fx()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to extract fx: {e}")

    def create_shortcuts(self):
        """Create shortcuts on the user's Desktop"""
        if not self.cod2_path:
            messagebox.showwarning("Path Not Set", "Please set COD2 path first")
            return

        cod2_path = Path(self.cod2_path)
        bin_path = cod2_path / "bin"

        if not bin_path.exists():
            messagebox.showerror("Error", "/bin folder not found in COD2 directory")
            return

        created = 0
        errors = []

        for exe_name, display_name in self.shortcut_tools:
            exe_path = bin_path / exe_name
            if not exe_path.exists():
                errors.append(f"{exe_name} not found in /bin")
                continue

            shortcut_name = f"{display_name}.lnk"

            ps_script = f'''
$WshShell = New-Object -ComObject WScript.Shell
$desktop = [Environment]::GetFolderPath("Desktop")
$shortcut_path = Join-Path $desktop "{shortcut_name}"

$Shortcut = $WshShell.CreateShortcut($shortcut_path)
$Shortcut.TargetPath = "{exe_path}"
$Shortcut.WorkingDirectory = "{bin_path}"
$Shortcut.IconLocation = "{exe_path},0"
$Shortcut.Description = "Call of Duty 2 - {display_name}"
$Shortcut.Save()

# Set "Run as administrator"
$bytes = [IO.File]::ReadAllBytes($shortcut_path)
$bytes[21] = $bytes[21] -bor 0x20
[IO.File]::WriteAllBytes($shortcut_path, $bytes)
'''

            try:
                subprocess.run(["powershell", "-Command", ps_script], check=True, capture_output=True)
                created += 1
            except Exception as e:
                errors.append(f"{display_name}: {str(e)}")

        msg = f"Successfully created/updated {created} desktop shortcut(s)."
        if errors:
            msg += "\n\nErrors:\n" + "\n".join(errors)

        messagebox.showinfo("Desktop Shortcuts", msg)

    def fix_grid_batch(self):
        """Create/fix the grid batch file"""
        if not self.cod2_path:
            messagebox.showwarning("Path Not Set", "Please set COD2 path first")
            return

        cod2_path = Path(self.cod2_path)
        bin_path = cod2_path / "bin"

        if not bin_path.exists():
            messagebox.showerror("Error", "/bin folder not found in COD2 directory")
            return

        grid_batch_path = bin_path / "cod2compiletools_grid.bat"

        batch_content = """@ECHO OFF

set treepath=%~1
set makelog=%~2
set cullxmodel=%~3
set mapname=%~4

IF "%mapname:~0,3%" == "mp_" (
    set exe=CoD2MP_s.exe
    set mapdir=main\\maps\\mp
) ELSE (
    set exe=CoD2SP_s.exe
    set mapdir=main\\maps
)

mkdir "%treepath%%mapdir%"
IF EXIST "%treepath%\\map_source\\%mapname%.grid" copy "%treepath%\\map_source\\%mapname%.grid" "%treepath%%mapdir%\\%mapname%.grid"

cd %treepath%

%exe% +set developer 1 +set logfile 2 +set r_smc_enable 0 +set r_smp_backend 0 +set sv_pure 0 +set scr_dm_timelimit 0 +set r_vc_makelog %makelog% +set r_vc_showlog 16 +set r_cullxmodel %cullxmodel% +set com_introplayed 1 +devmap %mapname%

IF EXIST "%treepath%\\map_source\\%mapname%.grid" attrib -r "%treepath%\\map_source\\%mapname%.grid"
IF EXIST "%treepath%%mapdir%\\%mapname%.grid" move /y "%treepath%%mapdir%\\%mapname%.grid" "%treepath%\\map_source\\%mapname%.grid"

cls
"""

        try:
            grid_batch_path.write_text(batch_content)
            messagebox.showinfo("Success", f"Grid batch file created/updated at:\n{grid_batch_path}")
            self.check_grid_batch()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to write batch file: {e}")

    def save_files(self, cod2_path, mapname):
        """Save any tools setup configuration (placeholder)"""
        pass

    def load_from_file(self, cod2_path, mapname):
        """Load any tools setup configuration from file (placeholder)"""
        pass