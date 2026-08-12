"""Legacy script tabs for FX, sound aliases, SUN files, and basic map resources."""

from __future__ import annotations
import json
import re
from pathlib import Path
from typing import Dict, List

from PyQt6 import QtWidgets

from config import DEFAULT_CSV_CONTENT
from helpers import (
    map_csv_path,
    map_arena_path,
    map_gsc_path,
    map_sun_path,
    map_soundaliases_path,
)
from .qt_tab_mixin import QtTabMixin


class FxGscTab(QtTabMixin, QtWidgets.QWidget):
    def __init__(self, app: QtWidgets.QWidget) -> None:
        super().__init__(app)
        self._build_ui()
        self.update_missing_status()

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        self.missing_label = QtWidgets.QLabel("")
        self.missing_label.setStyleSheet("color: #b00020; font-weight: 600;")
        layout.addWidget(self.missing_label)
        self.create_button = QtWidgets.QPushButton("Create missing FX GSC")
        self.create_button.clicked.connect(self.create_file_if_missing)
        layout.addWidget(self.create_button)

        content_layout = QtWidgets.QHBoxLayout()
        layout.addLayout(content_layout)

        left_col = QtWidgets.QWidget(self)
        left_layout = QtWidgets.QVBoxLayout(left_col)
        left_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.addWidget(left_col, 1)

        right_col = QtWidgets.QWidget(self)
        right_layout = QtWidgets.QVBoxLayout(right_col)
        right_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.addWidget(right_col, 1)

        precache_group = QtWidgets.QGroupBox("PrecacheFX()", self)
        precache_layout = QtWidgets.QVBoxLayout(precache_group)
        left_layout.addWidget(precache_group)
        row = QtWidgets.QHBoxLayout()
        self.precache_name = QtWidgets.QLineEdit(self)
        self.precache_path = QtWidgets.QLineEdit(self)
        row.addWidget(QtWidgets.QLabel("Effect name:"))
        row.addWidget(self.precache_name)
        row.addWidget(QtWidgets.QLabel("FX path:"))
        row.addWidget(self.precache_path)
        browse_btn = QtWidgets.QPushButton("Browse")
        browse_btn.clicked.connect(self.browse_fx)
        row.addWidget(browse_btn)
        add_btn = QtWidgets.QPushButton("Add effect")
        add_btn.clicked.connect(self._add_precache)
        row.addWidget(add_btn)
        precache_layout.addLayout(row)
        self.precache_list = QtWidgets.QListWidget(self)
        precache_layout.addWidget(self.precache_list)

        precache_buttons = QtWidgets.QHBoxLayout()
        remove_precache_btn = QtWidgets.QPushButton("Remove selected")
        remove_precache_btn.clicked.connect(self._remove_selected_precache)
        clear_precache_btn = QtWidgets.QPushButton("Clear all")
        clear_precache_btn.clicked.connect(self._clear_precache_list)
        precache_buttons.addWidget(remove_precache_btn)
        precache_buttons.addWidget(clear_precache_btn)
        precache_layout.addLayout(precache_buttons)

        scr_group = QtWidgets.QGroupBox("scr_sound", self)
        scr_layout = QtWidgets.QVBoxLayout(scr_group)
        left_layout.addWidget(scr_group)
        scr_row = QtWidgets.QHBoxLayout()
        self.scr_key = QtWidgets.QLineEdit(self)
        self.scr_value = QtWidgets.QLineEdit(self)
        scr_row.addWidget(QtWidgets.QLabel("Key:"))
        scr_row.addWidget(self.scr_key)
        scr_row.addWidget(QtWidgets.QLabel("Value:"))
        scr_row.addWidget(self.scr_value)
        add_scr = QtWidgets.QPushButton("Add scr_sound")
        add_scr.clicked.connect(self._add_scr)
        scr_row.addWidget(add_scr)
        scr_layout.addLayout(scr_row)
        self.scr_list = QtWidgets.QListWidget(self)
        scr_layout.addWidget(self.scr_list)

        scr_buttons = QtWidgets.QHBoxLayout()
        remove_scr_btn = QtWidgets.QPushButton("Remove selected")
        remove_scr_btn.clicked.connect(self._remove_selected_scr)
        clear_scr_btn = QtWidgets.QPushButton("Clear all")
        clear_scr_btn.clicked.connect(self._clear_scr_list)
        scr_buttons.addWidget(remove_scr_btn)
        scr_buttons.addWidget(clear_scr_btn)
        scr_layout.addLayout(scr_buttons)

        usage_group = QtWidgets.QGroupBox("Ambient FX / usage calls", self)
        usage_layout = QtWidgets.QVBoxLayout(usage_group)
        right_layout.addWidget(usage_group)
        self.usage_effect = QtWidgets.QLineEdit(self)
        self.usage_type = QtWidgets.QComboBox(self)
        self.usage_type.addItems(
            ["loopfx", "OneShotfx", "soundfx", "gunfireloopfx", "GrenadeExplosionfx"]
        )
        self.usage_params = QtWidgets.QLineEdit(self)
        usage_layout.addWidget(QtWidgets.QLabel("Effect/alias:"))
        usage_layout.addWidget(self.usage_effect)
        usage_layout.addWidget(QtWidgets.QLabel("Function:"))
        usage_layout.addWidget(self.usage_type)
        usage_layout.addWidget(QtWidgets.QLabel("Params:"))
        usage_layout.addWidget(self.usage_params)
        add_usage = QtWidgets.QPushButton("Add usage")
        add_usage.clicked.connect(self._add_usage)
        usage_layout.addWidget(add_usage)
        self.usage_list = QtWidgets.QListWidget(self)
        usage_layout.addWidget(self.usage_list)

        usage_buttons = QtWidgets.QHBoxLayout()
        remove_usage_btn = QtWidgets.QPushButton("Remove selected")
        remove_usage_btn.clicked.connect(self._remove_selected_usage)
        clear_usage_btn = QtWidgets.QPushButton("Clear all")
        clear_usage_btn.clicked.connect(self._clear_usage_list)
        usage_buttons.addWidget(remove_usage_btn)
        usage_buttons.addWidget(clear_usage_btn)
        usage_layout.addLayout(usage_buttons)

        right_layout.addWidget(QtWidgets.QLabel("Preview"))
        self.preview = QtWidgets.QPlainTextEdit(self)
        self.preview.setReadOnly(True)
        right_layout.addWidget(self.preview)

        self.save_button = QtWidgets.QPushButton("Save FX GSC")
        self.save_button.clicked.connect(self.save_files)
        layout.addWidget(self.save_button)
        self._refresh_preview()

    def _add_precache(self) -> None:
        name = self.precache_name.text().strip()
        path = self.precache_path.text().strip()
        if name and path:
            self.precache_list.addItem(f"{name} -> {path}")
            self.precache_name.clear()
            self.precache_path.clear()
            self._refresh_preview()

    def _add_scr(self) -> None:
        key = self.scr_key.text().strip()
        value = self.scr_value.text().strip()
        if key and value:
            self.scr_list.addItem(f"{key} -> {value}")
            self.scr_key.clear()
            self.scr_value.clear()
            self._refresh_preview()

    def _add_usage(self) -> None:
        effect = self.usage_effect.text().strip()
        func = self.usage_type.currentText().strip()
        params = self.usage_params.text().strip()
        if effect and func:
            self.usage_list.addItem(f"{effect} | {func} | {params}")
            self.usage_effect.clear()
            self.usage_params.clear()
            self._refresh_preview()

    def _remove_selected_precache(self) -> None:
        self.remove_selected_list_items(self.precache_list)
        self._refresh_preview()

    def _clear_precache_list(self) -> None:
        if self.confirm_clear_list(
            self.precache_list,
            "Clear effects",
            "Remove all precache effects from the current FX script?",
        ):
            self._refresh_preview()

    def _remove_selected_scr(self) -> None:
        self.remove_selected_list_items(self.scr_list)
        self._refresh_preview()

    def _clear_scr_list(self) -> None:
        if self.confirm_clear_list(
            self.scr_list,
            "Clear scr_sound",
            "Remove all scr_sound entries from the current FX script?",
        ):
            self._refresh_preview()

    def _remove_selected_usage(self) -> None:
        self.remove_selected_list_items(self.usage_list)
        self._refresh_preview()

    def _clear_usage_list(self) -> None:
        if self.confirm_clear_list(
            self.usage_list,
            "Clear usage calls",
            "Remove all ambient FX / usage calls from the current FX script?",
        ):
            self._refresh_preview()

    def _refresh_preview(self) -> None:
        mapname = self.map_name() or "mapname"
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
            "{",
        ]
        for idx in range(self.precache_list.count()):
            text = self.precache_list.item(idx).text()
            name, path = [part.strip() for part in text.split("->", 1)]
            lines.append(f'    level._effect["{name}"] = loadfx("{path}");')
        for idx in range(self.scr_list.count()):
            text = self.scr_list.item(idx).text()
            key, value = [part.strip() for part in text.split("->", 1)]
            lines.append(f'    level.scr_sound["{key}"] = "{value}";')
        lines.append("}")
        lines.append("")
        lines.append("ambientFX()")
        lines.append("{")
        for idx in range(self.usage_list.count()):
            text = self.usage_list.item(idx).text()
            effect, func, params = [part.strip() for part in text.split("|", 2)]
            if func == "soundfx":
                lines.append(f'    maps\\mp\\_fx::soundfx("{effect}", {params});')
            else:
                lines.append(f'    maps\\mp\\_fx::{func}("{effect}", {params});')
        lines.append("}")
        self.preview.setPlainText("\n".join(lines))

    def _parse_fx_gsc_content(self, content: str) -> None:
        self.precache_list.clear()
        self.scr_list.clear()
        self.usage_list.clear()

        for line in content.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("//"):
                continue

            precache_match = re.match(
                r'level\._effect\["([^\"]+)"\]\s*=\s*loadfx\(\s*"([^\"]+)"\s*\)\s*;',
                stripped,
            )
            if precache_match:
                self.precache_list.addItem(
                    f"{precache_match.group(1)} -> {precache_match.group(2)}"
                )
                continue

            scr_match = re.match(
                r'level\.scr_sound\["([^\"]+)"\]\s*=\s*"([^\"]*)"\s*;',
                stripped,
            )
            if scr_match:
                self.scr_list.addItem(f"{scr_match.group(1)} -> {scr_match.group(2)}")
                continue

            usage_match = re.match(
                r'maps\\mp\\_fx::([A-Za-z0-9_]+)\(\s*"([^\"]*)"\s*,\s*(.*)\)\s*;',
                stripped,
            )
            if usage_match:
                func = usage_match.group(1)
                effect = usage_match.group(2)
                params = usage_match.group(3).strip()
                self.usage_list.addItem(f"{effect} | {func} | {params}")
                continue

    def browse_fx(self) -> None:
        cod2_path_str = self.cod2_path()
        if not cod2_path_str:
            QtWidgets.QMessageBox.warning(self, "No CoD2 Path", "Set the CoD2 folder first.")
            return
        initial_dir = Path(cod2_path_str) / "main" / "fx"
        selected, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Select FX Effect File (.efx)",
            str(initial_dir if initial_dir.exists() else Path(cod2_path_str)),
            "FX Effect Files (*.efx);;All Files (*.*)",
        )
        if selected:
            full_path = Path(selected)
            base_path = Path(cod2_path_str) / "main"
            try:
                rel_path = full_path.relative_to(base_path)
                fx_path = str(rel_path.with_suffix("")).replace("\\", "/")
                self.precache_path.setText(fx_path)
            except ValueError:
                QtWidgets.QMessageBox.warning(
                    self, "Invalid Path", "Choose a file inside the CoD2 main folder."
                )

    def update_missing_status(self) -> None:
        mapname = self.map_name()
        if not mapname:
            self.missing_label.setText("")
            self.create_button.setEnabled(False)
            return
        cod2 = Path(self.cod2_path())
        status = (
            self.app.check_missing_files(cod2, mapname)
            if hasattr(self.app, "check_missing_files")
            else {}
        )
        exists = bool(status.get("fx_gsc", {}).get("exists", False)) if status else False
        self.set_file_status(
            self.missing_label,
            self.create_button,
            exists,
            ok_text="FX GSC file exists ✓",
            missing_text=f"File missing: {mapname}_fx.gsc",
            create_button_text=f"Create {mapname}_fx.gsc",
        )
        if exists:
            self._load_file_if_exists(cod2, mapname)

    def _load_file_if_exists(self, cod2: Path, mapname: str) -> None:
        path = map_gsc_path(cod2, mapname, fx=True)
        if path.exists():
            content = path.read_text(encoding="utf-8")
            self._parse_fx_gsc_content(content)
            self._refresh_preview()

    def create_file_if_missing(self) -> None:
        mapname = self.map_name()
        if not mapname:
            return
        cod2 = Path(self.cod2_path())
        path = map_gsc_path(cod2, mapname, fx=True, for_write=True)
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
        self.update_missing_status()

    def save_files(self) -> None:
        mapname = self.map_name()
        if not mapname:
            QtWidgets.QMessageBox.warning(self, "No map", "Select a map first.")
            return
        cod2 = Path(self.cod2_path())
        path = map_gsc_path(cod2, mapname, fx=True, for_write=True)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.preview.toPlainText().strip() + "\n", encoding="utf-8")


class SunTab(QtTabMixin, QtWidgets.QWidget):
    def __init__(self, app: QtWidgets.QWidget) -> None:
        super().__init__(app)
        self.json_path = Path(__file__).resolve().parent.parent / "presets" / "sun_presets.json"
        self.sun_presets = self.load_sun_presets()
        self._build_ui()
        self.update_missing_status()

    def load_sun_presets(self) -> Dict[str, Dict[str, str]]:
        if not self.json_path.is_file():
            return {}
        try:
            with open(self.json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {
                    p.get("name"): p.get("values", {})
                    for p in data.get("presets", [])
                    if p.get("name")
                }
        except Exception:
            return {}

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        self.missing_label = QtWidgets.QLabel("")
        self.missing_label.setStyleSheet("color: #b00020; font-weight: 600;")
        layout.addWidget(self.missing_label)
        self.create_button = QtWidgets.QPushButton("Create missing SUN file")
        self.create_button.clicked.connect(self.create_file_if_missing)
        layout.addWidget(self.create_button)

        preset_group = QtWidgets.QGroupBox("Presets", self)
        preset_layout = QtWidgets.QVBoxLayout(preset_group)
        layout.addWidget(preset_group)
        row = QtWidgets.QHBoxLayout()
        self.preset_combo = QtWidgets.QComboBox(self)
        self.preset_combo.addItems(list(self.sun_presets.keys()))
        row.addWidget(QtWidgets.QLabel("Load preset:"))
        row.addWidget(self.preset_combo)
        load_btn = QtWidgets.QPushButton("Load")
        load_btn.clicked.connect(self.load_preset)
        row.addWidget(load_btn)
        save_btn = QtWidgets.QPushButton("Save current as preset")
        save_btn.clicked.connect(self.save_current_preset)
        row.addWidget(save_btn)
        preset_layout.addLayout(row)

        scroll = QtWidgets.QScrollArea(self)
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll)
        inner = QtWidgets.QWidget(self)
        inner_layout = QtWidgets.QFormLayout(inner)
        scroll.setWidget(inner)
        self.fields: Dict[str, QtWidgets.QLineEdit] = {}
        for name, default in [
            ("r_sunsprite_shader", "sun_trainyard"),
            ("r_sunsprite_size", "109.722"),
            ("r_sunflare_shader", "sun_flare_trainyard"),
            ("r_sunflare_min_size", "390.1"),
            ("r_sunflare_min_angle", "82.3608"),
            ("r_sunflare_max_size", "889.3"),
            ("r_sunflare_max_angle", "0"),
            ("r_sunflare_max_alpha", "0.45622"),
            ("r_sunflare_fadein", "0.2604"),
            ("r_sunflare_fadeout", "0.2992"),
            ("r_sunblind_min_angle", "62.4258"),
            ("r_sunblind_max_angle", "14.6015"),
            ("r_sunblind_max_darken", "0.23165"),
            ("r_sunblind_fadein", "0.5"),
            ("r_sunblind_fadeout", "1"),
            ("r_sunglare_min_angle", "20.7108"),
            ("r_sunglare_max_angle", "5.7933"),
            ("r_sunglare_max_lighten", "0.0930199"),
            ("r_sunglare_fadein", "0.7758"),
            ("r_sunglare_fadeout", "3"),
            ("r_sun_fx_position", "-38.6856 -53.8224 0"),
        ]:
            line = QtWidgets.QLineEdit(default, self)
            self.fields[name] = line
            inner_layout.addRow(name, line)
        save_btn = QtWidgets.QPushButton("Save SUN file")
        save_btn.clicked.connect(self.save_files)
        layout.addWidget(save_btn)

    def save_current_preset(self) -> None:
        name, ok = QtWidgets.QInputDialog.getText(self, "Save Preset", "Enter a preset name:")
        if not ok or not name.strip():
            return
        values = {
            key: line.text().strip()
            for key, line in self.fields.items()
            if line.text().strip()
        }
        self.sun_presets[name.strip()] = values
        self.json_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "presets": [
                {"name": preset_name, "values": vals}
                for preset_name, vals in sorted(self.sun_presets.items())
            ]
        }
        self.json_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        self.preset_combo.clear()
        self.preset_combo.addItems(list(self.sun_presets.keys()))
        QtWidgets.QMessageBox.information(self, "Saved", f"Saved preset: {name.strip()}")

    def load_preset(self) -> None:
        name = self.preset_combo.currentText().strip()
        if not name:
            return
        values = self.sun_presets.get(name, {})
        for field_name, line in self.fields.items():
            line.setText(values.get(field_name, ""))

    def save_files(self) -> None:
        mapname = self.map_name()
        if not mapname:
            QtWidgets.QMessageBox.warning(self, "No map", "Select a map first.")
            return
        cod2 = Path(self.cod2_path())
        path = map_sun_path(cod2, mapname, for_write=True)
        path.parent.mkdir(parents=True, exist_ok=True)
        lines = ["// Generated SUN file"]
        for name, line in self.fields.items():
            value = line.text().strip()
            if value:
                lines.append(f"{name} {value}")
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def update_missing_status(self) -> None:
        mapname = self.map_name()
        if not mapname:
            self.missing_label.setText("")
            self.create_button.setEnabled(False)
            return
        cod2 = Path(self.cod2_path())
        status = (
            self.app.check_missing_files(cod2, mapname)
            if hasattr(self.app, "check_missing_files")
            else {}
        )
        exists = bool(status.get("sun", {}).get("exists", False)) if status else False
        self.set_file_status(
            self.missing_label,
            self.create_button,
            exists,
            ok_text="SUN file exists ✓",
            missing_text=f"File missing: {mapname}.sun",
            create_button_text=f"Create {mapname}.sun",
        )
        if exists:
            self.load_from_file(cod2, mapname)

    def load_from_file(self, cod2_path: Path, mapname: str) -> None:
        path = map_sun_path(cod2_path, mapname)
        if not path.exists():
            return
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("//"):
                continue
            parts = line.split(None, 1)
            if len(parts) == 2 and parts[0] in self.fields:
                self.fields[parts[0]].setText(parts[1].strip())

    def create_file_if_missing(self) -> None:
        mapname = self.map_name()
        if not mapname:
            return
        cod2 = Path(self.cod2_path())
        path = map_sun_path(cod2, mapname, for_write=True)
        if path.exists():
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("// Generated SUN file\n", encoding="utf-8")
        self.update_missing_status()


class SoundAliasesTab(QtTabMixin, QtWidgets.QWidget):
    def __init__(self, app: QtWidgets.QWidget) -> None:
        super().__init__(app)
        self._build_ui()
        self.update_missing_status()

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        self.missing_label = QtWidgets.QLabel("")
        self.missing_label.setStyleSheet("color: #b00020; font-weight: 600;")
        layout.addWidget(self.missing_label)
        self.create_button = QtWidgets.QPushButton("Create missing soundaliases CSV")
        self.create_button.clicked.connect(self.create_file_if_missing)
        layout.addWidget(self.create_button)

        self.table = QtWidgets.QTableWidget(self)
        self.table.setColumnCount(len(self.get_column_names()))
        self.table.setHorizontalHeaderLabels(self.get_column_names())
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.table.itemSelectionChanged.connect(self.on_table_select)
        layout.addWidget(self.table)

        form_group = QtWidgets.QGroupBox("Add / Edit Sound Alias", self)
        form_layout = QtWidgets.QGridLayout(form_group)
        layout.addWidget(form_group)
        self.entry_widgets = {}

        columns = self.get_column_names()

        tooltips = {
            "name": "Name of the alias that is used to play this sound (required)",
            "sequence": "Used to uniquely identify alias entries when more than one sound goes to an alias, used only to catch unwanted duplicates (default = 0)",
            "file": "The name of the file that contains the sound data (required)",
            "vol_min": "0 is silent, 1 is full volume (default = 1)",
            "vol_max": "0 is silent, 1 is full volume (default = same as vol_min)",
            "vol_mod": "Blank causes no effect on vol_min and vol_max, otherwise the string must match a string in the volumemodgroups.def file",
            "pitch_min": "1 is normal playback, 2 is twice as fast, 0.5 is half as fast (default = 1)",
            "pitch_max": "1 is normal playback, 2 is twice as fast, 0.5 is half as fast (default = same as pitch_min)",
            "dist_min": "Within this distance in inches, the sound is always full volume (default = 120)",
            "dist_max": "Outside this distance in inches, the sound is not started. If left blank or set to 0, the sound will play from any distance.",
            "channel": "auto, menu, weapon, voice, item, body, local, music, announcer (default = auto)",
            "type": "primed (a streamed sound which gets primed on some platforms) / streamed / loaded (default = loaded)",
            "probability": "Weight to use for the weighted probability of playing this sound instead of another sound (default = 1)",
            "loop": "Whether this sound is \"looping\" or \"nonlooping\" (default = \"nonlooping\")",
            "masterslave": "If \"master\", this is a master sound. If a number, then this sound's volume will be multiplied by that number (a percentage between 0 and 1) any master sound is playing.",
            "loadspec": "Space-separated list of which maps should use this alias; eg, \"burnville dawnville\". If blank, the alias is used on all maps.",
            "compression": "A string corresponding to an entry in \"XMAUpdate.tbl\" which is used to determine compression by XMAUpdate.exe",
            "secondaryaliasname": "Defines the name of an additional sound alias to play in addition to the current alias being played.",
            "volumefalloffcurve": "If blank uses the linear curve which can not be changed. A string 'XXXX' corresponds to the curve defined by the file 'soundaliases/XXXX.vfcurve'.",
            "startdelay": "Defaults to no delay. The value is the number of milliseconds to delay starting the sound by",
            "speakermap": "If blank uses the default speakermappings which cannot be changed. A string 'XXXX' corresponds to the speakermap defined by the file 'soundaliases/XXXX.spkrmap'.",
            "reverb": "Blank means the alias is affected normally by wet and dry levels, \"fulldrylevel\" forces the alias to use a full drylevel, \"nowetlevel\" forces the alias to use no wetlevel.",
            "lfe percentage": "This determines what percentage of the highest calculated spatialized speaker volume should be passed to the LFE. Blank means no LFE for the sound.",
        }

        for idx, col_name in enumerate(columns):
            row, column = divmod(idx, 3)

            label = QtWidgets.QLabel(f"{col_name}:")
            if col_name in tooltips:
                label.setToolTip(tooltips[col_name])

            form_layout.addWidget(label, row * 2, column)
            if col_name == "channel":
                widget = QtWidgets.QComboBox(self)
                widget.addItems(["", "local", "announce", "mission", "voice", "music", "voicechat", "effects"])
                widget.setCurrentText("local")
            elif col_name == "type":
                widget = QtWidgets.QComboBox(self)
                widget.addItems(["", "streamed", "loaded"])
                widget.setCurrentText("streamed")
            elif col_name == "loop":
                widget = QtWidgets.QComboBox(self)
                widget.addItems(["", "looping", "oneshot"])
                widget.setCurrentText("looping")
            elif col_name == "compression":
                widget = QtWidgets.QComboBox(self)
                widget.addItems(["", "pc", "xb"])
            elif col_name in ("vol_min", "vol_max", "pitch_min", "pitch_max", "startdelay"):
                widget = QtWidgets.QDoubleSpinBox(self)
                widget.setRange(0.0, 2.0)
                widget.setSingleStep(0.01)
                widget.setValue(0.65 if col_name in {"vol_min", "vol_max"} else 0.0)
            elif col_name in ("dist_min", "dist_max"):
                widget = QtWidgets.QSpinBox(self)
                widget.setRange(0, 20000)
                widget.setSingleStep(50)
            elif col_name in ("probability", "lfe percentage"):
                widget = QtWidgets.QSpinBox(self)
                widget.setRange(0, 100)
                widget.setSingleStep(5)
            else:
                widget = QtWidgets.QLineEdit(self)
            self.entry_widgets[col_name] = widget
            form_layout.addWidget(widget, row * 2 + 1, column)

        buttons = QtWidgets.QHBoxLayout()
        add_btn = QtWidgets.QPushButton("Add / Update")
        add_btn.clicked.connect(self.add_or_update_entry)
        clear_btn = QtWidgets.QPushButton("Clear Form")
        clear_btn.clicked.connect(self.clear_form)
        remove_btn = QtWidgets.QPushButton("Remove Selected")
        remove_btn.clicked.connect(self.remove_selected)
        buttons.addWidget(add_btn)
        buttons.addWidget(clear_btn)
        buttons.addWidget(remove_btn)
        layout.addLayout(buttons)

        self.current_row = None
        self._set_defaults()

    def get_column_names(self) -> List[str]:
        return [
            "name", "sequence", "file", "vol_min", "vol_max", "vol_mod",
            "pitch_min", "pitch_max", "dist_min", "dist_max", "channel",
            "type", "probability", "loop", "masterslave", "loadspec",
            "subtitle", "compression", "secondaryaliasname", "volumefalloffcurve",
            "startdelay", "speakermap", "reverb", "lfe percentage",
        ]

    def _set_defaults(self) -> None:
        mapname = self.map_name()

        widget = self.entry_widgets.get("name")
        if widget is not None and hasattr(widget, "setText"):
            widget.setText("Your alias name here")

        widget = self.entry_widgets.get("file")
        if widget is not None and hasattr(widget, "setText"):
            widget.setText("ambient/amb_yourpathhere.mp3")

        widget = self.entry_widgets.get("loadspec")
        if widget is not None and hasattr(widget, "setText"):
            widget.setText(f"{mapname}")

        if "vol_min" in self.entry_widgets:
            self.entry_widgets["vol_min"].setValue(0.65)
        if "vol_max" in self.entry_widgets:
            self.entry_widgets["vol_max"].setValue(0.65)

    def _widget_value(self, widget) -> str:
        if isinstance(widget, QtWidgets.QComboBox):
            return widget.currentText().strip()
        if isinstance(widget, QtWidgets.QDoubleSpinBox):
            return str(widget.value())
        if isinstance(widget, QtWidgets.QSpinBox):
            return str(widget.value())
        if isinstance(widget, QtWidgets.QLineEdit):
            return widget.text().strip()
        return ""

    def _set_widget_value(self, widget, value: str) -> None:
        if isinstance(widget, QtWidgets.QComboBox):
            widget.setCurrentText(value)
        elif isinstance(widget, QtWidgets.QDoubleSpinBox):
            try:
                widget.setValue(float(value))
            except Exception:
                widget.setValue(0.0)
        elif isinstance(widget, QtWidgets.QSpinBox):
            try:
                widget.setValue(int(float(value)))
            except Exception:
                widget.setValue(0)
        elif isinstance(widget, QtWidgets.QLineEdit):
            widget.setText(value)

    def clear_form(self) -> None:
        for widget in self.entry_widgets.values():
            if isinstance(widget, QtWidgets.QComboBox):
                widget.setCurrentText("")
            elif isinstance(widget, QtWidgets.QDoubleSpinBox):
                widget.setValue(0.0)
            elif isinstance(widget, QtWidgets.QSpinBox):
                widget.setValue(0)
            elif isinstance(widget, QtWidgets.QLineEdit):
                widget.clear()
        self.current_row = None
        self._set_defaults()

    def add_or_update_entry(self) -> None:
        values = [self._widget_value(self.entry_widgets[col]) for col in self.get_column_names()]
        if not values[0] or not values[2]:
            QtWidgets.QMessageBox.warning(self, "Missing values", "Alias name and file are required.")
            return
        if self.current_row is None:
            row = self.table.rowCount()
            self.table.setRowCount(row + 1)
            self.current_row = row
        self.table.setRowCount(self.table.rowCount())
        self.table.setItem(self.current_row, 0, QtWidgets.QTableWidgetItem(values[0]))
        for col_idx, val in enumerate(values[1:], start=1):
            if self.table.item(self.current_row, col_idx) is None:
                self.table.setItem(self.current_row, col_idx, QtWidgets.QTableWidgetItem(val))
            else:
                self.table.item(self.current_row, col_idx).setText(val)
        self.clear_form()

    def on_table_select(self) -> None:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        row = rows[0].row()
        self.current_row = row
        values = [
            self.table.item(row, idx).text() if self.table.item(row, idx) is not None else ""
            for idx in range(self.table.columnCount())
        ]
        for col_name, widget in self.entry_widgets.items():
            idx = self.get_column_names().index(col_name)
            if idx < len(values):
                self._set_widget_value(widget, values[idx])

    def remove_selected(self) -> None:
        rows = sorted({r.row() for r in self.table.selectionModel().selectedRows()}, reverse=True)
        for row in rows:
            self.table.removeRow(row)
        self.clear_form()

    def update_missing_status(self) -> None:
        mapname = self.map_name()
        if not mapname:
            self.missing_label.setText("")
            self.create_button.setEnabled(False)
            return

        cod2 = Path(self.cod2_path())
        status = (
            self.app.check_missing_files(cod2, mapname)
            if hasattr(self.app, "check_missing_files")
            else {}
        )
        exists = bool(status.get("soundaliases_csv", {}).get("exists", False))

        self.set_file_status(
            self.missing_label,
            self.create_button,
            exists,
            ok_text="Soundaliases CSV exists ✓",
            missing_text=f"Missing: soundaliases/{mapname}.csv",
            create_button_text=f"Create {mapname}.csv",
        )

        if exists:
            self.load_from_file(cod2, mapname)
            self.clear_form()
        else:
            self.table.setRowCount(0)
            self.clear_form()

    def load_from_file(self, cod2_path: Path, mapname: str) -> None:
        path = map_soundaliases_path(cod2_path, mapname)
        if not path.exists():
            return
        self.table.setRowCount(0)
        try:
            with open(path, "r", encoding="utf-8") as handle:
                rows = [line.rstrip("\n") for line in handle if line.strip()]
            columns = self.get_column_names()
            for row_text in rows:
                if row_text.startswith("#"):
                    continue
                if row_text.split(",")[0].lower() == "name":
                    continue
                values = [cell.strip() for cell in row_text.split(",")]
                if not values[0].strip():
                    continue
                row = self.table.rowCount()
                self.table.setRowCount(row + 1)
                for col_idx, value in enumerate(values[: len(columns)]):
                    self.table.setItem(row, col_idx, QtWidgets.QTableWidgetItem(value))
        except Exception:
            pass

    def create_file_if_missing(self) -> None:
        mapname = self.map_name()
        if not mapname:
            return
        cod2 = Path(self.cod2_path())
        path = map_soundaliases_path(cod2, mapname, for_write=True)
        if path.exists():
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        default_lines = [
            "# Generated by CoD2 Map Script Generator",
            ",".join(self.get_column_names()),
            f"ambient_mp_{mapname},,ambient/amb_{mapname}_01.mp3,0.65,,,,,,,local,streamed,,looping,,mp_{mapname},,,,,",
        ]
        path.write_text("\n".join(default_lines) + "\n", encoding="utf-8")
        self.update_missing_status()

    def save_files(self) -> None:
        mapname = self.map_name()
        if not mapname:
            QtWidgets.QMessageBox.warning(self, "No map", "Select a map first.")
            return
        cod2 = Path(self.cod2_path())
        path = map_soundaliases_path(cod2, mapname, for_write=True)
        path.parent.mkdir(parents=True, exist_ok=True)
        header = ",".join(self.get_column_names())
        lines = ["# Generated by CoD2 Map Script Generator", header]
        for row in range(self.table.rowCount()):
            values = [
                self.table.item(row, col).text() if self.table.item(row, col) else ""
                for col in range(self.table.columnCount())
            ]
            lines.append(",".join(values))
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")


class BasicFilesTab(QtTabMixin, QtWidgets.QWidget):
    def __init__(self, app: QtWidgets.QWidget) -> None:
        super().__init__(app)
        self._build_ui()
        self.update_missing_status()

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        self.missing_label = QtWidgets.QLabel("")
        self.missing_label.setStyleSheet("color: #b00020; font-weight: 600;")
        layout.addWidget(self.missing_label)
        self.create_button = QtWidgets.QPushButton("Create missing basic files")
        self.create_button.clicked.connect(self.create_missing_files)
        layout.addWidget(self.create_button)

        layout.addWidget(QtWidgets.QLabel("CSV File (maps/mp/{mapname}.csv)"))
        self.csv_text = QtWidgets.QPlainTextEdit("", self)
        layout.addWidget(self.csv_text)

        form = QtWidgets.QGroupBox("Arena file", self)
        form_layout = QtWidgets.QFormLayout(form)
        self.longname_entry = QtWidgets.QLineEdit("", self)
        form_layout.addRow("Longname:", self.longname_entry)
        self.gametype_vars = {
            name: QtWidgets.QCheckBox(name.upper()) for name in ["dm", "tdm", "sd", "hq", "ctf"]
        }
        checks = QtWidgets.QHBoxLayout()
        for box in self.gametype_vars.values():
            box.setChecked(box.text() == "DM")
            checks.addWidget(box)
        form_layout.addRow("Gametype support:", checks)
        layout.addWidget(form)

        self.save_button = QtWidgets.QPushButton("Save basic files")
        self.save_button.clicked.connect(self.save_files)
        layout.addWidget(self.save_button)

    def save_files(self) -> None:
        mapname = self.map_name()
        if not mapname:
            QtWidgets.QMessageBox.warning(self, "No map", "Select a map first.")
            return
        cod2 = Path(self.cod2_path())

        csv_path = map_csv_path(cod2, mapname, for_write=True)
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        content = self.csv_text.toPlainText().strip() or DEFAULT_CSV_CONTENT(mapname)
        csv_path.write_text(content + "\n", encoding="utf-8")

        longname = self.longname_entry.text().strip()
        gametypes = " ".join(
            box.text().upper() for box in self.gametype_vars.values() if box.isChecked()
        )
        arena_content = (
            "{\n"
            f'    map\t\t"{mapname}"\n'
            f'    longname\t"{longname}"\n'
            f'    gametype\t"{gametypes}"\n'
            "}\n"
        )
        arena_path = map_arena_path(cod2, mapname, for_write=True)
        arena_path.parent.mkdir(parents=True, exist_ok=True)
        arena_path.write_text(arena_content, encoding="utf-8")

    def update_missing_status(self) -> None:
        mapname = self.map_name()
        if not mapname:
            self.missing_label.setText("")
            self.create_button.setEnabled(False)
            self.csv_text.setPlainText("")
            self.longname_entry.clear()
            return

        cod2 = Path(self.cod2_path())
        status = (
            self.app.check_missing_files(cod2, mapname)
            if hasattr(self.app, "check_missing_files")
            else {}
        )
        missing = [
            k for k, v in status.items() if k in {"csv", "arena"} and not v.get("exists", False)
        ]

        if missing:
            self.set_file_status(
                self.missing_label,
                self.create_button,
                False,
                ok_text="All files exist ✓",
                missing_text=f"Missing files: {', '.join(missing)}",
                create_button_text="Create missing files",
            )
            self.csv_text.setPlainText(DEFAULT_CSV_CONTENT(mapname).strip())
            self.longname_entry.setText("")
            for box in self.gametype_vars.values():
                box.setChecked(box.text() == "DM")
        else:
            self.set_file_status(
                self.missing_label,
                self.create_button,
                True,
                ok_text="All files exist ✓",
                missing_text="",
            )
            self.load_from_files(cod2, mapname)

    def load_from_files(self, cod2_path: Path, mapname: str) -> None:
        csv_path = map_csv_path(cod2_path, mapname)
        if csv_path.exists():
            self.csv_text.setPlainText(csv_path.read_text(encoding="utf-8").strip())
        else:
            self.csv_text.setPlainText(DEFAULT_CSV_CONTENT(mapname).strip())

        arena_path = map_arena_path(cod2_path, mapname)
        if arena_path.exists():
            content = arena_path.read_text(encoding="utf-8")
            if "longname" in content:
                try:
                    self.longname_entry.setText(content.split("longname", 1)[1].split('"')[1])
                except Exception:
                    self.longname_entry.setText("")
            else:
                self.longname_entry.setText("")

            for line in content.splitlines():
                stripped = line.strip()
                if stripped.startswith("gametype"):
                    try:
                        gametypes = stripped.split('"', 2)[1] if '"' in stripped else ""
                    except Exception:
                        gametypes = ""
                    for box in self.gametype_vars.values():
                        box.setChecked(False)
                    for gt in gametypes.split():
                        key = gt.lower()
                        if key in self.gametype_vars:
                            self.gametype_vars[key].setChecked(True)
                    break
        else:
            self.longname_entry.setText("")
            for box in self.gametype_vars.values():
                box.setChecked(box.text() == "DM")

    def create_missing_files(self) -> None:
        mapname = self.map_name()
        if not mapname:
            return
        cod2 = Path(self.cod2_path())
        status = (
            self.app.check_missing_files(cod2, mapname)
            if hasattr(self.app, "check_missing_files")
            else {}
        )

        if not status.get("csv", {}).get("exists", False):
            csv_path = map_csv_path(cod2, mapname, for_write=True)
            csv_path.parent.mkdir(parents=True, exist_ok=True)
            csv_path.write_text(DEFAULT_CSV_CONTENT(mapname), encoding="utf-8")

        if not status.get("arena", {}).get("exists", False):
            arena_path = map_arena_path(cod2, mapname, for_write=True)
            arena_path.parent.mkdir(parents=True, exist_ok=True)
            arena_content = (
                "{\n"
                f'    map\t\t"{mapname}"\n'
                '    longname\t""\n'
                '    gametype\t"DM"\n'
                "}\n"
            )
            arena_path.write_text(arena_content, encoding="utf-8")

        self.update_missing_status()