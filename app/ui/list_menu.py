import os
import tempfile
from collections import defaultdict
from datetime import datetime

from PyQt6.QtCore import QDateTime, QEvent, QProcess, QSize, Qt, QTimer
from PyQt6.QtGui import QGuiApplication, QKeySequence
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDateTimeEdit,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTreeWidgetItemIterator,
    QTreeWidget,
    QTreeWidgetItem,
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
        self._build_ui()
        self.load_items()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        title = QLabel("List")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(title)
        self.tree = QTreeWidget()
        self._row_height = 36
        self.tree.setColumnCount(5)
        self.tree.setHeaderLabels(["Title", "Added On", "Added By", "Notes", "Play"])
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.tree.itemDoubleClicked.connect(self.handle_double_click)
        self.tree.itemExpanded.connect(lambda _item: self._auto_resize_columns())
        self.tree.itemCollapsed.connect(lambda _item: self._auto_resize_columns())
        self.tree.setUniformRowHeights(False)
        self.tree.setStyleSheet("QTreeWidget::item { padding-top: 6px; padding-bottom: 6px; }")
        header = self.tree.header()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
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
        font = item.font(0)
        font.setBold(True)
        item.setFont(0, font)

    def _apply_row_height(self, item):
        item.setSizeHint(0, QSize(0, self._row_height))

    def _auto_resize_columns(self):
        for col in (1, 2, 3, 4):
            self.tree.resizeColumnToContents(col)
        self._auto_resize_title_column()
        self.tree.setColumnWidth(0, max(self.tree.columnWidth(0), 120))

    def _on_header_double_click(self, section):
        if section == 0:
            QTimer.singleShot(0, self._auto_resize_title_column)
        else:
            QTimer.singleShot(0, lambda: self.tree.resizeColumnToContents(section))

    def eventFilter(self, obj, event):
        if obj in (self.tree.header(), self.tree.header().viewport()) and event.type() == QEvent.Type.MouseButtonDblClick:
            pos = event.position().toPoint()
            header = self.tree.header()
            boundary = header.sectionViewportPosition(0) + header.sectionSize(0)
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
                text = item.text(0)
                width = metrics.horizontalAdvance(text) if text else 0
                width += depth(item) * indentation
                width += 40
                max_width = max(max_width, width)
            it += 1

        if max_width:
            self.tree.setColumnWidth(0, max_width)

    def load_items(self):
        self.tree.clear()
        items = self.db.get_items()
        self.items_by_id = {row[0]: row for row in items}
        library_items = self.library_db.get_items()
        self.library_items_by_path = {row[1]: row for row in library_items}
        library_index = self._build_library_index(library_items)
        self.link_info_by_id = {}

        movies_root = QTreeWidgetItem(["Movies", "", "", "", ""])
        tv_root = QTreeWidgetItem(["TV Shows", "", "", "", ""])
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
            node = QTreeWidgetItem([title, self._format_added_on(added_at), person_name or "", notes, ""])
            node.setData(0, Qt.ItemDataRole.UserRole, {"id": item_id})
            self._set_title_bold(node)
            self._apply_row_height(node)
            (movies_root if media_type == "Movie" else tv_root).addChild(node)
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
        self._auto_resize_columns()

    def _set_play_widget(self, item, item_id, resume):
        widget = QWidget()
        row = QHBoxLayout(widget)
        row.setContentsMargins(0, 0, 0, 0)
        button = QPushButton("Continue" if resume else "Play")
        button.setFixedWidth(72 if resume else 56)
        button.setFixedHeight(24)
        button.clicked.connect(lambda: self._play_ids([item_id], resume=resume))
        row.addWidget(button)
        self.tree.setItemWidget(item, 4, widget)

    def _set_link_widget(self, item, item_id):
        widget = QWidget()
        row = QHBoxLayout(widget)
        row.setContentsMargins(0, 0, 0, 0)
        button = QPushButton("Link")
        button.setFixedWidth(56)
        button.setFixedHeight(24)
        button.clicked.connect(lambda: self._prompt_links([item_id], allow_batch=False))
        row.addWidget(button)
        self.tree.setItemWidget(item, 4, widget)

    def _collect_ids(self, item):
        data = item.data(0, Qt.ItemDataRole.UserRole)
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
        self.db.close()
        self.library_db.close()
        self.people_db.close()
        self.back_callback()
