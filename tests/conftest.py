# Test configuration for BookTranslateAI project
# This file configures pytest and provides common fixtures

import os
import shutil
import sys
import tempfile
from unittest.mock import Mock

import pytest

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def sample_text():
    """Sample text for tests."""
    return """
    Chapter 1: The Beginning of the Journey

    Once upon a time, in a distant land, there was a young hero named Rand al'Thor.
    He lived in a small village called Emond's Field, where the days passed
    peacefully until extraordinary events changed his life forever.

    The wind was not a beginning. There are no beginnings or endings in the wheel of time.
    But that was a beginning.

    Mat Cauthon and Perrin Aybara were his best friends since childhood.
    Together, they would face unimaginable dangers and discover powers
    that would change the fate of the world.
    """.strip()


@pytest.fixture
def sample_chapters():
    """List of sample chapters for tests."""
    return [
        {
            "id": "cap1",
            "title": "Chapter 1: The Beginning",
            "content": "Once upon a time there was a young hero. He had a great destiny.",
        },
        {
            "id": "cap2",
            "title": "Chapter 2: The Journey",
            "content": "The journey began with one step. Then another. And another.",
        },
        {
            "id": "cap3",
            "title": "Chapter 3: The Destiny",
            "content": "Destiny awaited. The hero was ready to face it.",
        },
    ]


@pytest.fixture
def mock_epub_book():
    """Mock of an EPUB book for tests."""
    import ebooklib

    mock_book = Mock()

    # Mock EPUB items
    mock_item1 = Mock()
    mock_item1.get_type.return_value = ebooklib.ITEM_DOCUMENT  # Correct value: 9
    mock_item1.get_content.return_value = b"""
    <!DOCTYPE html>
    <html>
    <head><title>Chapter 1</title></head>
    <body>
        <h1>Chapter 1: The Beginning</h1>
        <p>This is the first chapter of our story.</p>
        <p>It was a dark and stormy night...</p>
    </body>
    </html>
    """
    mock_item1.get_name.return_value = "chapter1.xhtml"
    mock_item1.get_id.return_value = "ch1"

    mock_item2 = Mock()
    mock_item2.get_type.return_value = ebooklib.ITEM_DOCUMENT  # Correct value: 9
    mock_item2.get_content.return_value = b"""
    <!DOCTYPE html>
    <html>
    <body>
        <h2>Chapter 2: The Journey</h2>
        <p>The journey begins here.</p>
    </body>
    </html>
    """
    mock_item2.get_name.return_value = "chapter2.xhtml"
    mock_item2.get_id.return_value = "ch2"

    mock_book.get_items.return_value = [mock_item1, mock_item2]

    # Mock metadata
    mock_book.get_metadata.return_value = [("Sample Book Title", {})]

    return mock_book


@pytest.fixture
def mock_translation_response():
    """Mock of translation response from API."""
    return {
        "choices": [
            {"message": {"content": "This is the text translated to Portuguese."}}
        ],
        "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
    }


# Global pytest configuration
def pytest_configure(config):
    """Global pytest configuration."""
    # Suppress specific warnings if needed
    import warnings

    warnings.filterwarnings("ignore", category=DeprecationWarning)
