from __future__ import annotations

"""Shared Qt tab utilities used by multiple UI pages."""

from typing import Optional

from PyQt6 import QtWidgets


class QtTabMixin:
    """Mixin that exposes shared application helpers for individual tabs."""

    def __init__(self, app: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__()
        self.app = app

    def cod2_path(self) -> str:
        if self.app is None:
            return ""
        return self.app.cod2_path.text().strip()

    def map_name(self) -> str:
        if self.app is None:
            return ""
        return self.app.map_combo.currentText().strip()

    def populate_map_combo(
        self,
        combo: QtWidgets.QComboBox,
        maps: list[str],
        preferred: str | None = None,
    ) -> str:
        """Fill a map combo and restore preferred/current selection. Returns selected text."""
        current = (preferred or combo.currentText() or "").strip()
        combo.blockSignals(True)
        combo.clear()
        combo.addItems(maps)
        combo.blockSignals(False)
        if not maps:
            return ""
        if current in maps:
            combo.setCurrentText(current)
        else:
            combo.setCurrentIndex(0)
        return combo.currentText().strip()

    def set_file_status(
        self,
        label: QtWidgets.QLabel,
        button: QtWidgets.QPushButton | None,
        exists: bool,
        *,
        ok_text: str,
        missing_text: str,
        create_button_text: str | None = None,
    ) -> None:
        if exists:
            label.setText(ok_text)
            label.setStyleSheet("color: #127a20; font-weight: 600;")
            if button is not None:
                button.setEnabled(False)
        else:
            label.setText(missing_text)
            label.setStyleSheet("color: #b00020; font-weight: 600;")
            if button is not None:
                button.setEnabled(True)
                if create_button_text:
                    button.setText(create_button_text)

    def remove_selected_list_items(self, list_widget: QtWidgets.QListWidget) -> None:
        for item in list_widget.selectedItems():
            list_widget.takeItem(list_widget.row(item))

    def confirm_clear_list(
        self,
        list_widget: QtWidgets.QListWidget,
        title: str,
        message: str,
    ) -> bool:
        if not list_widget.count():
            return False
        reply = QtWidgets.QMessageBox.question(
            self,  # type: ignore[arg-type]
            title,
            message,
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
        )
        if reply == QtWidgets.QMessageBox.StandardButton.Yes:
            list_widget.clear()
            return True
        return False