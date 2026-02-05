import os
import sys
from pathlib import Path

# Ensure repository root is on sys.path so we import local app package
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.ui.library_menu import (
    _clean_series_title,
    _default_episode_title,
    _default_show_and_series,
    _extract_tv_episode_parts,
    _import_dir_sort_key,
    _import_file_sort_key,
    _normalize_episode_title_case,
    _parse_series_index_values,
    _season_number_from_name,
    _series_index_sort_key,
)


def test_clean_series_title_removes_year_and_tail():
    raw = "30 Rock (2005) Season 1-7 S01-S07 (1080p BluRay x265 HEVC 10bit AAC 5.1 Silence)"
    assert _clean_series_title(raw) == "30 Rock"


def test_extract_tv_episode_parts_uses_episode_title_and_series():
    path = r"C:\TV\30 Rock (2005)\Season 7\30 Rock (2005) - S07E03 - Stride Of Pride (1080p BluRay x265 Silence).mkv"
    parsed = _extract_tv_episode_parts(path)
    assert parsed is not None
    assert parsed["series_title"] == "30 Rock"
    assert parsed["episode_code"] == "S07E03"
    assert parsed["series_index"] == "7.3"
    assert parsed["episode_title"] == "Stride of Pride"


def test_default_episode_title_falls_back_to_series_index_code():
    path = r"C:\TV\30 Rock\Season 1\random-source-name-that-does-not-match.mkv"
    assert _default_episode_title(path, "1.5") == "S01E05"


def test_default_episode_title_uses_hard_default_when_no_parse_or_index():
    path = r"C:\TV\30 Rock\Season 1\random-source-name-that-does-not-match.mkv"
    assert _default_episode_title(path, "") == "S01E01"


def test_normalize_episode_title_case_handles_minor_words():
    assert _normalize_episode_title_case("the head and the hair") == "The Head and the Hair"


def test_normalize_episode_title_case_preserves_hyphenated_words():
    assert _normalize_episode_title_case("jack-tor") == "Jack-Tor"
    assert _normalize_episode_title_case("double-edged sword") == "Double-Edged Sword"
    assert _normalize_episode_title_case("do-over") == "Do-Over"


def test_normalize_episode_title_case_keeps_vs_lowercase():
    assert _normalize_episode_title_case("aunt phatso vs. jack donaghy") == "Aunt Phatso vs. Jack Donaghy"


def test_normalize_episode_title_case_keeps_first_word_after_inverted_exclamation_capitalized():
    assert _normalize_episode_title_case("¡qué sorpresa!") == "¡Qué Sorpresa!"


def test_normalize_episode_title_case_preserves_acronyms_and_roman_numerals():
    assert _normalize_episode_title_case("MILF island") == "MILF Island"
    assert _normalize_episode_title_case("queen of jordan ii mystery of the phantom pooper") == (
        "Queen of Jordan II Mystery of the Phantom Pooper"
    )


def test_normalize_episode_title_case_preserves_alnum_case_and_parenthetical_words():
    assert _normalize_episode_title_case("live from studio 6H (east coast)") == "Live from Studio 6H (East Coast)"
    assert _normalize_episode_title_case("the one with the cast of “night court”") == (
        "The One With the Cast of “Night Court”"
    )


def test_extract_tv_episode_parts_supports_double_episode_ranges():
    path = r"C:\TV\30 Rock (2005)\Season 7\30 Rock (2005) - S07E12-E13 - Hogcock! & Last Lunch (1080p BluRay x265 Silence).mkv"
    parsed = _extract_tv_episode_parts(path)
    assert parsed is not None
    assert parsed["episode_code"] == "S07E12-E13"
    assert parsed["series_index"] == "7.12-13"
    assert parsed["episode_title"] == "Hogcock! & Last Lunch"


def test_parse_series_index_values_expands_ranges():
    assert _parse_series_index_values("5.20-21") == [(5, 20), (5, 21)]


def test_series_index_sort_key_uses_first_episode_from_range():
    assert _series_index_sort_key("5.20-21") == (5, 20)


def test_import_dir_sort_key_orders_seasons_numerically_before_other_folders():
    names = ["Featurettes", "Season 7", "Season 2", "Season 10", "Season 1"]
    assert sorted(names, key=_import_dir_sort_key) == [
        "Season 1",
        "Season 2",
        "Season 7",
        "Season 10",
        "Featurettes",
    ]


def test_extract_tv_episode_parts_supports_loose_spaced_pattern_with_title():
    path = (
        r"C:\TV\The Pitt\Season 2\The Pitt S02E04 10 00 A M 1080p AMZN WEB-DL DD 5 1 H 264-playWEB[asdf].mkv"
    )
    parsed = _extract_tv_episode_parts(path)
    assert parsed is not None
    assert parsed["series_title"] == "The Pitt"
    assert parsed["series_index"] == "2.4"
    assert parsed["episode_title"] == "10 00 A M"


def test_extract_tv_episode_parts_supports_dotted_pattern_without_title():
    path = r"C:\TV\The Pitt\Season 2\The.Pitt.S02E01.1080p.WEB.h264-ETHEL[asdf].mkv"
    parsed = _extract_tv_episode_parts(path)
    assert parsed is not None
    assert parsed["series_title"] == "The Pitt"
    assert parsed["series_index"] == "2.1"
    assert parsed["episode_title"] == "S02E01"


def test_import_file_sort_key_prefers_detected_episode_numbers():
    season_dir = r"C:\TV\The Pitt\Season 2"
    spaced = os.path.join(
        season_dir,
        "The Pitt S02E04 10 00 A M 1080p AMZN WEB-DL DD 5 1 H 264-playWEB[asdf].mkv",
    )
    dotted_1 = os.path.join(season_dir, "The.Pitt.S02E01.1080p.WEB.h264-ETHEL[asdf].mkv")
    dotted_2 = os.path.join(season_dir, "The.Pitt.S02E02.1080p.WEB.h264-ETHEL[asdf].mkv")
    dotted_3 = os.path.join(season_dir, "The.Pitt.S02E03.1080p.WEB.h264-ETHEL[asdf].mkv")
    paths = [spaced, dotted_1, dotted_2, dotted_3]
    ordered = sorted(paths, key=_import_file_sort_key)
    assert ordered == [dotted_1, dotted_2, dotted_3, spaced]


def test_season_number_from_name_supports_sxx_folder_style():
    assert _season_number_from_name("Shrinking.S01.1080p.ATVP.WEB-DL.DDP5.1.H.264-EniaHD") == 1
    assert _season_number_from_name("Season 3") == 3


def test_season_number_from_name_ignores_season_range_collection_names():
    assert _season_number_from_name("Brooklyn Nine-Nine (2013) Season 1-8 S01-S08 REPACK") is None
    assert _season_number_from_name("Show S01-S03") is None


def test_clean_series_title_extracts_show_from_sxx_release_folder_name():
    assert _clean_series_title("Shrinking.S01.1080p.ATVP.WEB-DL.DDP5.1.H.264-EniaHD") == "Shrinking"


def test_clean_series_title_removes_trailing_year_from_release_folder_name():
    raw = "3.Body.Problem.2024.S01.MULTI.2160p.WEB-DL.SDR.H265-AOC"
    assert _clean_series_title(raw) == "3 Body Problem"


def test_extract_tv_episode_parts_strips_language_tokens_and_dots_in_title():
    path = (
        r"C:\TV\Shrinking\Season 2\Shrinking.S02E02.Amo.Il.Dolore.ITA-ENG.2160p.ATVP.WEB-DL.DDP5.1.Atmos.DV.HDR.H.265-gattopollo.mkv"
    )
    parsed = _extract_tv_episode_parts(path)
    assert parsed is not None
    assert parsed["series_title"] == "Shrinking"
    assert parsed["series_index"] == "2.2"
    assert parsed["episode_title"] == "Amo Il Dolore"


def test_extract_tv_episode_parts_drops_hdr_only_tail_and_uses_default_code_title():
    path = r"C:\TV\Shrinking\Season 2\shrinking.s02e01.hdr.2160p.web.h265-successfulcrab.mkv"
    parsed = _extract_tv_episode_parts(path)
    assert parsed is not None
    assert parsed["series_title"] == "Shrinking"
    assert parsed["series_index"] == "2.1"
    assert parsed["episode_title"] == "S02E01"


def test_extract_tv_episode_parts_supports_underscore_separator_format():
    path = r"C:\TV\Some Show\Season 1\S01E06_The Stars Our Destination.mkv"
    parsed = _extract_tv_episode_parts(path)
    assert parsed is not None
    assert parsed["series_index"] == "1.6"
    assert parsed["episode_title"] == "The Stars Our Destination"


def test_default_show_and_series_uses_grandparent_for_sxx_season_folder():
    path = (
        r"C:\TV\3.Body.Problem.2024.S01.MULTI.2160p.WEB-DL.SDR.H265-AOC\S01"
        r"\3.body.problem.s01e01.2160p.web.h265.mkv"
    )
    show, series = _default_show_and_series(path)
    assert show == "3 Body Problem"
    assert series == "S01"
