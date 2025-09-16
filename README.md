# BookTranslateAI

> Automated Book Translation System using AI

BookTranslateAI is a complete system for automatic translation of books in EPUB a## ⚙️ Advanced Options

### Chunk Control
```bash
--chunk-size 4000        # Maximum chunk size (characters)
--overlap-size 200       # Overlap between chunks (characters)
```

### Performance
```bash
--max-workers 4          # Number of parallel workers
--rate-limit 2.0         # Requests per second (0 = no limit)
```

## ✨ Features

- **Multiple Formats**: Processes EPUB and PDF files
- **Multiple AI Providers**: OpenAI, Anthropic, Google, Cohere, and others via LiteLLM
- **Smart Chunking**: Text division with overlap to maintain context
- **Parallel Processing**: Multi-threaded translation for better performance
- **Progress Resumption**: Continue interrupted translations from where they left off
- **Progress Tracking**: Detailed and persistent monitoring
- **Comprehensive Logging**: Configurable logging system
- **Interactive Interface**: User-friendly script for non-technical users

## 🚀 Installation

### Prerequisites

- Python 3.8 or higher
- Valid API key for your AI provider (OpenAI, Anthropic, etc.)

### Install Dependencies

```bash
pip install -r requirements.txt
```

## 📖 How to Use

### 1. Basic Translation

```bash
# Simple EPUB to Markdown translation
python main.py --input book.epub --output-md translation.md --api-key your_api_key

# PDF translation
python main.py --input document.pdf --output-md translation.md --api-key your_api_key
```

### 2. Interactive Script (Recommended for Beginners)

```bash
# Run the interactive script that guides you through the process
./executar.sh
```

The interactive script will:
- Request the input file
- Ask for your API key
- Allow you to choose the AI model
- Configure advanced options
- Execute the translation with visual interface

### 3. Advanced Usage Examples

```bash
# Translation with specific model (GPT-4)
python main.py --input book.epub --output-md translation.md \
    --model openai/gpt-4 --api-key your_key

# Using Claude (Anthropic)
python main.py --input book.epub --output-md translation.md \
    --model anthropic/claude-3.5-sonnet --api-key your_key

# With custom context
python main.py --input book.epub --output-md translation.md \
    --context "Epic fantasy romance" --api-key your_key

# Loading context from file
python main.py --input book.epub --output-md translation.md \
    --context-file input/instructions.txt --api-key your_key

# Translation to another language
python main.py --input book.epub --output-md translation.md \
    --target-lang pt-BR --api-key your_key

# Performance configuration
python main.py --input book.epub --output-md translation.md \
    --max-workers 8 --chunk-size 5000 --rate-limit 3.0 --api-key your_key
```

### 4. Useful Commands

```bash
# List available models
python main.py --list-models

# Test API connection
python main.py --test-connection --model openai/gpt-4 --api-key your_key

# See complete help
python main.py --help
```

## ⚙️ Environment Variables Configuration

To avoid passing the API key every time, configure an environment variable:

```bash
# On Linux/Mac
export API_KEY="your_api_key_here"
export OPENAI_API_KEY="your_openai_key"  # For OpenAI specifically

# On Windows
set API_KEY=your_api_key_here
```

Then run without `--api-key`:

```bash
python main.py --input book.epub --output-md translation.md
```

## 🤖 Supported AI Models

The system supports various models through LiteLLM:

### OpenAI
```bash
--model openai/gpt-4-turbo        # Recommended for quality
--model openai/gpt-4              # Good quality, slower
--model openai/gpt-3.5-turbo      # Faster, less accurate
```

### Anthropic
```bash
--model anthropic/claude-3.5-sonnet    # Excellent for literature
--model anthropic/claude-3-opus        # Maximum quality
--model anthropic/claude-3-haiku       # Faster
```

### Google
```bash
--model gemini/gemini-pro         # Good free option
--model gemini/gemini-pro-vision  # With image support
```

### Others
```bash
--model cohere/command-r-plus     # Cohere
--model mistral/mistral-large     # Mistral AI
```

## � Opções Avançadas

### Controle de Chunks
```bash
--chunk-size 4000        # Tamanho máximo do chunk (caracteres)
--overlap-size 200       # Sobreposição entre chunks (caracteres)
```

### Performance
```bash
--max-workers 4          # Número de workers paralelos
--rate-limit 2.0         # Requisições por segundo (0 = sem limite)
```

### Logging
```bash
--log-level INFO         # DEBUG, INFO, WARNING, ERROR
--log-file translation.log  # Custom log file
--clean-terminal         # Clean terminal vs. verbose
```

### Progress Resumption
```bash
--resume                 # Resume translation (default)
--no-resume             # Force new translation
```

## 📋 Complete Workflow Example

```bash
# 1. Test connection first
python main.py --test-connection --model openai/gpt-4 --api-key your_key

# 2. Execute the translation
python main.py \
    --input input/book.epub \
    --output-md output/translation.md \
    --model openai/gpt-4-turbo \
    --target-lang en-US \
    --context-file input/instructions.txt \
    --max-workers 6 \
    --chunk-size 5000 \
    --log-level INFO \
    --api-key your_key

# Alternative: High-performance translation with virtual environment
./venv/bin/python main.py \
    --input input/large_book.epub \
    --output-md output/large_book.md \
    --model gemini/gemini-2.5-pro \
    --api-key your_gemini_key \
    --max-workers 200 \
    --target-lang pt-BR \
    --chunk-size 300000 \
    --context-file input/instructions.txt \
    --rate-limit 2 \
    --log-level WARNING \
    --clean-terminal \
    --overlap-size 0

# 3. If interrupted, resume with the same command
# The system automatically detects and continues from where it left off
```

## 📂 File Structure

```
├── input/                    # Place your books here
│   ├── instructions.txt     # Example context file
│   ├── book.epub           # Your EPUB books
│   └── document.pdf        # Your PDF files
├── logs/                    # Translation logs
├── main.py                 # Main program
├── executar.sh            # Interactive script
└── src/                   # Source code
```

## 🔍 Troubleshooting

### API Key Error
```bash
# Make sure the key is configured
export API_KEY="your_key_here"
python main.py --test-connection --model your_model
```

### Rate Limit Error
```bash
# Reduce speed
python main.py --rate-limit 1.0 --max-workers 2 [other options]
```

### Chunk Size Error
```bash
# For models with smaller token limits
python main.py --chunk-size 2000 --overlap-size 100 [other options]
```

### Insufficient Memory
```bash
# Reduce workers and chunks
python main.py --max-workers 2 --chunk-size 3000 [other options]
```

## 💡 Usage Tips

### For Long Books
- Use `--max-workers 2` to avoid rate limits
- Configure `--rate-limit 1.0` for APIs with restricted limits
- Monitor logs in `logs/` to track progress

### Custom Context
Create an instructions file like `input/instructions.txt`:
```
You are a translator specialized in epic fantasy.
Keep proper names original.
Use formal and eloquent language.
Preserve metaphors and figures of speech.
```

### Best Practices
- **Test first**: Always use `--test-connection` before long translations
- **Backup**: Keep copies of original files
- **Progress**: Use `--log-level DEBUG` for detailed debugging
- **Costs**: Monitor API usage to control expenses

## 🧪 Testing the System

```bash
# Basic connection test
python main.py --test-connection --model openai/gpt-3.5-turbo --api-key your_key

# Test with small file
python main.py --input small_file.epub --output-md test.md --api-key your_key

# Run unit tests (for developers)
pytest tests/
```

## ❓ FAQ

**Q: Can I translate password-protected PDFs?**
A: No, the system does not support password-protected PDFs.

**Q: How much does it cost to translate a book?**
A: It depends on the model and size. A 300-page book with GPT-4 costs approximately $10-20.

**Q: Can I stop and continue later?**
A: Yes! Use `--resume` (default) and the system continues from where it left off.

**Q: Which model is best for literature?**
A: Claude-3.5-Sonnet or GPT-4-turbo are excellent for literary texts.

**Q: How to speed up translation?**
A: Increase `--max-workers` and `--rate-limit`, but be careful with API limits.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🔗 Useful Links

- **Repository**: [https://github.com/diegogrosmann/BookTranslateAI](https://github.com/diegogrosmann/BookTranslateAI)
- **Issues**: [https://github.com/diegogrosmann/BookTranslateAI/issues](https://github.com/diegogrosmann/BookTranslateAI/issues)
- **LiteLLM**: [https://docs.litellm.ai/](https://docs.litellm.ai/)

---

**⚠️ Warning**: This system requires valid API keys from AI providers. Make sure you understand pricing models before processing large books. Use responsibly respecting copyrights.
