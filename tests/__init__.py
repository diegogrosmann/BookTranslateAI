# __init__.py file for the tests directory
# This file allows Python to recognize the tests directory as a package

"""
Test suite for BookTranslateAI project.

This package contains comprehensive tests for all system modules:

- test_chunker.py: Tests for text fragmentation
- test_extractors.py: Tests for content extraction from files
- test_translator.py: Tests for translation using LLMs
- test_parallel.py: Tests for parallel processing
- test_progress.py: Tests for progress system and persistence
- test_logging_config.py: Tests for logging configuration

To run all tests:
    pytest tests/

To run specific tests:
    pytest tests/test_chunker.py

To run with coverage:
    pytest tests/ --cov=src --cov-report=html
"""

__version__ = "1.0.0"
__author__ = "BookTranslateAI Project"
