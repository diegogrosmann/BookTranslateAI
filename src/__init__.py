"""BookTranslateAI - Automatic Book Translation System.

This package provides a complete system for automatic translation of books
in EPUB and PDF formats using AI models through the LiteLLM library.

The system offers:
    - Support for multiple AI providers (OpenAI, Anthropic, Google, etc.)
    - Parallel processing for improved performance
    - Intelligent text chunking with overlap
    - Resume system for interrupted translations
    - Automatic generation of EPUB and PDF documents
    - Detailed logging and progress control
    - User-friendly command-line interface

Main modules:
    extractors: Content extraction from EPUB/PDF files
    chunker: Intelligent text fragmentation
    translator: Translation client using LiteLLM
    parallel: Parallel processing and coordination
    progress: Progress control and persistence
    chapter_manager: Individual chapter management
    document_generator: Final document generation
    logging_config: Configurable logging system

Example:
    Basic system usage:

    >>> from src.extractors import ContentExtractorFactory
    >>> from src.translator import TranslationClient, TranslationConfig
    >>>
    >>> # Extract book content
    >>> extractor = ContentExtractorFactory.create_extractor("book.epub")
    >>> chapters = extractor.extract_content("book.epub")
    >>>
    >>> # Configure translator
    >>> config = TranslationConfig(model="gpt-3.5-turbo", target_language="pt-BR")
    >>> translator = TranslationClient(config)
    >>>
    >>> # Translate chapter
    >>> translated = await translator.translate_text(chapters[0]['content'])

Note:
    This system requires a valid API key for AI providers.
    Consult the documentation for configuration instructions.
"""

__version__ = "1.0.0"
__author__ = "BookTranslateAI Contributors"
__description__ = "Tradutor automático de livros usando IA com LiteLLM"
__license__ = "MIT"
__url__ = "https://github.com/diegogrosmann/BookTranslateAI"

# Exposição das classes principais para facilitar importação
from src.chapter_manager import ChapterFileManager
from src.chunker import TextChunk, TextChunker
from src.document_generator import DocumentGenerator, EpubGenerator, PdfGenerator
from src.extractors import ContentExtractorFactory, EPUBExtractor, PDFExtractor
from src.parallel import ParallelProcessor
from src.progress import OutputManager, ProgressManager
from src.translator import TranslationClient, TranslationConfig

__all__ = [
    "ChapterFileManager",
    "ContentExtractorFactory",
    "DocumentGenerator",
    "EPUBExtractor",
    "EpubGenerator",
    "OutputManager",
    "PDFExtractor",
    "ParallelProcessor",
    "PdfGenerator",
    "ProgressManager",
    "TextChunk",
    "TextChunker",
    "TranslationClient",
    "TranslationConfig",
]
