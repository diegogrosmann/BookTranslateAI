"""
Testes simples para o módulo progress.py
Testando apenas as classes que realmente existem.
"""
import pytest
import tempfile
import os
from unittest.mock import Mock, patch

from progress import ChapterProgress, TranslationProgress, ProgressManager


class TestChapterProgress:
    """Testes para a classe ChapterProgress."""
    
    def test_chapter_progress_creation(self):
        """Testa criação de progresso de capítulo."""
        progress = ChapterProgress(
            chapter_id="cap1",
            title="Capítulo 1",
            total_chunks=10
        )
        
        assert progress.chapter_id == "cap1"
        assert progress.title == "Capítulo 1"
        assert progress.total_chunks == 10
        assert progress.completed_chunks == 0


class TestTranslationProgress:
    """Testes para a classe TranslationProgress."""
    
    def test_translation_progress_creation(self):
        """Testa criação de progresso de tradução."""
        progress = TranslationProgress(
            input_file="livro.epub",
            output_file="livro_pt.epub",
            model="gpt-4",
            target_language="pt-BR",
            total_chapters=5
        )
        
        assert progress.input_file == "livro.epub"
        assert progress.output_file == "livro_pt.epub"
        assert progress.model == "gpt-4"
        assert progress.target_language == "pt-BR"
        assert progress.total_chapters == 5


class TestProgressManager:
    """Testes básicos para a classe ProgressManager."""
    
    def test_manager_initialization(self):
        """Testa inicialização do manager."""
        temp_dir = tempfile.mkdtemp()
        progress_file = os.path.join(temp_dir, "progress.json")
        
        try:
            manager = ProgressManager(progress_file)
            assert manager.progress_file == progress_file
            
        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)