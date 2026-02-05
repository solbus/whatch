import os
import tempfile
import uuid
import re
from datetime import datetime, timedelta
from collections import defaultdict

from PyQt6.QtCore import Qt, QProcess, QSize, QTimer, QEvent
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QWidget,
    QVBoxLayout,
    QLabel,
    QTreeWidget,
    QTreeWidgetItem,
    QTreeWidgetItemIterator,
    QPushButton,
    QHBoxLayout,
    QMessageBox,
    QFileDialog,
    QDialog,
    QComboBox,
    QCheckBox,
    QLineEdit,
    QDateTimeEdit,
    QSpinBox,
    QPlainTextEdit,
    QHeaderView,
    QStyle,
    QTableWidget,
    QTableWidgetItem,
)

from app.core.library_db import LibraryDB


VIDEO_EXTENSIONS = {
    ".mp4",
    ".mkv",
    ".avi",
    ".mov",
    ".wmv",
    ".flv",
    ".m4v",
    ".mpg",
    ".mpeg",
    ".webm",
    ".bdmv",
    ".m2ts",
}


def _is_video_file(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".bdmv":
        return _is_bdmv_movieobject(path)
    return ext in VIDEO_EXTENSIONS


def _is_bdmv_movieobject(path):
    return (
        os.path.basename(path).lower() == "movieobject.bdmv"
        and os.path.basename(os.path.dirname(path)).lower() == "bdmv"
    )


def _default_display_title(path):
    if _is_bdmv_movieobject(path):
        parent = os.path.dirname(os.path.dirname(path))
        return os.path.basename(parent) or os.path.basename(path)
    return os.path.splitext(os.path.basename(path))[0]


def _clean_series_title(raw):
    text = (raw or "").strip()
    if not text:
        return ""
    text = re.sub(r"[._]+", " ", text).strip()
    # Strip release year and trailing metadata.
    text = re.sub(r"\s*\(\d{4}\).*$", "", text)
    # Handle "Show Name - Season 1" style folder names.
    text = re.split(r"\s+-\s+season\s+\d+.*$", text, maxsplit=1, flags=re.IGNORECASE)[0]
    # Handle "Show Name S01 ..." style names.
    text = re.split(r"\s+S\d{1,2}(?!E\d)\b.*$", text, maxsplit=1, flags=re.IGNORECASE)[0]
    # Strip trailing bare year tokens common in release folder names.
    text = re.sub(r"\s+(?:19|20)\d{2}$", "", text)
    cleaned = text.strip(" -._")
    if cleaned and cleaned == cleaned.lower():
        return _normalize_episode_title_case(cleaned)
    return cleaned


def _normalize_episode_title_case(text):
    if not text:
        return ""

    minor = {
        "a", "an", "and", "as", "at", "but", "by", "for", "from", "in", "nor",
        "of", "on", "or", "the", "to", "vs", "via",
    }

    def split_token(raw):
        match = re.match(r"^([^\w]*)([\w][\w']*)([^\w]*)$", raw, flags=re.UNICODE)
        if not match:
            return raw, "", ""
        return match.group(1), match.group(2), match.group(3)

    def is_roman_numeral(core):
        upper = core.upper()
        if not upper:
            return False
        if not re.fullmatch(r"[IVXLCDM]+", upper):
            return False
        if len(upper) < 2:
            return False
        return bool(
            re.fullmatch(
                r"M{0,4}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})",
                upper,
            )
        )

    def normalize_core(core, is_first, is_last):
        if not core:
            return core
        if is_roman_numeral(core):
            return core.upper()
        if core.isalpha() and core.isupper() and len(core) >= 2:
            return core
        if any(ch.isdigit() for ch in core) and any(ch.isalpha() for ch in core):
            return core
        lower = core.lower()
        if not is_first and not is_last and lower in minor and len(core) > 1:
            return lower
        return lower[:1].upper() + lower[1:]

    words = text.split()
    normalized_words = []
    last_word_index = len(words) - 1
    for i, word in enumerate(words):
        parts = word.split("-")
        normalized_parts = []
        for part in parts:
            prefix, core, suffix = split_token(part)
            normalized_core = normalize_core(core, i == 0, i == last_word_index)
            normalized_parts.append(f"{prefix}{normalized_core}{suffix}" if core else part)
        normalized_words.append("-".join(normalized_parts))
    return " ".join(normalized_words)


def _episode_code_from_series_index(series_index):
    parsed = _parse_series_index_values(series_index)
    if not parsed:
        return None
    season, episode = parsed[0]
    return f"S{season:02d}E{episode:02d}"


def _parse_episode_code(code_text):
    text = (code_text or "").strip().upper()
    match = re.match(r"^S(?P<season>\d{2})E(?P<start>\d{2})(?:-(?:E)?(?P<end>\d{2}))?$", text)
    if not match:
        return None
    season = int(match.group("season"))
    start = int(match.group("start"))
    end = int(match.group("end") or start)
    if end < start:
        start, end = end, start
    return {
        "season": season,
        "start_episode": start,
        "end_episode": end,
    }


def _format_series_index_range(season, start_episode, end_episode):
    if end_episode <= start_episode:
        return f"{season}.{start_episode}"
    return f"{season}.{start_episode}-{end_episode}"


def _parse_series_index_values(series_index):
    values = []
    raw = (series_index or "").strip()
    if not raw:
        return values
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    for part in parts:
        match = re.match(r"^(?P<season>\d+)\.(?P<start>\d+)(?:-(?P<end>\d+))?$", part)
        if not match:
            continue
        season = int(match.group("season"))
        start = int(match.group("start"))
        end = int(match.group("end") or start)
        if end < start:
            start, end = end, start
        for episode in range(start, end + 1):
            values.append((season, episode))
    return values


def _extract_tv_episode_parts(path):
    name = os.path.splitext(os.path.basename(path))[0]
    strict_pattern = (
        r"^(?P<show>.*?)\s*(?:\(\d{4}\))?\s*-\s*(?P<code>S\d{2}E\d{2}(?:-(?:E)?\d{2})?)\s*-\s*"
        r"(?P<title>.*?)(?:\s*\((?:720|1080|2160)p\b.*)?$"
    )
    match = re.match(strict_pattern, name, flags=re.IGNORECASE)
    if match:
        show = _clean_series_title(match.group("show"))
        title = match.group("title").strip(" -._")
        code_text = match.group("code")
    else:
        loose_match = re.search(
            r"(?<![A-Za-z0-9])S\d{1,2}E\d{1,2}(?:-(?:E)?\d{1,2})?(?=$|[._\s-])",
            name,
            flags=re.IGNORECASE,
        )
        if not loose_match:
            return None
        show_raw = name[:loose_match.start()]
        tail = name[loose_match.end():]
        show = _clean_series_title(re.sub(r"[._]+", " ", show_raw).strip(" -._"))
        code_text = loose_match.group(0)

        tail = tail.strip(" -._")
        quality_marker = re.search(
            r"(?i)(?:^|[\s._-])(?:hdr|dv|uhd|720p|1080p|2160p|webrip|web-dl|web|bluray|bdrip|amzn|atvp|nf|ddp?|atmos|aac|x264|x265|h264|h265|hevc|proper|repack|remux)\b",
            tail,
        )
        if quality_marker:
            tail = tail[:quality_marker.start()]
        tail = re.sub(r"\[[^\]]*\]\s*$", "", tail).strip(" -._")
        tail = re.sub(r"[._]+", " ", tail).strip()
        if tail:
            words = tail.split()
            language_tokens = {
                "ita", "eng", "en", "it", "spa", "esp", "fra", "fre", "deu", "ger", "jpn", "kor",
                "rus", "pt", "por", "lat", "multi", "sub", "subs", "dub", "dual", "audio",
            }
            while words:
                trailing = words[-1].lower().strip("-")
                trailing_parts = [p for p in trailing.split("-") if p]
                if trailing_parts and all(part in language_tokens for part in trailing_parts):
                    words.pop()
                    continue
                if trailing in language_tokens:
                    words.pop()
                    continue
                break
            tail = " ".join(words).strip()
        title = tail

    episode_data = _parse_episode_code(code_text)
    if not episode_data:
        return None
    episode_code = (
        f"S{episode_data['season']:02d}E{episode_data['start_episode']:02d}"
        if episode_data["start_episode"] == episode_data["end_episode"]
        else f"S{episode_data['season']:02d}E{episode_data['start_episode']:02d}"
        f"-E{episode_data['end_episode']:02d}"
    )
    if not title:
        title = episode_code
    return {
        "series_title": show or None,
        "episode_code": episode_code,
        "season": episode_data["season"],
        "start_episode": episode_data["start_episode"],
        "end_episode": episode_data["end_episode"],
        "series_index": _format_series_index_range(
            episode_data["season"],
            episode_data["start_episode"],
            episode_data["end_episode"],
        ),
        "episode_title": _normalize_episode_title_case(title),
    }


def _default_episode_title(path, series_index=""):
    parsed = _extract_tv_episode_parts(path)
    if parsed and parsed["episode_title"]:
        return parsed["episode_title"]
    return _episode_code_from_series_index(series_index) or "S01E01"


def _detect_default_type(path):
    lowered = path.lower()
    if "tv shows" in lowered or os.sep + "tv" + os.sep in lowered:
        return "TV"
    if "season" in lowered:
        return "TV"
    return "Movie"


def _default_show_and_series(path):
    parent = os.path.basename(os.path.dirname(path))
    grandparent = os.path.basename(os.path.dirname(os.path.dirname(path)))
    if _season_number_from_name(parent) is not None:
        cleaned = _clean_series_title(grandparent) or grandparent or parent
        return cleaned, parent
    cleaned = _clean_series_title(parent) or parent
    return cleaned, ""


def _season_number_from_name(name):
    text = re.sub(r"[._]+", " ", (name or "").strip())
    lowered = text.lower()
    # Ignore "season packs" like "Season 1-8" / "S01-S08" that represent collections, not a single season.
    if re.search(r"\bseason\s+\d+\s*-\s*\d+\b", lowered):
        return None
    if re.search(r"\bS\d{1,2}\s*-\s*S\d{1,2}\b", text, flags=re.IGNORECASE):
        return None
    if lowered.startswith("season"):
        parts = lowered.split()
        if len(parts) >= 2 and parts[1].isdigit():
            return int(parts[1])
    # Support folder styles like "Show.Name.S01.1080p..."
    match = re.search(r"\bS(?P<season>\d{1,2})(?!E\d)\b", text, flags=re.IGNORECASE)
    if match:
        return int(match.group("season"))
    return None


def _import_dir_sort_key(name):
    season_num = _season_number_from_name(name)
    if season_num is not None:
        return (0, season_num, name.lower())
    return (1, 0, name.lower())


def _import_file_sort_key(path):
    parsed = _extract_tv_episode_parts(path)
    if parsed:
        return (
            0,
            parsed["season"],
            parsed["start_episode"],
            parsed["end_episode"],
            os.path.basename(path).lower(),
        )
    return (1, 0, 0, 0, os.path.basename(path).lower())


def _series_index_sort_key(value):
    parsed = _parse_series_index_values(value)
    if parsed:
        return parsed[0]
    if value and value.isdigit():
        return (int(value), 0)
    return (9999, 9999)


def _series_index_prefix(value):
    if not value:
        return None
    text = value.strip()
    if text.isdigit():
        return text
    if "." in text:
        left = text.split(".", 1)[0]
        if left.isdigit():
            return left
    return None


class LibraryImportDialog(QDialog):
    def __init__(self, selected_paths, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add to Library")
        self.selected_paths = selected_paths
        self.row_widgets = {}
        self.file_items = []
        self.init_ui()
        self.build_tree()

    def init_ui(self):
        layout = QVBoxLayout(self)

        title = QLabel("Select type and details for each file or folder")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        apply_layout = QHBoxLayout()
        self.apply_type = QComboBox()
        self.apply_type.addItems(["Movie", "TV"])
        self.apply_series = QCheckBox("Series")
        self.apply_series_title = QLineEdit()
        self.apply_series_title.setPlaceholderText("Series Title")
        self.apply_button = QPushButton("Apply to All")
        self.apply_button.clicked.connect(self.apply_to_all)
        apply_layout.addWidget(self.apply_type)
        apply_layout.addWidget(self.apply_series)
        apply_layout.addWidget(self.apply_series_title)
        apply_layout.addWidget(self.apply_button)
        layout.addLayout(apply_layout)

        self.tree = QTreeWidget()
        self.tree.setColumnCount(7)
        self.tree.setHeaderLabels(
            ["Type", "File", "Title", "Series", "Series Title", "# in Series", "Exclude"]
        )
        header = self.tree.header()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        layout.addWidget(self.tree)

        button_layout = QHBoxLayout()
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        self.resize(1100, 720)

    def build_tree(self):
        self.tree.clear()
        self.row_widgets.clear()
        self.file_items.clear()

        folder_roots = [p for p in self.selected_paths if os.path.isdir(p)]
        file_roots = [p for p in self.selected_paths if os.path.isfile(p)]

        root_items = {}
        path_to_item = {}
        show_has_seasons = {}

        for root in folder_roots:
            root_item = QTreeWidgetItem(["", os.path.basename(root) or root])
            root_item.setData(0, Qt.ItemDataRole.UserRole, {"path": root, "is_folder": True})
            self.tree.addTopLevelItem(root_item)
            root_name = os.path.basename(root) or root
            season_for_root = _season_number_from_name(root_name)
            default_series_title = _clean_series_title(root_name)
            default_index = str(season_for_root) if season_for_root is not None else ""
            if season_for_root is not None:
                parent_name = os.path.basename(os.path.dirname(root))
                default_series_title = _clean_series_title(parent_name) or default_series_title
            self._init_row_widgets(
                root_item,
                root,
                is_folder=True,
                default_index=default_index,
                default_series_title=default_series_title or root_name,
            )
            root_items[root] = root_item
            path_to_item[root] = root_item

            for dirpath, dirnames, _filenames in os.walk(root):
                for dirname in dirnames:
                    season_num = _season_number_from_name(dirname)
                    if season_num is None:
                        continue
                    show_root = os.path.dirname(os.path.join(dirpath, dirname))
                    show_has_seasons[show_root] = True

            for dirpath, dirnames, filenames in os.walk(root):
                dirnames.sort(key=_import_dir_sort_key)
                rel = os.path.relpath(dirpath, root)
                if rel != ".":
                    parent_path = os.path.dirname(dirpath)
                    parent_item = path_to_item.get(parent_path, root_item)
                    if dirpath not in path_to_item:
                        folder_item = QTreeWidgetItem(["", os.path.basename(dirpath)])
                        folder_item.setData(
                            0, Qt.ItemDataRole.UserRole, {"path": dirpath, "is_folder": True}
                        )
                        parent_item.addChild(folder_item)
                        season_num = _season_number_from_name(os.path.basename(dirpath))
                        default_index = str(season_num) if season_num else ""
                        self._init_row_widgets(
                            folder_item, dirpath, is_folder=True, default_index=default_index
                        )
                        path_to_item[dirpath] = folder_item

                episode_counter = 1
                filenames = sorted(
                    filenames,
                    key=lambda x: _import_file_sort_key(os.path.join(dirpath, x)),
                )
                for filename in filenames:
                    file_path = os.path.join(dirpath, filename)
                    if os.path.basename(dirpath).lower() == "bdmv":
                        if os.path.basename(file_path).lower() != "movieobject.bdmv":
                            continue
                    if not _is_video_file(file_path):
                        continue
                    parent_item = path_to_item.get(dirpath, root_item)
                    file_item = QTreeWidgetItem(["", filename])
                    file_item.setData(
                        0, Qt.ItemDataRole.UserRole, {"path": file_path, "is_folder": False}
                    )
                    parent_item.addChild(file_item)
                    season_num = _season_number_from_name(os.path.basename(dirpath))
                    if season_num is None and show_has_seasons.get(dirpath) is None:
                        season_num = 1 if "tv shows" in dirpath.lower() else None
                    parsed_episode = _extract_tv_episode_parts(file_path)
                    default_index = ""
                    if parsed_episode:
                        default_index = parsed_episode["series_index"]
                        if season_num and parsed_episode["season"] == season_num:
                            episode_counter = max(episode_counter, parsed_episode["end_episode"] + 1)
                    elif season_num:
                        default_index = f"{season_num}.{episode_counter}"
                        episode_counter += 1
                    self._init_row_widgets(
                        file_item, file_path, is_folder=False, default_index=default_index
                    )
                    self.file_items.append(file_item)

        for file_path in sorted(file_roots, key=_import_file_sort_key):
            if not _is_video_file(file_path):
                continue
            file_item = QTreeWidgetItem(["", os.path.basename(file_path)])
            file_item.setData(
                0, Qt.ItemDataRole.UserRole, {"path": file_path, "is_folder": False}
            )
            self.tree.addTopLevelItem(file_item)
            parsed_episode = _extract_tv_episode_parts(file_path)
            default_index = parsed_episode["series_index"] if parsed_episode else ""
            self._init_row_widgets(
                file_item,
                file_path,
                is_folder=False,
                default_index=default_index,
            )
            self.file_items.append(file_item)

        for i in range(self.tree.topLevelItemCount()):
            self._sort_import_children_recursive(self.tree.topLevelItem(i))
        self._rebind_import_row_widgets()
        self._normalize_import_series_titles()

        self.tree.expandAll()
        self._auto_resize_import_columns()

    def _sort_import_children_recursive(self, parent):
        for i in range(parent.childCount()):
            self._sort_import_children_recursive(parent.child(i))
        if parent.childCount() <= 1:
            return
        children = []
        while parent.childCount() > 0:
            children.append(parent.takeChild(0))
        children.sort(key=self._import_tree_sort_key)
        for child in children:
            parent.addChild(child)

    def _import_tree_sort_key(self, item):
        index_key = self._effective_import_item_index_key(item)
        if index_key is not None:
            return (0, index_key[0], index_key[1], item.text(1).lower())
        season_num = _season_number_from_name(item.text(1) or "")
        if season_num is not None:
            return (1, season_num, 0, item.text(1).lower())
        return (2, 9999, 9999, item.text(1).lower())

    def _effective_import_item_index_key(self, item):
        widgets = self._widgets(item)
        if widgets:
            parsed = _parse_series_index_values(widgets["series_index"].text().strip())
            if parsed:
                return parsed[0]

        best = None
        for i in range(item.childCount()):
            child = item.child(i)
            child_key = self._effective_import_item_index_key(child)
            if child_key is None:
                continue
            if best is None or child_key < best:
                best = child_key
        return best

    def _rebind_import_row_widgets(self):
        for widgets in self.row_widgets.values():
            item = widgets["item"]
            self.tree.setItemWidget(item, 0, widgets["type"])
            self.tree.setItemWidget(item, 3, widgets["series_check"])
            self.tree.setItemWidget(item, 4, widgets["series_title"])
            self.tree.setItemWidget(item, 5, widgets["series_index"])
            self.tree.setItemWidget(item, 6, widgets["exclude"])
            if widgets["display_title"] is not None:
                self.tree.setItemWidget(item, 2, widgets["display_title"])

    def _normalize_import_series_titles(self):
        generic = {"tv", "tv show", "tv shows"}

        def descendant_series_titles(item):
            titles = []
            for i in range(item.childCount()):
                child = item.child(i)
                child_widgets = self._widgets(child)
                if child_widgets:
                    title = child_widgets["series_title"].text().strip()
                    if title and title.lower() not in generic:
                        titles.append(title)
                titles.extend(descendant_series_titles(child))
            return titles

        it = QTreeWidgetItemIterator(self.tree)
        while it.value():
            item = it.value()
            widgets = self._widgets(item)
            if not widgets or not widgets["is_folder"]:
                it += 1
                continue
            current = widgets["series_title"].text().strip()
            if current and current.lower() not in generic:
                it += 1
                continue
            titles = descendant_series_titles(item)
            if titles:
                counts = {}
                first_seen = {}
                for idx, title in enumerate(titles):
                    key = title.casefold()
                    counts[key] = counts.get(key, 0) + 1
                    if key not in first_seen:
                        first_seen[key] = (idx, title)
                best_key = min(
                    counts.keys(),
                    key=lambda k: (-counts[k], first_seen[k][0]),
                )
                widgets["series_title"].setText(first_seen[best_key][1])
            it += 1

    def _auto_resize_import_columns(self):
        header = self.tree.header()
        metrics = self.tree.fontMetrics()

        def header_width(col):
            return metrics.horizontalAdvance(self.tree.headerItem().text(col) or "") + 20

        file_width = header_width(1)
        title_width = header_width(2)
        series_title_width = header_width(4)
        series_index_width = header_width(5)

        it = QTreeWidgetItemIterator(self.tree)
        while it.value():
            item = it.value()
            file_width = max(file_width, metrics.horizontalAdvance(item.text(1) or "") + 24)

            title_widget = self.tree.itemWidget(item, 2)
            if isinstance(title_widget, QLineEdit):
                title_width = max(title_width, metrics.horizontalAdvance(title_widget.text()) + 24)

            series_title_widget = self.tree.itemWidget(item, 4)
            if isinstance(series_title_widget, QLineEdit):
                series_title_width = max(
                    series_title_width, metrics.horizontalAdvance(series_title_widget.text()) + 24
                )

            series_index_widget = self.tree.itemWidget(item, 5)
            if isinstance(series_index_widget, QLineEdit):
                series_index_width = max(
                    series_index_width, metrics.horizontalAdvance(series_index_widget.text()) + 24
                )
            it += 1

        self.tree.setColumnWidth(1, min(max(file_width, 190), 320))
        self.tree.setColumnWidth(2, max(title_width, 260))
        self.tree.setColumnWidth(4, max(series_title_width, header_width(4)))
        self.tree.setColumnWidth(5, max(series_index_width, header_width(5)))
        self.tree.resizeColumnToContents(3)
        self.tree.resizeColumnToContents(6)

        max_width = 0
        indentation = self.tree.indentation()

        def depth(item):
            level = 0
            current = item.parent()
            while current is not None:
                level += 1
                current = current.parent()
            return level

        it = QTreeWidgetItemIterator(self.tree)
        while it.value():
            item = it.value()
            widget = self.tree.itemWidget(item, 0)
            if widget is not None:
                width = widget.sizeHint().width()
            else:
                text = item.text(0)
                width = metrics.horizontalAdvance(text) if text else 0
            width += depth(item) * indentation
            width += 24
            max_width = max(max_width, width)
            it += 1

        if max_width:
            self.tree.setColumnWidth(0, max_width)

    def _init_row_widgets(
        self,
        item,
        path,
        is_folder,
        default_index="",
        default_series_title=None,
    ):
        default_type = _detect_default_type(path)
        show_title, series_title = _default_show_and_series(path)
        parsed_episode = _extract_tv_episode_parts(path) if not is_folder else None

        exclude_check = QCheckBox()

        type_combo = QComboBox()
        type_combo.addItems(["Movie", "TV"])
        type_combo.setCurrentText(default_type)

        series_check = QCheckBox()
        series_check.setChecked(default_type == "TV")

        series_title_field = QLineEdit()
        if default_type == "TV":
            auto_series_title = default_series_title or show_title
            if parsed_episode and parsed_episode.get("series_title"):
                auto_series_title = parsed_episode["series_title"]
            series_title_field.setText(auto_series_title)

        series_index_field = QLineEdit()
        if default_index:
            series_index_field.setText(default_index)

        display_title_field = None
        if not is_folder:
            display_title_field = QLineEdit()
            if default_type == "TV":
                display_title_field.setText(_default_episode_title(path, default_index))
            else:
                display_title_field.setText(_default_display_title(path))

        self.tree.setItemWidget(item, 0, type_combo)
        self.tree.setItemWidget(item, 3, series_check)
        self.tree.setItemWidget(item, 4, series_title_field)
        self.tree.setItemWidget(item, 5, series_index_field)
        self.tree.setItemWidget(item, 6, exclude_check)
        if display_title_field is not None:
            self.tree.setItemWidget(item, 2, display_title_field)

        self._set_widgets(item, {
            "exclude": exclude_check,
            "type": type_combo,
            "series_check": series_check,
            "series_title": series_title_field,
            "series_index": series_index_field,
            "display_title": display_title_field,
            "is_folder": is_folder,
        })

        def on_type_change(text):
            if text == "TV" and not series_check.isChecked():
                series_check.setChecked(True)
            self._update_row_enabled(item)
            if is_folder:
                self._propagate(item, "type", text)

        def on_series_toggle(checked):
            self._update_row_enabled(item)
            if is_folder:
                self._propagate(item, "series_check", checked)

        def on_exclude_toggle(checked):
            if is_folder:
                self._propagate(item, "exclude", checked)

        type_combo.currentTextChanged.connect(on_type_change)
        series_check.toggled.connect(on_series_toggle)
        exclude_check.toggled.connect(on_exclude_toggle)
        series_title_field.textChanged.connect(
            lambda text: self._propagate(item, "series_title", text) if is_folder else None
        )
        series_index_field.textChanged.connect(
            lambda text: self._propagate(item, "series_index", text) if is_folder else None
        )

        self._update_row_enabled(item)

    def _update_row_enabled(self, item):
        widgets = self._widgets(item)
        widgets["series_check"].setEnabled(True)
        series_enabled = widgets["series_check"].isChecked()
        widgets["series_title"].setEnabled(series_enabled)
        widgets["series_index"].setEnabled(series_enabled)
        widgets["series_title"].setVisible(series_enabled)
        widgets["series_index"].setVisible(series_enabled)

    def _propagate(self, item, field, value):
        if field == "series_index":
            self._propagate_series_index(item, value)
            return
        for i in range(item.childCount()):
            child = item.child(i)
            widgets = self._widgets(child)
            if not widgets:
                continue
            widget = widgets.get(field)
            if field == "type":
                widget.blockSignals(True)
                widget.setCurrentText(value)
                widget.blockSignals(False)
                self._update_row_enabled(child)
            elif field == "series_check":
                widget.blockSignals(True)
                widget.setChecked(value)
                widget.blockSignals(False)
                self._update_row_enabled(child)
            elif field == "exclude":
                widget.blockSignals(True)
                widget.setChecked(value)
                widget.blockSignals(False)
            else:
                widget.blockSignals(True)
                widget.setText(value)
                widget.blockSignals(False)
            if widgets["is_folder"]:
                self._propagate(child, field, value)

    def _propagate_series_index(self, item, value):
        prefix = _series_index_prefix(value)
        episode_counter = 1

        def update_child(child_item):
            nonlocal episode_counter
            widgets = self._widgets(child_item)
            if not widgets:
                return
            target_value = value
            if not widgets["is_folder"] and prefix:
                target_value = f"{prefix}.{episode_counter}"
                episode_counter += 1
            widgets["series_index"].blockSignals(True)
            widgets["series_index"].setText(target_value)
            widgets["series_index"].blockSignals(False)
            if widgets["is_folder"]:
                for i in range(child_item.childCount()):
                    update_child(child_item.child(i))

        for i in range(item.childCount()):
            update_child(item.child(i))

    def apply_to_all(self):
        type_value = self.apply_type.currentText()
        series_checked = self.apply_series.isChecked()
        series_title = self.apply_series_title.text().strip()

        for widgets in self.row_widgets.values():
            widgets["type"].setCurrentText(type_value)
            widgets["series_check"].setChecked(series_checked)
            if series_title:
                widgets["series_title"].setText(series_title)
            self._update_row_enabled(widgets["item"])

    def get_results(self):
        results = []
        for item in self.file_items:
            data = item.data(0, Qt.ItemDataRole.UserRole)
            path = data["path"]
            widgets = self._widgets(item)
            if widgets["exclude"].isChecked():
                continue
            media_type = widgets["type"].currentText()
            is_series = widgets["series_check"].isChecked()
            series_title = widgets["series_title"].text().strip() or None
            series_index = widgets["series_index"].text().strip() or None
            display_title = widgets["display_title"].text().strip() or _default_display_title(path)
            results.append(
                {
                    "path": path,
                    "media_type": media_type,
                    "is_series": is_series,
                    "series_title": series_title,
                    "show_title": series_index,
                    "display_title": display_title,
                }
            )
        return results

    def _set_widgets(self, item, widgets):
        key = id(item)
        widgets["item"] = item
        self.row_widgets[key] = widgets

    def _widgets(self, item):
        return self.row_widgets.get(id(item))


class LibraryEditDialog(QDialog):
    def __init__(self, items, parent=None, include_air_datetime=False):
        super().__init__(parent)
        self.setWindowTitle("Edit Library Items")
        self.items = items
        self.include_air_datetime = include_air_datetime
        self.row_widgets = {}
        self.row_order = []
        self.init_ui()
        self.build_tree()

    def init_ui(self):
        layout = QVBoxLayout(self)

        title = QLabel("Edit details for selected items")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        apply_layout = QHBoxLayout()
        self.apply_type = QComboBox()
        self.apply_type.addItems(["Movie", "TV"])
        self.apply_series = QCheckBox("Series")
        self.apply_series_title = QLineEdit()
        self.apply_series_title.setPlaceholderText("Series title")
        self.apply_series_index = QLineEdit()
        self.apply_series_index.setPlaceholderText("Series index (e.g., 5)")
        self.apply_button = QPushButton("Apply to All")
        self.apply_button.clicked.connect(self.apply_to_all)
        apply_layout.addWidget(self.apply_type)
        apply_layout.addWidget(self.apply_series)
        apply_layout.addWidget(self.apply_series_title)
        apply_layout.addWidget(self.apply_series_index)
        apply_layout.addWidget(self.apply_button)
        layout.addLayout(apply_layout)

        self.tree = QTreeWidget()
        if self.include_air_datetime:
            self.tree.setColumnCount(7)
            self.tree.setHeaderLabels(
                ["Type", "Title", "Series", "Series Title", "# in Series", "Air Date/Time", "Path"]
            )
        else:
            self.tree.setColumnCount(6)
            self.tree.setHeaderLabels(
                ["Type", "Title", "Series", "Series Title", "# in Series", "Path"]
            )
        layout.addWidget(self.tree)

        button_layout = QHBoxLayout()
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

    def build_tree(self):
        self.tree.clear()
        self.row_widgets.clear()
        self.row_order.clear()

        def sort_key(entry):
            series_index = entry.get("show_title") or ""
            title = entry.get("display_title") or ""
            return (_series_index_sort_key(series_index), title.lower())

        for entry in sorted(self.items, key=sort_key):
            path = entry["path"]
            if self.include_air_datetime:
                item = QTreeWidgetItem(["", "", "", "", "", "", path])
            else:
                item = QTreeWidgetItem(["", "", "", "", "", path])
            item.setData(0, Qt.ItemDataRole.UserRole, {"path": path})
            self.tree.addTopLevelItem(item)
            self._init_row_widgets(item, entry)
            self.row_order.append(id(item))

        self.tree.resizeColumnToContents(0)
        self.tree.resizeColumnToContents(1)
        self.tree.resizeColumnToContents(2)
        self.tree.resizeColumnToContents(3)
        self.tree.resizeColumnToContents(4)
        if self.include_air_datetime:
            self.tree.resizeColumnToContents(5)

    def _init_row_widgets(self, item, entry):
        exclude_check = QCheckBox()

        type_combo = QComboBox()
        type_combo.addItems(["Movie", "TV"])
        type_combo.setCurrentText(entry.get("media_type") or "Movie")

        series_check = QCheckBox()
        is_series = entry.get("is_series", False)
        series_check.setChecked(is_series or type_combo.currentText() == "TV")

        series_title_field = QLineEdit()
        series_title_field.setText(entry.get("series_title") or "")

        series_index_field = QLineEdit()
        series_index_field.setText(entry.get("show_title") or "")

        display_title_field = QLineEdit()
        display_title_field.setText(entry.get("display_title") or "")

        air_datetime_field = None
        if self.include_air_datetime:
            air_datetime_field = QLineEdit()
            air_datetime_field.setPlaceholderText("YYYY-MM-DD HH:MM")
            air_datetime_field.setText(entry.get("air_datetime") or "")

        self.tree.setItemWidget(item, 0, type_combo)
        self.tree.setItemWidget(item, 2, series_check)
        self.tree.setItemWidget(item, 3, series_title_field)
        self.tree.setItemWidget(item, 4, series_index_field)
        if self.include_air_datetime:
            self.tree.setItemWidget(item, 5, air_datetime_field)
            self.tree.setItemWidget(item, 1, display_title_field)
        else:
            self.tree.setItemWidget(item, 1, display_title_field)

        self._set_widgets(item, {
            "exclude": exclude_check,
            "type": type_combo,
            "series_check": series_check,
            "series_title": series_title_field,
            "series_index": series_index_field,
            "display_title": display_title_field,
            "air_datetime": air_datetime_field,
            "air_datetime_value": entry.get("air_datetime"),
            "is_folder": False,
        })

        def on_type_change(text):
            if text == "TV" and not series_check.isChecked():
                series_check.setChecked(True)
            self._update_row_enabled(item)

        def on_series_toggle(_checked):
            self._update_row_enabled(item)

        type_combo.currentTextChanged.connect(on_type_change)
        series_check.toggled.connect(on_series_toggle)

        self._update_row_enabled(item)

    def _update_row_enabled(self, item):
        widgets = self._widgets(item)
        widgets["series_check"].setEnabled(True)
        series_enabled = widgets["series_check"].isChecked()
        widgets["series_title"].setEnabled(series_enabled)
        widgets["series_index"].setEnabled(series_enabled)
        widgets["series_title"].setVisible(series_enabled)
        widgets["series_index"].setVisible(series_enabled)

    def apply_to_all(self):
        type_value = self.apply_type.currentText()
        series_checked = self.apply_series.isChecked()
        series_title = self.apply_series_title.text().strip()
        series_index = self.apply_series_index.text().strip()

        prefix = _series_index_prefix(series_index)
        episode_counter = 1

        for key in self.row_order:
            widgets = self.row_widgets.get(key)
            if not widgets:
                continue
            widgets["type"].setCurrentText(type_value)
            widgets["series_check"].setChecked(series_checked or type_value == "TV")
            if series_title:
                widgets["series_title"].setText(series_title)
            if series_index:
                if prefix:
                    widgets["series_index"].setText(f"{prefix}.{episode_counter}")
                    episode_counter += 1
                else:
                    widgets["series_index"].setText(series_index)
            self._update_row_enabled(widgets["item"])

    def get_results(self):
        results = []
        for key in self.row_order:
            widgets = self.row_widgets.get(key)
            if not widgets:
                continue
            item = widgets["item"]
            data = item.data(0, Qt.ItemDataRole.UserRole)
            path = data["path"]
            media_type = widgets["type"].currentText()
            is_series = widgets["series_check"].isChecked()
            series_title = widgets["series_title"].text().strip() or None
            series_index = widgets["series_index"].text().strip() or None
            display_title = widgets["display_title"].text().strip()
            if self.include_air_datetime:
                air_datetime = widgets["air_datetime"].text().strip() or None
            else:
                air_datetime = widgets.get("air_datetime_value")
            if not is_series:
                series_title = None
                series_index = None
            results.append(
                {
                    "path": path,
                    "media_type": media_type,
                    "is_series": is_series,
                    "series_title": series_title,
                    "show_title": series_index,
                    "display_title": display_title,
                    "air_datetime": air_datetime,
                }
            )
        return results

    def _set_widgets(self, item, widgets):
        key = id(item)
        widgets["item"] = item
        self.row_widgets[key] = widgets

    def _widgets(self, item):
        return self.row_widgets.get(id(item))


class PlaceholderDialog(QDialog):
    def __init__(self, series_title, parent=None, default_season=None, get_start_episode=None):
        super().__init__(parent)
        self.setWindowTitle("Add Placeholder(s)")
        self.series_title = series_title
        self.default_season = default_season
        self.get_start_episode = get_start_episode
        self.season_field = QLineEdit()
        self.count_field = QSpinBox()
        self.count_field.setMinimum(1)
        self.count_field.setMaximum(999)
        self.start_datetime = QDateTimeEdit()
        self.start_datetime.setCalendarPopup(True)
        self.start_datetime.setDateTime(datetime.now())
        self.interval_days = QSpinBox()
        self.interval_days.setMinimum(1)
        self.interval_days.setMaximum(365)
        self.interval_days.setValue(7)
        self.add_airing_info = QCheckBox("Add airing info")
        self.titles_table = QTableWidget(0, 2)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        title = QLabel(f"Add placeholders for {self.series_title}")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        form = QHBoxLayout()
        season_label = QLabel("Season:")
        form.addWidget(season_label)
        form.addWidget(self.season_field)
        count_label = QLabel("Count:")
        form.addWidget(count_label)
        form.addWidget(self.count_field)
        layout.addLayout(form)

        layout.addWidget(self.add_airing_info)
        self.airing_row = QWidget()
        date_layout = QHBoxLayout(self.airing_row)
        date_layout.setContentsMargins(0, 0, 0, 0)
        date_layout.addWidget(QLabel("Next Airing:"))
        date_layout.addWidget(self.start_datetime)
        self.every_label = QLabel("Every")
        date_layout.addWidget(self.every_label)
        date_layout.addWidget(self.interval_days)
        self.days_label = QLabel("days")
        date_layout.addWidget(self.days_label)
        layout.addWidget(self.airing_row)

        layout.addWidget(QLabel("Episode title(s) (Leave blank for default)"))
        self.titles_table.setHorizontalHeaderLabels(["Episode", "Title"])
        header = self.titles_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.titles_table.verticalHeader().setVisible(False)
        self.titles_table.setShowGrid(False)
        layout.addWidget(self.titles_table)

        button_layout = QHBoxLayout()
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        self.count_field.valueChanged.connect(self._update_interval_visibility)
        self.count_field.valueChanged.connect(self._refresh_episode_rows)
        self.season_field.textChanged.connect(self._refresh_episode_rows)
        self.add_airing_info.toggled.connect(self._update_airing_visibility)
        if self.default_season is not None:
            self.season_field.setText(str(self.default_season))
        self._update_interval_visibility(self.count_field.value())
        self._update_airing_visibility(self.add_airing_info.isChecked())
        self._refresh_episode_rows()

    def _update_interval_visibility(self, count):
        show = count > 1
        self.every_label.setVisible(show)
        self.interval_days.setVisible(show)
        self.days_label.setVisible(show)

    def _update_airing_visibility(self, checked):
        self.airing_row.setVisible(checked)
        if not checked:
            self._update_interval_visibility(self.count_field.value())

    def _refresh_episode_rows(self):
        count = int(self.count_field.value())
        season_text = self.season_field.text().strip()
        season = int(season_text) if season_text.isdigit() else None
        start_episode = 1
        if season is not None and self.get_start_episode:
            start_episode = self.get_start_episode(season)

        existing = []
        for row in range(self.titles_table.rowCount()):
            item = self.titles_table.item(row, 1)
            existing.append(item.text() if item else "")

        self.titles_table.setRowCount(count)
        for row in range(count):
            if season is not None:
                label = f"S{season:02d}E{start_episode + row:02d}"
            else:
                label = f"Episode {row + 1}"
            episode_item = QTableWidgetItem(label)
            episode_item.setFlags(episode_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.titles_table.setItem(row, 0, episode_item)
            title_item = QTableWidgetItem(existing[row] if row < len(existing) else "")
            self.titles_table.setItem(row, 1, title_item)

    def get_results(self):
        season_text = self.season_field.text().strip()
        if not season_text.isdigit():
            return None
        season = int(season_text)
        count = int(self.count_field.value())
        include_airing = self.add_airing_info.isChecked()
        start_dt = self.start_datetime.dateTime().toPyDateTime() if include_airing else None
        interval = int(self.interval_days.value()) if include_airing else 0
        titles = []
        for row in range(self.titles_table.rowCount()):
            item = self.titles_table.item(row, 1)
            titles.append(item.text().strip() if item else "")
        return {
            "season": season,
            "count": count,
            "start_dt": start_dt,
            "interval_days": interval,
            "titles": titles,
            "include_airing": include_airing,
        }


class LibraryMenu(QWidget):
    def __init__(self, back_callback, parent=None, show_only_watching=False, title_text="Library"):
        super().__init__(parent)
        self.back_callback = back_callback
        self.db = LibraryDB()
        self._mpv_processes = {}
        self._has_loaded_once = False
        self.show_only_watching = show_only_watching
        self.title_text = title_text
        self.init_ui()
        self.load_items()

    def init_ui(self):
        layout = QVBoxLayout(self)

        title = QLabel(self.title_text)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(title)

        self.tree = QTreeWidget()
        self.tree.setColumnCount(6)
        watched_header = "✓" if self.show_only_watching else "Watched"
        self.tree.setHeaderLabels(["Title", "Play", watched_header, "Index", "Notes", "Path"])
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.tree.itemDoubleClicked.connect(self.handle_double_click)
        self.tree.itemExpanded.connect(lambda _item: self._auto_resize_columns())
        self.tree.itemCollapsed.connect(lambda _item: self._auto_resize_columns())
        self.tree.setUniformRowHeights(False)
        self.tree.setStyleSheet("QTreeWidget::item { padding-top: 6px; padding-bottom: 6px; }")
        layout.addWidget(self.tree)
        self._row_height = 36
        header = self.tree.header()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(True)
        header.sectionDoubleClicked.connect(self._on_header_double_click)
        header.installEventFilter(self)
        header.viewport().installEventFilter(self)

        buttons = QHBoxLayout()
        self.add_button = QPushButton("Add to Library")
        self.add_button.clicked.connect(self.add_to_library)
        buttons.addWidget(self.add_button)

        self.play_button = QPushButton("Play")
        self.play_button.clicked.connect(self.play_selected)
        buttons.addWidget(self.play_button)

        self.resume_button = QPushButton("Continue")
        self.resume_button.clicked.connect(self.resume_selected)
        buttons.addWidget(self.resume_button)

        self.mark_watched_button = QPushButton("Mark Watched")
        self.mark_watched_button.clicked.connect(lambda: self.set_selected_watched(True))
        buttons.addWidget(self.mark_watched_button)

        self.mark_unwatched_button = QPushButton("Mark Unwatched")
        self.mark_unwatched_button.clicked.connect(lambda: self.set_selected_watched(False))
        buttons.addWidget(self.mark_unwatched_button)

        layout.addLayout(buttons)

        buttons_row_two = QHBoxLayout()

        self.edit_button = QPushButton("Edit")
        self.edit_button.clicked.connect(self.edit_selected)
        buttons_row_two.addWidget(self.edit_button)

        self.add_placeholder_button = QPushButton("Add Placeholder(s)")
        self.add_placeholder_button.clicked.connect(self.add_placeholders)
        buttons_row_two.addWidget(self.add_placeholder_button)

        self.remove_button = QPushButton("Remove")
        self.remove_button.clicked.connect(self.remove_selected)
        buttons_row_two.addWidget(self.remove_button)

        self.back_button = QPushButton("Back")
        self.back_button.clicked.connect(self.go_back)
        buttons_row_two.addWidget(self.back_button)

        layout.addLayout(buttons_row_two)

    def load_items(self):
        view_state = self._capture_view_state()
        items = self.db.get_items()
        self._apply_auto_airing(items)
        if self.show_only_watching:
            items = self._filter_watching_items(items)
        self.tree.clear()
        self.items_by_path = {item[1]: item for item in items}

        movies_root = QTreeWidgetItem(["Movies", "", "", "", "", ""])
        tv_root = QTreeWidgetItem(["TV Shows", "", "", "", "", ""])
        self._apply_row_height(movies_root)
        self._apply_row_height(tv_root)
        self.tree.addTopLevelItem(movies_root)
        self.tree.addTopLevelItem(tv_root)

        movies = [item for item in items if item[2] == "Movie"]
        movie_series = defaultdict(list)
        standalone_movies = []
        for item in movies:
            is_series = item[4] == 1
            series_title = item[5] or ""
            if is_series and series_title:
                movie_series[series_title].append(item)
            else:
                standalone_movies.append(item)

        movie_entries = []
        for item in standalone_movies:
            movie_entries.append(("item", item[3], item))
        for series_title in movie_series.keys():
            movie_entries.append(("series", series_title, movie_series[series_title]))

        movie_entries.sort(key=lambda x: self._title_sort_key(x[1]))
        for entry_type, title, payload in movie_entries:
            if entry_type == "item":
                self._add_movie_item(movies_root, payload)
            else:
                series_node = QTreeWidgetItem([title, "", "", "", "", ""])
                self._apply_row_height(series_node)
                movies_root.addChild(series_node)
                entries = sorted(
                    payload,
                    key=lambda x: _series_index_sort_key(x[6] or ""),
                )
                for item in entries:
                    self._add_movie_item(series_node, item)

        tv_items = [item for item in items if item[2] == "TV"]
        by_show = defaultdict(list)
        for item in tv_items:
            show_title = item[5] or "Unknown Show"
            by_show[show_title].append(item)

        for show_title in sorted(by_show.keys(), key=self._title_sort_key):
            show_item = QTreeWidgetItem([show_title, "", "", "", "", ""])
            self._apply_row_height(show_item)
            tv_root.addChild(show_item)
            by_season = defaultdict(list)
            for item in by_show[show_title]:
                series_index = item[6] or ""
                parsed_values = _parse_series_index_values(series_index)
                season_part = str(parsed_values[0][0]) if parsed_values else "1"
                by_season[season_part].append(item)

            season_keys = sorted(by_season.keys(), key=lambda x: _series_index_sort_key(x))
            if len(season_keys) == 1:
                episodes = sorted(
                    by_season[season_keys[0]],
                    key=lambda x: _series_index_sort_key(x[6] or ""),
                )
                for item in episodes:
                    self._add_tv_item(show_item, item)
            else:
                for season_key in season_keys:
                    season_item = QTreeWidgetItem([f"Season {season_key}", "", "", "", "", ""])
                    self._apply_row_height(season_item)
                    show_item.addChild(season_item)
                    episodes = sorted(
                        by_season[season_key],
                        key=lambda x: _series_index_sort_key(x[6] or ""),
                    )
                    for item in episodes:
                        self._add_tv_item(season_item, item)

        if self._has_loaded_once:
            self._restore_view_state(view_state)
        else:
            movies_root.setExpanded(self.show_only_watching)
            tv_root.setExpanded(self.show_only_watching)
            self._has_loaded_once = True
        self._update_group_statuses()
        if self.show_only_watching:
            if movies_root.childCount() == 0:
                idx = self.tree.indexOfTopLevelItem(movies_root)
                if idx != -1:
                    self.tree.takeTopLevelItem(idx)
            if tv_root.childCount() == 0:
                idx = self.tree.indexOfTopLevelItem(tv_root)
                if idx != -1:
                    self.tree.takeTopLevelItem(idx)
        self._resize_columns(view_state)

    def _add_movie_item(self, parent, item):
        (
            _id,
            path,
            media_type,
            display_title,
            is_series,
            series_title,
            show_title,
            _added,
            watched,
            is_placeholder,
            air_datetime,
            _currently_airing,
        ) = item
        title = self._format_title(display_title)
        notes = self._format_notes(air_datetime, is_placeholder)
        watched_mark = self._format_watched(watched)
        node = QTreeWidgetItem([title, "", watched_mark, show_title or "", notes, path])
        node.setData(0, Qt.ItemDataRole.UserRole, {"path": path, "is_placeholder": bool(is_placeholder)})
        self._apply_row_height(node)
        parent.addChild(node)
        if is_placeholder:
            self._set_assign_widget(node, path)
        else:
            self._set_play_widget(node, path)

    def _add_tv_item(self, parent, item):
        (
            _id,
            path,
            media_type,
            display_title,
            is_series,
            series_title,
            show_title,
            _added,
            watched,
            is_placeholder,
            air_datetime,
            _currently_airing,
        ) = item
        title = self._format_title(display_title)
        notes = self._format_notes(air_datetime, is_placeholder)
        watched_mark = self._format_watched(watched)
        node = QTreeWidgetItem([title, "", watched_mark, show_title or "", notes, path])
        node.setData(0, Qt.ItemDataRole.UserRole, {"path": path, "is_placeholder": bool(is_placeholder)})
        self._apply_row_height(node)
        parent.addChild(node)
        if is_placeholder:
            self._set_assign_widget(node, path)
        else:
            self._set_play_widget(node, path)

    def _format_title(self, title):
        return title

    def _format_watched(self, watched):
        return "✓" if watched else ""

    def _format_notes(self, air_datetime, is_placeholder):
        if not is_placeholder or not air_datetime:
            return ""
        return f"Airs {air_datetime}"

    def _apply_row_height(self, item):
        item.setSizeHint(0, QSize(0, self._row_height))

    def _set_play_widget(self, item, path):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        play_button = QPushButton("Play")
        play_button.setFixedWidth(56)
        play_button.setFixedHeight(24)
        play_button.clicked.connect(lambda: self._play_paths([path]))
        layout.addWidget(play_button)
        self.tree.setItemWidget(item, 1, widget)

    def _set_resume_widget(self, item, paths):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        resume_button = QPushButton("Continue")
        resume_button.setFixedWidth(72)
        resume_button.setFixedHeight(24)
        resume_button.clicked.connect(lambda: self._play_paths_from_selection(paths, resume=True))
        layout.addWidget(resume_button)
        self.tree.setItemWidget(item, 1, widget)

    def _clear_play_widget(self, item):
        widget = QWidget()
        widget.setLayout(QHBoxLayout())
        self.tree.setItemWidget(item, 1, widget)

    def _set_assign_widget(self, item, placeholder_path):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        assign_button = QPushButton("Find")
        assign_button.setFixedWidth(56)
        assign_button.setFixedHeight(24)
        assign_button.clicked.connect(lambda: self.assign_placeholder(placeholder_path))
        layout.addWidget(assign_button)
        self.tree.setItemWidget(item, 1, widget)

    def handle_double_click(self, item, _column):
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data and data.get("is_placeholder"):
            return
        self.play_item(item, resume=False)

    def play_selected(self):
        items = self.tree.selectedItems()
        if not items:
            QMessageBox.warning(self, "Selection Error", "Please select an item to play.")
            return
        self.play_items(items, resume=False)

    def resume_selected(self):
        items = self.tree.selectedItems()
        if not items:
            QMessageBox.warning(self, "Selection Error", "Please select an item to continue.")
            return
        self.play_items(items, resume=True)

    def play_item(self, item, resume):
        paths = self._collect_leaf_paths(item)
        self._play_paths_from_selection(paths, resume)

    def play_items(self, items, resume):
        paths = []
        for item in items:
            paths.extend(self._collect_leaf_paths(item))
        self._play_paths_from_selection(paths, resume)

    def _play_paths_from_selection(self, paths, resume):
        if not paths:
            QMessageBox.warning(self, "Selection Error", "No media items found to play.")
            return

        sorted_paths = self._sorted_paths(self._dedupe_paths(paths))
        if resume:
            sorted_paths = [
                path
                for path in sorted_paths
                if self.items_by_path.get(path, (None,) * 12)[8] == 0
            ]

        self._play_paths(sorted_paths)

    def _play_paths(self, paths):
        if not paths:
            return
        try:
            if len(paths) == 1:
                os.startfile(paths[0])
                self.db.update_watched(paths, True)
                self.load_items()
            else:
                self._play_paths_in_mpv(paths)
        except OSError:
            QMessageBox.warning(
                self,
                "Playback Error",
                "Unable to launch mpv. Please ensure mpv is installed and available in PATH.",
            )
            return

    def _play_paths_in_mpv(self, paths):
        script_path = os.path.join(os.path.dirname(__file__), "..", "core", "whatch_watch.lua")
        script_path = os.path.abspath(script_path).replace("\\", "/")
        fd, log_path = tempfile.mkstemp(prefix="whatch_mpv_", suffix=".log")
        os.close(fd)
        log_path = os.path.abspath(log_path).replace("\\", "/")

        process = QProcess(self)
        process.finished.connect(lambda _code, _status, proc=process: self._on_mpv_finished(proc))
        process.errorOccurred.connect(
            lambda _error, proc=process: self._on_mpv_error(proc)
        )
        self._mpv_processes[process] = {"log_path": log_path, "paths": paths}
        args = [
            f"--script={script_path}",
            f"--script-opts=whatch_watch-log_path={log_path}",
            *paths,
        ]
        process.start("mpv", args)
        if not process.waitForStarted(2000):
            self._mpv_processes.pop(process, None)
            QMessageBox.warning(
                self,
                "Playback Error",
                "Unable to launch mpv. Please ensure mpv is installed and available in PATH.",
            )

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
        played_paths = self._read_played_paths(info["log_path"], info["paths"])
        self._cleanup_mpv_log(info["log_path"])
        if played_paths:
            self.db.update_watched(played_paths, True)
            self.load_items()

    def _read_played_paths(self, log_path, allowed_paths):
        if not os.path.exists(log_path):
            return []
        allowed_by_norm = {}
        allowed_by_basename = defaultdict(list)
        for path in allowed_paths:
            normalized = self._normalize_media_path(path)
            allowed_by_norm[normalized] = path
            allowed_by_basename[os.path.basename(path).lower()].append(path)
        played = []
        seen = set()
        with open(log_path, "r", encoding="utf-8") as handle:
            for line in handle:
                path = line.strip()
                if not path:
                    continue
                normalized = self._normalize_media_path(path)
                matched = allowed_by_norm.get(normalized)
                if not matched:
                    basename = os.path.basename(path).lower()
                    candidates = allowed_by_basename.get(basename, [])
                    if len(candidates) == 1:
                        matched = candidates[0]
                if not matched or matched in seen:
                    continue
                played.append(matched)
                seen.add(matched)
        return played

    def _cleanup_mpv_log(self, log_path):
        try:
            if os.path.exists(log_path):
                os.remove(log_path)
        except OSError:
            pass

    def _collect_leaf_paths(self, item):
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data and data.get("path") and not data.get("is_placeholder"):
            return [data["path"]]
        paths = []
        for i in range(item.childCount()):
            paths.extend(self._collect_leaf_paths(item.child(i)))
        return paths

    def _sorted_paths(self, paths):
        def sort_key(path):
            item = self.items_by_path.get(path)
            if not item:
                return (_series_index_sort_key(""), path.lower())
            series_index = item[6] or ""
            title = item[3] or ""
            if series_index:
                return (_series_index_sort_key(series_index), title.lower())
            return ((0, 0), title.lower())

        return sorted(paths, key=sort_key)

    def set_selected_watched(self, watched):
        selected = self.tree.selectedItems()
        if not selected:
            QMessageBox.warning(self, "Selection Error", "Please select an item to update.")
            return
        paths = []
        for item in selected:
            paths.extend(self._collect_paths(item))
        paths = self._dedupe_paths(paths)
        if not paths:
            QMessageBox.warning(self, "Selection Error", "No media items found to update.")
            return
        self.db.update_watched(paths, watched)
        self.load_items()

    def _select_folders(self):
        dialog = QFileDialog(self, "Select Media Folder(s)")
        dialog.setFileMode(QFileDialog.FileMode.Directory)
        dialog.setOption(QFileDialog.Option.ShowDirsOnly, True)
        dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)
        for view in dialog.findChildren(QAbstractItemView):
            view.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return dialog.selectedFiles()
        return []

    def _select_files(self):
        dialog = QFileDialog(self, "Select Media File(s)")
        dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
        dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)
        dialog.setNameFilter(
            "Video Files (*.mp4 *.mkv *.avi *.mov *.wmv *.flv *.m4v *.mpg *.mpeg *.webm *.bdmv *.m2ts);;All Files (*)"
        )
        for view in dialog.findChildren(QAbstractItemView):
            view.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return dialog.selectedFiles()
        return []

    def add_to_library(self):
        chooser = QMessageBox(self)
        chooser.setWindowTitle("Add to Library")
        chooser.setText("Add a file or a folder?")
        file_button = chooser.addButton("File(s)", QMessageBox.ButtonRole.AcceptRole)
        folder_button = chooser.addButton("Folder(s)", QMessageBox.ButtonRole.AcceptRole)
        chooser.addButton(QMessageBox.StandardButton.Cancel)
        chooser.exec()

        if chooser.clickedButton() == file_button:
            selected = self._select_files()
        elif chooser.clickedButton() == folder_button:
            selected = self._select_folders()
        else:
            return

        if not selected:
            return

        dialog = LibraryImportDialog(selected, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        results = dialog.get_results()
        if not results:
            QMessageBox.information(
                self,
                "No Media Found",
                "No supported video files were found in the selection.",
            )
            return

        for item in results:
            self.db.add_item(
                item["path"],
                item["media_type"],
                item["display_title"],
                is_series=item["is_series"],
                series_title=item["series_title"],
                show_title=item["show_title"],
            )

        self.load_items()

    def remove_selected(self):
        selected = self.tree.selectedItems()
        if not selected:
            QMessageBox.warning(self, "Selection Error", "Please select an item to remove.")
            return

        paths = []
        for item in selected:
            paths.extend(self._collect_paths(item))
        paths = self._dedupe_paths(paths)

        if not paths:
            QMessageBox.warning(self, "Selection Error", "No media items found to remove.")
            return

        reply = QMessageBox.question(
            self,
            "Remove Items",
            f"Remove {len(paths)} item(s) from the library?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self.db.delete_by_paths(paths)
        self.load_items()

    def _collect_paths(self, item):
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data and data.get("path"):
            return [data["path"]]
        paths = []
        for i in range(item.childCount()):
            paths.extend(self._collect_paths(item.child(i)))
        return paths

    def _dedupe_paths(self, paths):
        seen = set()
        deduped = []
        for path in paths:
            if path in seen:
                continue
            seen.add(path)
            deduped.append(path)
        return deduped

    def _normalize_media_path(self, path):
        text = (path or "").strip()
        if text.lower().startswith("file://"):
            text = text[7:]
            if text.startswith("/") and len(text) > 2 and text[2] == ":":
                text = text[1:]
        text = text.replace("/", "\\")
        return os.path.normcase(os.path.abspath(text))

    def _filter_watching_items(self, items):
        series_counts = defaultdict(lambda: [0, 0])
        for item in items:
            is_series = item[4] == 1
            series_title = item[5]
            media_type = item[2]
            if not is_series or not series_title:
                continue
            watched = item[8]
            key = (media_type, series_title)
            series_counts[key][1] += 1
            if watched:
                series_counts[key][0] += 1

        watching_keys = {
            key for key, counts in series_counts.items() if 0 < counts[0] < counts[1]
        }
        if not watching_keys:
            return []
        return [
            item
            for item in items
            if item[4] == 1 and item[5] and (item[2], item[5]) in watching_keys
        ]

    def _title_sort_key(self, value):
        if not value:
            return ""
        text = value.strip()
        lowered = text.lower()
        for prefix in ("the ", "el ", "la "):
            if lowered.startswith(prefix):
                return lowered[len(prefix):]
        return lowered

    def _capture_view_state(self):
        header = self.tree.header()
        column_sizes = [header.sectionSize(i) for i in range(self.tree.columnCount())]
        expanded_keys = set()
        selected_keys = set()
        scroll_value = self.tree.verticalScrollBar().value()

        it = QTreeWidgetItemIterator(self.tree)
        while it.value():
            item = it.value()
            key = self._item_key(item)
            if item.isExpanded():
                expanded_keys.add(key)
            if item.isSelected():
                selected_keys.add(key)
            it += 1

        return {
            "column_sizes": column_sizes,
            "expanded_keys": expanded_keys,
            "selected_keys": selected_keys,
            "scroll_value": scroll_value,
        }

    def _restore_view_state(self, state):
        expanded_keys = state.get("expanded_keys", set())
        selected_keys = state.get("selected_keys", set())

        it = QTreeWidgetItemIterator(self.tree)
        while it.value():
            item = it.value()
            key = self._item_key(item)
            if key in expanded_keys:
                item.setExpanded(True)
            if key in selected_keys:
                item.setSelected(True)
            it += 1

        scroll_value = state.get("scroll_value")
        if scroll_value is not None:
            self.tree.verticalScrollBar().setValue(scroll_value)

    def _item_key(self, item):
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data and data.get("path"):
            return f"path::{data['path']}"
        parts = []
        current = item
        while current is not None:
            parts.append(current.text(0))
            current = current.parent()
        return "node::" + "/".join(reversed(parts))

    def _resize_columns(self, view_state):
        self._auto_resize_columns()
        sizes = view_state.get("column_sizes", [])
        if len(sizes) == self.tree.columnCount():
            self.tree.setColumnWidth(5, sizes[5])

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

    def _update_group_statuses(self):
        def update_node(node):
            data = node.data(0, Qt.ItemDataRole.UserRole)
            if data and data.get("path"):
                watched = self.items_by_path.get(data["path"], (None,) * 12)[8]
                return (1 if watched else 0), 1

            watched_count = 0
            total_count = 0
            for i in range(node.childCount()):
                child = node.child(i)
                child_watched, child_total = update_node(child)
                watched_count += child_watched
                total_count += child_total

            if node.parent() is not None:
                if total_count > 0 and watched_count == total_count:
                    node.setText(2, "✓")
                    self._clear_play_widget(node)
                elif watched_count > 0:
                    if self.show_only_watching:
                        node.setText(2, "")
                    else:
                        node.setText(2, "Watching")
                    paths = self._collect_leaf_paths(node)
                    unwatched = [
                        path
                        for path in self._sorted_paths(paths)
                        if self.items_by_path.get(path, (None,) * 12)[8] == 0
                    ]
                    if unwatched:
                        self._set_resume_widget(node, unwatched)
                    else:
                        self._clear_play_widget(node)
                else:
                    node.setText(2, "")
                    self._clear_play_widget(node)

            return watched_count, total_count

        for i in range(self.tree.topLevelItemCount()):
            update_node(self.tree.topLevelItem(i))

    def edit_selected(self):
        selected = self.tree.selectedItems()
        if not selected:
            QMessageBox.warning(self, "Selection Error", "Please select items to edit.")
            return

        paths = []
        for item in selected:
            paths.extend(self._collect_paths(item))
        paths = self._dedupe_paths(paths)
        if not paths:
            QMessageBox.warning(self, "Selection Error", "No media items found to edit.")
            return

        items = []
        has_placeholder = False
        has_non_placeholder = False
        for path in paths:
            record = self.items_by_path.get(path)
            if not record:
                continue
            (
                _id,
                path,
                media_type,
                display_title,
                is_series,
                series_title,
                show_title,
                _added,
                _watched,
                _is_placeholder,
                air_datetime,
                _currently_airing,
            ) = record
            if _is_placeholder:
                has_placeholder = True
            else:
                has_non_placeholder = True
            items.append(
                {
                    "path": path,
                    "media_type": media_type,
                    "display_title": display_title,
                    "is_series": bool(is_series),
                    "series_title": series_title,
                    "show_title": show_title,
                    "air_datetime": air_datetime,
                    "is_placeholder": bool(_is_placeholder),
                }
            )

        if not items:
            QMessageBox.warning(self, "Selection Error", "No media items found to edit.")
            return
        if has_placeholder and has_non_placeholder:
            QMessageBox.warning(
                self,
                "Selection Error",
                "Please edit placeholders and non-placeholders separately.",
            )
            return

        dialog = LibraryEditDialog(
            items,
            parent=self,
            include_air_datetime=has_placeholder,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        results = dialog.get_results()
        if not results:
            return

        self.db.update_items(results)
        self.load_items()

    def add_placeholders(self):
        series_title, media_type = self._resolve_series_from_selection()
        if not series_title:
            return
        selected = self.tree.selectedItems()
        default_season = self._selected_season_number(selected)
        dialog = PlaceholderDialog(
            series_title,
            parent=self,
            default_season=default_season,
            get_start_episode=lambda season: self._next_episode_number(series_title, season, media_type),
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        results = dialog.get_results()
        if not results:
            QMessageBox.warning(
                self,
                "Input Error",
                "Please provide a valid season number.",
            )
            return

        season = results["season"]
        count = results["count"]
        start_dt = results["start_dt"]
        interval_days = results["interval_days"]
        titles = results["titles"]
        include_airing = results["include_airing"]

        start_episode = self._next_episode_number(series_title, season, media_type)
        for offset in range(count):
            episode_number = start_episode + offset
            index_value = f"{season}.{episode_number}"
            title_value = titles[offset] if offset < len(titles) else ""
            if title_value:
                title = title_value
            else:
                title = f"S{season:02d}E{episode_number:02d}"
            if include_airing and start_dt:
                air_dt = start_dt + timedelta(days=interval_days * offset)
                air_text = air_dt.strftime("%Y-%m-%d %H:%M")
            else:
                air_text = None
            placeholder_path = (
                f"__placeholder__::{series_title}::S{season}E{episode_number}::{uuid.uuid4()}"
            )
            self.db.add_item(
                placeholder_path,
                media_type,
                title,
                is_series=True,
                series_title=series_title,
                show_title=index_value,
                is_placeholder=True,
                air_datetime=air_text,
                currently_airing=0,
            )

        self.load_items()

    def _selected_season_number(self, selected_items):
        seasons = set()
        for item in selected_items:
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if data and data.get("path"):
                record = self.items_by_path.get(data["path"])
                if record:
                    for season, _episode in _parse_series_index_values(record[6] or ""):
                        seasons.add(season)
                continue

            text = item.text(0).strip()
            if text.lower().startswith("season "):
                parts = text.split()
                if len(parts) >= 2 and parts[1].isdigit():
                    seasons.add(int(parts[1]))
        if len(seasons) == 1:
            return seasons.pop()
        return None

    def assign_placeholder(self, placeholder_path):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Assign File",
            "",
            "Video Files (*.mp4 *.mkv *.avi *.mov *.wmv *.flv *.m4v *.mpg *.mpeg *.webm *.bdmv *.m2ts);;All Files (*)",
        )
        if not file_path:
            return
        if file_path in self.items_by_path:
            QMessageBox.warning(
                self,
                "Assignment Error",
                "That file is already in the library.",
            )
            return
        self.db.assign_placeholder(placeholder_path, file_path)
        self.load_items()

    def _apply_auto_airing(self, items):
        now = datetime.now()
        status_by_series = defaultdict(lambda: False)
        for item in items:
            series_title = item[5]
            if not series_title:
                continue
            is_placeholder = item[9]
            air_datetime = item[10]
            if not is_placeholder or not air_datetime:
                continue
            try:
                air_dt = datetime.strptime(air_datetime, "%Y-%m-%d %H:%M")
            except ValueError:
                continue
            if air_dt > now:
                status_by_series[(item[2], series_title)] = True

        for (media_type, series_title), is_airing in status_by_series.items():
            self.db.update_currently_airing(series_title, media_type, is_airing)

    def _resolve_series_from_selection(self):
        selected = self.tree.selectedItems()
        if not selected:
            QMessageBox.warning(self, "Selection Error", "Please select a show or series.")
            return None, None
        paths = []
        for item in selected:
            paths.extend(self._collect_paths(item))
        paths = self._dedupe_paths(paths)
        if not paths:
            QMessageBox.warning(self, "Selection Error", "Please select a show or series.")
            return None, None

        series_titles = set()
        media_types = set()
        for path in paths:
            record = self.items_by_path.get(path)
            if not record:
                continue
            series_title = record[5]
            media_type = record[2]
            if not series_title:
                continue
            series_titles.add(series_title)
            media_types.add(media_type)

        if len(series_titles) != 1 or len(media_types) != 1:
            QMessageBox.warning(
                self,
                "Selection Error",
                "Please select items from a single series.",
            )
            return None, None

        return series_titles.pop(), media_types.pop()

    def _next_episode_number(self, series_title, season, media_type):
        max_episode = 0
        for item in self.items_by_path.values():
            if item[5] != series_title or item[2] != media_type:
                continue
            for idx_season, idx_episode in _parse_series_index_values(item[6] or ""):
                if idx_season != season:
                    continue
                max_episode = max(max_episode, idx_episode)
        return max_episode + 1 if max_episode > 0 else 1

    def go_back(self):
        self.db.close()
        self.back_callback()
