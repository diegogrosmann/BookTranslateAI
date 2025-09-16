# BookTranslateAI

> Automatic Book Translation System using AI Models

BookTranslateAI is a comprehensive system for automatic translation of books in EPUB and PDF formats using AI models through the LiteLLM library. It provides intelligent text processing, parallel processing capabilities, and seamless integration with multiple AI providers.

## ✨ Features

- **Multi-format Support**: Process EPUB and PDF files seamlessly
- **Multiple AI Providers**: Support for OpenAI, Anthropic, Google, Cohere, and more through LiteLLM
- **Intelligent Text Chunking**: Smart text fragmentation with overlap to maintain context
- **Parallel Processing**: Multi-threaded translation for improved performance
- **Resume Capability**: Continue interrupted translations from where they left off
- **Progress Tracking**: Detailed progress monitoring and persistence
- **Document Generation**: Automatic generation of translated EPUB and PDF documents
- **Comprehensive Logging**: Detailed logging system with configurable levels
- **Chapter Management**: Individual chapter processing and management

## 🚀 Installation

### Prerequisites

- Python 3.8 or higher
- Valid API key for your chosen AI provider (OpenAI, Anthropic, etc.)

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Required Python Packages

The system requires the following main dependencies:

- `litellm` - Unified interface for multiple AI providers
- `ebooklib` - EPUB file processing
- `PyPDF2` - PDF file processing
- `beautifulsoup4` - HTML parsing for EPUB content
- `reportlab` - PDF generation
- `tenacity` - Retry mechanisms

## 🎯 Quick Start

### Basic Usage

```python
from src.extractors import ContentExtractorFactory
from src.translator import TranslationClient, TranslationConfig
from src.chunker import TextChunker
from src.progress import ProgressManager, OutputManager

# 1. Extract content from book
extractor = ContentExtractorFactory.create_extractor("book.epub")
chapters = extractor.extract_content("book.epub")

# 2. Configure translator
config = TranslationConfig(
    model="gpt-3.5-turbo",
    target_language="pt-BR",
    context="Fiction novel"
)
translator = TranslationClient(config, api_key="your-api-key")

# 3. Test connection
success, message = await translator.test_connection()
if not success:
    print(f"Connection failed: {message}")
    exit(1)

# 4. Set up text chunking
chunker = TextChunker(
    chunk_size=4000,
    overlap_size=200,
    preserve_sentences=True
)

# 5. Translate a chapter
if chapters:
    chunks = chunker.chunk_text(chapters[0]['content'], chapters[0]['id'])
    for chunk in chunks:
        translated = await translator.translate_text(chunk.content)
        print(f"Translated chunk: {translated[:100]}...")
```

### Command Line Usage

For full book translation, use the main application:

```bash
# Set your API key
export OPENAI_API_KEY="your-api-key-here"

# Run translation
python main.py
```

## 🏗️ Architecture

### Core Components

- **Extractors** (`src/extractors.py`): Content extraction from EPUB/PDF files
- **Chunker** (`src/chunker.py`): Intelligent text fragmentation
- **Translator** (`src/translator.py`): AI-powered translation client
- **Parallel Processor** (`src/parallel.py`): Multi-threaded processing coordination
- **Progress Manager** (`src/progress.py`): Progress tracking and persistence
- **Chapter Manager** (`src/chapter_manager.py`): Individual chapter management
- **Document Generator** (`src/document_generator.py`): Output document generation
- **Logging Config** (`src/logging_config.py`): Configurable logging system

### Supported AI Models

BookTranslateAI supports a wide range of AI models through LiteLLM:

- **OpenAI**: GPT-3.5-turbo, GPT-4, GPT-4-turbo
- **Anthropic**: Claude-3-sonnet, Claude-3-opus, Claude-3-haiku
- **Google**: Gemini-pro, Gemini-pro-vision
- **Cohere**: Command models
- **And many more...**

## ⚙️ Configuration

### Translation Configuration

```python
from src.translator import TranslationConfig

config = TranslationConfig(
    model="gpt-4",
    target_language="pt-BR",
    context="Historical fiction novel set in the 19th century",
    custom_instructions="Maintain formal tone and eloquent style"
)
```

### Chunking Configuration

```python
from src.chunker import TextChunker

chunker = TextChunker(
    chunk_size=4000,      # Maximum characters per chunk
    overlap_size=300,     # Overlap between chunks for context
    preserve_sentences=True,    # Avoid breaking sentences
    preserve_paragraphs=True    # Prefer paragraph breaks
)
```

### Parallel Processing

```python
from src.parallel import ParallelProcessor

processor = ParallelProcessor(
    translator_config=config,
    chunker=chunker,
    progress_manager=progress_manager,
    output_manager=output_manager,
    max_workers=4,        # Number of parallel workers
    rate_limit=2.0        # Requests per second
)
```

## 📁 Project Structure

```
├── src/
│   ├── __init__.py           # Package initialization
│   ├── extractors.py         # Content extraction
│   ├── chunker.py           # Text fragmentation  
│   ├── translator.py        # Translation client
│   ├── parallel.py          # Parallel processing
│   ├── progress.py          # Progress management
│   ├── chapter_manager.py   # Chapter management
│   ├── document_generator.py # Document generation
│   └── logging_config.py    # Logging configuration
├── tests/                   # Unit tests
├── input/                   # Input files directory
├── logs/                    # Log files
├── main.py                  # Main application
├── requirements.txt         # Dependencies
└── README.md               # This file
```

## 🧪 Testing

Run the test suite:

```bash
pytest tests/
```

Run specific test categories:

```bash
# Test extractors
pytest tests/test_extractors.py

# Test chunker
pytest tests/test_chunker.py

# Test translator
pytest tests/test_translator.py
```

## 📖 Documentation

### API Reference

The system provides comprehensive docstrings following Google/NumPy style. Key classes:

- `ContentExtractorFactory`: Factory for creating file extractors
- `TranslationClient`: Main translation interface
- `TextChunker`: Intelligent text fragmentation
- `ParallelProcessor`: Parallel processing coordinator
- `ProgressManager`: Progress tracking and persistence

### Logging

The system uses a sophisticated logging configuration:

```python
from src.logging_config import setup_logging

setup_logging(
    log_level="INFO",
    log_file="logs/translation.log",
    clean_terminal=True
)
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

### Development Setup

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Run tests: `pytest`
4. Follow PEP 8 style guidelines

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🔗 Links

- **Repository**: [https://github.com/diegogrosmann/BookTranslateAI](https://github.com/diegogrosmann/BookTranslateAI)
- **Issues**: [https://github.com/diegogrosmann/BookTranslateAI/issues](https://github.com/diegogrosmann/BookTranslateAI/issues)
- **LiteLLM Documentation**: [https://docs.litellm.ai/](https://docs.litellm.ai/)

## 🙏 Acknowledgments

- [LiteLLM](https://github.com/BerriAI/litellm) for the unified AI interface
- [ebooklib](https://github.com/aerkalov/ebooklib) for EPUB processing
- All the AI providers for making this possible

---

**Note**: This system requires valid API keys for AI providers. Ensure you have proper access and understand the pricing models of your chosen provider before processing large books.
