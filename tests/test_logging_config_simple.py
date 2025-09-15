"""
Testes simples para o módulo logging_config.py
Testando apenas as classes que realmente existem.
"""
import pytest
import logging
import tempfile
import os
from io import StringIO
from unittest.mock import Mock, patch

from logging_config import ColoredFormatter, CleanTerminalHandler, setup_logging


class TestColoredFormatter:
    """Testes para a classe ColoredFormatter."""
    
    def test_colored_formatter_creation(self):
        """Testa criação do formatter colorido."""
        formatter = ColoredFormatter(fmt='%(levelname)s - %(message)s')
        assert formatter is not None
        assert hasattr(formatter, 'COLORS')
    
    def test_format_with_colors(self):
        """Testa formatação com cores."""
        formatter = ColoredFormatter(fmt='%(levelname)s - %(message)s')
        
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=1,
            msg='Test message',
            args=(),
            exc_info=None
        )
        
        formatted = formatter.format(record)
        
        # Deve conter códigos de cor ANSI
        assert '\033[32m' in formatted  # Verde para INFO
        assert '\033[0m' in formatted   # Reset
        assert 'Test message' in formatted


class TestCleanTerminalHandler:
    """Testes para a classe CleanTerminalHandler."""
    
    def test_clean_terminal_handler_creation(self):
        """Testa criação do handler limpo."""
        handler = CleanTerminalHandler(show_debug=True)
        assert handler.show_debug is True
        assert handler.last_message == ""
    
    def test_clean_terminal_handler_default(self):
        """Testa criação com configuração padrão."""
        handler = CleanTerminalHandler()
        assert handler.show_debug is False


class TestSetupLogging:
    """Testes para a função setup_logging."""
    
    def setup_method(self):
        """Setup para cada teste."""
        self.temp_dir = tempfile.mkdtemp()
        self.log_file = os.path.join(self.temp_dir, "test.log")
        
    def teardown_method(self):
        """Cleanup após cada teste."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
        # Limpa handlers do logger raiz
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
    
    def test_setup_logging_basic(self):
        """Testa configuração básica do logging."""
        setup_logging(
            log_file=self.log_file,
            level=logging.INFO,
            show_debug=False
        )
        
        # Verifica se logger raiz foi configurado
        root_logger = logging.getLogger()
        assert root_logger.level <= logging.INFO
        
        # Verifica se handlers foram adicionados
        assert len(root_logger.handlers) > 0


# Teste de integração simples
class TestIntegration:
    """Teste de integração básico."""
    
    def test_basic_logging_workflow(self):
        """Testa fluxo básico de logging."""
        temp_dir = tempfile.mkdtemp()
        log_file = os.path.join(temp_dir, "integration.log")
        
        try:
            # Configura logging
            setup_logging(log_file=log_file, level=logging.INFO)
            
            # Cria logger e testa
            logger = logging.getLogger("test.integration")
            logger.info("Test message")
            
            # Verifica se arquivo foi criado
            assert os.path.exists(log_file)
            
        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
            
            # Limpa handlers
            root_logger = logging.getLogger()
            for handler in root_logger.handlers[:]:
                root_logger.removeHandler(handler)