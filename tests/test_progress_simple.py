"""
Simple tests for the progress.py module
Testing only classes that actually exist.
"""

import os
import tempfile

from src.progress import ChapterProgress, ProgressManager, TranslationProgress


class TestChapterProgress:
    """Tests for the ChapterProgress class."""

    def test_chapter_progress_creation(self):
        """Test creation of chapter progress."""
        progress = ChapterProgress(
            chapter_id="cap1", title="Chapter 1", total_chunks=10
        )

        assert progress.chapter_id == "cap1"
        assert progress.title == "Chapter 1"
        assert progress.total_chunks == 10
        assert progress.completed_chunks == 0


class TestTranslationProgress:
    """Tests for the TranslationProgress class."""

    def test_translation_progress_creation(self):
        """Test creation of translation progress."""
        progress = TranslationProgress(
            input_file="book.epub",
            output_file="book_pt.epub",
            model="gpt-4",
            target_language="pt-BR",
            total_chapters=5,
        )

        assert progress.input_file == "book.epub"
        assert progress.output_file == "book_pt.epub"
        assert progress.model == "gpt-4"
        assert progress.target_language == "pt-BR"
        assert progress.total_chapters == 5


class TestProgressManager:
    """Basic tests for the ProgressManager class."""

    def test_manager_initialization(self):
        """Test manager initialization."""
        temp_dir = tempfile.mkdtemp()
        progress_file = os.path.join(temp_dir, "progress.json")

        try:
            manager = ProgressManager(progress_file)
            assert manager.progress_file == progress_file

        finally:
            import shutil

            shutil.rmtree(temp_dir, ignore_errors=True)
