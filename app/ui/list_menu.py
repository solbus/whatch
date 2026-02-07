import os
import random
import re
import tempfile
from collections import defaultdict
from datetime import datetime

from PyQt6.QtCore import QDateTime, QEvent, QProcess, QSize, Qt, QTimer
from PyQt6.QtGui import QColor, QGuiApplication, QIntValidator, QKeySequence
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDateTimeEdit,
    QDialog,
    QDialogButtonBox,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QTreeWidgetItemIterator,
    QHeaderView,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from app.core.library_db import LibraryDB
from app.core.list_db import ListDB
from app.core.people_db import PeopleDB
from app.ui.library_utils import _series_index_sort_key

NO_CHANGE = "__NO_CHANGE__"


class _ListAddTable(QTableWidget):
    def __init__(self, dialog):
        super().__init__(0, 3, dialog)
        self._dialog = dialog

    def keyPressEvent(self, event):
        if event.matches(QKeySequence.StandardKey.Paste) and self.currentColumn() == 1:
            text = QGuiApplication.clipboard().text()
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            if lines:
                row = self.currentRow()
                if row < 0:
                    row = max(0, self.rowCount() - 1)
                self._dialog.paste_titles(lines, row)
                return
        super().keyPressEvent(event)


class ListBulkAddDialog(QDialog):
    def __init__(self, people, parent=None):
        super().__init__(parent)
        self.people = people
        self._suppress_item_changed = False
        self.setWindowTitle("Add to List")
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Enter titles directly in the table. Paste multiple lines into Title to fill rows."))

        apply_row = QHBoxLayout()
        apply_row.addWidget(QLabel("Type:"))
        self.apply_type = QComboBox()
        self.apply_type.addItem("", NO_CHANGE)
        self.apply_type.addItem("Movie", "Movie")
        self.apply_type.addItem("TV Show", "TV")
        apply_row.addWidget(self.apply_type)

        apply_row.addWidget(QLabel("Added by:"))
        self.apply_person = QComboBox()
        self.apply_person.addItem("", NO_CHANGE)
        for person_id, name, _ in sorted(self.people, key=lambda p: (p[1] or "").lower()):
            self.apply_person.addItem(name, person_id)
        apply_row.addWidget(self.apply_person)

        apply_all = QPushButton("Apply to All")
        apply_all.clicked.connect(self.apply_to_all)
        apply_row.addWidget(apply_all)
        apply_row.addStretch(1)
        layout.addLayout(apply_row)

        self.table = _ListAddTable(self)
        self.table.setHorizontalHeaderLabels(["Type", "Title", "Added By"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.itemChanged.connect(self._on_item_changed)
        layout.addWidget(self.table)

        buttons = QHBoxLayout()
        remove_btn = QPushButton("Remove")
        remove_btn.clicked.connect(self.remove_selected_rows)
        buttons.addWidget(remove_btn)
        buttons.addStretch(1)
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(ok_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)
        self._add_row()
        self.resize(900, 620)

    def _type_combo(self):
        combo = QComboBox()
        combo.addItem("Movie", "Movie")
        combo.addItem("TV Show", "TV")
        return combo

    def _person_combo(self):
        combo = QComboBox()
        combo.addItem("", None)
        for person_id, name, _ in sorted(self.people, key=lambda p: (p[1] or "").lower()):
            combo.addItem(name, person_id)
        return combo

    def _set_combo_data(self, combo, value):
        for i in range(combo.count()):
            if combo.itemData(i) == value:
                combo.setCurrentIndex(i)
                return

    def _add_row(self, title="", media_type="Movie", added_by=None):
        row = self.table.rowCount()
        self._suppress_item_changed = True
        try:
            self.table.insertRow(row)
            type_combo = self._type_combo()
            self._set_combo_data(type_combo, media_type or "Movie")
            self.table.setCellWidget(row, 0, type_combo)
            self.table.setItem(row, 1, QTableWidgetItem(title))
            person_combo = self._person_combo()
            self._set_combo_data(person_combo, added_by)
            self.table.setCellWidget(row, 2, person_combo)
        finally:
            self._suppress_item_changed = False

    def _ensure_blank_last_row(self):
        if self.table.rowCount() == 0:
            self._add_row()
            return
        last_title_item = self.table.item(self.table.rowCount() - 1, 1)
        last_title = last_title_item.text().strip() if last_title_item else ""
        if last_title:
            self._add_row()

    def _on_item_changed(self, item):
        if self._suppress_item_changed:
            return
        if not item or item.column() != 1:
            return
        if item.row() == self.table.rowCount() - 1 and item.text().strip():
            self._add_row()
            self.table.resizeColumnsToContents()

    def paste_titles(self, lines, start_row):
        row = max(0, start_row)
        for text in lines:
            while row >= self.table.rowCount():
                self._add_row()
            title_item = self.table.item(row, 1)
            if title_item is None:
                self._suppress_item_changed = True
                try:
                    title_item = QTableWidgetItem("")
                    self.table.setItem(row, 1, title_item)
                finally:
                    self._suppress_item_changed = False
            title_item.setText(text)
            row += 1
        self._ensure_blank_last_row()
        self.table.setCurrentCell(min(row, self.table.rowCount() - 1), 1)
        self.table.resizeColumnsToContents()

    def remove_selected_rows(self):
        rows = sorted({idx.row() for idx in self.table.selectionModel().selectedRows()}, reverse=True)
        for row in rows:
            self.table.removeRow(row)
        if self.table.rowCount() == 0:
            self._add_row()
        self._ensure_blank_last_row()

    def apply_to_all(self):
        apply_type = self.apply_type.currentData()
        apply_person = self.apply_person.currentData()
        for row in range(self.table.rowCount()):
            type_combo = self.table.cellWidget(row, 0)
            person_combo = self.table.cellWidget(row, 2)
            if apply_type in ("Movie", "TV"):
                self._set_combo_data(type_combo, apply_type)
            if apply_person != NO_CHANGE:
                self._set_combo_data(person_combo, apply_person)

    def get_results(self):
        results = []
        for row in range(self.table.rowCount()):
            media_type = self.table.cellWidget(row, 0).currentData()
            title_item = self.table.item(row, 1)
            title = title_item.text().strip() if title_item else ""
            added_by = self.table.cellWidget(row, 2).currentData()

            if not title:
                continue
            results.append({"media_type": media_type, "title": title, "added_by_person_id": added_by})
        return results, None


class ListEditDialog(QDialog):
    def __init__(self, rows, people, parent=None):
        super().__init__(parent)
        self.rows = rows
        self.people = people
        self.setWindowTitle("Edit List Items")
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        apply_row = QHBoxLayout()
        apply_row.addWidget(QLabel("Type:"))
        self.apply_type = QComboBox()
        self.apply_type.addItem("", NO_CHANGE)
        self.apply_type.addItem("Movie", "Movie")
        self.apply_type.addItem("TV Show", "TV")
        apply_row.addWidget(self.apply_type)

        apply_row.addWidget(QLabel("Added by:"))
        self.apply_person = QComboBox()
        self.apply_person.addItem("", NO_CHANGE)
        for person_id, name, _ in sorted(self.people, key=lambda p: (p[1] or "").lower()):
            self.apply_person.addItem(name, person_id)
        apply_row.addWidget(self.apply_person)

        apply_all = QPushButton("Apply to All")
        apply_all.clicked.connect(self.apply_to_all)
        apply_row.addWidget(apply_all)
        apply_row.addStretch(1)
        layout.addLayout(apply_row)

        self.table = QTableWidget(len(self.rows), 4)
        self.table.setHorizontalHeaderLabels(["Type", "Title", "Added By", "Added On"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._fill()
        self.table.resizeColumnsToContents()
        layout.addWidget(self.table)

        buttons = QHBoxLayout()
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(ok_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)
        self.resize(860, 500)

    def _set_combo_data(self, combo, value):
        for i in range(combo.count()):
            if combo.itemData(i) == value:
                combo.setCurrentIndex(i)
                return

    def _parse_added_at(self, text):
        if not text:
            return None
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(text.strip(), fmt)
            except ValueError:
                pass
        return None

    def _fill(self):
        people_sorted = sorted(self.people, key=lambda p: (p[1] or "").lower())
        for row, item in enumerate(self.rows):
            type_combo = QComboBox()
            type_combo.addItem("Movie", "Movie")
            type_combo.addItem("TV Show", "TV")
            self._set_combo_data(type_combo, item["media_type"])
            self.table.setCellWidget(row, 0, type_combo)
            self.table.setItem(row, 1, QTableWidgetItem(item["title"]))

            person_combo = QComboBox()
            person_combo.addItem("(None)", None)
            for person_id, name, _ in people_sorted:
                person_combo.addItem(name, person_id)
            self._set_combo_data(person_combo, item.get("added_by_person_id"))
            self.table.setCellWidget(row, 2, person_combo)

            date_edit = QDateTimeEdit()
            date_edit.setCalendarPopup(True)
            date_edit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
            date_edit.setDateTime(QDateTime(self._parse_added_at(item.get("added_at")) or datetime.utcnow()))
            self.table.setCellWidget(row, 3, date_edit)

    def apply_to_all(self):
        apply_type = self.apply_type.currentData()
        apply_person = self.apply_person.currentData()
        for row in range(self.table.rowCount()):
            type_combo = self.table.cellWidget(row, 0)
            person_combo = self.table.cellWidget(row, 2)
            if apply_type in ("Movie", "TV"):
                self._set_combo_data(type_combo, apply_type)
            if apply_person != NO_CHANGE:
                self._set_combo_data(person_combo, apply_person)

    def get_results(self):
        output = []
        for row, base in enumerate(self.rows):
            title_item = self.table.item(row, 1)
            title = title_item.text().strip() if title_item else ""
            if not title:
                return None
            output.append(
                {
                    "id": base["id"],
                    "media_type": self.table.cellWidget(row, 0).currentData(),
                    "title": title,
                    "added_by_person_id": self.table.cellWidget(row, 2).currentData(),
                    "added_at": self.table.cellWidget(row, 3).dateTime().toString("yyyy-MM-ddTHH:mm:ss"),
                    "library_linked": base.get("library_linked", 0),
                }
            )
        return output


class LinkConfirmDialog(QDialog):
    def __init__(self, candidates, parent=None):
        super().__init__(parent)
        self.candidates = candidates
        self.setWindowTitle("Confirm List Links")
        layout = QVBoxLayout(self)
        self.table = QTableWidget(len(candidates), 3)
        self.table.setHorizontalHeaderLabels(["Link", "List Title", "Library Title"])
        self._fill()
        self.table.resizeColumnsToContents()
        layout.addWidget(self.table)
        buttons = QHBoxLayout()
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(ok_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)
        self.resize(960, 500)

    def _fill(self):
        for row, candidate in enumerate(self.candidates):
            check = QTableWidgetItem()
            check.setFlags(
                Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsUserCheckable
            )
            check.setCheckState(Qt.CheckState.Checked)
            check.setData(Qt.ItemDataRole.UserRole, candidate["id"])
            self.table.setItem(row, 0, check)
            for col, text in enumerate([candidate["list_title"], candidate["library_title"]], start=1):
                item = QTableWidgetItem(text)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, col, item)

    def selected_ids(self):
        ids = []
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and item.checkState() == Qt.CheckState.Checked:
                ids.append(item.data(Qt.ItemDataRole.UserRole))
        return ids


class DoListSetupDialog(QDialog):
    def __init__(self, people, parent=None):
        super().__init__(parent)
        self._people = sorted(people, key=lambda p: (p[1] or "").lower())
        self._results = []
        self.setWindowTitle("Who's making the list?")
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        self.setStyleSheet(
            """
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #141b29, stop:1 #1a2637);
            }
            QTableWidget {
                background-color: #1f2d42;
                border: 1px solid #304a6e;
                border-radius: 8px;
                gridline-color: #2c3f5c;
            }
            QHeaderView::section {
                background-color: #2a3d59;
                color: #e8f4ff;
                border: none;
                padding: 6px;
                font-weight: 600;
            }
            QLineEdit, QSpinBox {
                background-color: #182233;
                color: #ecf0f1;
                border: 1px solid #41638f;
                border-radius: 6px;
                padding: 4px 6px;
            }
            QPushButton {
                background-color: #1f7a8c;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 6px 14px;
                font-weight: 700;
            }
            QPushButton:hover {
                background-color: #249bb2;
            }
            """
        )
        title = QLabel("Who's making the list?")
        title.setStyleSheet("font-size: 20px; font-weight: 700; color: #5dade2;")
        layout.addWidget(title)
        subtitle = QLabel("Set optional target counts and turn order, then press Start.")
        subtitle.setStyleSheet("color: #d6eaf8;")
        layout.addWidget(subtitle)

        self.table = QTableWidget(len(self._people), 4)
        self.table.setHorizontalHeaderLabels(["Include", "Person", "# Picks", "Order"])
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(True)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)

        for row, person in enumerate(self._people):
            include = QTableWidgetItem()
            include.setFlags(
                Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable
            )
            include.setCheckState(Qt.CheckState.Checked)
            include.setData(Qt.ItemDataRole.UserRole, {"person_id": person[0], "name": person[1]})
            self.table.setItem(row, 0, include)

            name_item = QTableWidgetItem(person[1])
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 1, name_item)

            picks_edit = QLineEdit("")
            picks_edit.setPlaceholderText("optional")
            picks_edit.setValidator(QIntValidator(0, 9999, picks_edit))
            self.table.setCellWidget(row, 2, picks_edit)

            order_spin = QSpinBox()
            order_spin.setRange(1, 999)
            order_spin.setValue(row + 1)
            self.table.setCellWidget(row, 3, order_spin)

        self.table.resizeColumnsToContents()
        self.table.setColumnWidth(1, max(self.table.columnWidth(1), 160))
        self.table.setColumnWidth(2, max(self.table.columnWidth(2), 110))
        self.table.setColumnWidth(3, max(self.table.columnWidth(3), 82))
        table_height = self.table.horizontalHeader().height() + (self.table.rowHeight(0) * max(1, self.table.rowCount())) + 8
        table_height = min(max(table_height, 130), 260)
        self.table.setMinimumHeight(table_height)
        self.table.setMaximumHeight(table_height)
        layout.addWidget(self.table)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Start")
        buttons.accepted.connect(self._on_start)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.resize(560, min(360, table_height + 140))

    def _on_start(self):
        picked = []
        used_orders = set()
        for row in range(self.table.rowCount()):
            include_item = self.table.item(row, 0)
            if not include_item or include_item.checkState() != Qt.CheckState.Checked:
                continue
            meta = include_item.data(Qt.ItemDataRole.UserRole) or {}
            order = self.table.cellWidget(row, 3).value()
            if order in used_orders:
                QMessageBox.warning(self, "Input Error", "Order values must be unique.")
                return
            used_orders.add(order)
            raw_target = self.table.cellWidget(row, 2).text().strip()
            target = int(raw_target) if raw_target else None
            picked.append(
                {
                    "person_id": meta.get("person_id"),
                    "name": meta.get("name") or self.table.item(row, 1).text().strip(),
                    "target": target,
                    "order": order,
                }
            )

        if not picked:
            QMessageBox.warning(self, "Input Error", "Select at least one person.")
            return
        self._results = sorted(picked, key=lambda p: p["order"])
        self.accept()

    def get_results(self):
        return list(self._results)


class LastPickerDialog(QDialog):
    def __init__(self, initial_people, all_people, parent=None):
        super().__init__(parent)
        self._results = []
        self._last_picker_person_id = None
        self._last_picker_name = ""
        self._rows = []
        self.setWindowTitle("Who's picking last?")
        self._build_ui(initial_people, all_people)

    def _build_ui(self, initial_people, all_people):
        layout = QVBoxLayout(self)
        self.setStyleSheet(
            """
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #261f15, stop:1 #2f2a1d);
            }
            QTableWidget {
                background-color: #3a3023;
                border: 1px solid #6e5b3f;
                border-radius: 8px;
                gridline-color: #5b4d36;
            }
            QHeaderView::section {
                background-color: #5c4a31;
                color: #fff5d6;
                border: none;
                padding: 6px;
                font-weight: 600;
            }
            QSpinBox, QComboBox {
                background-color: #30281d;
                color: #fff5d6;
                border: 1px solid #8d734f;
                border-radius: 6px;
                padding: 3px 6px;
            }
            QPushButton {
                background-color: #af7c2c;
                color: #1d1306;
                border: none;
                border-radius: 8px;
                padding: 6px 14px;
                font-weight: 700;
            }
            QPushButton:hover {
                background-color: #d39c45;
            }
            """
        )
        title = QLabel("Who's picking last?")
        title.setStyleSheet("font-size: 20px; font-weight: 700; color: #f4d03f;")
        layout.addWidget(title)
        subtitle = QLabel("Use Include to add/remove pickers, then mark exactly one Last Picker.")
        subtitle.setStyleSheet("color: #f9e79f;")
        layout.addWidget(subtitle)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Include", "Last Picker", "Person", "Order"])
        self.table.verticalHeader().setVisible(False)
        self._last_group = QButtonGroup(self)
        self._last_group.setExclusive(True)

        all_lookup = {person[0]: person[1] for person in all_people}
        for person in initial_people:
            self._add_row(person["person_id"], person["name"], person["order"], included=True, checked_last=False)

        self.add_combo = QComboBox()
        existing_ids = {row["person_id"] for row in self._rows}
        for person_id, name, _ in sorted(all_people, key=lambda p: (p[1] or "").lower()):
            if person_id not in existing_ids:
                self.add_combo.addItem(name, person_id)

        add_row = QHBoxLayout()
        add_row.addWidget(QLabel("Add person:"))
        add_row.addWidget(self.add_combo)
        add_btn = QPushButton("Add")
        add_btn.clicked.connect(lambda: self._add_selected_from_combo(all_lookup))
        add_row.addWidget(add_btn)
        add_row.addStretch(1)
        layout.addLayout(add_row)
        layout.addWidget(self.table)
        self._update_table_height()

        if self._rows:
            self._rows[0]["last_radio"].setChecked(True)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Start Removing")
        buttons.accepted.connect(self._on_start)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.resize(620, 420)

    def _update_table_height(self):
        visible_rows = max(1, min(7, self.table.rowCount()))
        row_height = self.table.rowHeight(0) if self.table.rowCount() else 28
        table_height = self.table.horizontalHeader().height() + (row_height * visible_rows) + 8
        self.table.setMinimumHeight(table_height)
        self.table.setMaximumHeight(table_height)

    def _add_row(self, person_id, name, order, included, checked_last):
        row = self.table.rowCount()
        self.table.insertRow(row)

        include_item = QTableWidgetItem()
        include_item.setFlags(
            Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable
        )
        include_item.setCheckState(Qt.CheckState.Checked if included else Qt.CheckState.Unchecked)
        include_item.setData(Qt.ItemDataRole.UserRole, {"person_id": person_id, "name": name})
        self.table.setItem(row, 0, include_item)

        last_radio = QRadioButton()
        self._last_group.addButton(last_radio)
        if checked_last:
            last_radio.setChecked(True)
        radio_wrap = QWidget()
        radio_layout = QHBoxLayout(radio_wrap)
        radio_layout.setContentsMargins(0, 0, 0, 0)
        radio_layout.addWidget(last_radio, alignment=Qt.AlignmentFlag.AlignCenter)
        self.table.setCellWidget(row, 1, radio_wrap)

        name_item = QTableWidgetItem(name)
        name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.table.setItem(row, 2, name_item)

        order_spin = QSpinBox()
        order_spin.setRange(1, 999)
        order_spin.setValue(order)
        self.table.setCellWidget(row, 3, order_spin)

        self._rows.append({"person_id": person_id, "name": name, "last_radio": last_radio})
        self.table.resizeColumnsToContents()
        self.table.setColumnWidth(2, max(self.table.columnWidth(2), 150))
        self._update_table_height()

    def _add_selected_from_combo(self, all_lookup):
        person_id = self.add_combo.currentData()
        if person_id is None:
            return
        name = all_lookup.get(person_id) or self.add_combo.currentText().strip()
        self._add_row(person_id, name, self.table.rowCount() + 1, included=True, checked_last=False)
        self.add_combo.removeItem(self.add_combo.currentIndex())
        if self._last_group.checkedButton() is None and self._rows:
            self._rows[0]["last_radio"].setChecked(True)

    def _on_start(self):
        included = []
        used_orders = set()
        selected_last = None
        for row in range(self.table.rowCount()):
            include_item = self.table.item(row, 0)
            if not include_item or include_item.checkState() != Qt.CheckState.Checked:
                continue
            meta = include_item.data(Qt.ItemDataRole.UserRole) or {}
            order = self.table.cellWidget(row, 3).value()
            if order in used_orders:
                QMessageBox.warning(self, "Input Error", "Order values must be unique.")
                return
            used_orders.add(order)

            radio = self._rows[row]["last_radio"]
            person = {
                "person_id": meta.get("person_id"),
                "name": meta.get("name") or self.table.item(row, 2).text().strip(),
                "order": order,
            }
            included.append(person)
            if radio.isChecked():
                selected_last = person

        if len(included) < 1:
            QMessageBox.warning(self, "Input Error", "Include at least one picker.")
            return
        if not selected_last or selected_last["person_id"] not in {p["person_id"] for p in included}:
            QMessageBox.warning(self, "Input Error", "Select one included person as the last picker.")
            return

        self._results = sorted(included, key=lambda p: p["order"])
        self._last_picker_person_id = selected_last["person_id"]
        self._last_picker_name = selected_last["name"]
        self.accept()

    def get_results(self):
        return list(self._results), self._last_picker_person_id, self._last_picker_name


class EliminationDialog(QDialog):
    def __init__(self, picks, picker_order, last_picker_name, parent=None):
        super().__init__(parent)
        self._active = list(picks)
        self._picker_order = list(picker_order)
        self._required_kind = None
        self._turn = 1
        self._winner = None
        self._winner_title = ""

        self._current_picker_idx = self._initial_picker_index(last_picker_name)
        self.setWindowTitle("Do A List: Eliminate")
        self._build_ui()
        self._refresh_ui()

    def _initial_picker_index(self, last_picker_name):
        if not self._picker_order:
            return 0
        try:
            last_idx = self._picker_order.index(last_picker_name)
        except ValueError:
            last_idx = 0
        return (last_idx - (len(self._active) - 2)) % len(self._picker_order) if self._active else 0

    def _build_ui(self):
        layout = QVBoxLayout(self)
        self.setStyleSheet(
            """
            QDialog {
                background: qradialgradient(cx:0.5, cy:0.15, radius:1.0, fx:0.5, fy:0.15, stop:0 #1f2e3d, stop:1 #151f2b);
            }
            QTableWidget {
                background-color: #1f2b38;
                border: 1px solid #36506b;
                border-radius: 8px;
                gridline-color: #2d435a;
            }
            QHeaderView::section {
                background-color: #2c4258;
                color: #e8f6ff;
                border: none;
                padding: 6px;
                font-weight: 700;
            }
            """
        )

        self.turn_label = QLabel("")
        self.turn_label.setStyleSheet("font-size: 18px; font-weight: 800; color: #5dade2;")
        layout.addWidget(self.turn_label)

        self.rule_label = QLabel("")
        self.rule_label.setStyleSheet("font-size: 14px; color: #d6eaf8;")
        layout.addWidget(self.rule_label)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Eliminate", "Title", "Picked By"])
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #34495e;
                color: #ecf0f1;
                border: none;
                border-radius: 8px;
                padding: 6px 14px;
            }
            QPushButton:hover { background-color: #4a647d; }
            """
        )
        cancel_btn.clicked.connect(self.reject)
        button_row = QHBoxLayout()
        button_row.addStretch(1)
        button_row.addWidget(cancel_btn)
        layout.addLayout(button_row)
        self.resize(760, 520)

    def _relation(self, picker_name, entry):
        return "self" if entry["picked_by"] == picker_name else "other"

    def _eligible_for_required_kind(self, picker_name):
        if not self._required_kind:
            return list(self._active)
        return [entry for entry in self._active if self._relation(picker_name, entry) == self._required_kind]

    def _refresh_ui(self):
        if len(self._active) <= 1:
            self._winner = self._active[0] if self._active else None
            self._winner_title = self._winner["title"] if self._winner else ""
            self.accept()
            return

        picker_name = self._picker_order[self._current_picker_idx] if self._picker_order else ""
        self.turn_label.setText(f"{picker_name} removing (turn {self._turn})")
        if self._required_kind == "self":
            rule = "Rule: eliminate one of your own picks."
        elif self._required_kind == "other":
            rule = "Rule: eliminate a pick made by someone else."
        else:
            rule = "Rule: choose self-delete or other-delete for this pair."
        self.rule_label.setText(rule)

        self.table.setRowCount(0)
        for row, entry in enumerate(self._active):
            self.table.insertRow(row)
            elim_btn = QPushButton("X")
            elim_btn.setFixedWidth(44)
            relation = self._relation(picker_name, entry)
            elim_btn.setStyleSheet(
                """
                QPushButton {
                    border: none;
                    border-radius: 8px;
                    color: white;
                    font-weight: 700;
                    background-color: #117a65;
                    padding: 3px 8px;
                }
                QPushButton:hover { background-color: #17a589; }
                """
                if relation == "self"
                else """
                QPushButton {
                    border: none;
                    border-radius: 8px;
                    color: white;
                    font-weight: 700;
                    background-color: #6c3483;
                    padding: 3px 8px;
                }
                QPushButton:hover { background-color: #884ea0; }
                """
            )
            elim_btn.clicked.connect(lambda _checked=False, item_id=entry["id"]: self._eliminate(item_id))
            self.table.setCellWidget(row, 0, elim_btn)
            title_item = QTableWidgetItem(entry["title"])
            picker_item = QTableWidgetItem(entry["picked_by"])
            if relation == "self":
                bg = QColor("#1f3b45")
            else:
                bg = QColor("#36233f")
            title_item.setBackground(bg)
            picker_item.setBackground(bg)
            self.table.setItem(row, 1, title_item)
            self.table.setItem(row, 2, picker_item)
        self.table.resizeColumnsToContents()

    def _eliminate(self, item_id):
        picker_name = self._picker_order[self._current_picker_idx] if self._picker_order else ""
        target = next((entry for entry in self._active if entry["id"] == item_id), None)
        if not target:
            return

        relation = self._relation(picker_name, target)
        if self._required_kind and relation != self._required_kind:
            eligible = self._eligible_for_required_kind(picker_name)
            if eligible:
                QMessageBox.warning(self, "Rule", "This turn must remove the same kind as the previous turn.")
                return

        self._active = [entry for entry in self._active if entry["id"] != item_id]
        if self._turn % 2 == 1:
            self._required_kind = relation
        else:
            self._required_kind = None

        if self._picker_order:
            self._current_picker_idx = (self._current_picker_idx + 1) % len(self._picker_order)
        self._turn += 1
        self._refresh_ui()

    def get_winner(self):
        return self._winner


class WinnerDialog(QDialog):
    _PHRASES = [
        "{title} wins!",
        "{title} it is!",
        "{title}, booyah!",
        "{title} takes the crown!",
        "{title} gets the spotlight!",
    ]

    def __init__(self, title, parent=None):
        super().__init__(parent)
        self._title = title
        self.setWindowTitle("Winner")
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        self.setStyleSheet(
            """
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #241f3a, stop:1 #352a5a);
            }
            QCheckBox {
                color: #f5eef8;
                font-size: 14px;
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #8e44ad, stop:1 #a569bd);
                color: white;
                border: none;
                border-radius: 8px;
                padding: 6px 18px;
                font-weight: 700;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #9b59b6, stop:1 #bb8fce);
            }
            """
        )
        sparkle = QLabel("* * *")
        sparkle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sparkle.setStyleSheet("font-size: 18px; color: #d2b4de; letter-spacing: 5px;")
        layout.addWidget(sparkle)
        label = QLabel(random.choice(self._PHRASES).format(title=self._title))
        label.setStyleSheet("font-size: 24px; font-weight: 800; color: #6c3483;")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)

        self.add_to_library_check = QCheckBox("Add winner to Library as placeholder")
        self.remove_from_list_check = QCheckBox("Remove winner from List")
        layout.addWidget(self.add_to_library_check)
        layout.addWidget(self.remove_from_list_check)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)
        self.resize(520, 240)

    def get_options(self):
        return self.add_to_library_check.isChecked(), self.remove_from_list_check.isChecked()


class ListMenu(QWidget):
    def __init__(self, back_callback, parent=None):
        super().__init__(parent)
        self.back_callback = back_callback
        self.db = ListDB()
        self.library_db = LibraryDB()
        self.people_db = PeopleDB()
        self._mpv_processes = {}
        self.items_by_id = {}
        self.library_items_by_path = {}
        self.link_info_by_id = {}
        self._do_list_state = None
        self._do_list_hue = 160
        self._build_ui()
        self.load_items()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        self.do_list_button = QPushButton("DO A LIST")
        self.do_list_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.do_list_button.setMinimumHeight(64)
        self.do_list_button.setStyleSheet(
            """
            QPushButton {
                border: none;
                border-radius: 18px;
                color: white;
                font-size: 34px;
                font-weight: 800;
                padding: 10px 18px;
            }
            QPushButton:hover { padding-top: 8px; padding-bottom: 12px; }
            """
        )
        glow = QGraphicsDropShadowEffect(self)
        glow.setBlurRadius(24)
        glow.setOffset(0, 6)
        glow.setColor(QColor("#17a589"))
        self.do_list_button.setGraphicsEffect(glow)
        self.do_list_button.clicked.connect(self._start_do_list)
        layout.addWidget(self.do_list_button)

        self._do_list_anim_timer = QTimer(self)
        self._do_list_anim_timer.timeout.connect(self._animate_do_list_button)
        self._do_list_anim_timer.start(150)
        self._animate_do_list_button()

        self.mode_status_label = QLabel("")
        self.mode_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.mode_status_label.setStyleSheet("font-size: 24px; font-weight: 800; color: #2ecc71; letter-spacing: 1px;")
        self.mode_status_label.hide()
        layout.addWidget(self.mode_status_label)

        self.tree = QTreeWidget()
        self._row_height = 36
        self.tree.setColumnCount(6)
        self.tree.setHeaderLabels(["", "Title", "Added On", "Added By", "Notes", "Play"])
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.tree.setIndentation(14)
        self.tree.itemDoubleClicked.connect(self.handle_double_click)
        self.tree.itemExpanded.connect(lambda _item: self._auto_resize_columns())
        self.tree.itemCollapsed.connect(lambda _item: self._auto_resize_columns())
        self.tree.setUniformRowHeights(False)
        self.tree.setStyleSheet("QTreeWidget::item { padding-top: 6px; padding-bottom: 6px; }")
        header = self.tree.header()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setStretchLastSection(True)
        header.sectionDoubleClicked.connect(self._on_header_double_click)
        header.installEventFilter(self)
        header.viewport().installEventFilter(self)
        layout.addWidget(self.tree)
        buttons = QHBoxLayout()
        for label, handler in (
            ("Add to List", self.add_to_list),
            ("Edit", self.edit_selected),
            ("Remove", self.remove_selected),
            ("Back", self.go_back),
        ):
            button = QPushButton(label)
            button.clicked.connect(handler)
            buttons.addWidget(button)
        layout.addLayout(buttons)
        self.done_row = QHBoxLayout()
        self.done_row.addStretch(1)
        self.done_button = QPushButton("Done")
        self.done_button.setStyleSheet(
            """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #16a085, stop:1 #1abc9c);
                color: white;
                border: none;
                border-radius: 10px;
                padding: 7px 28px;
                font-weight: 700;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1abc9c, stop:1 #48c9b0);
            }
            """
        )
        self.done_button.clicked.connect(self._advance_do_list_picker)
        self.done_button.hide()
        self.done_row.addWidget(self.done_button)
        self.done_row.addStretch(1)
        layout.addLayout(self.done_row)

    def _animate_do_list_button(self):
        self._do_list_hue = (self._do_list_hue + 7) % 360
        a = QColor.fromHsv(self._do_list_hue, 190, 220).name()
        b = QColor.fromHsv((self._do_list_hue + 55) % 360, 180, 235).name()
        c = QColor.fromHsv((self._do_list_hue + 125) % 360, 170, 210).name()
        self.do_list_button.setStyleSheet(
            f"""
            QPushButton {{
                border: none;
                border-radius: 18px;
                color: white;
                font-size: 34px;
                font-weight: 800;
                padding: 10px 18px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {a}, stop:0.5 {b}, stop:1 {c});
            }}
            QPushButton:hover {{
                padding-top: 8px;
                padding-bottom: 12px;
            }}
            """
        )
        if self._do_list_state and self._do_list_state.get("phase") == "collecting":
            status_color = QColor.fromHsv((self._do_list_hue + 145) % 360, 170, 220).name()
            self.mode_status_label.setStyleSheet(
                f"font-size: 24px; font-weight: 800; color: {status_color}; letter-spacing: 1px;"
            )

    def _start_do_list(self):
        people = self.people_db.get_people()
        if not people:
            QMessageBox.warning(self, "People Needed", "Add at least one person in People first.")
            return
        dialog = DoListSetupDialog(people, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        participants = dialog.get_results()
        if not participants:
            return
        self._do_list_state = {
            "phase": "collecting",
            "participants": [
                {
                    "person_id": p["person_id"],
                    "name": p["name"],
                    "target": p["target"],
                    "order": p["order"],
                    "picked_ids": set(),
                    "done": False,
                }
                for p in participants
            ],
            "current_index": 0,
            "picked_by_item_id": {},
        }
        self._refresh_do_list_banner()
        self.load_items()

    def _finish_do_list(self):
        self._do_list_state = None
        self._refresh_do_list_banner()
        self.load_items()

    def _refresh_do_list_banner(self):
        is_collecting = self._do_list_state and self._do_list_state.get("phase") == "collecting"
        self.do_list_button.setVisible(not is_collecting)
        self.mode_status_label.setVisible(bool(is_collecting))
        self.done_button.setVisible(bool(is_collecting))
        if is_collecting:
            self.mode_status_label.setText(self._do_list_status_text())
            self.tree.setColumnWidth(0, 56)
            self.tree.header().showSection(0)
        else:
            self.mode_status_label.setText("")
            self.tree.setColumnWidth(0, 0)
            self.tree.header().hideSection(0)
        self._auto_resize_columns()

    def _current_participant(self):
        if not self._do_list_state:
            return None
        participants = self._do_list_state.get("participants") or []
        idx = self._do_list_state.get("current_index", 0)
        if idx < 0 or idx >= len(participants):
            return None
        return participants[idx]

    def _do_list_status_text(self):
        participant = self._current_participant()
        if not participant:
            return ""
        picked = len(participant["picked_ids"])
        target = participant.get("target")
        if target is None:
            return f"{participant['name']} picking"
        return f"{participant['name']} picking ({target - picked} selections left)"

    def _participant_name_for_item(self, item_id):
        if not self._do_list_state:
            return ""
        person_id = self._do_list_state["picked_by_item_id"].get(item_id)
        if person_id is None:
            return ""
        for person in self._do_list_state["participants"]:
            if person["person_id"] == person_id:
                return person["name"]
        return ""

    def _toggle_pick(self, item_id):
        if not self._do_list_state or self._do_list_state.get("phase") != "collecting":
            return
        participant = self._current_participant()
        if not participant:
            return

        owner_id = self._do_list_state["picked_by_item_id"].get(item_id)
        if owner_id == participant["person_id"]:
            self._do_list_state["picked_by_item_id"].pop(item_id, None)
            participant["picked_ids"].discard(item_id)
        elif owner_id is not None:
            owner_name = self._participant_name_for_item(item_id) or "Another person"
            QMessageBox.warning(self, "Already Picked", f"That title is already picked by {owner_name}.")
            return
        else:
            self._do_list_state["picked_by_item_id"][item_id] = participant["person_id"]
            participant["picked_ids"].add(item_id)

        self._refresh_do_list_banner()
        self.load_items()

    def _advance_do_list_picker(self):
        if not self._do_list_state or self._do_list_state.get("phase") != "collecting":
            return
        participants = self._do_list_state["participants"]
        idx = self._do_list_state["current_index"]
        if idx >= len(participants):
            return
        current = participants[idx]
        current["done"] = True

        if idx + 1 < len(participants):
            nxt = participants[idx + 1]
            if nxt.get("target") is None:
                nxt["target"] = len(current["picked_ids"])
            self._do_list_state["current_index"] = idx + 1
            self._refresh_do_list_banner()
            self.load_items()
            return

        if not self._start_last_picker_phase():
            self._refresh_do_list_banner()
            self.load_items()

    def _start_last_picker_phase(self):
        if not self._do_list_state:
            return False
        participants = self._do_list_state["participants"]
        picks = []
        for item_id, person_id in self._do_list_state["picked_by_item_id"].items():
            row = self.items_by_id.get(item_id)
            if not row:
                continue
            person_name = ""
            for person in participants:
                if person["person_id"] == person_id:
                    person_name = person["name"]
                    break
            picks.append({"id": row[0], "media_type": row[1], "title": row[2], "picked_by": person_name})
        if not picks:
            QMessageBox.warning(self, "No Picks", "No titles were selected for this list.")
            self._finish_do_list()
            return True

        all_people = self.people_db.get_people()
        dialog = LastPickerDialog(participants, all_people, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return False
        picker_order, last_picker_person_id, last_picker_name = dialog.get_results()
        if not picker_order:
            return False
        picker_names = [person["name"] for person in picker_order]

        winner = None
        if len(picks) == 1:
            winner = picks[0]
        else:
            elim_dialog = EliminationDialog(picks, picker_names, last_picker_name, parent=self)
            if elim_dialog.exec() != QDialog.DialogCode.Accepted:
                return False
            winner = elim_dialog.get_winner()
            if not winner:
                return False

        winner_dialog = WinnerDialog(winner["title"], parent=self)
        add_library = False
        remove_list = False
        if winner_dialog.exec() == QDialog.DialogCode.Accepted:
            add_library, remove_list = winner_dialog.get_options()

        if add_library:
            self._add_winner_placeholder(winner)
        if remove_list:
            self.db.delete_by_ids([winner["id"]])
        if last_picker_person_id is not None:
            self.people_db.increment_list_last_pick_count(last_picker_person_id)

        self._finish_do_list()
        return True

    def _winner_placeholder_path(self, media_type, title):
        slug = re.sub(r"[^a-z0-9]+", "-", (title or "").lower()).strip("-")
        slug = slug or "untitled"
        return f"__list_winner__::{media_type}::{slug}"

    def _add_winner_placeholder(self, winner):
        media_type = winner["media_type"]
        title = winner["title"]
        path = self._winner_placeholder_path(media_type, title)
        is_tv = media_type == "TV"
        self.library_db.add_item(
            path=path,
            media_type=media_type,
            display_title=title,
            is_series=is_tv,
            series_title=title if is_tv else None,
            show_title=title if is_tv else None,
            is_placeholder=True,
        )

    def _normalize_title(self, text):
        return " ".join((text or "").strip().lower().split())

    def _title_sort_key(self, text):
        lowered = (text or "").strip().lower()
        for prefix in ("the ", "el ", "la "):
            if lowered.startswith(prefix):
                return lowered[len(prefix):]
        return lowered

    def _build_library_index(self, library_items):
        index = {"Movie": defaultdict(set), "TV": defaultdict(set)}
        for item in library_items:
            media_type = item[2]
            if media_type not in index or item[9]:
                continue
            keys = {self._normalize_title(item[3])}
            if media_type == "Movie" and item[4] and item[5]:
                keys.add(self._normalize_title(item[5]))
            if media_type == "TV" and item[5]:
                keys.add(self._normalize_title(item[5]))
            for key in keys:
                if key:
                    index[media_type][key].add(item[1])
        return index

    def _sorted_library_paths(self, paths):
        def key(path):
            item = self.library_items_by_path.get(path)
            if not item:
                return (_series_index_sort_key(""), path.lower())
            idx = item[6] or ""
            title = item[3] or ""
            return (_series_index_sort_key(idx), title.lower()) if idx else ((0, 0), title.lower())

        return sorted(paths, key=key)

    def _match_info(self, row, library_index):
        key = self._normalize_title(row[2])
        paths = self._sorted_library_paths(list(library_index.get(row[1], {}).get(key, set())))
        return {"paths": paths, "unwatched": [p for p in paths if self.library_items_by_path.get(p, [0] * 12)[8] == 0]}

    def _format_added_on(self, text):
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime((text or "").strip(), fmt).strftime("%d-%b-%Y")
            except ValueError:
                pass
        return text or ""

    def _set_title_bold(self, item):
        font = item.font(1)
        font.setBold(True)
        item.setFont(1, font)

    def _apply_row_height(self, item):
        item.setSizeHint(0, QSize(0, self._row_height))
        item.setSizeHint(1, QSize(0, self._row_height))

    def _auto_resize_columns(self):
        for col in (2, 3, 4, 5):
            self.tree.resizeColumnToContents(col)
        self._auto_resize_title_column()
        self.tree.setColumnWidth(1, max(self.tree.columnWidth(1), 120))
        if self._do_list_state and self._do_list_state.get("phase") == "collecting":
            self.tree.setColumnWidth(0, 56)
        else:
            self.tree.setColumnWidth(0, 0)

    def _on_header_double_click(self, section):
        if section == 1:
            QTimer.singleShot(0, self._auto_resize_title_column)
        else:
            QTimer.singleShot(0, lambda: self.tree.resizeColumnToContents(section))

    def eventFilter(self, obj, event):
        if obj in (self.tree.header(), self.tree.header().viewport()) and event.type() == QEvent.Type.MouseButtonDblClick:
            pos = event.position().toPoint()
            header = self.tree.header()
            boundary = header.sectionViewportPosition(1) + header.sectionSize(1)
            handle_width = header.style().pixelMetric(QStyle.PixelMetric.PM_HeaderGripMargin)
            if abs(pos.x() - boundary) <= max(8, handle_width):
                self._auto_resize_title_column()
                return True
        return super().eventFilter(obj, event)

    def _auto_resize_title_column(self):
        max_width = 0
        indentation = self.tree.indentation()
        metrics = self.tree.fontMetrics()

        def depth(item):
            level = 0
            current = item.parent()
            while current is not None:
                level += 1
                current = current.parent()
            return level

        def is_tree_visible(item):
            current = item
            while current is not None:
                parent = current.parent()
                if parent is not None and not parent.isExpanded():
                    return False
                current = parent
            return True

        it = QTreeWidgetItemIterator(self.tree)
        while it.value():
            item = it.value()
            if is_tree_visible(item):
                text = item.text(1)
                width = metrics.horizontalAdvance(text) if text else 0
                width += depth(item) * indentation
                width += 40
                max_width = max(max_width, width)
            it += 1

        if max_width:
            self.tree.setColumnWidth(1, max_width)

    def _sync_do_list_state_to_items(self, items):
        if not self._do_list_state:
            return
        valid_ids = {row[0] for row in items}
        picked_by_item_id = self._do_list_state.get("picked_by_item_id", {})
        removed_ids = [item_id for item_id in picked_by_item_id if item_id not in valid_ids]
        for item_id in removed_ids:
            picked_by_item_id.pop(item_id, None)
        for person in self._do_list_state.get("participants", []):
            person["picked_ids"] = {item_id for item_id in person["picked_ids"] if item_id in valid_ids}

    def load_items(self):
        self.tree.clear()
        items = self.db.get_items()
        self._sync_do_list_state_to_items(items)
        self.items_by_id = {row[0]: row for row in items}
        library_items = self.library_db.get_items()
        self.library_items_by_path = {row[1]: row for row in library_items}
        library_index = self._build_library_index(library_items)
        self.link_info_by_id = {}

        movies_root = QTreeWidgetItem(["", "Movies", "", "", "", ""])
        tv_root = QTreeWidgetItem(["", "TV Shows", "", "", "", ""])
        self._apply_row_height(movies_root)
        self._apply_row_height(tv_root)
        self.tree.addTopLevelItem(movies_root)
        self.tree.addTopLevelItem(tv_root)
        movies_root.setExpanded(False)
        tv_root.setExpanded(False)

        for row in sorted(items, key=lambda r: (r[1], self._title_sort_key(r[2]))):
            item_id, media_type, title, _person_id, person_name, added_at, linked = row
            info = self._match_info(row, library_index)
            self.link_info_by_id[item_id] = info
            notes = "In Library" if info["paths"] and linked else "Match Found" if info["paths"] else "Link Missing" if linked else ""
            picker_name = self._participant_name_for_item(item_id)
            if picker_name:
                notes = f"Picked by {picker_name}" if not notes else f"Picked by {picker_name} | {notes}"
            node = QTreeWidgetItem(["", title, self._format_added_on(added_at), person_name or "", notes, ""])
            node.setData(1, Qt.ItemDataRole.UserRole, {"id": item_id})
            self._set_title_bold(node)
            self._apply_row_height(node)
            (movies_root if media_type == "Movie" else tv_root).addChild(node)
            if self._do_list_state and self._do_list_state.get("phase") == "collecting":
                self._set_pick_widget(node, item_id)
            if info["paths"]:
                if linked:
                    watched_count = len(info["paths"]) - len(info["unwatched"])
                    has_unwatched = len(info["unwatched"]) > 0
                    if watched_count == 0 and has_unwatched:
                        self._set_play_widget(node, item_id, resume=False)
                    elif watched_count > 0 and has_unwatched:
                        self._set_play_widget(node, item_id, resume=True)
                else:
                    self._set_link_widget(node, item_id)
        self._refresh_do_list_banner()
        self._auto_resize_columns()

    def _set_pick_widget(self, item, item_id):
        widget = QWidget()
        row = QHBoxLayout(widget)
        row.setContentsMargins(2, 0, 0, 0)
        row.setAlignment(Qt.AlignmentFlag.AlignCenter)

        button = QPushButton("+")
        button.setFixedSize(16, 16)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setStyleSheet(
            """
            QPushButton {
                border: none;
                background: transparent;
                font-size: 18px;
                font-weight: 800;
                color: #1abc9c;
            }
            QPushButton:hover { color: #48c9b0; }
            """
        )

        owner_id = self._do_list_state["picked_by_item_id"].get(item_id) if self._do_list_state else None
        participant = self._current_participant()
        if owner_id is not None:
            button.setText("-" if participant and owner_id == participant["person_id"] else "*")
            button.setStyleSheet(
                """
                QPushButton {
                    border: none;
                    background: transparent;
                    font-size: 18px;
                    font-weight: 800;
                    color: #95a5a6;
                }
                QPushButton:hover { color: #bdc3c7; }
                """
            )
        button.clicked.connect(lambda: self._toggle_pick(item_id))
        row.addWidget(button)
        self.tree.setItemWidget(item, 0, widget)

    def _set_play_widget(self, item, item_id, resume):
        widget = QWidget()
        row = QHBoxLayout(widget)
        row.setContentsMargins(0, 0, 0, 0)
        button = QPushButton("Continue" if resume else "Play")
        button.setFixedWidth(72 if resume else 56)
        button.setFixedHeight(24)
        button.clicked.connect(lambda: self._play_ids([item_id], resume=resume))
        row.addWidget(button)
        self.tree.setItemWidget(item, 5, widget)

    def _set_link_widget(self, item, item_id):
        widget = QWidget()
        row = QHBoxLayout(widget)
        row.setContentsMargins(0, 0, 0, 0)
        button = QPushButton("Link")
        button.setFixedWidth(56)
        button.setFixedHeight(24)
        button.clicked.connect(lambda: self._prompt_links([item_id], allow_batch=False))
        row.addWidget(button)
        self.tree.setItemWidget(item, 5, widget)

    def _collect_ids(self, item):
        data = item.data(1, Qt.ItemDataRole.UserRole)
        if data and data.get("id"):
            return [data["id"]]
        ids = []
        for i in range(item.childCount()):
            ids.extend(self._collect_ids(item.child(i)))
        return ids

    def _dedupe(self, values):
        seen = set()
        out = []
        for value in values:
            if value in seen:
                continue
            seen.add(value)
            out.append(value)
        return out

    def _library_title_for_paths(self, paths, media_type):
        titles = []
        for path in paths:
            row = self.library_items_by_path.get(path)
            if not row:
                continue
            if media_type == "TV":
                title = row[5] or row[3]
            else:
                title = row[3]
            if title:
                titles.append(title)
        unique = self._dedupe(titles)
        if not unique:
            return ""
        return ", ".join(unique[:3]) if len(unique) > 1 else unique[0]

    def _prompt_links(self, item_ids, allow_batch=True):
        candidates = []
        for item_id in self._dedupe(item_ids):
            row = self.items_by_id.get(item_id)
            info = self.link_info_by_id.get(item_id)
            if not row or not info or row[6] or not info["paths"]:
                continue
            candidates.append(
                {
                    "id": item_id,
                    "media_type": row[1],
                    "list_title": row[2],
                    "library_title": self._library_title_for_paths(info["paths"], row[1]) or "(Unknown)",
                }
            )
        if not candidates:
            return
        if len(candidates) == 1 or not allow_batch:
            one = candidates[0]
            list_title = one["list_title"]
            library_title = one["library_title"]
            reply = QMessageBox.question(
                self,
                "Link to Library",
                f"Link List title '{list_title}' to Library title '{library_title}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
            self.db.set_library_linked([one["id"]], True)
            self.load_items()
            return
        dialog = LinkConfirmDialog(candidates, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        selected = dialog.selected_ids()
        if not selected:
            return
        self.db.set_library_linked(selected, True)
        self.load_items()

    def add_to_list(self):
        dialog = ListBulkAddDialog(self.people_db.get_people(), parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        rows, error = dialog.get_results()
        if error:
            QMessageBox.warning(self, "Input Error", error)
            return
        if not rows:
            QMessageBox.warning(self, "Input Error", "Please add at least one list entry.")
            return
        ids = []
        for row in rows:
            ids.append(self.db.add_item(row["media_type"], row["title"], row["added_by_person_id"]))
        self.load_items()
        self._prompt_links(ids, allow_batch=True)

    def edit_selected(self):
        selected = self.tree.selectedItems()
        if not selected:
            QMessageBox.warning(self, "Selection Error", "Please select entries to edit.")
            return
        ids = self._dedupe([item_id for item in selected for item_id in self._collect_ids(item)])
        rows = []
        for item_id in ids:
            row = self.items_by_id.get(item_id)
            if row:
                rows.append(
                    {
                        "id": row[0],
                        "media_type": row[1],
                        "title": row[2],
                        "added_by_person_id": row[3],
                        "added_at": row[5],
                        "library_linked": bool(row[6]),
                    }
                )
        if not rows:
            QMessageBox.warning(self, "Selection Error", "No list entries found to edit.")
            return
        dialog = ListEditDialog(rows, self.people_db.get_people(), parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        results = dialog.get_results()
        if not results:
            QMessageBox.warning(self, "Input Error", "Title cannot be empty.")
            return
        for item in results:
            old = self.items_by_id.get(item["id"])
            if not old:
                item["library_linked"] = 0
                continue
            if old[1] != item["media_type"] or self._normalize_title(old[2]) != self._normalize_title(item["title"]):
                item["library_linked"] = 0
            else:
                item["library_linked"] = bool(old[6])
        self.db.update_items(results)
        self.load_items()
        self._prompt_links([item["id"] for item in results], allow_batch=True)

    def remove_selected(self):
        selected = self.tree.selectedItems()
        if not selected:
            QMessageBox.warning(self, "Selection Error", "Please select entries to remove.")
            return
        ids = self._dedupe([item_id for item in selected for item_id in self._collect_ids(item)])
        if not ids:
            QMessageBox.warning(self, "Selection Error", "No list entries found to remove.")
            return
        reply = QMessageBox.question(
            self,
            "Remove Items",
            f"Remove {len(ids)} item(s) from the list?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self.db.delete_by_ids(ids)
        self.load_items()

    def handle_double_click(self, item, _column):
        if _column == 0:
            return
        self._play_ids(self._collect_ids(item), resume=False)

    def _play_ids(self, item_ids, resume):
        paths = []
        for item_id in self._dedupe(item_ids):
            row = self.items_by_id.get(item_id)
            info = self.link_info_by_id.get(item_id, {})
            if not row or not row[6]:
                continue
            paths.extend(info.get("unwatched", []) if resume else info.get("paths", []))
        paths = self._sorted_library_paths(self._dedupe(paths))
        if not paths:
            msg = "No linked unwatched items found to continue." if resume else "No linked items found to play."
            QMessageBox.warning(self, "Selection Error", msg)
            return
        self._play_paths(paths)

    def _play_paths(self, paths):
        try:
            if len(paths) == 1:
                os.startfile(paths[0])
                self.library_db.update_watched(paths, True)
                self.load_items()
                return
            self._play_paths_in_mpv(paths)
        except OSError:
            QMessageBox.warning(
                self,
                "Playback Error",
                "Unable to launch mpv. Please ensure mpv is installed and available in PATH.",
            )

    def _play_paths_in_mpv(self, paths):
        script_path = os.path.join(os.path.dirname(__file__), "..", "core", "whatch_watch.lua")
        script_path = os.path.abspath(script_path).replace("\\", "/")
        fd, log_path = tempfile.mkstemp(prefix="whatch_mpv_", suffix=".log")
        os.close(fd)
        log_path = os.path.abspath(log_path).replace("\\", "/")
        process = QProcess(self)
        process.finished.connect(lambda _code, _status, proc=process: self._on_mpv_finished(proc))
        process.errorOccurred.connect(lambda _error, proc=process: self._on_mpv_error(proc))
        self._mpv_processes[process] = {"log_path": log_path, "paths": paths}
        process.start(
            "mpv",
            [f"--script={script_path}", f"--script-opts=whatch_watch-log_path={log_path}", *paths],
        )
        if not process.waitForStarted(2000):
            self._mpv_processes.pop(process, None)
            QMessageBox.warning(
                self,
                "Playback Error",
                "Unable to launch mpv. Please ensure mpv is installed and available in PATH.",
            )

    def _normalize_media_path(self, path):
        text = (path or "").strip()
        if text.lower().startswith("file://"):
            text = text[7:]
            if text.startswith("/") and len(text) > 2 and text[2] == ":":
                text = text[1:]
        text = text.replace("/", "\\")
        return os.path.normcase(os.path.abspath(text))

    def _read_played_paths(self, log_path, allowed_paths):
        if not os.path.exists(log_path):
            return []
        allowed_by_norm = {}
        allowed_by_basename = defaultdict(list)
        for path in allowed_paths:
            allowed_by_norm[self._normalize_media_path(path)] = path
            allowed_by_basename[os.path.basename(path).lower()].append(path)
        played = []
        seen = set()
        with open(log_path, "r", encoding="utf-8") as handle:
            for line in handle:
                raw = line.strip()
                if not raw:
                    continue
                matched = allowed_by_norm.get(self._normalize_media_path(raw))
                if not matched:
                    candidates = allowed_by_basename.get(os.path.basename(raw).lower(), [])
                    matched = candidates[0] if len(candidates) == 1 else None
                if not matched or matched in seen:
                    continue
                seen.add(matched)
                played.append(matched)
        return played

    def _cleanup_mpv_log(self, log_path):
        try:
            if os.path.exists(log_path):
                os.remove(log_path)
        except OSError:
            pass

    def _on_mpv_error(self, process):
        info = self._mpv_processes.pop(process, None)
        if info:
            self._cleanup_mpv_log(info["log_path"])
        QMessageBox.warning(
            self,
            "Playback Error",
            "Unable to launch mpv. Please ensure mpv is installed and available in PATH.",
        )

    def _on_mpv_finished(self, process):
        info = self._mpv_processes.pop(process, None)
        if not info:
            return
        played = self._read_played_paths(info["log_path"], info["paths"])
        self._cleanup_mpv_log(info["log_path"])
        if played:
            self.library_db.update_watched(played, True)
            self.load_items()

    def go_back(self):
        self._do_list_anim_timer.stop()
        self.db.close()
        self.library_db.close()
        self.people_db.close()
        self.back_callback()
