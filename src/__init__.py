"""BookTranslateAI - Tradutor Automático de Livros.

Este pacote fornece um sistema completo para tradução automática de livros 
em formato EPUB e PDF usando modelos de IA através da biblioteca LiteLLM.

O sistema oferece:
    - Suporte a múltiplos provedores de IA (OpenAI, Anthropic, Google, etc.)
    - Processamento paralelo para melhor performance
    - Fragmentação inteligente de texto com overlap
    - Sistema de retomada para traduções interrompidas
    - Geração automática de documentos EPUB e PDF
    - Logging detalhado e controle de progresso
    - Interface de linha de comando amigável

Módulos principais:
    extractors: Extração de conteúdo de arquivos EPUB/PDF
    chunker: Fragmentação inteligente de texto
    translator: Cliente de tradução usando LiteLLM
    parallel: Processamento paralelo e coordenação
    progress: Controle de progresso e persistência
    chapter_manager: Gerenciamento de capítulos individuais
    document_generator: Geração de documentos finais
    logging_config: Sistema de logging configurável

Example:
    Uso básico do sistema:
    
    >>> from src.extractors import ContentExtractorFactory
    >>> from src.translator import TranslationClient, TranslationConfig
    >>> 
    >>> # Extrai conteúdo do livro
    >>> extractor = ContentExtractorFactory.create_extractor("book.epub")
    >>> chapters = extractor.extract_content("book.epub")
    >>> 
    >>> # Configura tradutor
    >>> config = TranslationConfig(model="gpt-3.5-turbo", target_language="pt-BR")
    >>> translator = TranslationClient(config)
    >>> 
    >>> # Traduz capítulo
    >>> translated = await translator.translate_text(chapters[0]['content'])

Note:
    Este sistema requer uma chave de API válida para os provedores de IA.
    Consulte a documentação para instruções de configuração.
"""

__version__ = "1.0.0"
__author__ = "BookTranslateAI Contributors"
__description__ = "Tradutor automático de livros usando IA com LiteLLM"
__license__ = "MIT"
__url__ = "https://github.com/diegogrosmann/BookTranslateAI"

# Exposição das classes principais para facilitar importação
from .extractors import ContentExtractorFactory, EPUBExtractor, PDFExtractor
from .translator import TranslationClient, TranslationConfig
from .chunker import TextChunker, TextChunk
from .progress import ProgressManager, OutputManager
from .parallel import ParallelProcessor
from .chapter_manager import ChapterFileManager
from .document_generator import DocumentGenerator, EpubGenerator, PdfGenerator

__all__ = [
    'ContentExtractorFactory',
    'EPUBExtractor', 
    'PDFExtractor',
    'TranslationClient',
    'TranslationConfig',
    'TextChunker',
    'TextChunk',
    'ProgressManager',
    'OutputManager',
    'ParallelProcessor',
    'ChapterFileManager',
    'DocumentGenerator',
    'EpubGenerator',
    'PdfGenerator'
]