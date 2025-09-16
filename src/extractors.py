"""Content Extractors for Multiple Formats.

This module provides specialized extractors for different file formats,
allowing the translation system to process books in EPUB, PDF and
potentially other formats.

The extractor system features:
    - Architecture based on Factory Pattern
    - Automatic format detection
    - Structured extraction of chapters/sections
    - Text cleaning and normalization
    - Metadata handling
    - Detailed logging of the process

Classes:
    ContentExtractor: Abstract base class
    EPUBExtractor: Extractor for EPUB files
    PDFExtractor: Extractor for PDF files
    ContentExtractorFactory: Factory to create extractors

Example:
    Basic extractor usage:

    >>> from extractors import ContentExtractorFactory
    >>>
    >>> # Automatic format detection
    >>> extractor = ContentExtractorFactory.create_extractor("book.epub")
    >>> chapters = extractor.extract_content("book.epub")
    >>>
    >>> for chapter in chapters:
    ...     print(f"Chapter: {chapter['title']}")
    ...     print(f"Size: {len(chapter['content'])} characters")

Note:
    Each extractor returns data in the same standardized format,
    facilitating subsequent processing independent of the source.
"""

import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import ClassVar

import ebooklib
import PyPDF2
from bs4 import BeautifulSoup
from ebooklib import epub

logger = logging.getLogger(__name__)


class ContentExtractor(ABC):
    """Abstract base class for content extractors.

    Defines the common interface that all extractors must implement.
    Ensures consistency in output format regardless of input file format.

    Methods:
        extract_content: Main extraction method (abstract)
        detect_format: Detects file format (static)
    """

    @abstractmethod
    def extract_content(self, file_path: str) -> list[dict[str, str]]:
        """Extract structured content from file.

        This method must be implemented by each specific extractor
        and return a standardized list of chapters/sections.

        Args:
            file_path: Path to the file to be processed

        Returns:
            List of dictionaries with standard structure:
            - 'title': Chapter/section title
            - 'content': Clean textual content
            - 'id': Unique identifier (optional)

        Raises:
            FileNotFoundError: If file does not exist
            Exception: For format-specific errors

        Example:
            >>> extractor = SomeExtractor()
            >>> chapters = extractor.extract_content("book.ext")
            >>> print(chapters[0]['title'])  # "Chapter 1"
        """
        pass

    @staticmethod
    def detect_format(file_path: str) -> str:
        """Detect file format based on extension.

        Args:
            file_path: Path to the file

        Returns:
            String identifying the format ('epub', 'pdf', 'unknown')

        Example:
            >>> fmt = ContentExtractor.detect_format("book.epub")
            >>> print(fmt)  # "epub"
        """
        extension = Path(file_path).suffix.lower()
        if extension == ".epub":
            return "epub"
        elif extension == ".pdf":
            return "pdf"
        else:
            raise ValueError(f"Unsupported format: {extension}")


class EPUBExtractor(ContentExtractor):
    """Specialized extractor for EPUB files.

    Implements complete content extraction from EPUB files,
    including HTML processing, metadata extraction
    and text cleaning for translation.

    Features:
    - Processing of all HTML documents in the EPUB
    - Automatic extraction of section titles
    - Text cleaning and normalization
    - Encoding and special character handling
    - Detailed logging of the extraction process

    Note:
        This extractor depends on 'ebooklib' and 'beautifulsoup4'
        libraries for complete EPUB file processing.
    """

    def extract_content(self, file_path: str) -> list[dict[str, str]]:
        """
        Extract chapters from an EPUB file.

        Args:
            file_path: Path to the EPUB file

        Returns:
            List of dictionaries with chapter information
        """
        logger.info("=== EXTRACTING EPUB CONTENT ===")
        logger.info(f"File: {file_path}")

        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            raise FileNotFoundError(f"File not found: {file_path}")

        file_size = os.path.getsize(file_path)
        logger.info(f"File size: {file_size:,} bytes")

        try:
            logger.debug("Opening EPUB file...")
            book = epub.read_epub(file_path)

            # Get metadata
            title = book.get_metadata("DC", "title")
            creator = book.get_metadata("DC", "creator")
            if title:
                logger.info(f"Book title: {title[0][0] if title else 'N/A'}")
            if creator:
                logger.info(f"Author: {creator[0][0] if creator else 'N/A'}")

            chapters = []
            total_items = len(list(book.get_items()))
            document_items = 0

            logger.info(f"Total items in EPUB: {total_items}")

            # Get all HTML documents from the EPUB
            for _i, item in enumerate(book.get_items()):
                if item.get_type() == ebooklib.ITEM_DOCUMENT:
                    document_items += 1
                    item_name = item.get_name()
                    item_id = item.get_id()

                    logger.debug(
                        f"Processing document {document_items}: {item_name} (ID: {item_id})"
                    )

                    # Extract HTML text
                    try:
                        content = item.get_content().decode("utf-8")
                        logger.debug(f"HTML extracted: {len(content):,} characters")
                    except Exception as decode_error:
                        logger.warning(
                            f"Error decoding item {item_name}: {decode_error}"
                        )
                        continue

                    # Parse HTML to extract clean text
                    soup = BeautifulSoup(content, "html.parser")

                    # Remove scripts and styles
                    scripts_removed = len(soup(["script", "style"]))
                    for script in soup(["script", "style"]):
                        script.decompose()
                    if scripts_removed > 0:
                        logger.debug(f"Removed {scripts_removed} script/style elements")

                    # Extract clean text
                    text = soup.get_text()
                    raw_text_length = len(text)

                    # Clean and normalize text
                    text = self._clean_text(text)
                    clean_text_length = len(text)

                    logger.debug(
                        f"Text processed: {raw_text_length:,} → {clean_text_length:,} characters"
                    )

                    if text.strip():  # Only add if there's content
                        # Try to extract title from first h1, h2, etc., or use file name
                        title = self._extract_title(soup) or item.get_name()

                        chapters.append(
                            {
                                "title": title,
                                "content": text,
                                "id": item.get_id(),
                                "file_name": item.get_name(),
                            }
                        )

                        logger.debug(
                            f"Chapter added: '{title}' ({clean_text_length:,} chars)"
                        )
                    else:
                        logger.debug(f"Item {item_name} ignored - no text content")

            total_chars = sum(len(ch["content"]) for ch in chapters)
            logger.info("=== EPUB EXTRACTION COMPLETED ===")
            logger.info(f"Documents processed: {document_items}")
            logger.info(f"Chapters extracted: {len(chapters)}")
            logger.info(f"Total characters: {total_chars:,}")

            if chapters:
                avg_chars = total_chars // len(chapters)
                logger.info(f"Average characters per chapter: {avg_chars:,}")

            return chapters

        except Exception as e:
            logger.error(f"Error extracting content from EPUB {file_path}: {e}")
            raise

    def _extract_title(self, soup: BeautifulSoup) -> str | None:
        """Extract title from HTML section."""
        # Procura por tags de cabeçalho
        for tag in ["h1", "h2", "h3", "title"]:
            element = soup.find(tag)
            if element and element.get_text().strip():
                return element.get_text().strip()
        return None

    def _clean_text(self, text: str) -> str:
        """Clean and normalize extracted text."""
        # Remove múltiplas linhas em branco
        lines = text.split("\n")
        cleaned_lines = []

        for line in lines:
            cleaned_line = line.strip()
            if cleaned_line:
                cleaned_lines.append(cleaned_line)

        # Junta com quebras de linha simples
        return "\n".join(cleaned_lines)


class PDFExtractor(ContentExtractor):
    """Specialized extractor for PDF files.

    Implements text extraction from PDF files page by page,
    with proper cleaning and normalization for subsequent processing.

    Features:
    - Page-by-page extraction
    - Formatting and spacing cleanup
    - Empty page filtering
    - Character encoding handling
    - Processing statistics

    Note:
        This extractor uses PyPDF2 for reading PDF files.
        Files with protection or complex formatting may have
        limited results.
    """

    def extract_content(self, file_path: str) -> list[dict[str, str]]:
        """
        Extract pages from a PDF file.

        Args:
            file_path: Path to the PDF file

        Returns:
            List of dictionaries with page information
        """
        logger.info("=== EXTRACTING PDF CONTENT ===")
        logger.info(f"File: {file_path}")

        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            raise FileNotFoundError(f"File not found: {file_path}")

        file_size = os.path.getsize(file_path)
        logger.info(f"File size: {file_size:,} bytes")

        try:
            pages = []

            with open(file_path, "rb") as file:
                logger.debug("Opening PDF file...")
                pdf_reader = PyPDF2.PdfReader(file)
                total_pages = len(pdf_reader.pages)

                logger.info(f"Total pages in PDF: {total_pages}")

                # Get metadata if available
                if pdf_reader.metadata:
                    metadata = pdf_reader.metadata
                    if "/Title" in metadata:
                        logger.info(f"PDF title: {metadata['/Title']}")
                    if "/Author" in metadata:
                        logger.info(f"Author: {metadata['/Author']}")
                    if "/Creator" in metadata:
                        logger.debug(f"Creator: {metadata['/Creator']}")

                pages_processed = 0
                pages_with_content = 0
                total_chars = 0

                for page_num, page in enumerate(pdf_reader.pages, 1):
                    try:
                        logger.debug(f"Processing page {page_num}/{total_pages}")

                        # Extract text from page
                        text = page.extract_text()
                        raw_text_length = len(text) if text else 0

                        # Clean and normalize text
                        text = self._clean_text(text)
                        clean_text_length = len(text) if text else 0

                        logger.debug(
                            f"Page {page_num}: {raw_text_length:,} → {clean_text_length:,} characters"
                        )

                        if text.strip():  # Only add if there's content
                            pages.append(
                                {
                                    "title": f"Page {page_num}",
                                    "content": text,
                                    "page_number": str(page_num),
                                }
                            )
                            pages_with_content += 1
                            total_chars += clean_text_length
                        else:
                            logger.debug(f"Page {page_num} ignored - no text content")

                        pages_processed += 1

                    except Exception as e:
                        logger.warning(f"Error extracting page {page_num}: {e}")
                        continue

            logger.info("=== PDF EXTRACTION COMPLETED ===")
            logger.info(f"Pages processed: {pages_processed}/{total_pages}")
            logger.info(f"Pages with content: {pages_with_content}")
            logger.info(f"Total characters: {total_chars:,}")

            if pages_with_content > 0:
                avg_chars = total_chars // pages_with_content
                logger.info(f"Average characters per page: {avg_chars:,}")

            return pages

        except Exception as e:
            logger.error(f"Error extracting content from PDF {file_path}: {e}")
            raise

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text extracted from PDF."""
        # Remove multiple blank lines and spaces
        lines = text.split("\n")
        cleaned_lines = []

        for line in lines:
            cleaned_line = " ".join(line.split())  # Remove multiple spaces
            if cleaned_line:
                cleaned_lines.append(cleaned_line)

        return "\n".join(cleaned_lines)


class ContentExtractorFactory:
    """Factory to create content extractors."""

    _extractors: ClassVar = {"epub": EPUBExtractor, "pdf": PDFExtractor}

    @classmethod
    def create_extractor(
        cls, file_path: str, format_override: str | None = None
    ) -> ContentExtractor:
        """
        Create an appropriate extractor for the file.

        Args:
            file_path: Path to the file
            format_override: Force a specific format (optional)

        Returns:
            Instance of the appropriate extractor
        """
        if format_override:
            format_type = format_override.lower()
        else:
            format_type = ContentExtractor.detect_format(file_path)

        if format_type not in cls._extractors:
            raise ValueError(f"Unsupported format: {format_type}")

        return cls._extractors[format_type]()
