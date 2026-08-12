"""Tools setup tab for managing CoD2 install helpers and asset extraction."""

from importlib.resources import path
from pathlib import Path
from posixpath import sep
import zipfile
import os
import urllib.request
from PyQt6 import QtWidgets,QtGui,QtCore


from ui.qt_tab_mixin import QtTabMixin


class ToolsSetupTab(QtTabMixin, QtWidgets.QWidget):
    def __init__(self, app: QtWidgets.QWidget) -> None:
        super().__init__(app)
        self._build_ui()
        self.refresh_status()

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        self.path_label = QtWidgets.QLabel("Not set")
        layout.addWidget(QtWidgets.QLabel("COD2 Path"))
        layout.addWidget(self.path_label)
        set_path_btn = QtWidgets.QPushButton("Set COD2 path")
        set_path_btn.clicked.connect(self.set_cod2_path)
        layout.addWidget(set_path_btn)
        self.add_separator(layout)
        layout.addWidget(QtWidgets.QLabel("COD2 Folder"))
        layout.addWidget(self.path_label)
        open_folder_btn = QtWidgets.QPushButton("Open COD2 Folder")
        open_folder_btn.clicked.connect(self.open_cod2_folder)
        layout.addWidget(open_folder_btn)
        self.add_separator(layout)
        self.dll_status = QtWidgets.QLabel("Missing")
        self.dll_status_label = QtWidgets.QLabel(
    "<span style='color: red;'>IF asset manager fails to start or reports missing dlls </span> "
    "<span style='color: white;'>click the button below to get the required dlls</span>"
)

        layout.addWidget(self.dll_status_label)
        layout.addWidget(self.dll_status)
        extract_dlls_btn = QtWidgets.QPushButton("Get asset manager dlls")
        extract_dlls_btn.clicked.connect(self.get_assetmanager_dlls)
        layout.addWidget(extract_dlls_btn)
        self.add_separator(layout)
        self.xmodel_status = QtWidgets.QLabel("missing")
        self.xmodel_status_label = QtWidgets.QLabel("Extracts xmodels from the iwds to the main/xmodel folder")
        layout.addWidget(self.xmodel_status_label)
        layout.addWidget(self.xmodel_status)
        extract_xmodels_btn = QtWidgets.QPushButton("Extract/Fix XModels")
        extract_xmodels_btn.clicked.connect(self.extract_xmodels)
        layout.addWidget(extract_xmodels_btn)
        self.add_separator(layout)
        self.fx_status = QtWidgets.QLabel("missing")
        self.fx_status_label = QtWidgets.QLabel("Extracts fx from the iwds to the main/fx folder")
        layout.addWidget(self.fx_status_label)
        layout.addWidget(self.fx_status)
        extract_fx_btn = QtWidgets.QPushButton("Extract/Fix FX")
        extract_fx_btn.clicked.connect(self.extract_fx)
        layout.addWidget(extract_fx_btn)
        self.add_separator(layout)
        self.grid_status = QtWidgets.QLabel("missing")
        self.grid_status_label = QtWidgets.QLabel("fixes the grid batch file")
        layout.addWidget(self.grid_status_label)
        layout.addWidget(self.grid_status)
        fix_grid_btn = QtWidgets.QPushButton("Fix Grid Batch File")
        fix_grid_btn.clicked.connect(self.fix_grid_batch)
        layout.addWidget(fix_grid_btn)
        


        layout.addStretch()

    def add_separator(self, layout):
        sep = QtWidgets.QFrame()
        sep.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        sep.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        layout.addWidget(sep)

    def open_cod2_folder(self):
        path = self.path_label.text().strip()  # <-- MUST have parentheses

        if not path or path.lower() == "not set" or not os.path.isdir(path):
            QtWidgets.QMessageBox.warning(self, "Invalid Path", "COD2 path is not set or is invalid.")
            return

        QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(path))




    def refresh_status(self) -> None:
        path = self.cod2_path()
        if path:
            self.path_label.setText(path)
            xmodels_path = Path(path) / "main" / "xmodel"
            self.xmodel_status.setText("Status: Extracted" if xmodels_path.exists() else "Status: Missing")
            fx_path = Path(path) / "main" / "fx"
            self.fx_status.setText("Status: Extracted" if fx_path.exists() else "Status: Missing")
            grid_path = Path(path) / "bin" / "cod2compiletools_grid.bat"
            self.grid_status.setText("Status: unknown" if grid_path.exists() else "Status: unknown")  #this will always be true i need to check the file contents for the changes.
            dlls_path = Path(path) / "bin" / "MFC71.DLL"
            self.dll_status.setText("Status: installed" if dlls_path.exists() else "Status: Missing")

        else:
            self.path_label.setText("Not set")
            self.xmodel_status.setText("Status: Waiting")
            self.fx_status.setText("Status: Waiting")
            self.grid_status.setText("Status: Waiting")
            self.dll_status.setText("Status: Waiting")

    def set_cod2_path(self) -> None:
        path = QtWidgets.QFileDialog.getExistingDirectory(self, "Select CoD2 Directory")
        if path:
            self.app.cod2_path.setText(path)
            self.refresh_status()

    def get_assetmanager_dlls(self) -> None:
        path = self.cod2_path()
        if not path:
            return

        cod2_path = Path(path)
        bin_path = cod2_path / "bin"
        dlls_zip_url = "https://github.com/Grimm1/cod2scripts_stock/raw/refs/heads/main/dlls/dlls.zip"

        try:
            # Download using urlopen (urlretrieve is obsolete and doesn't give status)
            with urllib.request.urlopen(dlls_zip_url) as response:
                if response.status != 200:
                    QtWidgets.QMessageBox.critical(self, "Error", "Failed to download DLLs")
                    return

                data = response.read()

            zip_path = bin_path / "dlls.zip"

            # Write ZIP file
            with open(zip_path, "wb") as f:
                f.write(data)

            # Extract ZIP
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(bin_path)

            # Delete ZIP after extraction
            try:
                os.remove(zip_path)
            except Exception as e:
                # Non‑fatal: extraction succeeded, ZIP cleanup failed
                print(f"Warning: could not delete zip file: {e}")

            QtWidgets.QMessageBox.information(self, "AssetManager DLLs", "DLLs downloaded and extracted successfully")

        except Exception as e:

            QtWidgets.QMessageBox.critical(self, "Error", f"Download failed: {e}")

        self.refresh_status()

    def extract_xmodels(self) -> None:
        path = self.cod2_path()
        if not path:
            return
        cod2_path = Path(path)
        xmodels_path = cod2_path / "main" / "xmodel"
        if xmodels_path.exists():
            QtWidgets.QMessageBox.information(self, "XModels", "XModels folder already exists")
            return
        iwd_path = cod2_path / "main" / "iw_13.iwd"
        if not iwd_path.exists():
            QtWidgets.QMessageBox.warning(self, "Missing IWD", "iw_13.iwd not found")
            return
        with zipfile.ZipFile(iwd_path, "r") as zf:
            for member in zf.namelist():
                if member.startswith("xmodel/"):
                    zf.extract(member, cod2_path / "main")
        self.refresh_status()

    def extract_fx(self) -> None:
        path = self.cod2_path()
        if not path:
            return
        cod2_path = Path(path)
        fx_path = cod2_path / "main" / "fx"
        if fx_path.exists():
            QtWidgets.QMessageBox.information(self, "FX", "FX folder already exists")
            return
        iwd_path = cod2_path / "main" / "iw_07.iwd"
        if not iwd_path.exists():
            QtWidgets.QMessageBox.warning(self, "Missing IWD", "iw_07.iwd not found")
            return
        with zipfile.ZipFile(iwd_path, "r") as zf:
            for member in zf.namelist():
                if member.startswith("fx"):
                    zf.extract(member, cod2_path / "main")
        self.refresh_status()


    def fix_grid_batch(self) -> None:
        path = self.cod2_path()
        if not path:
            return
        cod2_path = Path(path)
        grid_batch_path = cod2_path / "bin" / "cod2compiletools_grid.bat"
        #this fucking sucked
        batch_content = (
            "@ECHO OFF\n\n"
            "set treepath=%~1\n"
            "set makelog=%~2\n"
            "set cullxmodel=%~3\n"
            "set mapname=%~4\n\n"
            "IF \"%mapname:~0,3%\" == \"mp_\" (\n"
            "    set exe=CoD2MP_s.exe\n"
            "    set mapdir=main\\\\maps\\\\mp\n"
            ") ELSE (\n"
            "    set exe=CoD2SP_s.exe\n"
            "    set mapdir=main\\\\maps\n"
            ")\n\n"
            "mkdir \"%treepath%%mapdir%\"\n"
            "IF EXIST \"%treepath%\\\\map_source\\\\%mapname%.grid\" copy \"%treepath%\\\\map_source\\\\%mapname%.grid\" \"%treepath%%mapdir%\\\\%mapname%.grid\"\n\n"
            "cd %treepath%\n\n"
            "%exe% +set developer 1 +set logfile 2 +set r_smc_enable 0 +set r_smp_backend 0 +set sv_pure 0 +set scr_dm_timelimit 0 +set r_vc_makelog %makelog% +set r_vc_showlog 16 +set r_cullxmodel %cullxmodel% +set com_introplayed 1 +devmap %mapname%\n\n"
            "IF EXIST \"%treepath%\\\\map_source\\\\%mapname%.grid\" attrib -r \"%treepath%\\\\map_source\\\\%mapname%.grid\"\n"
            "IF EXIST \"%treepath%%mapdir%\\\\%mapname%.grid\" move /y \"%treepath%%mapdir%\\\\%mapname%.grid\" \"%treepath%\\\\map_source\\\\%mapname%.grid\"\n\n"
            "cls\n"
        )

        try:
            grid_batch_path.write_text(batch_content, encoding="utf-8")
            QtWidgets.QMessageBox.information(self, "Success", f"Grid batch file created/updated at:\n{grid_batch_path}")
            self.refresh_status()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Failed to write batch file: {e}")


