import os
import re
from collections import defaultdict
from datetime import datetime


VIDEO_EXTENSIONS = (
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
)

VIDEO_FILE_FILTER = f"Video Files ({' '.join(f'*{ext}' for ext in VIDEO_EXTENSIONS)});;All Files (*)"


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
    text = re.sub(r"\s*\(\d{4}\).*$", "", text)
    text = re.split(r"\s+-\s+season\s+\d+.*$", text, maxsplit=1, flags=re.IGNORECASE)[0]
    text = re.split(r"\s+S\d{1,2}(?!E\d)\b.*$", text, maxsplit=1, flags=re.IGNORECASE)[0]
    text = re.sub(r"\s+(?:19|20)\d{2}$", "", text)
    cleaned = text.strip(" -._")
    if cleaned and cleaned == cleaned.lower():
        return _normalize_episode_title_case(cleaned)
    return cleaned


def _normalize_episode_title_case(text):
    if not text:
        return ""

    minor = {
        "a",
        "an",
        "and",
        "as",
        "at",
        "but",
        "by",
        "for",
        "from",
        "in",
        "nor",
        "of",
        "on",
        "or",
        "the",
        "to",
        "vs",
        "via",
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


def _parse_air_datetime_value(air_datetime):
    if not air_datetime:
        return None
    try:
        return datetime.strptime(air_datetime, "%Y-%m-%d %H:%M")
    except ValueError:
        return None


def _format_air_datetime_display(air_dt, include_time=True, include_year=True):
    if not air_dt:
        return ""
    if include_year:
        date_text = air_dt.strftime("%d-%b-%Y")
    else:
        date_text = air_dt.strftime("%d-%b")
    if include_time:
        return f"{date_text} {air_dt.strftime('%H:%M')}"
    return date_text


def _format_last_aired_dates(air_dates):
    if not air_dates:
        return ""
    if len(air_dates) == 1:
        return _format_air_datetime_display(air_dates[0], include_time=False, include_year=True)
    if len(air_dates) == 2:
        older, newer = air_dates
        older_has_year = older.year != newer.year
        return (
            f"{_format_air_datetime_display(older, include_time=False, include_year=older_has_year)} & "
            f"{_format_air_datetime_display(newer, include_time=False, include_year=True)}"
        )

    older, newer, newest = air_dates[-3:]
    older_has_year = older.year != newer.year
    newer_has_year = newer.year != newest.year
    return (
        f"{_format_air_datetime_display(older, include_time=False, include_year=older_has_year)}, "
        f"{_format_air_datetime_display(newer, include_time=False, include_year=newer_has_year)}, & "
        f"{_format_air_datetime_display(newest, include_time=False, include_year=True)}"
    )


def _build_show_air_notes(tv_items, now=None):
    if now is None:
        now = datetime.now()
    by_show = defaultdict(list)
    for item in tv_items:
        show_title = item[5] or "Unknown Show"
        is_placeholder = bool(item[9])
        air_dt = _parse_air_datetime_value(item[10])
        if not is_placeholder or not air_dt:
            continue
        by_show[show_title].append(air_dt)

    notes = {}
    for show_title, datetimes in by_show.items():
        datetimes = sorted(datetimes)
        past = [dt for dt in datetimes if dt <= now]
        if past:
            notes[show_title] = f"Last aired {_format_last_aired_dates(past[-3:])}"
            continue
        upcoming = [dt for dt in datetimes if dt > now]
        if not upcoming:
            continue
        notes[show_title] = f"Next airs {_format_air_datetime_display(upcoming[0])}"
    return notes


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
        tail = name[loose_match.end() :]
        show = _clean_series_title(re.sub(r"[._]+", " ", show_raw).strip(" -._"))
        code_text = loose_match.group(0)

        tail = tail.strip(" -._")
        quality_marker = re.search(
            r"(?i)(?:^|[\s._-])(?:hdr|dv|uhd|720p|1080p|2160p|webrip|web-dl|web|bluray|bdrip|amzn|atvp|nf|ddp?|atmos|aac|x264|x265|h264|h265|hevc|proper|repack|remux)\b",
            tail,
        )
        if quality_marker:
            tail = tail[: quality_marker.start()]
        tail = re.sub(r"\[[^\]]*\]\s*$", "", tail).strip(" -._")
        tail = re.sub(r"[._]+", " ", tail).strip()
        if tail:
            words = tail.split()
            language_tokens = {
                "ita",
                "eng",
                "en",
                "it",
                "spa",
                "esp",
                "fra",
                "fre",
                "deu",
                "ger",
                "jpn",
                "kor",
                "rus",
                "pt",
                "por",
                "lat",
                "multi",
                "sub",
                "subs",
                "dub",
                "dual",
                "audio",
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
    if re.search(r"\bseason\s+\d+\s*-\s*\d+\b", lowered):
        return None
    if re.search(r"\bS\d{1,2}\s*-\s*S\d{1,2}\b", text, flags=re.IGNORECASE):
        return None
    if lowered.startswith("season"):
        parts = lowered.split()
        if len(parts) >= 2 and parts[1].isdigit():
            return int(parts[1])
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
