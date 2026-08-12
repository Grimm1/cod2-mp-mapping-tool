"""Main GSC editor tab for creating and editing main game script content."""

from pathlib import Path
from typing import Optional
from PyQt6 import QtWidgets, QtGui, QtCore
from config import MINIMAL_MAIN_GSC
from helpers import parse_gsc_hq_locations, parse_gsc_kill_triggers, map_gsc_path, map_soundaliases_path
from .qt_tab_mixin import QtTabMixin


class MainGscTab(QtTabMixin, QtWidgets.QWidget):
    def __init__(self, app: QtWidgets.QWidget) -> None:
        super().__init__(app)
        self._build_ui()
        self.update_missing_status()

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        self.missing_label = QtWidgets.QLabel("")
        self.missing_label.setStyleSheet("color: #b00020; font-weight: 600;")
        layout.addWidget(self.missing_label)

        self.create_button = QtWidgets.QPushButton("Create missing main GSC")
        self.create_button.clicked.connect(self.create_file_if_missing)
        layout.addWidget(self.create_button)

        scroll = QtWidgets.QScrollArea(self)
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll)

        inner = QtWidgets.QWidget(self)
        scroll.setWidget(inner)
        inner_layout = QtWidgets.QHBoxLayout(inner)

        left_col = QtWidgets.QWidget(self)
        left_layout = QtWidgets.QVBoxLayout(left_col)
        left_layout.setContentsMargins(0, 0, 0, 0)
        inner_layout.addWidget(left_col, 1)

        right_col = QtWidgets.QWidget(self)
        right_layout = QtWidgets.QVBoxLayout(right_col)
        right_layout.setContentsMargins(0, 0, 0, 0)
        inner_layout.addWidget(right_col, 1)

        top = QtWidgets.QGroupBox("Map Setup", self)
        top_layout = QtWidgets.QFormLayout(top)
        left_layout.addWidget(top)

        self.ambient_enabled = QtWidgets.QCheckBox("Enable ambientPlay()", self)
        top_layout.addRow(self.ambient_enabled)
        self.ambient_combo = QtWidgets.QComboBox(self)
        self.ambient_combo.addItems([
            "ambient_mp_carentan",
            "ambient_mp_dawnville",
            "ambient_mp_toujane",
            "ambient_mp_burgundy",
            "ambient_mp_railyard",
            "ambient_mp_harbor",
            "ambient_mp_farmhouse",
            "ambient_mp_matmata",
            "ambient_mp_brecourt",
        ])
        top_layout.addRow("Ambient alias:", self.ambient_combo)

        self.allies_combo = QtWidgets.QComboBox(self)
        self.allies_combo.addItems(["british", "american", "russian"])
        self.allies_combo.setCurrentText("british")
        top_layout.addRow("Allies:", self.allies_combo)

        self.axis_combo = QtWidgets.QComboBox(self)
        self.axis_combo.addItems(["german"])
        self.axis_combo.setCurrentText("german")
        top_layout.addRow("Axis:", self.axis_combo)

        self.defenders_combo = QtWidgets.QComboBox(self)
        self.defenders_combo.addItems(["allies", "axis"])
        self.defenders_combo.setCurrentText("axis")
        top_layout.addRow("Defenders:", self.defenders_combo)

        self.attackers_combo = QtWidgets.QComboBox(self)
        self.attackers_combo.addItems(["allies", "axis"])
        self.attackers_combo.setCurrentText("allies")
        top_layout.addRow("Attackers:", self.attackers_combo)

        self.german_combo = QtWidgets.QComboBox(self)
        self.german_combo.addItems(["winterlight", "winterdark", "normandy", "africa"])
        self.german_combo.setCurrentText("normandy")
        top_layout.addRow("German soldier type:", self.german_combo)

        self.allies_soldier_combo = QtWidgets.QComboBox(self)
        self.allies_soldier_combo.addItems(["normandy", "africa", "coats", "padded"])
        top_layout.addRow("Allied soldier type:", self.allies_soldier_combo)
        self.allies_combo.currentTextChanged.connect(self._update_allied_soldier_options)
        self._update_allied_soldier_options(self.allies_combo.currentText())

        fog_group = QtWidgets.QGroupBox("Fog and glow", self)
        fog_layout = QtWidgets.QFormLayout(fog_group)
        left_layout.addWidget(fog_group)

        self.expfog_enabled = QtWidgets.QCheckBox("Enable setExpFog()", self)
        fog_layout.addRow(self.expfog_enabled)

        self.expfog_start = QtWidgets.QLineEdit("0.0001144", self)
        self.expfog_color_btn = self._make_color_button("0.51, 0.45, 0.28")
        self.expfog_time = QtWidgets.QLineEdit("0", self)
        fog_layout.addRow("Density:", self.expfog_start)
        fog_layout.addRow("Color (R, G, B):", self.expfog_color_btn)
        fog_layout.addRow("Transition time:", self.expfog_time)

        self.cullfog_enabled = QtWidgets.QCheckBox("Enable setcullfog()", self)
        fog_layout.addRow(self.cullfog_enabled)
        self.cullfog_near = QtWidgets.QLineEdit("0", self)
        self.cullfog_far = QtWidgets.QLineEdit("16500", self)
        self.cullfog_color_btn = self._make_color_button("0.7, 0.85, 1.0")
        self.cullfog_time = QtWidgets.QLineEdit("0", self)
        fog_layout.addRow("Near:", self.cullfog_near)
        fog_layout.addRow("Far:", self.cullfog_far)
        fog_layout.addRow("Color:", self.cullfog_color_btn)
        fog_layout.addRow("Transition time:", self.cullfog_time)

        self.glow_bloom0 = QtWidgets.QCheckBox("Enable r_glowbloomintensity0", self)
        fog_layout.addRow(self.glow_bloom0)
        self.glow_bloom0_value = QtWidgets.QLineEdit("0.25", self)
        fog_layout.addRow("Bloom 0 value:", self.glow_bloom0_value)

        self.glow_bloom1 = QtWidgets.QCheckBox("Enable r_glowbloomintensity1", self)
        fog_layout.addRow(self.glow_bloom1)
        self.glow_bloom1_value = QtWidgets.QLineEdit("0.25", self)
        fog_layout.addRow("Bloom 1 value:", self.glow_bloom1_value)

        self.glow_skybleed0 = QtWidgets.QCheckBox("Enable r_glowskybleedintensity0", self)
        fog_layout.addRow(self.glow_skybleed0)
        self.glow_skybleed0_value = QtWidgets.QLineEdit("0.30", self)
        fog_layout.addRow("Sky bleed value:", self.glow_skybleed0_value)

        script_group = QtWidgets.QGroupBox("Extra script calls", self)
        script_layout = QtWidgets.QVBoxLayout(script_group)
        right_layout.addWidget(script_group)
        input_row = QtWidgets.QHBoxLayout()
        self.script_path_entry = QtWidgets.QLineEdit(self)
        self.script_func_entry = QtWidgets.QLineEdit(self)
        input_row.addWidget(QtWidgets.QLabel("Path:"))
        input_row.addWidget(self.script_path_entry)
        input_row.addWidget(QtWidgets.QLabel("Function:"))
        input_row.addWidget(self.script_func_entry)
        add_btn = QtWidgets.QPushButton("Add call")
        add_btn.clicked.connect(self._add_script_call)
        input_row.addWidget(add_btn)
        script_layout.addLayout(input_row)
        self.script_list = QtWidgets.QListWidget(self)
        self.script_list.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
        script_layout.addWidget(self.script_list)

        script_buttons = QtWidgets.QHBoxLayout()
        remove_script_btn = QtWidgets.QPushButton("Remove selected")
        remove_script_btn.clicked.connect(self._remove_selected_script)
        clear_script_btn = QtWidgets.QPushButton("Clear all")
        clear_script_btn.clicked.connect(self._clear_script_list)
        script_buttons.addWidget(remove_script_btn)
        script_buttons.addWidget(clear_script_btn)
        script_layout.addLayout(script_buttons)

        hq_group = QtWidgets.QGroupBox("HQ radio locations", self)
        hq_layout = QtWidgets.QVBoxLayout(hq_group)
        right_layout.addWidget(hq_group)
        hq_inputs = QtWidgets.QHBoxLayout()
        self.hq_pos = QtWidgets.QLineEdit(self)
        self.hq_angles = QtWidgets.QLineEdit(self)
        hq_inputs.addWidget(QtWidgets.QLabel("Pos:"))
        hq_inputs.addWidget(self.hq_pos)
        hq_inputs.addWidget(QtWidgets.QLabel("Angles:"))
        hq_inputs.addWidget(self.hq_angles)
        add_hq = QtWidgets.QPushButton("Add HQ")
        add_hq.clicked.connect(self._add_hq)
        hq_inputs.addWidget(add_hq)
        hq_layout.addLayout(hq_inputs)
        self.hq_list = QtWidgets.QListWidget(self)
        self.hq_list.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
        hq_layout.addWidget(self.hq_list)

        hq_buttons = QtWidgets.QHBoxLayout()
        self.remove_hq_button = QtWidgets.QPushButton("Remove selected")
        self.remove_hq_button.clicked.connect(self._remove_selected_hq)
        self.clear_hq_button = QtWidgets.QPushButton("Clear all")
        self.clear_hq_button.clicked.connect(self._clear_hq_list)
        hq_buttons.addWidget(self.remove_hq_button)
        hq_buttons.addWidget(self.clear_hq_button)
        hq_layout.addLayout(hq_buttons)

        kt_group = QtWidgets.QGroupBox("Kill triggers", self)
        kt_layout = QtWidgets.QVBoxLayout(kt_group)
        right_layout.addWidget(kt_group)
        kt_inputs = QtWidgets.QHBoxLayout()
        self.kt_origin = QtWidgets.QLineEdit(self)
        self.kt_radius = QtWidgets.QLineEdit(self)
        self.kt_height = QtWidgets.QLineEdit(self)
        kt_inputs.addWidget(QtWidgets.QLabel("Origin:"))
        kt_inputs.addWidget(self.kt_origin)
        kt_inputs.addWidget(QtWidgets.QLabel("Radius:"))
        kt_inputs.addWidget(self.kt_radius)
        kt_inputs.addWidget(QtWidgets.QLabel("Height:"))
        kt_inputs.addWidget(self.kt_height)
        add_kt = QtWidgets.QPushButton("Add trigger")
        add_kt.clicked.connect(self._add_killtrigger)
        kt_inputs.addWidget(add_kt)
        kt_layout.addLayout(kt_inputs)
        self.kt_list = QtWidgets.QListWidget(self)
        self.kt_list.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
        kt_layout.addWidget(self.kt_list)

        kt_buttons = QtWidgets.QHBoxLayout()
        self.remove_kt_button = QtWidgets.QPushButton("Remove selected")
        self.remove_kt_button.clicked.connect(self._remove_selected_kt)
        self.clear_kt_button = QtWidgets.QPushButton("Clear all")
        self.clear_kt_button.clicked.connect(self._clear_kt_list)
        kt_buttons.addWidget(self.remove_kt_button)
        kt_buttons.addWidget(self.clear_kt_button)
        kt_layout.addLayout(kt_buttons)

        self.save_button = QtWidgets.QPushButton("Save main GSC")
        self.save_button.clicked.connect(self.save_files)
        layout.addWidget(self.save_button)


    def _parse_rgb01(self, text: str) -> QtGui.QColor:
        try:
            parts = [float(p.strip()) for p in text.split(",")]
            if len(parts) >= 3:
                r, g, b = [max(0.0, min(1.0, c)) for c in parts[:3]]
                return QtGui.QColor.fromRgbF(r, g, b)
        except Exception:
            pass
        return QtGui.QColor.fromRgbF(0.5, 0.5, 0.5)


    def _rgb01_text(self, color: QtGui.QColor) -> str:
        return f"{color.redF():.6g}, {color.greenF():.6g}, {color.blueF():.6g}"


    def _apply_color_button_style(self, btn: QtWidgets.QPushButton, rgb_text: str) -> None:
        c = self._parse_rgb01(rgb_text)
        text_color = "#000000" if c.lightnessF() > 0.55 else "#ffffff"
        btn.setProperty("rgb_text", rgb_text)
        btn.setToolTip(rgb_text)
        btn.setText("Pick")
        btn.setStyleSheet(
            f"QPushButton {{"
            f"  background-color: {c.name()};"
            f"  color: {text_color};"
            f"  border: 1px solid #666;"
            f"  border-radius: 3px;"
            f"  padding: 2px 8px;"
            f"}}"
        )


    def _make_color_button(self, initial_rgb: str) -> QtWidgets.QPushButton:
        btn = QtWidgets.QPushButton(self)
        btn.setFixedHeight(24)
        btn.setMinimumWidth(72)
        btn.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self._apply_color_button_style(btn, initial_rgb)
        btn.clicked.connect(lambda checked=False, b=btn: self._pick_color(b))
        return btn


    def _pick_color(self, btn: QtWidgets.QPushButton) -> None:
        current = self._parse_rgb01(str(btn.property("rgb_text") or "0.5, 0.5, 0.5"))
        color = QtWidgets.QColorDialog.getColor(current, self, "Pick fog color")
        if not color.isValid():
            return
        rgb_text = self._rgb01_text(color)
        self._apply_color_button_style(btn, rgb_text)


    def _color_value(self, btn: QtWidgets.QPushButton) -> str:
        return str(btn.property("rgb_text") or "0, 0, 0")


    def clear_all_ui(self) -> None:
        self.ambient_enabled.setChecked(False)
        self.ambient_combo.setCurrentIndex(0)
        self.allies_combo.setCurrentText("british")
        self.axis_combo.setCurrentText("german")
        self.defenders_combo.setCurrentText("axis")
        self.attackers_combo.setCurrentText("allies")
        self.german_combo.setCurrentText("normandy")
        self.allies_soldier_combo.setCurrentIndex(0)
        self.script_list.clear()
        self.expfog_enabled.setChecked(False)
        self.expfog_start.setText("0.0001144")
        self._apply_color_button_style(self.expfog_color_btn, "0.51, 0.45, 0.28")
        self.expfog_time.setText("0")
        self.cullfog_enabled.setChecked(False)
        self.cullfog_near.setText("0")
        self.cullfog_far.setText("16500")
        self._apply_color_button_style(self.cullfog_color_btn, "0.7, 0.85, 1.0")
        self.cullfog_time.setText("0")
        self.glow_bloom0.setChecked(False)
        self.glow_bloom0_value.setText("0.25")
        self.glow_bloom1.setChecked(False)
        self.glow_bloom1_value.setText("0.25")
        self.glow_skybleed0.setChecked(False)
        self.glow_skybleed0_value.setText("0.30")
        self.hq_list.clear()
        self.kt_list.clear()


    def save_files(self) -> None:
        mapname = self.map_name()
        if not mapname:
            QtWidgets.QMessageBox.warning(self, "No map", "Select a map first.")
            return

        cod2 = Path(self.cod2_path())
        path = map_gsc_path(cod2, mapname, for_write=True)
        path.parent.mkdir(parents=True, exist_ok=True)

        lines = []
        lines.append("main()")
        lines.append("{")
        lines.append(f"    maps\\mp\\{mapname}_fx::main();")
        lines.append("    maps\\mp\\_load::main();")

        if self.script_list.count() > 0:
            lines.append("")
            for i in range(self.script_list.count()):
                text = self.script_list.item(i).text().strip()
                if text:
                    if not text.endswith(";"):
                        text += ";"
                    lines.append(f"    {text}")

        if self.ambient_enabled.isChecked():
            alias = self.ambient_combo.currentText().strip()
            if alias:
                lines.append("")
                lines.append(f'    ambientPlay("{alias}");')

        lines.append("")
        lines.append(f'    game["allies"] = "{self.allies_combo.currentText()}";')
        lines.append(f'    game["axis"] = "{self.axis_combo.currentText()}";')
        lines.append(f'    game["defenders"] = "{self.defenders_combo.currentText()}";')
        lines.append(f'    game["attackers"] = "{self.attackers_combo.currentText()}";')
        lines.append(f'    game["german_soldiertype"] = "{self.german_combo.currentText()}";')

        allied_st = self.allies_soldier_combo.currentText()
        allies = self.allies_combo.currentText()
        if allies == "american":
            lines.append(f'    game["american_soldiertype"] = "{allied_st}";')
        elif allies == "british":
            lines.append(f'    game["british_soldiertype"] = "{allied_st}";')
        elif allies == "russian":
            lines.append(f'    game["russian_soldiertype"] = "{allied_st}";')

        if self.hq_list.count() > 0:
            lines.append("")
            lines.append('    if (getcvar("g_gametype") == "hq")')
            lines.append("    {")
            lines.append("        level.radio = [];" )
            for i in range(self.hq_list.count()):
                text = self.hq_list.item(i).text().strip()
                if text and "|" in text:
                    pos, angles = [p.strip() for p in text.split("|", 1)]
                    pos = self._strip_outer_parens(pos)
                    angles = self._strip_outer_parens(angles)
                    lines.append(f'        level.radio[{i}] = spawn("script_model", ({pos}));')
                    lines.append(f"        level.radio[{i}].angles = ({angles});")
            lines.append("    }")

        if self.kt_list.count() > 0:
            lines.append("")
            lines.append("    level.killtriggers = [];" )
            for i in range(self.kt_list.count()):
                text = self.kt_list.item(i).text().strip()
                if text and "|" in text:
                    parts = [p.strip() for p in text.split("|")]
                    if len(parts) >= 3:
                        origin, radius, height = parts[:3]
                        origin = self._strip_outer_parens(origin)
                        lines.append(f"    level.killtriggers[{i}] = spawnstruct();")
                        lines.append(f"    level.killtriggers[{i}].origin = ({origin});")
                        lines.append(f"    level.killtriggers[{i}].radius = {radius};")
                        lines.append(f"    level.killtriggers[{i}].height = {height};")
            lines.append("    thread maps\\mp\\_killtriggers::init();")

        if self.expfog_enabled.isChecked():
            lines.append("")
            lines.append(
                f"    setExpFog({self.expfog_start.text()}, "
                f"{self._color_value(self.expfog_color_btn)}, "
                f"{self.expfog_time.text()});"
            )

        if self.cullfog_enabled.isChecked():
            lines.append("")
            lines.append(
                f"    setcullfog({self.cullfog_near.text()}, {self.cullfog_far.text()}, "
                f"{self._color_value(self.cullfog_color_btn)}, {self.cullfog_time.text()});"
            )

        if self.glow_bloom0.isChecked():
            lines.append(f'    setcvar("r_glowbloomintensity0", "{self.glow_bloom0_value.text()}");')
        if self.glow_bloom1.isChecked():
            lines.append(f'    setcvar("r_glowbloomintensity1", "{self.glow_bloom1_value.text()}");')
        if self.glow_skybleed0.isChecked():
            lines.append(f'    setcvar("r_glowskybleedintensity0", "{self.glow_skybleed0_value.text()}");')

        lines.append("}")

        final_content = "\n".join(lines) + "\n"
        path.write_text(final_content, encoding="utf-8")
        QtWidgets.QMessageBox.information(self, "Saved", f"Successfully saved {mapname}.gsc")

    def _strip_outer_parens(value: str) -> str:
        value = value.strip()
        while value.startswith("(") and value.endswith(")"):
            inner = value[1:-1].strip()
            if inner.startswith("(") and inner.endswith(")"):
                value = inner
                continue
            return inner
        return value

    def _load_ambient_aliases(self) -> None:
        """Load stock + custom ambient aliases from soundaliases CSV"""
        current = self.ambient_combo.currentText()
        self.ambient_combo.clear()

        stock = [
            "ambient_mp_carentan", "ambient_mp_dawnville", "ambient_mp_toujane",
            "ambient_mp_burgundy", "ambient_mp_railyard", "ambient_mp_harbor",
            "ambient_mp_farmhouse", "ambient_mp_matmata", "ambient_mp_brecourt",
        ]
        self.ambient_combo.addItems(stock)

        try:
            cod2 = Path(self.cod2_path())
            mapname = self.map_name()
            csv_path = map_soundaliases_path(cod2, mapname)
            if not csv_path.exists():
                csv_path = cod2 / "soundaliases" / f"{mapname}.csv"

            if csv_path.exists():
                content = csv_path.read_text(encoding="utf-8", errors="ignore")
                for line in content.splitlines():
                    if not line.strip() or line.startswith("#"):
                        continue
                    parts = [p.strip() for p in line.split(",")]
                    if len(parts) > 0 and parts[0].startswith("ambient_"):
                        alias = parts[0]
                        if alias not in stock and alias not in [self.ambient_combo.itemText(i) for i in range(self.ambient_combo.count())]:
                            self.ambient_combo.addItem(alias)
        except Exception as e:
            print(f"[Ambient] Failed to load custom aliases: {e}")

        index = self.ambient_combo.findText(current)
        if index >= 0:
            self.ambient_combo.setCurrentIndex(index)

    def _update_allied_soldier_options(self, allies: str) -> None:
        options = {
            "american": ["normandy"],
            "british": ["normandy", "africa"],
            "russian": ["coats", "padded"],
        }.get(allies, ["normandy"])
        self.allies_soldier_combo.clear()
        self.allies_soldier_combo.addItems(options)
        if options:
            self.allies_soldier_combo.setCurrentIndex(0)

    def _add_script_call(self) -> None:
        path = self.script_path_entry.text().strip()
        func = self.script_func_entry.text().strip()
        if not path or not func:
            return
        self.script_list.addItem(f"maps\\mp\\{path.replace('/', '\\')}::{func}();")
        self.script_path_entry.clear()
        self.script_func_entry.clear()

    def _remove_selected_script(self) -> None:
        self.remove_selected_list_items(self.script_list)

    def _clear_script_list(self) -> None:
        self.confirm_clear_list(
            self.script_list,
            "Clear scripts",
            "Remove all extra script calls from the current Main GSC?",
        )

    def _add_hq(self) -> None:
        pos = self.hq_pos.text().strip()
        angles = self.hq_angles.text().strip()
        if pos and angles:
            self.hq_list.addItem(f"{pos} | {angles}")
            self.hq_pos.clear()
            self.hq_angles.clear()

    def _add_killtrigger(self) -> None:
        origin = self.kt_origin.text().strip()
        radius = self.kt_radius.text().strip()
        height = self.kt_height.text().strip()
        if origin and radius and height:
            self.kt_list.addItem(f"{origin} | {radius} | {height}")
            self.kt_origin.clear()
            self.kt_radius.clear()
            self.kt_height.clear()

    def _remove_selected_hq(self) -> None:
        self.remove_selected_list_items(self.hq_list)

    def _clear_hq_list(self) -> None:
        self.confirm_clear_list(
            self.hq_list,
            "Clear HQ list",
            "Remove all HQ radio locations from the current Main GSC?",
        )

    def _remove_selected_kt(self) -> None:
        self.remove_selected_list_items(self.kt_list)

    def _clear_kt_list(self) -> None:
        self.confirm_clear_list(
            self.kt_list,
            "Clear kill triggers",
            "Remove all kill triggers from the current Main GSC?",
        )


        self.ambient_enabled.setChecked(False)
        self.ambient_combo.setCurrentIndex(0)
        self.allies_combo.setCurrentText("british")
        self.axis_combo.setCurrentText("german")
        self.defenders_combo.setCurrentText("axis")
        self.attackers_combo.setCurrentText("allies")
        self.german_combo.setCurrentText("normandy")
        self.allies_soldier_combo.setCurrentIndex(0)
        self.script_list.clear()
        self.expfog_enabled.setChecked(False)
        self.expfog_start.setText("0.0001144")
        self._apply_color_button_style(self.expfog_color_btn, "0.51, 0.45, 0.28")
        self.expfog_time.setText("0")
        self.cullfog_enabled.setChecked(False)
        self.cullfog_near.setText("0")
        self.cullfog_far.setText("16500")
        self._apply_color_button_style(self.cullfog_color_btn, "0.7, 0.85, 1.0")
        self.cullfog_time.setText("0")
        self.glow_bloom0.setChecked(False)
        self.glow_bloom0_value.setText("0.25")
        self.glow_bloom1.setChecked(False)
        self.glow_bloom1_value.setText("0.25")
        self.glow_skybleed0.setChecked(False)
        self.glow_skybleed0_value.setText("0.30")
        self.hq_list.clear()
        self.kt_list.clear()

    def load_from_file(self, cod2_path: Path, mapname: str) -> None:
        path = map_gsc_path(cod2_path, mapname)
        if not path.exists():
            return

        try:
            content = path.read_text(encoding="utf-8")
            self.clear_all_ui()

            for line in content.splitlines():
                stripped = line.strip()
                if not stripped or stripped.startswith("//"):
                    continue

                if "ambientPlay(" in stripped:
                    self.ambient_enabled.setChecked(True)
                    try:
                        alias = stripped.split('"')[1]
                        if self.ambient_combo.findText(alias) == -1:
                            self.ambient_combo.addItem(alias)
                        self.ambient_combo.setCurrentText(alias)
                    except Exception:
                        pass

                elif "game[" in stripped and '] = "' in stripped:
                    try:
                        key = stripped.split('game["')[1].split('"')[0]
                        value = stripped.split('"] = "')[1].split('"')[0]
                        if key == "allies":
                            self.allies_combo.setCurrentText(value)
                        elif key == "axis":
                            self.axis_combo.setCurrentText(value)
                        elif key == "defenders":
                            self.defenders_combo.setCurrentText(value)
                        elif key == "attackers":
                            self.attackers_combo.setCurrentText(value)
                        elif key == "german_soldiertype":
                            self.german_combo.setCurrentText(value)
                        elif key in {"american_soldiertype", "british_soldiertype", "russian_soldiertype"}:
                            self.allies_soldier_combo.setCurrentText(value)
                    except Exception:
                        pass

                elif "setExpFog(" in stripped:
                    self.expfog_enabled.setChecked(True)
                    params = stripped.split("setExpFog(", 1)[1].split(")", 1)[0].split(",")
                    if len(params) >= 6:
                        self.expfog_start.setText(params[0].strip())
                        rgb = f"{params[2].strip()}, {params[3].strip()}, {params[4].strip()}"
                        self._apply_color_button_style(self.expfog_color_btn, rgb)
                        self.expfog_time.setText(params[5].strip())

                elif "setcullfog(" in stripped:
                    self.cullfog_enabled.setChecked(True)
                    params = stripped.split("setcullfog(", 1)[1].split(")", 1)[0].split(",")
                    if len(params) >= 6:
                        self.cullfog_near.setText(params[0].strip())
                        self.cullfog_far.setText(params[1].strip())
                        rgb = f"{params[2].strip()}, {params[3].strip()}, {params[4].strip()}"
                        self._apply_color_button_style(self.cullfog_color_btn, rgb)
                        self.cullfog_time.setText(params[5].strip())

                elif "r_glowbloomintensity0" in stripped:
                    self.glow_bloom0.setChecked(True)
                    try:
                        self.glow_bloom0_value.setText(str(float(stripped.split('"')[3])))
                    except Exception:
                        pass
                elif "r_glowbloomintensity1" in stripped:
                    self.glow_bloom1.setChecked(True)
                    try:
                        self.glow_bloom1_value.setText(str(float(stripped.split('"')[3])))
                    except Exception:
                        pass
                elif "r_glowskybleedintensity0" in stripped:
                    self.glow_skybleed0.setChecked(True)
                    try:
                        self.glow_skybleed0_value.setText(str(float(stripped.split('"')[3])))
                    except Exception:
                        pass

                elif "::" in stripped and stripped.endswith(";"):
                    call = stripped.rstrip(";").strip()
                    if any(token in call for token in [f"{mapname}_fx::main", "_load::main"]):
                        continue
                    self.script_list.addItem(call)

            # Parse HQ and Killtriggers
            for pos, angles in parse_gsc_hq_locations(content):
                self.hq_list.addItem(f"{pos} | {angles}")
            for origin, radius, height in parse_gsc_kill_triggers(content):
                self.kt_list.addItem(f"{origin} | {radius} | {height}")

            self._load_ambient_aliases()

        except Exception as e:
            print(f"[MainGSC] Load error: {e}")

    def update_missing_status(self, keep_user_data: bool = False) -> None:
        mapname = self.map_name()
        if not mapname:
            self.missing_label.setText("")
            self.create_button.setEnabled(False)
            return

        cod2 = Path(self.cod2_path())
        status = self.app.check_missing_files(cod2, mapname) if hasattr(self.app, "check_missing_files") else {}
        exists = bool(status.get("main_gsc", {}).get("exists", False))

        self.set_file_status(
            self.missing_label,
            self.create_button,
            exists,
            ok_text="Main GSC file exists ✓",
            missing_text=f"File missing: {mapname}.gsc",
            create_button_text=f"Create {mapname}.gsc",
        )

        if exists:
            if not keep_user_data:
                self.load_from_file(cod2, mapname)
                self._load_ambient_aliases()
        else:
            if not keep_user_data:
                self.clear_all_ui()    

    def create_file_if_missing(self) -> None:
        mapname = self.map_name()
        if not mapname:
            return
        cod2 = Path(self.cod2_path())
        path = map_gsc_path(cod2, mapname, for_write=True)
        if path.exists():
            return
        content = MINIMAL_MAIN_GSC.format(mapname=mapname, mapname_short=mapname)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        self.update_missing_status()
