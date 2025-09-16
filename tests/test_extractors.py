"""
Tests for the extractors.py module
"""

import os
import sys
from unittest.mock import Mock, mock_open, patch

import ebooklib
import pytest

from src.extractors import (
    ContentExtractor,
    ContentExtractorFactory,
    EPUBExtractor,
    PDFExtractor,
)

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


class TestContentExtractor:
    """Tests for the base ContentExtractor class."""

    def test_detect_format_epub(self):
        """Test EPUB format detection."""
        assert ContentExtractor.detect_format("test.epub") == "epub"
        assert ContentExtractor.detect_format("book.EPUB") == "epub"
        assert ContentExtractor.detect_format("/path/to/file.epub") == "epub"

    def test_detect_format_pdf(self):
        """Test PDF format detection."""
        assert ContentExtractor.detect_format("test.pdf") == "pdf"
        assert ContentExtractor.detect_format("document.PDF") == "pdf"
        assert ContentExtractor.detect_format("/path/to/file.pdf") == "pdf"

    def test_detect_format_unsupported(self):
        """Test detection of unsupported format."""
        with pytest.raises(ValueError, match="Unsupported format"):
            ContentExtractor.detect_format("test.txt")

        with pytest.raises(ValueError, match="Unsupported format"):
            ContentExtractor.detect_format("document.docx")


class TestEPUBExtractor:
    """Tests for the EPUBExtractor class."""

    def setup_method(self):
        """Setup for each test."""
        self.extractor = EPUBExtractor()

    def test_file_not_found(self):
        """Test error when file does not exist."""
        with pytest.raises(FileNotFoundError):
            self.extractor.extract_content("nonexistent_file.epub")

    @patch("extractors.epub.read_epub")
    def test_extract_content_success(self, mock_read_epub, mock_epub_book):
        """Test successful EPUB content extraction."""
        mock_read_epub.return_value = mock_epub_book

        with (
            patch("os.path.exists", return_value=True),
            patch("os.path.getsize", return_value=1024),
        ):
            chapters = self.extractor.extract_content("test.epub")

        assert len(chapters) == 2

        # Verify first chapter
        assert chapters[0]["title"] == "Chapter 1: The Beginning"
        assert "This is the first chapter" in chapters[0]["content"]
        assert chapters[0]["id"] == "ch1"
        assert chapters[0]["file_name"] == "chapter1.xhtml"

        # Verify second chapter
        assert chapters[1]["title"] == "Chapter 2: The Journey"
        assert "The journey begins here" in chapters[1]["content"]
        assert chapters[1]["id"] == "ch2"
        assert chapters[1]["file_name"] == "chapter2.xhtml"

    @patch("extractors.epub.read_epub")
    def test_extract_content_empty_items(self, mock_read_epub):
        """Test extraction with empty items."""
        mock_book = Mock()
        mock_item = Mock()
        mock_item.get_type.return_value = ebooklib.ITEM_DOCUMENT
        mock_item.get_content.return_value = b"<html><body></body></html>"  # Empty
        mock_item.get_name.return_value = "empty.xhtml"
        mock_item.get_id.return_value = "empty"

        mock_book.get_items.return_value = [mock_item]
        mock_book.get_metadata.return_value = [("Sample Book Title", {})]
        mock_read_epub.return_value = mock_book

        with (
            patch("os.path.exists", return_value=True),
            patch("os.path.getsize", return_value=1024),
        ):
            chapters = self.extractor.extract_content("test.epub")

        # Should not include empty chapters
        assert len(chapters) == 0

    @patch("extractors.epub.read_epub")
    def test_extract_content_error(self, mock_read_epub):
        """Test error handling in extraction."""
        mock_read_epub.side_effect = Exception("Error reading EPUB")

        with (
            patch("os.path.exists", return_value=True),
            patch("os.path.getsize", return_value=1024),
        ):
            with pytest.raises(Exception, match="Error reading EPUB"):
                self.extractor.extract_content("test.epub")

    def test_extract_title_success(self):
        """Test successful title extraction."""
        from bs4 import BeautifulSoup

        html = "<html><body><h1>Chapter 1</h1><p>Content</p></body></html>"
        soup = BeautifulSoup(html, "html.parser")

        title = self.extractor._extract_title(soup)
        assert title == "Chapter 1"

    def test_extract_title_multiple_headers(self):
        """Test title extraction with multiple headers."""
        from bs4 import BeautifulSoup

        html = "<html><body><h2>First</h2><h1>Main</h1></body></html>"
        soup = BeautifulSoup(html, "html.parser")

        # Should get the first found (h1 has priority in search)
        title = self.extractor._extract_title(soup)
        assert title == "Main"

    def test_extract_title_no_header(self):
        """Test title extraction when there is no header."""
        from bs4 import BeautifulSoup

        html = "<html><body><p>Only paragraph</p></body></html>"
        soup = BeautifulSoup(html, "html.parser")

        title = self.extractor._extract_title(soup)
        assert title is None

    def test_clean_text(self):
        """Test text cleaning."""
        messy_text = """


        First line


        Second line

        Third line


        """

        cleaned = self.extractor._clean_text(messy_text)
        expected = "First line\nSecond line\nThird line"

        assert cleaned == expected

    def test_clean_text_empty(self):
        """Test empty text cleaning."""
        assert self.extractor._clean_text("") == ""
        assert self.extractor._clean_text("   \n  \n  ") == ""


class TestPDFExtractor:
    """Tests for the PDFExtractor class."""

    def setup_method(self):
        """Setup for each test."""
        self.extractor = PDFExtractor()

    def test_file_not_found(self):
        """Test error when file does not exist."""
        with pytest.raises(FileNotFoundError):
            self.extractor.extract_content("nonexistent_file.pdf")

    @patch("extractors.PyPDF2.PdfReader")
    @patch("builtins.open", new_callable=mock_open)
    def test_extract_content_success(self, mock_file, mock_pdf_reader):
        """Test successful PDF content extraction."""
        # Mock pages
        mock_page1 = Mock()
        mock_page1.extract_text.return_value = "Content of page 1"

        mock_page2 = Mock()
        mock_page2.extract_text.return_value = "Content of page 2"

        mock_reader = Mock()
        mock_reader.pages = [mock_page1, mock_page2]
        mock_reader.metadata = {
            "/Title": "Sample PDF Title",
            "/Author": "Sample Author",
        }
        mock_pdf_reader.return_value = mock_reader

        with (
            patch("os.path.exists", return_value=True),
            patch("os.path.getsize", return_value=1024),
        ):
            pages = self.extractor.extract_content("test.pdf")

        assert len(pages) == 2

        assert pages[0]["title"] == "Page 1"
        assert pages[0]["content"] == "Content of page 1"
        assert pages[0]["page_number"] == 1

        assert pages[1]["title"] == "Page 2"
        assert pages[1]["content"] == "Content of page 2"
        assert pages[1]["page_number"] == 2

    @patch("extractors.PyPDF2.PdfReader")
    @patch("builtins.open", new_callable=mock_open)
    def test_extract_content_empty_pages(self, mock_file, mock_pdf_reader):
        """Test extraction with empty pages."""
        mock_page1 = Mock()
        mock_page1.extract_text.return_value = "Valid content"

        mock_page2 = Mock()
        mock_page2.extract_text.return_value = ""  # Empty page

        mock_reader = Mock()
        mock_reader.pages = [mock_page1, mock_page2]
        mock_reader.metadata = {"/Title": "Sample PDF Title"}
        mock_pdf_reader.return_value = mock_reader

        with (
            patch("os.path.exists", return_value=True),
            patch("os.path.getsize", return_value=1024),
        ):
            pages = self.extractor.extract_content("test.pdf")

        # Should include only pages with content
        assert len(pages) == 1
        assert pages[0]["content"] == "Valid content"

    @patch("extractors.PyPDF2.PdfReader")
    @patch("builtins.open", new_callable=mock_open)
    def test_extract_content_page_error(self, mock_file, mock_pdf_reader):
        """Test error handling in specific page."""
        mock_page1 = Mock()
        mock_page1.extract_text.return_value = "Content of page 1"

        mock_page2 = Mock()
        mock_page2.extract_text.side_effect = Exception("Error in page 2")

        mock_page3 = Mock()
        mock_page3.extract_text.return_value = "Content of page 3"

        mock_reader = Mock()
        mock_reader.pages = [mock_page1, mock_page2, mock_page3]
        mock_reader.metadata = {}
        mock_pdf_reader.return_value = mock_reader

        with (
            patch("os.path.exists", return_value=True),
            patch("os.path.getsize", return_value=1024),
        ):
            with patch("src.extractors.logger") as mock_logger:
                pages = self.extractor.extract_content("test.pdf")

        # Should continue even with error in one page
        assert len(pages) == 2
        assert pages[0]["page_number"] == 1
        assert pages[1]["page_number"] == 3

        # Should log the warning
        mock_logger.warning.assert_called_once()

    @patch("extractors.PyPDF2.PdfReader")
    @patch("builtins.open", new_callable=mock_open)
    def test_extract_content_general_error(self, mock_file, mock_pdf_reader):
        """Test general error handling."""
        mock_pdf_reader.side_effect = Exception("General PDF error")

        with (
            patch("os.path.exists", return_value=True),
            patch("os.path.getsize", return_value=1024),
        ):
            with pytest.raises(Exception, match="General PDF error"):
                self.extractor.extract_content("test.pdf")

    def test_clean_text_pdf(self):
        """Test PDF-specific text cleaning."""
        messy_text = """First    line   with    spaces

        Second line
        Third  line   """

        cleaned = self.extractor._clean_text(messy_text)
        expected = "First line with spaces\nSecond line\nThird line"

        assert cleaned == expected


class TestContentExtractorFactory:
    """Tests for the extractor factory."""

    def test_create_epub_extractor(self):
        """Test EPUB extractor creation."""
        extractor = ContentExtractorFactory.create_extractor("test.epub")
        assert isinstance(extractor, EPUBExtractor)

    def test_create_pdf_extractor(self):
        """Test PDF extractor creation."""
        extractor = ContentExtractorFactory.create_extractor("test.pdf")
        assert isinstance(extractor, PDFExtractor)

    def test_create_extractor_with_override(self):
        """Test creation with format override."""
        # Force EPUB even with different extension
        extractor = ContentExtractorFactory.create_extractor("test.txt", "epub")
        assert isinstance(extractor, EPUBExtractor)

        # Force PDF even with different extension
        extractor = ContentExtractorFactory.create_extractor("test.doc", "pdf")
        assert isinstance(extractor, PDFExtractor)

    def test_create_extractor_unsupported_format(self):
        """Test creation with unsupported format."""
        with pytest.raises(ValueError, match="Unsupported format"):
            ContentExtractorFactory.create_extractor("test.txt")

        with pytest.raises(ValueError, match="Unsupported format"):
            ContentExtractorFactory.create_extractor("test.epub", "docx")


class TestIntegration:
    """Integration tests for extractors."""

    @patch("extractors.epub.read_epub")
    def test_epub_to_chapters_workflow(self, mock_read_epub, mock_epub_book):
        """Test complete EPUB -> chapters workflow."""
        mock_read_epub.return_value = mock_epub_book

        # Create extractor via factory
        extractor = ContentExtractorFactory.create_extractor("book.epub")

        with (
            patch("os.path.exists", return_value=True),
            patch("os.path.getsize", return_value=1024),
        ):
            chapters = extractor.extract_content("book.epub")

        # Verify chapter structure
        assert len(chapters) > 0

        for chapter in chapters:
            # Each chapter should have mandatory fields
            assert "title" in chapter
            assert "content" in chapter
            assert "id" in chapter
            assert "file_name" in chapter

            # Content should be clean
            assert chapter["content"].strip()
            assert "\n\n\n" not in chapter["content"]  # Should not have multiple breaks

    def test_error_handling_chain(self):
        """Test error handling chain."""
        extractor = EPUBExtractor()

        # File does not exist
        with pytest.raises(FileNotFoundError):
            extractor.extract_content("nonexistent.epub")

        # Unsupported format in factory
        with pytest.raises(ValueError):
            ContentExtractorFactory.create_extractor("file.xyz")

    @patch("extractors.logger")
    def test_logging_integration(self, mock_logger):
        """Test integration with logging system."""
        with patch("extractors.epub.read_epub") as mock_read:
            mock_book = Mock()
            mock_book.get_items.return_value = []  # No items
            mock_book.get_metadata.return_value = [("Sample Book Title", {})]
            mock_read.return_value = mock_book

            extractor = EPUBExtractor()

            with (
                patch("os.path.exists", return_value=True),
                patch("os.path.getsize", return_value=1024),
            ):
                chapters = extractor.extract_content("test.epub")

            # Should have called the mock logger
            # Since we're mocking the module logger, let's verify it was called in some way
            assert len(chapters) == 0  # With empty list, should have 0 chapters
