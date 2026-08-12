"""IWD packer tab for collecting custom map assets and creating IWD archives."""

import shutil
import tempfile
import zipfile
import os
import re
from pathlib import Path

from helpers import (
    get_map_list,
    get_missing_custom_assets_from_map,
    get_xmodel_dependencies,
    get_textures_from_material,
    extract_loadscreen_iwi_candidates,
    load_json_name_set,
    load_stock_fx_keys,
    fx_lookup_key,
    parse_gsc_loadfx,
    material_path,
    fx_file_path,
    map_gsc_path,
    map_csv_path,
    map_arena_path,
    map_sun_path,
    map_soundaliases_path,
    relative_to_asset_root,
)
from ui.qt_tab_mixin import QtTabMixin
from PyQt6 import QtWidgets


class IwdPackerTab(QtTabMixin, QtWidgets.QWidget):
    def __init__(self, app: QtWidgets.QWidget) -> None:
        super().__init__(app)
        self.custom_files: set[Path] = set()
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        map_group = QtWidgets.QGroupBox("Map to pack", self)
        map_layout = QtWidgets.QHBoxLayout(map_group)
        map_layout.addWidget(QtWidgets.QLabel("Map:"))
        self.map_combo = QtWidgets.QComboBox(self)
        self.map_combo.setEditable(True)
        self.map_combo.setMinimumWidth(220)
        map_layout.addWidget(self.map_combo)
        refresh_btn = QtWidgets.QPushButton("Refresh maps")
        refresh_btn.clicked.connect(self.refresh_maps)
        map_layout.addWidget(refresh_btn)
        layout.addWidget(map_group)

        buttons = QtWidgets.QHBoxLayout()
        analyze_btn = QtWidgets.QPushButton("Analyze custom files")
        analyze_btn.clicked.connect(self.analyze_custom_files)
        self.pack_btn = QtWidgets.QPushButton("Pack to IWD")
        self.pack_btn.clicked.connect(self.pack_to_iwd)
        self.pack_btn.setEnabled(False)
        buttons.addWidget(analyze_btn)
        buttons.addWidget(self.pack_btn)
        layout.addLayout(buttons)

        self.status_label = QtWidgets.QLabel("No analysis yet")
        layout.addWidget(self.status_label)
        self.count_label = QtWidgets.QLabel("")
        layout.addWidget(self.count_label)
        self.file_list = QtWidgets.QListWidget(self)
        self.file_list.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.NoSelection)
        layout.addWidget(self.file_list)

    def refresh_maps(self, preferred_map: str | None = None) -> None:
        path = self.cod2_path()
        if not path or not Path(path).is_dir():
            self.map_combo.clear()
            return
        maps = get_map_list(path)
        self.populate_map_combo(self.map_combo, maps, preferred_map)

    def add_file(self, full_path: Path) -> None:
        if full_path.exists():
            self.custom_files.add(full_path)

    def analyze_custom_files(self):
        mapname = self.map_combo.currentText().strip()
        if not mapname:
            QtWidgets.QMessageBox.warning(self, "No Map", "Select a map first.")
            return

        cod2_path = Path(self.cod2_path())
        project_root = Path(__file__).resolve().parent.parent

        self.custom_files.clear()
        self.file_list.clear()

        self.status_label.setText(f"Analyzing {mapname}...")

        try:
            asset_result = get_missing_custom_assets_from_map(
                str(cod2_path),
                mapname,
                xmodel_json=str(project_root / "lists" / "xmodel_list.json"),
                material_json=str(project_root / "lists" / "materials.json"),
            )

            # XModels + dependencies
            for xmodel in asset_result["missing_xmodels"]:
                self.add_file(cod2_path / "main" / "xmodel" / xmodel)
                deps = get_xmodel_dependencies(str(cod2_path), xmodel)
                for surf in deps.get("surfs", []):
                    self.add_file(cod2_path / "main" / "xmodelsurfs" / surf)
                if deps.get("parts"):
                    self.add_file(cod2_path / "main" / "xmodelparts" / deps["parts"])

            # Materials
            for mat in asset_result["missing_materials"]:
                p = material_path(str(cod2_path), mat)
                if p:
                    self.add_file(p)

            # Textures
            for tex in asset_result.get("missing_textures", []):
                self.add_file(cod2_path / "main" / "images" / tex)

            stock_fx = load_stock_fx_keys(project_root / "lists" / "fx_files.json")
            stock_materials = {
                n.lower()
                for n in load_json_name_set(project_root / "lists" / "materials.json")
            }

            # Hidden FX from .map
            for fx_ref in asset_result.get("hidden_fx_paths", []):
                if fx_lookup_key(fx_ref) in stock_fx:
                    continue
                full_path = fx_file_path(str(cod2_path), fx_ref)
                if full_path:
                    self.add_file(full_path)

            # Parse mp_mapname_fx.gsc for loadfx calls
            fx_gsc_path = map_gsc_path(cod2_path, mapname, fx=True)
            if fx_gsc_path.exists():
                print(f"[IWD Packer] Parsing FX GSC: {fx_gsc_path.name}")
                fx_content = fx_gsc_path.read_text(encoding="utf-8", errors="ignore")
                for fx_path_raw in parse_gsc_loadfx(fx_content):
                    clean_key = fx_lookup_key(fx_path_raw)
                    if clean_key in stock_fx:
                        print(f"   → Skipping stock FX from _fx.gsc: {clean_key}")
                        continue
                    full_path = fx_file_path(str(cod2_path), fx_path_raw)
                    if full_path:
                        self.add_file(full_path)
                        print(f"   → Added custom FX from _fx.gsc: {clean_key}")

            # Parse custom EFX files for shaders + textures
            custom_efx_files = [
                p
                for p in self.custom_files
                if p.suffix.lower() == ".efx" and "fx" in str(p).lower()
            ]

            for efx_path in custom_efx_files:
                fx_name = efx_path.stem.lower()
                if fx_name in stock_fx or any(fx_name in s for s in stock_fx):
                    print(f"   → Skipping stock FX: {efx_path.name}")
                    continue

                try:
                    content = efx_path.read_text(encoding="utf-8", errors="ignore")
                    shader_blocks = re.findall(
                        r"shaders\s*\[\s*([^]]*)\s*\]",
                        content,
                        re.IGNORECASE | re.DOTALL,
                    )

                    for block in shader_blocks:
                        shaders = [
                            s.strip().strip('"').strip()
                            for s in re.split(r"[\r\n,]+", block)
                            if s.strip().strip('"').strip()
                        ]
                        for shader_name in shaders:
                            if not shader_name or shader_name.lower() in stock_materials:
                                continue

                            print(f"   → Found custom shader in {efx_path.name}: {shader_name}")

                            mat_file = material_path(str(cod2_path), shader_name)
                            if mat_file:
                                self.add_file(mat_file)

                            tex_bases = get_textures_from_material(str(cod2_path), shader_name)
                            for tex_base in tex_bases:
                                iwi_path = cod2_path / "main" / "images" / f"{tex_base}.iwi"
                                if iwi_path.exists():
                                    self.add_file(iwi_path)
                except Exception as e:
                    print(f"[IWD Packer] Failed to parse EFX {efx_path.name}: {e}")

            # Core map files
            base_mp = cod2_path / "main" / "maps" / "mp"
            self.add_file(map_gsc_path(cod2_path, mapname, for_write=True))
            self.add_file(map_gsc_path(cod2_path, mapname, fx=True, for_write=True))
            csv_path = map_csv_path(cod2_path, mapname, for_write=True)
            self.add_file(csv_path)
            self.add_file(base_mp / f"{mapname}.d3dbsp")
            self.add_file(map_arena_path(cod2_path, mapname, for_write=True))
            self.add_file(map_soundaliases_path(cod2_path, mapname, for_write=True))
            self.add_file(map_sun_path(cod2_path, mapname, for_write=True))

            # Loadscreen
            if csv_path.exists():
                try:
                    content = csv_path.read_text(encoding="utf-8", errors="ignore")
                    for rel_path in extract_loadscreen_iwi_candidates(content):
                        iwi_path = cod2_path / "main" / rel_path
                        if iwi_path.exists():
                            self.add_file(iwi_path)

                    match = re.search(
                        r"levelBriefing\s*,\s*(load(?:ing)?screen_[^\s,]+)",
                        content,
                        re.IGNORECASE,
                    )
                    if match:
                        mat_name = match.group(1).strip()
                        candidate = material_path(str(cod2_path), mat_name)
                        if candidate:
                            self.add_file(candidate)
                except Exception as e:
                    print(f"[Loadscreen] Error: {e}")

            # Populate UI
            for p in sorted(self.custom_files):
                if p.exists():
                    try:
                        rel = str(p.relative_to(cod2_path)).replace("\\", "/")
                        self.file_list.addItem(rel)
                    except Exception:
                        self.file_list.addItem(p.name)

            count = self.file_list.count()
            self.count_label.setText(f"Found {count} files")
            self.status_label.setText(f"Analysis complete — {count} files")
            self.pack_btn.setEnabled(count > 0)

        except Exception as e:
            import traceback

            print(traceback.format_exc())
            QtWidgets.QMessageBox.critical(self, "Analysis Failed", str(e))

    def pack_to_iwd(self) -> None:
        mapsavename = self.map_combo.currentText().strip()
        if not self.custom_files:
            QtWidgets.QMessageBox.warning(self, "Nothing to pack", "Run analysis first.")
            return
        save_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save IWD", f"zzz_{mapsavename}.iwd", "IWD Files (*.iwd)"
        )
        if not save_path:
            return
        temp_dir = Path(tempfile.mkdtemp())
        main_temp = temp_dir / "main"
        main_temp.mkdir(parents=True, exist_ok=True)
        try:
            for src_path in self.custom_files:
                if not src_path.exists():
                    continue
                rel = relative_to_asset_root(src_path)
                dest = main_temp / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_path, dest)
            with zipfile.ZipFile(save_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for root, _, files in os.walk(main_temp):
                    for file in files:
                        fp = Path(root) / file
                        zf.write(fp, fp.relative_to(main_temp))
            QtWidgets.QMessageBox.information(self, "Packed", f"Wrote {save_path}")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)