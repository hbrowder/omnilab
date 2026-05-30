"""Tests for EVE-NG .unl annotation parsing (drawing-tool import).

Fixtures are real labs pulled from the EVE-NG server (raw type= attrs):
  master_bgp.unl  — 19 text, 2 circle, 1 shape(=ellipse) → 19 text + 3 circle
  squares.unl     — 28 text, 3 square → 28 text + 3 rectangle
                    (rounded rects, multi-line <strong> text)
Note: EVE type="shape" holds a real SVG primitive; we classify by the SVG
element (<ellipse>/<circle> → circle, <rect> → rectangle), not the attribute.
"""
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

# Import the parser from the migration script
SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
from migrate_lab import (  # noqa: E402
    parse_annotations,
    _parse_inline_style,
    _px,
    _html_to_text,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "unl"


def _annotations(name):
    root = ET.parse(FIXTURES / name).getroot()
    return parse_annotations(root)


# ── unit tests for helpers ──

def test_px_conversions():
    assert _px("176px") == 176.0
    assert _px("153.778px") == 153.778
    assert _px("auto") is None
    assert _px("") is None
    assert _px(None) is None


def test_parse_inline_style():
    s = _parse_inline_style("z-index: 999; left: 176px; top: 332px; width: auto;")
    assert s["z-index"] == "999"
    assert s["left"] == "176px"
    assert s["width"] == "auto"


def test_html_to_text_strips_tags_and_entities():
    html = "<p><strong>VLAN 10 E1/1</strong></p><p>VLAN 20</p><p>&nbsp;</p><p>&nbsp;</p>"
    # trailing whitespace-only paragraphs dropped, blocks joined by newline
    assert _html_to_text(html) == "VLAN 10 E1/1\nVLAN 20"


# ── integration against real fixtures ──

def test_master_bgp_counts_and_types():
    objs = _annotations("master_bgp.unl")
    types = [o["type"] for o in objs]
    assert types.count("text") == 19
    # 2 type="circle" + 1 type="shape" holding an <ellipse> → 3 circles
    assert types.count("circle") == 3
    assert types.count("rectangle") == 0  # square→rectangle, none here


def test_squares_map_to_rectangles():
    objs = _annotations("squares.unl")
    types = [o["type"] for o in objs]
    assert types.count("text") == 28
    assert types.count("rectangle") == 3   # EVE "square" → OmniLab "rectangle"
    assert types.count("circle") == 0


def test_text_geometry_and_content():
    objs = _annotations("master_bgp.unl")
    # id=5 in master_bgp: single line "1.1.1.1/8" at left:176 top:332
    o = next(o for o in objs if o["original_eve_id"] == "5")
    assert o["type"] == "text"
    assert o["x"] == 176.0 and o["y"] == 332.0
    assert o["width"] is None and o["height"] is None   # width/height: auto
    assert o["text"] == "1.1.1.1/8"
    assert o["z_index"] == 999


def test_circle_colors_and_box():
    objs = _annotations("master_bgp.unl")
    circ = next(o for o in objs if o["type"] == "circle")
    # from <ellipse stroke="#000000" fill="#FFFFFF">, div 351x178 @ 319,237
    assert circ["fill"] == "#FFFFFF"
    assert circ["stroke"] == "#000000"
    assert circ["width"] == 351.0 and circ["height"] == 178.0
    assert circ["x"] == 319.0 and circ["y"] == 237.0
    assert circ["text"] == ""


def test_rectangle_colors_not_confused_with_stroke_width():
    objs = _annotations("squares.unl")
    rect = next(o for o in objs if o["type"] == "rectangle")
    # <rect ... fill="#f2e982" stroke-width="5" stroke="#000000">
    assert rect["fill"] == "#f2e982"
    assert rect["stroke"] == "#000000"          # must NOT pick up stroke-width="5"
    assert rect["width"] is not None and rect["width"] > 0


def test_multiline_strong_text_preserved():
    objs = _annotations("squares.unl")
    multis = [o for o in objs if "\n" in o["text"]]
    assert multis, "expected at least one multi-line text annotation"
    sample = next(o for o in objs if o["text"].startswith("VLAN 10"))
    assert sample["text"] == "VLAN 10 E1/1\nVLAN 20 E1/2\nVLAN 30 E1/3"


def test_all_objects_have_required_schema_fields():
    for name in ("master_bgp.unl", "squares.unl"):
        for o in _annotations(name):
            for field in ("type", "x", "y", "fill", "stroke", "text", "z_index"):
                assert field in o, f"{name}: {o.get('original_eve_id')} missing {field}"
            assert o["type"] in ("text", "circle", "rectangle")
            assert isinstance(o["x"], float) and isinstance(o["y"], float)


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
