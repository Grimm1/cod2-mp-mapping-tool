"""Main Qt application window for the CoD2 mapping tool.

This module builds the primary window, installs all child tab widgets,
manages map refresh behavior, and provides the launcher actions for
external utilities such as asset manager, compiler tools, and Radiant.
"""

from __future__ import annotations
from pathlib import Path
import subprocess
from typing import Optional

from PyQt6 import QtCore, QtGui, QtWidgets, uic

from config import DEFAULT_COD2_PATH, load_config, save_config
from helpers import get_map_list, resolve_cod2_path, map_gsc_path, map_csv_path, map_arena_path, map_sun_path, map_soundaliases_path
from .main_gsc_tab import MainGscTab
from .qt_tabs_ported import BasicFilesTab, FxGscTab, SoundAliasesTab, SunTab
from .modelviewer_tab import ModelViewerTab
from .iwd_packer_tab import IwdPackerTab
from .tools_setup_tab import ToolsSetupTab
from .compile_tools_tab import CompileToolsTab


class QtMainWindow(QtWidgets.QMainWindow):
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self._ui_path = Path(__file__).with_name("main_window_qt.ui")
        uic.loadUi(str(self._ui_path), self)

        self.config = load_config()
        self.cod2_path = self.findChild(QtWidgets.QLineEdit, "cod2_path_edit")
        self.map_combo = self.findChild(QtWidgets.QComboBox, "map_name_combo")
        self.browse_button = self.findChild(QtWidgets.QPushButton, "browse_button")
        self.refresh_button = self.findChild(QtWidgets.QPushButton, "refresh_button")
        self.generate_button = self.findChild(QtWidgets.QPushButton, "generate_button")
        self.asset_manager_button = self.findChild(QtWidgets.QToolButton, "asset_manager_button")
        self.effects_editor_button = self.findChild(QtWidgets.QToolButton, "effects_editor_button")
        self.compile_tools_button = self.findChild(QtWidgets.QToolButton, "compile_tools_button")
        self.radiant_button = self.findChild(QtWidgets.QToolButton, "radiant_button")

        if self.cod2_path is None or self.map_combo is None or self.browse_button is None or self.refresh_button is None or self.generate_button is None:
            raise RuntimeError("The Qt UI layout is missing required widgets. Please re-run the UI build or verify the .ui file.")

        self.cod2_path.setText(self.config.get("last_cod2_path", str(DEFAULT_COD2_PATH)))
        self.map_combo.setEditText(self.config.get("last_selected_map", ""))

        self.browse_button.clicked.connect(self.browse_cod2)
        self.refresh_button.clicked.connect(self.refresh_maps)
        self.generate_button.clicked.connect(self.generate_files)
        if self.asset_manager_button is not None:
            self.asset_manager_button.clicked.connect(lambda: self.launch_tool("asset_manager.exe"))
        if self.effects_editor_button is not None:
            self.effects_editor_button.clicked.connect(lambda: self.launch_tool("CoD2_EffectsEd.exe"))
        if self.compile_tools_button is not None:
            self.compile_tools_button.clicked.connect(lambda: self.launch_tool("CoD2CompileTools.exe"))
        if self.radiant_button is not None:
            self.radiant_button.clicked.connect(lambda: self.launch_tool("CoD2Radiant.exe"))

        self._install_tabs()
        self.refresh_maps()
        self.setWindowTitle("CoD2 MP Mapping tools")
        self.resize(1200, 950)
        self.setMinimumSize(1100, 800)

        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose, True)

    def _install_tabs(self) -> None:
        main_tab = self.findChild(QtWidgets.QWidget, "script_tools_tab")
        if main_tab is None:
            return

        script_subtab_widget = main_tab.findChild(QtWidgets.QTabWidget, "script_subtabs")
        if script_subtab_widget is not None:
            script_subtab_widget.clear()

        self.main_gsc_tab = MainGscTab(self)
        self.fx_gsc_tab = FxGscTab(self)
        self.sun_tab = SunTab(self)
        self.soundaliases_tab = SoundAliasesTab(self)
        self.basic_files_tab = BasicFilesTab(self)

        if script_subtab_widget is not None:
            script_subtab_widget.addTab(self.main_gsc_tab, "Main GSC")
            script_subtab_widget.addTab(self.fx_gsc_tab, "FX GSC")
            script_subtab_widget.addTab(self.sun_tab, "SUN File")
            script_subtab_widget.addTab(self.soundaliases_tab, "Sound Aliases")
            script_subtab_widget.addTab(self.basic_files_tab, "Basic Files")

        # Model Viewer
        model_tab_widget = self.findChild(QtWidgets.QWidget, "model_viewer_tab")
        if model_tab_widget is not None:
            self.model_viewer_tab = ModelViewerTab(self)
            layout = model_tab_widget.layout()
            if layout is not None:
                while layout.count():
                    item = layout.takeAt(0)
                    if item.widget():
                        item.widget().deleteLater()
                layout.addWidget(self.model_viewer_tab)

        # Tools Setup
        tools_tab_widget = self.findChild(QtWidgets.QWidget, "tools_setup_tab")
        if tools_tab_widget is not None:
            self.tools_setup_tab = ToolsSetupTab(self)
            layout = tools_tab_widget.layout()
            if layout is not None:
                while layout.count():
                    item = layout.takeAt(0)
                    if item.widget():
                        item.widget().deleteLater()
                layout.addWidget(self.tools_setup_tab)

        # Compiler Tools
        compiler_tab_widget = self.findChild(QtWidgets.QWidget, "Compiler_tab")
        if compiler_tab_widget is not None:
            self.compiler_tab = CompileToolsTab(self)
            layout = compiler_tab_widget.layout()
            if layout is not None:
                while layout.count():
                    item = layout.takeAt(0)
                    if item.widget():
                        item.widget().deleteLater()
                layout.addWidget(self.compiler_tab)



        # IWD Packer
        iwd_tab_widget = self.findChild(QtWidgets.QWidget, "iwd_packer_tab")
        if iwd_tab_widget is not None:
            self.iwd_packer_tab = IwdPackerTab(self)
            layout = iwd_tab_widget.layout()
            if layout is not None:
                while layout.count():
                    item = layout.takeAt(0)
                    if item.widget():
                        item.widget().deleteLater()
                layout.addWidget(self.iwd_packer_tab)

        # Connect map change signal
        self.map_combo.currentTextChanged.connect(self._on_map_changed)

    def _on_map_changed(self, new_map: str) -> None:
        """Called when user changes map in the combo box"""
        if new_map and new_map.strip():
            self._refresh_tab_states()

    def _refresh_tab_states(self) -> None:
        """Refresh all tabs when map changes — always load from files"""
        for tab in [
            getattr(self, "main_gsc_tab", None),
            getattr(self, "fx_gsc_tab", None),
            getattr(self, "sun_tab", None),
            getattr(self, "soundaliases_tab", None),
            getattr(self, "basic_files_tab", None),
            getattr(self, "iwd_packer_tab", None),
        ]:
            if tab is not None:
                try:
                    if hasattr(tab, "update_missing_status"):
                        # Only MainGscTab accepts keep_user_data=False
                        if isinstance(tab, MainGscTab):
                            tab.update_missing_status(keep_user_data=False)
                        else:
                            tab.update_missing_status()
                    if hasattr(tab, "refresh_status"):
                        tab.refresh_status()
                except Exception as e:
                    print(f"[Refresh] Failed to refresh {tab.__class__.__name__}: {e}")

    def generate_files(self) -> None:
        map_name = self.map_combo.currentText().strip()
        if not map_name:
            QtWidgets.QMessageBox.warning(self, "No Map", "Select a map first.")
            return

        try:
            if hasattr(self, "main_gsc_tab"):
                self.main_gsc_tab.save_files()
            if hasattr(self, "fx_gsc_tab"):
                self.fx_gsc_tab.save_files()
            if hasattr(self, "sun_tab"):
                self.sun_tab.save_files()
            if hasattr(self, "soundaliases_tab"):
                self.soundaliases_tab.save_files()
            if hasattr(self, "basic_files_tab"):
                self.basic_files_tab.save_files()

            # After saving, do normal refresh (load from files)
            self._refresh_tab_states()

            QtWidgets.QMessageBox.information(self, "Success", 
                f"All files saved successfully for **{map_name}**.")

        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Save Failed", str(e))

    def browse_cod2(self) -> None:
        path, _ = QtWidgets.QFileDialog.getExistingDirectory(self, "Select CoD2 Directory")
        if path:
            self.cod2_path.setText(path)
            self.refresh_maps()
            config = load_config()
            config["last_cod2_path"] = path
            save_config(config)

    def refresh_maps(self) -> None:
        path = self.cod2_path.text().strip()
        if not path or not Path(path).is_dir():
            self.map_combo.clear()
            return

        maps = get_map_list(path)
        current = self.map_combo.currentText().strip()
        self.map_combo.clear()
        self.map_combo.addItems(maps)
        if current in maps:
            self.map_combo.setCurrentText(current)
        elif maps:
            self.map_combo.setCurrentIndex(0)

        if hasattr(self, "iwd_packer_tab") and self.iwd_packer_tab is not None:
            try:
                self.iwd_packer_tab.refresh_maps(preferred_map=self.map_combo.currentText().strip())
            except Exception as exc:
                print(f"[Refresh] Failed to sync IWD packer maps: {exc}")
        if hasattr(self, "compiler_tab") and self.compiler_tab is not None:
            try:
                self.compiler_tab.refresh_maps(preferred_map=self.map_combo.currentText().strip())
            except Exception as exc:
                print(f"[Refresh] Failed to sync Compile Tools maps: {exc}")

        self._refresh_tab_states()

        for tab in [
            getattr(self, "main_gsc_tab", None),
            getattr(self, "fx_gsc_tab", None),
            getattr(self, "sun_tab", None),
            getattr(self, "soundaliases_tab", None),
            getattr(self, "basic_files_tab", None),
            getattr(self, "tools_setup_tab", None),
            getattr(self, "iwd_packer_tab", None),
            getattr(self, "model_viewer_tab", None),
        ]:
            if tab is not None and hasattr(tab, "update_missing_status"):
                tab.update_missing_status()
            if tab is not None and hasattr(tab, "refresh_status"):
                tab.refresh_status()

    def _refresh_tab_states_safely(self) -> None:
        """Refresh status but avoid clearing user-edited lists"""
        for tab_name in ["main_gsc_tab", "fx_gsc_tab", "sun_tab", "soundaliases_tab", "basic_files_tab"]:
            tab = getattr(self, tab_name, None)
            if tab is not None:
                if hasattr(tab, "update_missing_status"):
                    # For MainGSC, only update status, don't reload content if user has edits
                    if tab_name == "main_gsc_tab":
                        tab.update_missing_status(keep_user_data=True)  # we'll add this
                    else:
                        tab.update_missing_status()
                if hasattr(tab, "refresh_status"):
                    tab.refresh_status()

    def check_missing_files(self, cod2_path: Path, mapname: str) -> dict:
        files = {
            "main_gsc": map_gsc_path(cod2_path, mapname),
            "fx_gsc": map_gsc_path(cod2_path, mapname, fx=True),
            "sun": map_sun_path(cod2_path, mapname),
            "csv": map_csv_path(cod2_path, mapname),
            "arena": map_arena_path(cod2_path, mapname),
            "soundaliases_csv": map_soundaliases_path(cod2_path, mapname),
        }
        return {k: {"path": v, "exists": v.is_file()} for k, v in files.items()}

    def launch_tool(self, exe_name: str) -> None:
        cod2_path = self.cod2_path.text().strip()
        if not cod2_path:
            QtWidgets.QMessageBox.warning(self, "Missing CoD2 Path", "Set the CoD2 folder first.")
            return

        exe_path = Path(cod2_path) / "bin" / exe_name
        if not exe_path.exists():
            QtWidgets.QMessageBox.warning(self, "Tool Not Found", f"Could not find {exe_name} in {exe_path}.")
            return

        try:
            subprocess.Popen([str(exe_path)], cwd=str(exe_path.parent))
            self.statusBar().showMessage(f"Launched {exe_name}")
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Launch Failed", str(exc))

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        config_data = {
            "last_cod2_path": self.cod2_path.text().strip(),
            "last_selected_map": self.map_combo.currentText().strip(),
            "window_geometry": f"{self.width()}x{self.height()}+{self.x()}+{self.y()}",
        }
        save_config(config_data)
        super().closeEvent(event)


def launch_qt_app() -> None:
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    window = QtMainWindow()
    window.show()
    app.exec()


if __name__ == "__main__":
    launch_qt_app()
