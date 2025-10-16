from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.make_ass import build_lines, render_dialogue


def test_render_dialogue_uses_next_start_gap_for_durations():
    words = [
        {"w": "Hello", "s": 0.0, "e": 0.5},
        {"w": "world", "s": 0.7, "e": 1.1},
        {"w": "again", "s": 1.4, "e": 1.8},
    ]
    text, final_end = render_dialogue(words, pad_end=0.2)

    assert text == "{\\k70}Hello {\\k70}world {\\k60}again"
    assert final_end == 2.0


def test_render_dialogue_clamps_final_padding_to_next_line_start():
    words = [
        {"w": "Stay", "s": 3.0, "e": 3.5},
    ]
    text, final_end = render_dialogue(words, pad_end=0.5, next_line_start=3.8)

    assert text == "{\\k80}Stay"
    assert final_end == 3.8


def test_render_dialogue_respects_word_end_when_next_word_overlaps():
    words = [
        {"w": "Quick", "s": 0.0, "e": 0.5},
        {"w": "step", "s": 0.4, "e": 0.9},
    ]
    text, _ = render_dialogue(words, pad_end=0.1)

    assert text.startswith("{\\k50}Quick")


def test_build_lines_extends_dialogue_end_to_karaoke_duration():
    aligned = {
        "lines": [
            {
                "s": 0.0,
                "words": [
                    {"w": "Hi", "s": 0.0, "e": 0.4},
                    {"w": "there", "s": 0.6, "e": 1.0},
                ],
            }
        ]
    }

    lines = build_lines(aligned, pad_end=0.5)

    assert lines == [
        "Dialogue: 0,0:00:00.000,0:00:01.500,Karo,,0,0,120,,{\\k60}Hi {\\k90}there"
    ]
