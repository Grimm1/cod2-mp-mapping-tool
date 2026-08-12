"""Model viewer tab for browsing and previewing CoD2 xmodel thumbnails."""

import shutil
import tempfile
import urllib.request
import zipfile
from pathlib import Path

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import QThread, pyqtSignal

from ui.qt_tab_mixin import QtTabMixin


class DownloadWorker(QThread):
    progress = pyqtSignal(int)          # 0–100
    status = pyqtSignal(str)
    finished = pyqtSignal(bool, str)    # success, message

    def __init__(self, url: str, project_root: Path):
        super().__init__()
        self.url = url
        self.project_root = project_root

    def run(self):
        try:
            self.status.emit("Downloading archive...")
            temp_dir = Path(tempfile.mkdtemp())
            archive_path = temp_dir / "cod2xmodelimages.zip"

            # Download with progress
            def reporthook(block_num, block_size, total_size):
                if total_size > 0:
                    percent = int(block_num * block_size * 100 / total_size)
                    self.progress.emit(min(percent, 100))

            urllib.request.urlretrieve(self.url, archive_path, reporthook=reporthook)

            self.status.emit("Extracting files...")
            self.progress.emit(0)

            with zipfile.ZipFile(archive_path, "r") as zf:
                members = zf.namelist()
                total = len(members)
                for i, member in enumerate(members):
                    zf.extract(member, temp_dir)
                    if total > 0:
                        self.progress.emit(int((i + 1) * 100 / total))

            inner_dir = temp_dir / "cod2xmodelimages-main"
            if not inner_dir.exists():
                raise FileNotFoundError("Archive structure is incorrect.")

            for folder_name in ["thumbnails", "xmodel"]:
                src_dir = inner_dir / folder_name
                if not src_dir.exists():
                    continue
                dst_dir = self.project_root / folder_name
                if dst_dir.exists():
                    shutil.rmtree(dst_dir)
                shutil.copytree(src_dir, dst_dir)

            shutil.rmtree(temp_dir, ignore_errors=True)
            self.finished.emit(True, "Download and extraction complete!")

        except Exception as e:
            self.finished.emit(False, str(e))

class ModelViewerTab(QtTabMixin, QtWidgets.QWidget):
    def __init__(self, app: QtWidgets.QWidget) -> None:
        super().__init__(app)
        self.current_image_name = None
        self.thumbnail_dir = Path(__file__).resolve().parent.parent / "thumbnails"
        self.preview_dir = Path(__file__).resolve().parent.parent / "xmodel"
        self._build_ui()
        self._refresh_images()

    def _build_ui(self) -> None:
        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)

        # === LEFT PANEL: Controls + Thumbnail Grid ===
        left_panel = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left_panel)

        # Search
        search_layout = QtWidgets.QHBoxLayout()
        self.search_edit = QtWidgets.QLineEdit()
        self.search_edit.setPlaceholderText("Search models...")
        self.search_edit.textChanged.connect(self._filter_thumbnails)
        search_layout.addWidget(self.search_edit)
        left_layout.addLayout(search_layout)

        # Filter buttons
        filter_layout = QtWidgets.QHBoxLayout()
        self.filter_all = QtWidgets.QPushButton("All")
        self.filter_all.clicked.connect(lambda: self._set_filter(""))
        self.filter_weapons = QtWidgets.QPushButton("Weapons")
        self.filter_weapons.clicked.connect(lambda: self._set_filter("weapon"))
        self.filter_vehicles = QtWidgets.QPushButton("Vehicles")
        self.filter_vehicles.clicked.connect(lambda: self._set_filter("vehicle"))
        self.filter_furniture = QtWidgets.QPushButton("Furniture")
        self.filter_furniture.clicked.connect(lambda: self._set_filter("furniture"))
        self.filter_props = QtWidgets.QPushButton("props")
        self.filter_props.clicked.connect(lambda: self._set_filter("prop"))
        self.filter_military = QtWidgets.QPushButton("Military")
        self.filter_military.clicked.connect(lambda: self._set_filter("military"))  

        filter_layout.addWidget(self.filter_all)
        filter_layout.addWidget(self.filter_weapons)
        filter_layout.addWidget(self.filter_vehicles)
        filter_layout.addWidget(self.filter_furniture)
        filter_layout.addWidget(self.filter_props)
        filter_layout.addWidget(self.filter_military)
        left_layout.addLayout(filter_layout)

        # Thumbnail List
        self.thumb_list = QtWidgets.QListWidget()
        self.thumb_list.setViewMode(QtWidgets.QListView.ViewMode.IconMode)
        self.thumb_list.setMovement(QtWidgets.QListView.Movement.Static)
        self.thumb_list.setResizeMode(QtWidgets.QListView.ResizeMode.Adjust)
        self.thumb_list.setGridSize(QtCore.QSize(140, 160))
        self.thumb_list.setIconSize(QtCore.QSize(120, 120))
        self.thumb_list.setWordWrap(True)
        self.thumb_list.currentItemChanged.connect(self._show_preview_item)
        left_layout.addWidget(self.thumb_list)

        self.status_label = QtWidgets.QLabel("Loading thumbnails...")
        left_layout.addWidget(self.status_label)

        self.download_button = QtWidgets.QPushButton("Download Image Pack")
        self.download_button.clicked.connect(self.download_image_pack)
        left_layout.addWidget(self.download_button)

        main_layout.addWidget(left_panel, 1)

        # === RIGHT PANEL: Large Preview ===
        right_panel = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right_panel)

        self.preview_title = QtWidgets.QLabel("Preview")
        self.preview_title.setMaximumSize(QtCore.QSize(16777215, 100))
        self.preview_title.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignHCenter | QtCore.Qt.AlignmentFlag.AlignVCenter
        )
        right_layout.addWidget(self.preview_title)
        self.preview_label = QtWidgets.QLabel()
        self.preview_label.setStyleSheet("background-color: #2a2a2a; color: #dddddd;")
        self.preview_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        right_layout.addWidget(self.preview_label)

        # Copy button
        self.copy_button = QtWidgets.QPushButton("Copy Model Name")
        self.copy_button.clicked.connect(self.copy_model_name)
        self.copy_button.setEnabled(False)
        right_layout.addWidget(self.copy_button)

        main_layout.addWidget(right_panel, 2)

    def _set_filter(self, keyword: str):
        self.search_edit.setText(keyword)
        self._filter_thumbnails()

    def _filter_thumbnails(self):
        filter_text = self.search_edit.text().strip().lower()
        for i in range(self.thumb_list.count()):
            item = self.thumb_list.item(i)
            item.setHidden(filter_text not in item.text().lower())

    def _refresh_images(self) -> None:
        self.thumb_list.clear()
        thumbnails = sorted([p for p in self.thumbnail_dir.glob("*.png") if p.is_file()]) if self.thumbnail_dir.exists() else []

        if not thumbnails:
            self.status_label.setText("No thumbnails found. Download the pack below.")
            self.download_button.setEnabled(True)
            return

        for path in thumbnails:
            item = QtWidgets.QListWidgetItem(path.name)
            pixmap = QtGui.QPixmap(str(path))
            if not pixmap.isNull():
                item.setIcon(QtGui.QIcon(pixmap.scaled(120, 120, QtCore.Qt.AspectRatioMode.KeepAspectRatio)))
            self.thumb_list.addItem(item)

        self.status_label.setText(f"Loaded {len(thumbnails)} model thumbnails")
        self.download_button.setEnabled(False)
        if self.thumb_list.count():
            self.thumb_list.setCurrentRow(0)

    def _show_preview_item(self, item: QtWidgets.QListWidgetItem | None) -> None:
        if item is None:
            return
        self.current_image_name = item.text()
        self.copy_button.setEnabled(True)
        self._show_preview(self.current_image_name)

    def _show_preview(self, name: str) -> None:
        if not name:
            return
        preview_candidates = [self.preview_dir / name, self.thumbnail_dir / name]
        for path in preview_candidates:
            if path.exists() and path.is_file():
                pixmap = QtGui.QPixmap(str(path))
                if not pixmap.isNull():
                    size = self.preview_label.size()
                    self.preview_label.setPixmap(pixmap.scaled(size, QtCore.Qt.AspectRatioMode.KeepAspectRatio))
                    return
        self.preview_label.setText("Preview not available")

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        super().resizeEvent(event)
        if self.current_image_name:
            self._show_preview(self.current_image_name)

    def copy_model_name(self) -> None:
        if not self.current_image_name:
            return
        name = Path(self.current_image_name).stem
        QtWidgets.QApplication.clipboard().setText(name)
        self.status_label.setText(f"Copied: {name}")

    def download_image_pack(self) -> None:
        confirm = QtWidgets.QMessageBox.question(
            self,
            "Download model images",
            "Download the model image archive from GitHub?\nThis is a large file (~470 MB) and may take several minutes.",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No
        )
        if confirm != QtWidgets.QMessageBox.StandardButton.Yes:
            return

        self.download_button.setEnabled(False)
        self.status_label.setText("Starting download...")

        # Progress dialog
        self.progress_dialog = QtWidgets.QProgressDialog("Downloading...", "Cancel", 0, 100, self)
        self.progress_dialog.setWindowTitle("Model Image Pack")
        self.progress_dialog.setWindowModality(QtCore.Qt.WindowModality.WindowModal)
        self.progress_dialog.setMinimumDuration(0)
        self.progress_dialog.setValue(0)
        self.progress_dialog.show()

        project_root = Path(__file__).resolve().parent.parent
        url = "https://github.com/Grimm1/cod2xmodelimages/archive/refs/heads/main.zip"

        self.worker = DownloadWorker(url, project_root)
        self.worker.progress.connect(self.progress_dialog.setValue)
        self.worker.status.connect(self.status_label.setText)
        self.worker.finished.connect(self._on_download_finished)
        self.worker.start()

    def _on_download_finished(self, success: bool, message: str) -> None:
        self.progress_dialog.close()
        self.download_button.setEnabled(True)

        if success:
            self.status_label.setText(message)
            self._refresh_images()
            QtWidgets.QMessageBox.information(self, "Success", message)
        else:
            self.status_label.setText("Download failed.")
            QtWidgets.QMessageBox.critical(self, "Download failed", message)