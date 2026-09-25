"""Compile tools tab and worker thread for the CoD2 map compiler pipeline."""

from pathlib import Path
import ctypes
import shutil
import subprocess
import time
import psutil
from PyQt6 import QtWidgets, QtCore
from PyQt6.QtCore import QThread, pyqtSignal
from helpers import get_map_list, resolve_cod2_install_root
from ui.qt_tab_mixin import QtTabMixin
from config import load_compile_settings, save_compile_settings


class CompileWorker(QThread):
    """Runs the compile pipeline off the UI thread and streams log lines."""

    log_line = pyqtSignal(str)
    finished_ok = pyqtSignal()
    finished_error = pyqtSignal(str)

    def __init__(self, tab: "CompileToolsTab", map_name: str, opts: dict):
        super().__init__()
        self._tab = tab
        self._map_name = map_name
        self._opts = opts
        self._abort = False

    def request_abort(self) -> None:
        self._abort = True

    def _log(self, msg: str) -> None:
        self.log_line.emit(msg)

    def _run_tool(self, exe_name: str, args: list[str]) -> int:
        bin_dir = self._tab._bin_dir()
        if not bin_dir:
            self._log("[ERROR] bin dir missing")
            return -1
        exe = bin_dir / exe_name
        if not exe.is_file():
            self._log(f"[ERROR] Missing tool: {exe}")
            return -1

        cmd = [str(exe), *args]
        self._log(f"[RUN] {cmd}")

        try:
            proc = subprocess.Popen(
                cmd,
                cwd=str(bin_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )
        except OSError as e:
            self._log(f"[ERROR] failed to start: {e}")
            return -1

        assert proc.stdout is not None
        for line in proc.stdout:
            if self._abort:
                proc.kill()
                self._log("[ABORT] process killed")
                return -1
            self._log(line.rstrip("\r\n"))

        return proc.wait()

    def run(self) -> None:
        try:
            map_name = self._map_name
            opts = self._opts
            tab = self._tab

            tab._ensure_main_maps_dirs()

            needs_map = opts["do_bsp"] or opts["do_vis"] or opts["do_light"]
            if needs_map:
                src = tab._map_source_map(map_name)
                dst = tab._bsp_map_path(map_name)
                if not src or not src.is_file():
                    self.finished_error.emit(f"Map source file not found:\n{src}")
                    return
                if not dst:
                    self.finished_error.emit("Could not resolve staging path for .map")
                    return
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                self._log(f"[COPY] {src} → {dst}")

            if self._abort:
                self.finished_error.emit("Aborted.")
                return

            if opts["do_bsp"]:
                map_path = tab._bsp_map_path(map_name)
                args = [*opts["bsp_args"], "-platform", "pc", str(map_path)]
                rc = self._run_tool("cod2map.exe", args)
                if rc != 0:
                    self.finished_error.emit(f"BSP compile exited with code {rc}.")
                    return

            if self._abort:
                self.finished_error.emit("Aborted.")
                return

            if opts["do_vis"]:
                map_path = tab._bsp_map_path(map_name)
                args = ["-vis", "-platform", "pc", str(map_path)]
                rc = self._run_tool("cod2map.exe", args)
                if rc != 0:
                    self.finished_error.emit(f"VIS compile exited with code {rc}.")
                    return

            if self._abort:
                self.finished_error.emit("Aborted.")
                return

            if opts["do_light"]:
                src = tab._grid_source(map_name)
                dst = tab._bsp_file(".grid", map_name)
                if src and dst and src.exists():
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dst)
                    self._log(f"[GRID] staged {src} → {dst}")

                map_path = tab._bsp_map_path(map_name)
                args = [*opts["light_args"], "-platform", "pc", str(map_path)]
                rc = self._run_tool("cod2rad.exe", args)
                if rc != 0:
                    self.finished_error.emit(f"Lighting exited with code {rc}.")
                    return

                for suffix in (".map", ".d3dpoly", ".vclog", ".grid", ".lin"):
                    path = tab._bsp_file(suffix, map_name)
                    if path and path.exists():
                        try:
                            path.unlink()
                            self._log(f"[CLEANUP] removed {path}")
                        except OSError as e:
                            self._log(f"[CLEANUP] could not remove {path}: {e}")

            if self._abort:
                self.finished_error.emit("Aborted.")
                return

            self.finished_ok.emit()
        except Exception as e:
            self.finished_error.emit(str(e))


class CompileToolsTab(QtTabMixin, QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.custom_files: set[Path] = set()
        self._current_map: str = ""
        self._loading_settings: bool = False
        self._worker: CompileWorker | None = None
        self._active_compile_opts: dict | None = None
        self._active_compile_map: str = ""
        self._console_window: QtWidgets.QDialog | None = None
        self._console_popout: QtWidgets.QPlainTextEdit | None = None
        self.layout = QtWidgets.QVBoxLayout(self)
        self._build_ui()
        self._connect_settings_signals()
        self.refresh_maps()

    # ==================================================================
    # Path / map helpers
    # ==================================================================

    def _cod2_root(self) -> Path | None:
        path = self.cod2_path()
        if not path:
            return None
        root = resolve_cod2_install_root(path)
        return root if root.is_dir() else None

    def _current_map_name(self) -> str:
        return self.map_combo.currentText().strip()

    def _is_mp(self, map_name: str | None = None) -> bool:
        name = (map_name if map_name is not None else self._current_map_name()).strip()
        return name.startswith("mp_")

    def _exe_name(self, map_name: str | None = None) -> str:
        return "CoD2MP_s.exe" if self._is_mp(map_name) else "CoD2SP_s.exe"

    def _exe_path(self, map_name: str | None = None) -> Path | None:
        root = self._cod2_root()
        return (root / self._exe_name(map_name)) if root else None

    def _bin_dir(self) -> Path | None:
        root = self._cod2_root()
        return (root / "bin") if root else None

    def _map_source_dir(self) -> Path | None:
        root = self._cod2_root()
        return (root / "map_source") if root else None

    def _main_maps_dir(self, map_name: str | None = None) -> Path | None:
        """In-game / compile staging folder: main/maps or main/maps/mp."""
        root = self._cod2_root()
        if not root:
            return None
        if self._is_mp(map_name):
            return root / "main" / "maps" / "mp"
        return root / "main" / "maps"

    def _ensure_main_maps_dirs(self) -> None:
        root = self._cod2_root()
        if not root:
            return
        (root / "main" / "maps").mkdir(parents=True, exist_ok=True)
        (root / "main" / "maps" / "mp").mkdir(parents=True, exist_ok=True)

    def _map_source_map(self, map_name: str | None = None) -> Path | None:
        name = (map_name if map_name is not None else self._current_map_name()).strip()
        src = self._map_source_dir()
        return (src / f"{name}.map") if src and name else None

    def _bsp_map_path(self, map_name: str | None = None) -> Path | None:
        """Staged .map path passed to cod2map / cod2rad."""
        name = (map_name if map_name is not None else self._current_map_name()).strip()
        dest_dir = self._main_maps_dir(name)
        return (dest_dir / f"{name}.map") if dest_dir and name else None

    def _bsp_file(self, suffix: str, map_name: str | None = None) -> Path | None:
        """Sibling of the staged map (.grid, .lin, .d3dpoly, etc.)."""
        map_path = self._bsp_map_path(map_name)
        if not map_path:
            return None
        if not suffix.startswith("."):
            suffix = "." + suffix
        return map_path.with_suffix(suffix)

    def _grid_source(self, map_name: str | None = None) -> Path | None:
        name = (map_name if map_name is not None else self._current_map_name()).strip()
        src = self._map_source_dir()
        return (src / f"{name}.grid") if src and name else None

    def _grid_for_game(self, map_name: str | None = None) -> Path | None:
        """Grid location the game reads while editing (main/maps[/mp])."""
        return self._bsp_file(".grid", map_name)

    def _require_root_and_map(self) -> tuple[Path, str] | None:
        root = self._cod2_root()
        if not root:
            QtWidgets.QMessageBox.warning(
                self,
                "Invalid CoD2 Path",
                "Please set a valid Call of Duty 2 installation path in the settings.",
            )
            return None
        map_name = self._current_map_name()
        if not map_name:
            QtWidgets.QMessageBox.warning(
                self,
                "No Map Selected",
                "Please select a map first.",
            )
            return None
        return root, map_name

    # ==================================================================
    # Process / shell helpers
    # ==================================================================

    def wait_for_process_exit(self, exe_name: str) -> None:
        """Block until the given process name is no longer running."""
        while any(p.name().lower() == exe_name.lower() for p in psutil.process_iter()):
            time.sleep(0.5)

    def shell_execute(self, exe_path: str, args: str = "", workdir: str | None = None) -> None:
        ctypes.windll.shell32.ShellExecuteW(
            None,
            "open",
            exe_path,
            args,
            workdir,
            1,
        )

    def shell_execute_elevated(self, exe_path: str, args: str = "", workdir: str | None = None) -> None:
        ctypes.windll.shell32.ShellExecuteW(
            None,
            "runas",
            exe_path,
            args,
            workdir,
            1,
        )

    def build_cod2_args(self, makelog: int, cullxmodel: int, map_name: str) -> str:
        """Args used for grid capture (r_vc_makelog)."""
        return (
            "+set developer 1 "
            "+set logfile 2 "
            "+set r_smc_enable 0 "
            "+set r_smp_backend 0 "
            "+set sv_pure 0 "
            "+set scr_dm_timelimit 0 "
            f"+set r_vc_makelog {makelog} "
            "+set r_vc_showlog 16 "
            f"+set r_cullxmodel {cullxmodel} "
            "+set com_introplayed 1 "
            f"+devmap {map_name}"
        )

    def build_runmap_args(self, map_name: str, extra_options: str = "") -> str:
        """Args matching cod2compiletools_runmap.bat (+ optional connectpaths etc.)."""
        parts = [
            "+set developer 1",
            "+set logfile 2",
            "+set monkeytoy 0",
            "+set thereisacow 1337",
            "+set com_introplayed 1",
            "+set sv_pure 0",
        ]
        if self._is_mp(map_name):
            parts.append("+set g_gametype dm")
        if extra_options.strip():
            parts.append(extra_options.strip())
        parts.append(f"+devmap {map_name}")
        return " ".join(parts)

    # ==================================================================
    # Grid file shuttle
    # ==================================================================

    def on_start_grid(self) -> None:
        checked = self._require_root_and_map()
        if not checked:
            return
        root, map_name = checked

        exe_path = self._exe_path(map_name)
        if not exe_path or not exe_path.is_file():
            QtWidgets.QMessageBox.warning(
                self,
                "Missing Executable",
                f"Could not find {self._exe_name(map_name)} in:\n{root}",
            )
            return

        grid_mode = self.combo_grid.currentText()
        if grid_mode == "Edit Existing Grid":
            makelog = 2
        elif grid_mode == "Make New Grid":
            makelog = 1
        else:
            QtWidgets.QMessageBox.warning(
                self,
                "Invalid Grid Mode",
                "Please select a valid grid mode.",
            )
            return

        cullxmodel = 0 if self.chk_models_collect_dots.isChecked() else 1
        args = self.build_cod2_args(makelog, cullxmodel, map_name)

        source_grid = self._grid_source(map_name)
        dest_grid = self._grid_for_game(map_name)
        if not source_grid or not dest_grid:
            return

        self._ensure_main_maps_dirs()
        dest_grid.parent.mkdir(parents=True, exist_ok=True)

        if source_grid.exists():
            shutil.copy2(source_grid, dest_grid)
        else:
            dest_grid.write_text("", encoding="utf-8")

        self._append_console(f"[GRID LAUNCH] {exe_path} {args}")
        time.sleep(1.5)

        self.shell_execute(str(exe_path), args, str(root))
        self.wait_for_process_exit(exe_path.name)

        if dest_grid.exists():
            source_grid.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(dest_grid), str(source_grid))

        if dest_grid.exists():
            dest_grid.unlink()

        self._append_console("[GRID] finished — grid moved back to map_source")

    # ==================================================================
    # Compile pipeline
    # ==================================================================

    def _append_console(self, text: str) -> None:
        self.console.appendPlainText(text)
        sb = self.console.verticalScrollBar()
        sb.setValue(sb.maximum())
        if self._console_popout is not None:
            self._console_popout.appendPlainText(text)
            sb = self._console_popout.verticalScrollBar()
            sb.setValue(sb.maximum())

    def _clear_console(self) -> None:
        self.console.clear()
        if self._console_popout is not None:
            self._console_popout.clear()

    def _show_console_window(self) -> None:
        if self._console_window is not None:
            self._console_window.show()
            self._console_window.raise_()
            self._console_window.activateWindow()
            return

        window = QtWidgets.QDialog(self)
        window.setWindowTitle("Compile Console")
        window.setMinimumSize(500, 250)
        window.resize(900, 500)
        window.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose)

        layout = QtWidgets.QVBoxLayout(window)
        console = QtWidgets.QPlainTextEdit(window)
        console.setReadOnly(True)
        console.setMaximumBlockCount(5000)
        console.setStyleSheet(self.console.styleSheet())
        console.setPlainText(self.console.toPlainText())
        layout.addWidget(console)

        button_row = QtWidgets.QHBoxLayout()
        button_row.addStretch()
        clear_button = QtWidgets.QPushButton("Clear", window)
        clear_button.clicked.connect(self._clear_console)
        button_row.addWidget(clear_button)
        close_button = QtWidgets.QPushButton("Close", window)
        close_button.clicked.connect(window.close)
        button_row.addWidget(close_button)
        layout.addLayout(button_row)

        self._console_window = window
        self._console_popout = console
        window.destroyed.connect(self._on_console_window_destroyed)
        window.show()

    def _on_console_window_destroyed(self) -> None:
        self._console_window = None
        self._console_popout = None

    def _run_map_or_connect_paths(self, map_name: str, connect_paths: bool, run_map: bool) -> None:
        root = self._cod2_root()
        exe_path = self._exe_path(map_name)
        if not root or not exe_path:
            return

        if connect_paths:
            extra = "+set g_connectpaths 1" if run_map else "+set g_connectpaths 2"
            args = self.build_runmap_args(map_name, extra)
        elif run_map:
            args = self.build_runmap_args(map_name)
        else:
            return

        self._append_console(f"[RUNMAP] {exe_path} {args}")
        self.shell_execute(str(exe_path), args, str(root))
        if connect_paths and not run_map:
            self.wait_for_process_exit(exe_path.name)

    def on_run_selected(self) -> None:
        checked = self._require_root_and_map()
        if not checked:
            return
        _, map_name = checked
        self._append_console(f"=== Run map {map_name} ===")
        self._run_map_or_connect_paths(map_name, connect_paths=False, run_map=True)

    def on_compile(self) -> None:
        if self._worker is not None and self._worker.isRunning():
            QtWidgets.QMessageBox.information(
                self, "Busy", "A compile is already running."
            )
            return

        checked = self._require_root_and_map()
        if not checked:
            return
        _, map_name = checked

        opts = self.get_compile_args()
        if not opts:
            return

        if opts["do_vis"] and not self._is_mp(map_name):
            QtWidgets.QMessageBox.warning(
                self,
                "VIS unavailable",
                "VIS compilation is only available for multiplayer maps.",
            )
            return

        if not (
            opts["do_bsp"]
            or opts["do_vis"]
            or opts["do_light"]
            or opts["do_paths"]
            or opts["run_map"]
        ):
            QtWidgets.QMessageBox.information(
                self, "Nothing to do", "Select at least one compile/run option."
            )
            return

        self.console.clear()
        self._append_console(f"=== Compile {map_name} ===")
        self.btn_compile.setEnabled(False)
        self._active_compile_opts = opts.copy()
        self._active_compile_map = map_name

        self._worker = CompileWorker(self, map_name, opts)
        self._worker.log_line.connect(self._append_console)
        self._worker.finished_ok.connect(self._on_compile_finished_ok)
        self._worker.finished_error.connect(self._on_compile_finished_error)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.start()

    def _on_compile_finished_ok(self) -> None:
        self.btn_compile.setEnabled(True)
        opts = self._active_compile_opts
        map_name = self._active_compile_map
        self._append_console("=== Compile finished OK ===")
        if opts and (opts["do_paths"] or opts["run_map"]):
            self._run_map_or_connect_paths(
                map_name,
                connect_paths=opts["do_paths"],
                run_map=opts["run_map"],
            )



    def _on_compile_finished_error(self, message: str) -> None:
        self.btn_compile.setEnabled(True)
        self._append_console(f"=== ERROR: {message} ===")
        QtWidgets.QMessageBox.warning(self, "Compile failed", message)

    def _on_worker_finished(self) -> None:
        self.btn_compile.setEnabled(True)
        self._worker = None
        self._active_compile_opts = None
        self._active_compile_map = ""

    # ==================================================================
    # UI construction
    # ==================================================================

    def _build_ui(self) -> None:
        map_group = QtWidgets.QGroupBox("Map to Compile", self)
        map_layout = QtWidgets.QHBoxLayout(map_group)

        map_layout.addWidget(QtWidgets.QLabel("Map:"))
        self.map_combo = QtWidgets.QComboBox(self)
        self.map_combo.setEditable(True)
        self.map_combo.setMinimumWidth(220)
        map_layout.addWidget(self.map_combo)

        refresh_btn = QtWidgets.QPushButton("Refresh maps")
        refresh_btn.clicked.connect(self.refresh_maps)
        map_layout.addWidget(refresh_btn)

        self.btn_run_selected = QtWidgets.QPushButton("Run Selected")
        self.btn_run_selected.clicked.connect(self.on_run_selected)
        map_layout.addWidget(self.btn_run_selected)

        self.layout.addWidget(map_group)

        options_row = QtWidgets.QHBoxLayout()

        compile_group = QtWidgets.QGroupBox("Compile", self)
        compile_layout = QtWidgets.QVBoxLayout(compile_group)

        self.chk_compile_bsp = QtWidgets.QCheckBox("Compile BSP")
        compile_layout.addWidget(self.chk_compile_bsp)

        self.chk_compile_vis = QtWidgets.QCheckBox("Compile -Vis (Multiplayer Only)")
        compile_layout.addWidget(self.chk_compile_vis)

        self.chk_verbosebspvis = QtWidgets.QCheckBox("Verbose")
        compile_layout.addWidget(self.chk_verbosebspvis)

        self.chk_compile_lighting = QtWidgets.QCheckBox("Compile Lighting")
        compile_layout.addWidget(self.chk_compile_lighting)

        self.chk_connect_paths = QtWidgets.QCheckBox("Connect Paths")
        compile_layout.addWidget(self.chk_connect_paths)

        self.chk_run_map = QtWidgets.QCheckBox("Run Map When Done")
        compile_layout.addWidget(self.chk_run_map)

        bsp_label = QtWidgets.QLabel("BSP Options")
        font = bsp_label.font()
        font.setBold(True)
        bsp_label.setFont(font)
        compile_layout.addWidget(bsp_label)

        bsp_grid = QtWidgets.QGridLayout()
        bsp_grid.setContentsMargins(10, 0, 0, 0)

        self.chk_onlyents = QtWidgets.QCheckBox("onlyents")
        bsp_grid.addWidget(self.chk_onlyents, 0, 0)

        self.chk_blocksize = QtWidgets.QCheckBox("blocksize")
        bsp_grid.addWidget(self.chk_blocksize, 1, 0)
        self.spin_blocksize = QtWidgets.QSpinBox()
        self.spin_blocksize.setRange(64, 8192)
        self.spin_blocksize.setValue(1024)
        bsp_grid.addWidget(self.spin_blocksize, 1, 1)

        self.chk_samplescale = QtWidgets.QCheckBox("samplescale")
        bsp_grid.addWidget(self.chk_samplescale, 2, 0)
        self.edit_samplescale = QtWidgets.QLineEdit()
        self.edit_samplescale.setMaximumWidth(60)
        bsp_grid.addWidget(self.edit_samplescale, 2, 1)

        compile_layout.addLayout(bsp_grid)
        compile_layout.addStretch()

        compile_layout.addWidget(QtWidgets.QLabel("custom command line options"))
        self.edit_bsp_custom = QtWidgets.QLineEdit("")
        compile_layout.addWidget(self.edit_bsp_custom)

        options_row.addWidget(compile_group)

        light_group = QtWidgets.QGroupBox("Light Options", self)
        light_layout = QtWidgets.QVBoxLayout(light_group)

        light_grid = QtWidgets.QGridLayout()

        self.chk_fast = QtWidgets.QCheckBox("fast")
        light_grid.addWidget(self.chk_fast, 0, 0)

        self.chk_extra = QtWidgets.QCheckBox("extra")
        light_grid.addWidget(self.chk_extra, 1, 0)

        self.chk_verbose = QtWidgets.QCheckBox("verbose")
        light_grid.addWidget(self.chk_verbose, 2, 0)

        self.chk_modelshadow = QtWidgets.QCheckBox("ModelShadow")
        light_grid.addWidget(self.chk_modelshadow, 3, 0)

        self.chk_nomodelshadow = QtWidgets.QCheckBox("NoModelShadow")
        light_grid.addWidget(self.chk_nomodelshadow, 4, 0)
        self.chk_modelshadow.toggled.connect(self._sync_shadow_options)
        self.chk_nomodelshadow.toggled.connect(self._sync_shadow_options)

        self.chk_dumpoptions = QtWidgets.QCheckBox("DumpOptions")
        light_grid.addWidget(self.chk_dumpoptions, 5, 0)

        self.chk_traces = QtWidgets.QCheckBox("traces")
        light_grid.addWidget(self.chk_traces, 0, 1)
        self.spin_traces = QtWidgets.QSpinBox()
        self.spin_traces.setRange(1, 9999)
        self.spin_traces.setValue(128)
        light_grid.addWidget(self.spin_traces, 0, 2)
        self.lbl_traces_default = QtWidgets.QLabel("default 32")
        font = self.lbl_traces_default.font()
        font.setPointSize(font.pointSize() - 2)
        self.lbl_traces_default.setFont(font)
        light_grid.addWidget(self.lbl_traces_default, 1, 2)

        self.chk_bouncefraction = QtWidgets.QCheckBox("bouncefraction")
        light_grid.addWidget(self.chk_bouncefraction, 2, 1)
        self.edit_bouncefraction = QtWidgets.QLineEdit("")
        self.edit_bouncefraction.setMaximumWidth(60)
        light_grid.addWidget(self.edit_bouncefraction, 2, 2)
        self.lbl_bouncefraction_default = QtWidgets.QLabel("default 0.6")
        font = self.lbl_bouncefraction_default.font()
        font.setPointSize(font.pointSize() - 2)
        self.lbl_bouncefraction_default.setFont(font)
        light_grid.addWidget(self.lbl_bouncefraction_default, 3, 2)

        self.chk_jitter = QtWidgets.QCheckBox("jitter")
        light_grid.addWidget(self.chk_jitter, 4, 1)
        self.edit_jitter = QtWidgets.QLineEdit()
        self.edit_jitter.setMaximumWidth(60)
        light_grid.addWidget(self.edit_jitter, 4, 2)
        self.lbl_jitter_default = QtWidgets.QLabel("default 0.75")
        font = self.lbl_jitter_default.font()
        font.setPointSize(font.pointSize() - 2)
        self.lbl_jitter_default.setFont(font)
        light_grid.addWidget(self.lbl_jitter_default, 5, 2)

        light_layout.addLayout(light_grid)
        light_layout.addStretch()

        light_layout.addWidget(QtWidgets.QLabel("custom command line options"))
        self.edit_light_custom = QtWidgets.QLineEdit("")
        light_layout.addWidget(self.edit_light_custom)

        options_row.addWidget(light_group)
        scroll_widget = QtWidgets.QWidget()
        scroll_widget.setLayout(options_row)

        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        scroll_area.setVerticalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )

        self.layout.addWidget(scroll_area)

        btn_row = QtWidgets.QHBoxLayout()
        btn_row.addStretch()
        self.btn_compile = QtWidgets.QPushButton("Compile")
        self.btn_compile.setMinimumWidth(100)
        self.btn_compile.clicked.connect(self.on_compile)
        btn_row.addWidget(self.btn_compile)
        self.layout.addLayout(btn_row)

        grid_group = QtWidgets.QGroupBox("Grid File", self)
        grid_layout = QtWidgets.QHBoxLayout(grid_group)

        self.chk_models_collect_dots = QtWidgets.QCheckBox("models collect dots")
        grid_layout.addWidget(self.chk_models_collect_dots)

        self.combo_grid = QtWidgets.QComboBox()
        self.combo_grid.addItems(["Edit Existing Grid", "Make New Grid"])
        self.combo_grid.setMinimumWidth(140)
        grid_layout.addWidget(self.combo_grid)

        self.btn_start_grid = QtWidgets.QPushButton("Start Grid")
        self.btn_start_grid.clicked.connect(self.on_start_grid)
        grid_layout.addWidget(self.btn_start_grid)

        grid_layout.addStretch()
        self.layout.addWidget(grid_group)

        option_tooltips = {
            self.chk_compile_bsp: (
                "Build the map's BSP with cod2map, generating the compiled map geometry.\n"
                "Run this before VIS or lighting when the map geometry has changed."
            ),
            self.chk_compile_vis: (
                "Run cod2map's visibility (VIS) pass for multiplayer maps.\n"
                "This option is rejected for single-player maps; rebuild BSP first when geometry changed."
            ),
            self.chk_verbosebspvis: (
                "Pass -v to cod2map during BSP compilation for more detailed output.\n"
                "Does not change quality; normally leave off unless diagnosing a compile."
            ),
            self.chk_compile_lighting: (
                "Build map lighting with cod2rad.\n"
                "Compile BSP first after geometry changes. Use Fast for previews or Extra for slower, higher-quality lighting."
            ),
            self.chk_connect_paths: (
                "After the compile worker finishes, launch the map with g_connectpaths enabled.\n"
                "Use to rebuild navigation paths; without Run Map, the tool uses the connect-paths-only launch mode."
            ),
            self.chk_run_map: (
                "Launch the selected map after the compile worker finishes.\n"
                "Can also be selected by itself to launch without rebuilding BSP, VIS, or lighting."
            ),
            self.chk_onlyents: (
                "Pass -onlyEnts to update entity data without a full geometry rebuild.\n"
                "Use for entity-only edits; brush geometry is not rebuilt, and model-shadow results may remain stale."
            ),
            self.chk_blocksize: (
                "Enable the cod2map -blockSize option to control BSP subdivision size.\n"
                "UI accepts 64-8192 units; 512-1024 is a practical starting range. UI default: 1024."
            ),
            self.spin_blocksize: (
                "BSP block size passed to cod2map with -blockSize.\n"
                "UI range: 64-8192 units. Try 512-1024 for typical maps; smaller blocks can increase subdivision. Default: 1024."
            ),
            self.chk_samplescale: (
                "Enable the cod2map -sampleScale option. Leave its value blank to omit the flag.\n"
                "Use 1.0 as a neutral starting point; 2-4 can speed test builds with coarser lightmap sampling."
            ),
            self.edit_samplescale: (
                "Value passed to cod2map as -sampleScale. Must be a positive number.\n"
                "Recommended starting range: 0.5-4.0. Around 1.0 is neutral; higher values generally mean coarser sampling."
            ),
            self.edit_bsp_custom: (
                "Additional cod2map command-line arguments, appended after the selected BSP options.\n"
                "Enter space-separated flags and values. The tool does not validate them; supported options depend on your CoD2 tools."
            ),
            self.chk_fast: (
                "Pass -fast to cod2rad for a quicker lighting build with reduced quality.\n"
                "Useful for iteration and preview maps; turn off for final lighting. No numeric value."
            ),
            self.chk_extra: (
                "Pass -extra to cod2rad for a slower, higher-quality lighting build.\n"
                "Use for final results when compile time is acceptable. No numeric value."
            ),
            self.chk_verbose: (
                "Pass -verbose to cod2rad for additional lighting compiler output.\n"
                "Useful for troubleshooting; it does not select a quality level."
            ),
            self.chk_modelshadow: (
                "Pass -modelshadow to include model shadows in the lighting build.\n"
                "Mutually exclusive with NoModelShadow; enabling one disables the other."
            ),
            self.chk_nomodelshadow: (
                "Pass -nomodelshadow to exclude model shadows from the lighting build.\n"
                "Mutually exclusive with ModelShadow; enabling one disables the other."
            ),
            self.chk_dumpoptions: (
                "Pass -dumpoptions to cod2rad to print its active option values.\n"
                "Useful for checking compiler defaults and troubleshooting; no numeric value."
            ),
            self.chk_traces: (
                "Override the number of lighting traces per sample point. Higher values can improve quality but increase build time.\n"
                "UI range: 1-9999. Compiler default shown here: 32; practical tuning range: 64-256."
            ),
            self.spin_traces: (
                "Trace count passed to cod2rad with -traces. Higher values trade longer compile times for more lighting samples.\n"
                "UI range: 1-9999. The compiler default is 32; 64-256 is a practical tuning range. UI starts at 128."
            ),
            self.lbl_traces_default: (
                "The cod2rad trace default displayed by this UI: 32.\n"
                "When traces is enabled, the spin box value is used instead."
            ),
            self.chk_bouncefraction: (
                "Override cod2rad's bounce fraction, which influences how much bounced light contributes.\n"
                "Typical useful range: 0.3-0.6. Compiler default shown here: 0.6; leave the value blank to use the default."
            ),
            self.edit_bouncefraction: (
                "Value passed to cod2rad as -bouncefraction. Typical range: 0.0-1.0; the UI does not enforce a bound.\n"
                "Around 0.3-0.6 is a practical tuning range. Leave blank to omit the override; compiler default shown here: 0.6."
            ),
            self.lbl_bouncefraction_default: (
                "The cod2rad bouncefraction default displayed by this UI: 0.6.\n"
                "Leave the value field blank to use the compiler default."
            ),
            self.chk_jitter: (
                "Override cod2rad's sample jitter, which varies trace sample positions.\n"
                "Typical useful range: 0.0-1.0. Compiler default shown here: 0.75; leave the value blank to use the default."
            ),
            self.edit_jitter: (
                "Value passed to cod2rad as -jitter. Typical range: 0.0-1.0; the UI does not enforce a bound.\n"
                "Leave blank to omit the override; compiler default shown here: 0.75."
            ),
            self.lbl_jitter_default: (
                "The cod2rad jitter default displayed by this UI: 0.75.\n"
                "Leave the value field blank to use the compiler default."
            ),
            self.edit_light_custom: (
                "Additional cod2rad command-line arguments, appended after the selected lighting options.\n"
                "Enter space-separated flags and values. The tool does not validate them; supported options depend on your CoD2 tools."
            ),
            self.chk_models_collect_dots: (
                "During grid capture, set r_cullxmodel to 0 so xmodel dots are included.\n"
                "Enable if model points are missing from the grid; leave off for the usual culled-model capture."
            ),
            self.combo_grid: (
                "Choose the grid capture mode. Edit Existing Grid uses r_vc_makelog 2; Make New Grid uses 1.\n"
                "The game writes the capture during the session, and the tool moves the resulting .grid back to map_source."
            ),
        }
        for widget, description in option_tooltips.items():
            widget.setToolTip(description)

        console_group = QtWidgets.QGroupBox("Console", self)
        console_group.setMinimumHeight(150)
        console_group.setMaximumHeight(150)
        console_layout = QtWidgets.QVBoxLayout(console_group)

        self.console = QtWidgets.QPlainTextEdit(self)
        self.console.setReadOnly(True)
        self.console.setMaximumBlockCount(5000)
        self.console.setStyleSheet(
            "QPlainTextEdit {"
            "  background: #1e1e1e;"
            "  color: #d4d4d4;"
            "  font-family: Consolas, 'Courier New', monospace;"
            "  font-size: 12px;"
            "}"
        )

        console_layout.addWidget(self.console)

        clear_row = QtWidgets.QHBoxLayout()
        clear_row.addStretch()
        self.btn_clear_console = QtWidgets.QPushButton("Clear")
        self.btn_clear_console.clicked.connect(self._clear_console)
        clear_row.addWidget(self.btn_clear_console)
        self.btn_popout_console = QtWidgets.QPushButton("Pop out")
        self.btn_popout_console.clicked.connect(self._show_console_window)
        clear_row.addWidget(self.btn_popout_console)
        console_layout.addLayout(clear_row)

        self.layout.addWidget(console_group)

    # ==================================================================
    # Settings persistence
    # ==================================================================

    def _connect_settings_signals(self) -> None:
        self.map_combo.currentTextChanged.connect(self._on_map_changed)

        for chk in (
            self.chk_compile_bsp,
            self.chk_compile_vis,
            self.chk_verbosebspvis,
            self.chk_compile_lighting,
            self.chk_connect_paths,
            self.chk_run_map,
            self.chk_onlyents,
            self.chk_blocksize,
            self.chk_samplescale,
            self.chk_fast,
            self.chk_extra,
            self.chk_verbose,
            self.chk_modelshadow,
            self.chk_nomodelshadow,
            self.chk_dumpoptions,
            self.chk_traces,
            self.chk_bouncefraction,
            self.chk_jitter,
            self.chk_models_collect_dots,
        ):
            chk.toggled.connect(self._on_setting_changed)

        self.spin_blocksize.valueChanged.connect(self._on_setting_changed)
        self.spin_traces.valueChanged.connect(self._on_setting_changed)

        for edit in (
            self.edit_samplescale,
            self.edit_bsp_custom,
            self.edit_bouncefraction,
            self.edit_jitter,
            self.edit_light_custom,
        ):
            edit.textChanged.connect(self._on_setting_changed)

        self.combo_grid.currentTextChanged.connect(self._on_setting_changed)

    def _default_settings(self) -> dict:
        return {
            "compile_bsp": False,
            "compile_vis": False,
            "verbosebspvis": False,
            "compile_lighting": False,
            "connect_paths": False,
            "run_map": False,
            "onlyents": False,
            "blocksize": False,
            "blocksize_value": 1024,
            "samplescale": False,
            "samplescale_value": "",
            "bsp_custom": "",
            "fast": False,
            "extra": False,
            "verbose": False,
            "modelshadow": False,
            "nomodelshadow": False,
            "dumpoptions": False,
            "traces": False,
            "traces_value": 128,
            "bouncefraction": False,
            "bouncefraction_value": "",
            "jitter": False,
            "jitter_value": "",
            "light_custom": "",
            "models_collect_dots": False,
            "grid_mode": "Edit Existing Grid",
        }

    def _collect_settings(self) -> dict:
        return {
            "compile_bsp": self.chk_compile_bsp.isChecked(),
            "compile_vis": self.chk_compile_vis.isChecked(),
            "verbosebspvis": self.chk_verbosebspvis.isChecked(),
            "compile_lighting": self.chk_compile_lighting.isChecked(),
            "connect_paths": self.chk_connect_paths.isChecked(),
            "run_map": self.chk_run_map.isChecked(),
            "onlyents": self.chk_onlyents.isChecked(),
            "blocksize": self.chk_blocksize.isChecked(),
            "blocksize_value": self.spin_blocksize.value(),
            "samplescale": self.chk_samplescale.isChecked(),
            "samplescale_value": self.edit_samplescale.text(),
            "bsp_custom": self.edit_bsp_custom.text(),
            "fast": self.chk_fast.isChecked(),
            "extra": self.chk_extra.isChecked(),
            "verbose": self.chk_verbose.isChecked(),
            "modelshadow": self.chk_modelshadow.isChecked(),
            "nomodelshadow": self.chk_nomodelshadow.isChecked(),
            "dumpoptions": self.chk_dumpoptions.isChecked(),
            "traces": self.chk_traces.isChecked(),
            "traces_value": self.spin_traces.value(),
            "bouncefraction": self.chk_bouncefraction.isChecked(),
            "bouncefraction_value": self.edit_bouncefraction.text(),
            "jitter": self.chk_jitter.isChecked(),
            "jitter_value": self.edit_jitter.text(),
            "light_custom": self.edit_light_custom.text(),
            "models_collect_dots": self.chk_models_collect_dots.isChecked(),
            "grid_mode": self.combo_grid.currentText(),
        }

    def _apply_settings(self, settings: dict) -> None:
        defaults = self._default_settings()
        s = {**defaults, **(settings or {})}

        self._loading_settings = True
        try:
            self.chk_compile_bsp.setChecked(bool(s["compile_bsp"]))
            self.chk_compile_vis.setChecked(bool(s["compile_vis"]))
            self.chk_verbosebspvis.setChecked(bool(s["verbosebspvis"]))
            self.chk_compile_lighting.setChecked(bool(s["compile_lighting"]))
            self.chk_connect_paths.setChecked(bool(s["connect_paths"]))
            self.chk_run_map.setChecked(bool(s["run_map"]))

            self.chk_onlyents.setChecked(bool(s["onlyents"]))
            self.chk_blocksize.setChecked(bool(s["blocksize"]))
            self.spin_blocksize.setValue(int(s["blocksize_value"]))
            self.chk_samplescale.setChecked(bool(s["samplescale"]))
            self.edit_samplescale.setText(str(s["samplescale_value"]))
            self.edit_bsp_custom.setText(str(s["bsp_custom"]))

            self.chk_fast.setChecked(bool(s["fast"]))
            self.chk_extra.setChecked(bool(s["extra"]))
            self.chk_verbose.setChecked(bool(s["verbose"]))
            self.chk_modelshadow.setChecked(bool(s["modelshadow"]))
            self.chk_nomodelshadow.setChecked(bool(s["nomodelshadow"]))
            self.chk_dumpoptions.setChecked(bool(s["dumpoptions"]))
            self.chk_traces.setChecked(bool(s["traces"]))
            self.spin_traces.setValue(int(s["traces_value"]))
            self.chk_bouncefraction.setChecked(bool(s["bouncefraction"]))
            self.edit_bouncefraction.setText(str(s["bouncefraction_value"]))
            self.chk_jitter.setChecked(bool(s["jitter"]))
            self.edit_jitter.setText(str(s["jitter_value"]))
            self.edit_light_custom.setText(str(s["light_custom"]))

            self.chk_models_collect_dots.setChecked(bool(s["models_collect_dots"]))
            grid_mode = str(s["grid_mode"])
            idx = self.combo_grid.findText(grid_mode)
            self.combo_grid.setCurrentIndex(idx if idx >= 0 else 0)
            self._sync_shadow_options()
        finally:
            self._loading_settings = False

    def _sync_shadow_options(self) -> None:
        if self.chk_modelshadow.isChecked() and self.chk_nomodelshadow.isChecked():
            self.chk_nomodelshadow.setChecked(False)
        self.chk_nomodelshadow.setDisabled(self.chk_modelshadow.isChecked())
        self.chk_modelshadow.setDisabled(self.chk_nomodelshadow.isChecked())

    def _save_current_map_settings(self) -> None:
        mapname = self._current_map.strip()
        if not mapname or self._loading_settings:
            return
        all_settings = load_compile_settings()
        all_settings[mapname] = self._collect_settings()
        save_compile_settings(all_settings)

    def _load_map_settings(self, mapname: str) -> None:
        mapname = (mapname or "").strip()
        self._current_map = mapname
        if not mapname:
            self._apply_settings(self._default_settings())
            return
        all_settings = load_compile_settings()
        self._apply_settings(all_settings.get(mapname, self._default_settings()))

    def _on_map_changed(self, new_map: str) -> None:
        if self._current_map and self._current_map != new_map.strip():
            self._save_current_map_settings()
        self._load_map_settings(new_map)

    def _on_setting_changed(self, *args) -> None:
        if not self._loading_settings:
            self._save_current_map_settings()

    def refresh_maps(self, preferred_map: str | None = None) -> None:
        self._save_current_map_settings()
        path = self.cod2_path()
        if not path or not Path(path).is_dir():
            self.map_combo.blockSignals(True)
            self.map_combo.clear()
            self.map_combo.blockSignals(False)
            self._current_map = ""
            return
        maps = get_map_list(path)
        selected = self.populate_map_combo(
            self.map_combo,
            maps,
            preferred_map or self._current_map,
        )
        if selected:
            self._load_map_settings(selected)
        else:
            self._current_map = ""

    def get_compile_args(self) -> dict:
        """Return ready-to-use argument lists for the CoD2 compilers."""
        map_name = self._current_map_name()
        if not map_name:
            return {}

        bsp_args: list[str] = []
        if self.chk_verbosebspvis.isChecked():
            bsp_args.append("-v")
        if self.chk_onlyents.isChecked():
            bsp_args.append("-onlyEnts")
        if self.chk_blocksize.isChecked():
            bsp_args += ["-blockSize", str(self.spin_blocksize.value())]
        if self.chk_samplescale.isChecked() and self.edit_samplescale.text().strip():
            bsp_args += ["-sampleScale", self.edit_samplescale.text().strip()]
        bsp_args += self.edit_bsp_custom.text().split()

        light_args: list[str] = []
        if self.chk_fast.isChecked():
            light_args.append("-fast")
        if self.chk_extra.isChecked():
            light_args.append("-extra")
        if self.chk_verbose.isChecked():
            light_args.append("-verbose")
        if self.chk_modelshadow.isChecked():
            light_args.append("-modelshadow")
        if self.chk_nomodelshadow.isChecked():
            light_args.append("-nomodelshadow")
        if self.chk_dumpoptions.isChecked():
            light_args.append("-dumpoptions")
        if self.chk_traces.isChecked():
            light_args += ["-traces", str(self.spin_traces.value())]
        if self.chk_bouncefraction.isChecked() and self.edit_bouncefraction.text().strip():
            light_args += ["-bouncefraction", self.edit_bouncefraction.text().strip()]
        if self.chk_jitter.isChecked() and self.edit_jitter.text().strip():
            light_args += ["-jitter", self.edit_jitter.text().strip()]
        light_args += self.edit_light_custom.text().split()

        return {
            "map": map_name,
            "do_bsp": self.chk_compile_bsp.isChecked(),
            "do_vis": self.chk_compile_vis.isChecked(),
            "do_light": self.chk_compile_lighting.isChecked(),
            "do_paths": self.chk_connect_paths.isChecked(),
            "run_map": self.chk_run_map.isChecked(),
            "bsp_args": bsp_args,
            "light_args": light_args,
        }