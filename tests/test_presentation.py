"""Unit tests for PowerPoint presentation generator and slide data."""
from pathlib import Path
import pytest
from pptx import Presentation
from src.reporting.presentation_generator import (
    SLIDE_DATA,
    create_presentation_pptx,
    generate_presentation_bytes,
    save_presentation_to_file,
)


def test_presentation_slide_data_completeness():
    """Verify slide data contains all 8 required presentation slides."""
    assert len(SLIDE_DATA) == 8

    expected_categories = [
        "Title & Executive Overview",
        "Problem Statement",
        "Architecture",
        "Execution Flow",
        "Decision Matrix",
        "Tech Stack",
        "Governance",
        "Key Takeaways",
    ]

    actual_categories = [s["category"] for s in SLIDE_DATA]
    assert actual_categories == expected_categories

    for slide in SLIDE_DATA:
        assert slide["title"]
        assert slide["subtitle"]
        assert len(slide["bullet_points"]) >= 3
        assert len(slide.get("highlights", [])) >= 3


def test_create_presentation_pptx():
    """Verify PowerPoint object construction and dimensions."""
    prs = create_presentation_pptx()
    assert prs.__class__.__name__ == "Presentation"
    assert len(prs.slides) == 8
    # 16:9 widescreen: width 13.333 inches, height 7.5 inches
    assert round(prs.slide_width.inches, 2) == 13.33
    assert round(prs.slide_height.inches, 2) == 7.5


def test_generate_presentation_bytes():
    """Verify in-memory presentation byte stream generation."""
    pptx_bytes = generate_presentation_bytes()
    assert isinstance(pptx_bytes, bytes)
    assert len(pptx_bytes) > 10000
    # PPTX files are zip archives starting with 'PK'
    assert pptx_bytes[:2] == b"PK"


def test_save_presentation_to_file(tmp_path: Path):
    """Verify saving presentation to disk file."""
    output_file = tmp_path / "test_deck.pptx"
    saved_path = save_presentation_to_file(output_file)
    assert saved_path.exists()
    assert saved_path.stat().st_size > 10000
