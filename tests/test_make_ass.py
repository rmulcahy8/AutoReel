import pytest

from pipeline.make_ass import build_lines, render_dialogue


def test_render_dialogue_uses_next_starts_and_extends_final_token():
    words = [
        {"w": "alpha", "s": 0.0, "e": 0.3},
        {"w": "beta", "s": 0.6, "e": 1.0},
        {"w": "gamma", "s": 1.3, "e": 1.5},
    ]
    text, final_end = render_dialogue(words, pad_end=0.5, next_line_start=3.0)
    assert text == "{\\k60}alpha {\\k70}beta {\\k70}gamma"
    assert pytest.approx(final_end, rel=1e-6) == 2.0


def test_render_dialogue_handles_overlap_and_clamps_to_next_line():
    words = [
        {"w": "one", "s": 0.5, "e": 0.6},
        {"w": "two", "s": 0.45, "e": 0.7},
        {"w": "three", "s": 1.0, "e": 1.2},
    ]
    text, final_end = render_dialogue(words, pad_end=0.5, next_line_start=1.25)
    assert text == "{\\k1}one {\\k55}two {\\k25}three"
    assert pytest.approx(final_end, rel=1e-6) == 1.25


def test_build_lines_uses_karaoke_duration_for_dialogue_end():
    aligned = {
        "lines": [
            {
                "s": 0.0,
                "words": [
                    {"w": "alpha", "s": 0.0},
                    {"w": "beta", "s": 0.5},
                    {"w": "gamma", "s": 1.2, "e": 1.4},
                ],
            }
        ]
    }

    lines = build_lines(aligned, pad_end=0.6)
    assert lines == [
        "Dialogue: 0,0:00:00.000,0:00:02.000,Karo,,0,0,120,,{\\k50}alpha {\\k70}beta {\\k80}gamma"
    ]

