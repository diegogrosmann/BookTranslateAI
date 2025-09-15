"""
Testes para o módulo extractors.py
"""
import pytest
import os
import sys
import tempfile
from unittest.mock import Mock, patch, mock_open
from pathlib import Path
import ebooklib

# Adiciona o diretório src ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from extractors import (
    ContentExtractor, EPUBExtractor, PDFExtractor, 
    ContentExtractorFactory
)


class TestContentExtractor:
    """Testes para a classe base ContentExtractor."""
    
    def test_detect_format_epub(self):
        """Testa detecção de formato EPUB."""
        assert ContentExtractor.detect_format("test.epub") == "epub"
        assert ContentExtractor.detect_format("book.EPUB") == "epub"
        assert ContentExtractor.detect_format("/path/to/file.epub") == "epub"
    
    def test_detect_format_pdf(self):
        """Testa detecção de formato PDF."""
        assert ContentExtractor.detect_format("test.pdf") == "pdf"
        assert ContentExtractor.detect_format("document.PDF") == "pdf"
        assert ContentExtractor.detect_format("/path/to/file.pdf") == "pdf"
    
    def test_detect_format_unsupported(self):
        """Testa detecção de formato não suportado."""
        with pytest.raises(ValueError, match="Formato não suportado"):
            ContentExtractor.detect_format("test.txt")
        
        with pytest.raises(ValueError, match="Formato não suportado"):
            ContentExtractor.detect_format("document.docx")


class TestEPUBExtractor:
    """Testes para a classe EPUBExtractor."""
    
    def setup_method(self):
        """Configuração para cada teste."""
        self.extractor = EPUBExtractor()
    
    def test_file_not_found(self):
        """Testa erro quando arquivo não existe."""
        with pytest.raises(FileNotFoundError):
            self.extractor.extract_content("arquivo_inexistente.epub")
    
    @patch('extractors.epub.read_epub')
    def test_extract_content_success(self, mock_read_epub, mock_epub_book):
        """Testa extração bem-sucedida de conteúdo EPUB."""
        mock_read_epub.return_value = mock_epub_book
        
        with patch('os.path.exists', return_value=True):
            chapters = self.extractor.extract_content("test.epub")
        
        assert len(chapters) == 2
        
        # Verifica primeiro capítulo
        assert chapters[0]['title'] == 'Chapter 1: The Beginning'
        assert 'This is the first chapter' in chapters[0]['content']
        assert chapters[0]['id'] == 'ch1'
        assert chapters[0]['file_name'] == 'chapter1.xhtml'
        
        # Verifica segundo capítulo  
        assert chapters[1]['title'] == 'Chapter 2: The Journey'
        assert 'The journey begins here' in chapters[1]['content']
        assert chapters[1]['id'] == 'ch2'
        assert chapters[1]['file_name'] == 'chapter2.xhtml'
    
    @patch('extractors.epub.read_epub')
    def test_extract_content_empty_items(self, mock_read_epub):
        """Testa extração com itens vazios."""
        mock_book = Mock()
        mock_item = Mock()
        mock_item.get_type.return_value = ebooklib.ITEM_DOCUMENT
        mock_item.get_content.return_value = b'<html><body></body></html>'  # Vazio
        mock_item.get_name.return_value = 'empty.xhtml'
        mock_item.get_id.return_value = 'empty'
        
        mock_book.get_items.return_value = [mock_item]
        mock_read_epub.return_value = mock_book
        
        with patch('os.path.exists', return_value=True):
            chapters = self.extractor.extract_content("test.epub")
        
        # Não deve incluir capítulos vazios
        assert len(chapters) == 0
    
    @patch('extractors.epub.read_epub')
    def test_extract_content_error(self, mock_read_epub):
        """Testa tratamento de erro na extração."""
        mock_read_epub.side_effect = Exception("Erro na leitura do EPUB")
        
        with patch('os.path.exists', return_value=True):
            with pytest.raises(Exception, match="Erro na leitura do EPUB"):
                self.extractor.extract_content("test.epub")
    
    def test_extract_title_success(self):
        """Testa extração de título com sucesso."""
        from bs4 import BeautifulSoup
        
        html = '<html><body><h1>Capítulo 1</h1><p>Conteúdo</p></body></html>'
        soup = BeautifulSoup(html, 'html.parser')
        
        title = self.extractor._extract_title(soup)
        assert title == "Capítulo 1"
    
    def test_extract_title_multiple_headers(self):
        """Testa extração de título com múltiplos cabeçalhos."""
        from bs4 import BeautifulSoup
        
        html = '<html><body><h2>Primeiro</h2><h1>Principal</h1></body></html>'
        soup = BeautifulSoup(html, 'html.parser')
        
        # Deve pegar o primeiro encontrado (h1 tem prioridade na busca)
        title = self.extractor._extract_title(soup)
        assert title == "Principal"
    
    def test_extract_title_no_header(self):
        """Testa extração de título quando não há cabeçalho."""
        from bs4 import BeautifulSoup
        
        html = '<html><body><p>Só parágrafo</p></body></html>'
        soup = BeautifulSoup(html, 'html.parser')
        
        title = self.extractor._extract_title(soup)
        assert title is None
    
    def test_clean_text(self):
        """Testa limpeza de texto."""
        messy_text = """
        
        
        Primeira linha
        
        
        Segunda linha
        
        Terceira linha
        
        
        """
        
        cleaned = self.extractor._clean_text(messy_text)
        expected = "Primeira linha\nSegunda linha\nTerceira linha"
        
        assert cleaned == expected
    
    def test_clean_text_empty(self):
        """Testa limpeza de texto vazio."""
        assert self.extractor._clean_text("") == ""
        assert self.extractor._clean_text("   \n  \n  ") == ""


class TestPDFExtractor:
    """Testes para a classe PDFExtractor."""
    
    def setup_method(self):
        """Configuração para cada teste."""
        self.extractor = PDFExtractor()
    
    def test_file_not_found(self):
        """Testa erro quando arquivo não existe."""
        with pytest.raises(FileNotFoundError):
            self.extractor.extract_content("arquivo_inexistente.pdf")
    
    @patch('extractors.PyPDF2.PdfReader')
    @patch('builtins.open', new_callable=mock_open)
    def test_extract_content_success(self, mock_file, mock_pdf_reader):
        """Testa extração bem-sucedida de conteúdo PDF."""
        # Mock das páginas
        mock_page1 = Mock()
        mock_page1.extract_text.return_value = "Conteúdo da página 1"
        
        mock_page2 = Mock()
        mock_page2.extract_text.return_value = "Conteúdo da página 2"
        
        mock_reader = Mock()
        mock_reader.pages = [mock_page1, mock_page2]
        mock_pdf_reader.return_value = mock_reader
        
        with patch('os.path.exists', return_value=True):
            pages = self.extractor.extract_content("test.pdf")
        
        assert len(pages) == 2
        
        assert pages[0]['title'] == 'Página 1'
        assert pages[0]['content'] == 'Conteúdo da página 1'
        assert pages[0]['page_number'] == 1
        
        assert pages[1]['title'] == 'Página 2'
        assert pages[1]['content'] == 'Conteúdo da página 2'
        assert pages[1]['page_number'] == 2
    
    @patch('extractors.PyPDF2.PdfReader')
    @patch('builtins.open', new_callable=mock_open)
    def test_extract_content_empty_pages(self, mock_file, mock_pdf_reader):
        """Testa extração com páginas vazias."""
        mock_page1 = Mock()
        mock_page1.extract_text.return_value = "Conteúdo válido"
        
        mock_page2 = Mock()
        mock_page2.extract_text.return_value = ""  # Página vazia
        
        mock_reader = Mock()
        mock_reader.pages = [mock_page1, mock_page2]
        mock_pdf_reader.return_value = mock_reader
        
        with patch('os.path.exists', return_value=True):
            pages = self.extractor.extract_content("test.pdf")
        
        # Deve incluir apenas páginas com conteúdo
        assert len(pages) == 1
        assert pages[0]['content'] == 'Conteúdo válido'
    
    @patch('extractors.PyPDF2.PdfReader')
    @patch('builtins.open', new_callable=mock_open)
    def test_extract_content_page_error(self, mock_file, mock_pdf_reader):
        """Testa tratamento de erro em página específica."""
        mock_page1 = Mock()
        mock_page1.extract_text.return_value = "Conteúdo da página 1"
        
        mock_page2 = Mock()
        mock_page2.extract_text.side_effect = Exception("Erro na página 2")
        
        mock_page3 = Mock()
        mock_page3.extract_text.return_value = "Conteúdo da página 3"
        
        mock_reader = Mock()
        mock_reader.pages = [mock_page1, mock_page2, mock_page3]
        mock_pdf_reader.return_value = mock_reader
        
        with patch('os.path.exists', return_value=True):
            with patch('extractors.logger') as mock_logger:
                pages = self.extractor.extract_content("test.pdf")
        
        # Deve continuar mesmo com erro em uma página
        assert len(pages) == 2
        assert pages[0]['page_number'] == 1
        assert pages[1]['page_number'] == 3
        
        # Deve logar o warning
        mock_logger.warning.assert_called_once()
    
    @patch('extractors.PyPDF2.PdfReader')
    @patch('builtins.open', new_callable=mock_open) 
    def test_extract_content_general_error(self, mock_file, mock_pdf_reader):
        """Testa tratamento de erro geral."""
        mock_pdf_reader.side_effect = Exception("Erro geral do PDF")
        
        with patch('os.path.exists', return_value=True):
            with pytest.raises(Exception, match="Erro geral do PDF"):
                self.extractor.extract_content("test.pdf")
    
    def test_clean_text_pdf(self):
        """Testa limpeza específica de texto PDF."""
        messy_text = """Primeira    linha   com    espaços
        
        Segunda linha
        Terceira  linha   """
        
        cleaned = self.extractor._clean_text(messy_text)
        expected = "Primeira linha com espaços\nSegunda linha\nTerceira linha"
        
        assert cleaned == expected


class TestContentExtractorFactory:
    """Testes para a factory de extratores."""
    
    def test_create_epub_extractor(self):
        """Testa criação de extrator EPUB."""
        extractor = ContentExtractorFactory.create_extractor("test.epub")
        assert isinstance(extractor, EPUBExtractor)
    
    def test_create_pdf_extractor(self):
        """Testa criação de extrator PDF."""
        extractor = ContentExtractorFactory.create_extractor("test.pdf")
        assert isinstance(extractor, PDFExtractor)
    
    def test_create_extractor_with_override(self):
        """Testa criação com override de formato."""
        # Força EPUB mesmo com extensão diferente
        extractor = ContentExtractorFactory.create_extractor("test.txt", "epub")
        assert isinstance(extractor, EPUBExtractor)
        
        # Força PDF mesmo com extensão diferente
        extractor = ContentExtractorFactory.create_extractor("test.doc", "pdf")
        assert isinstance(extractor, PDFExtractor)
    
    def test_create_extractor_unsupported_format(self):
        """Testa criação com formato não suportado."""
        with pytest.raises(ValueError, match="Formato não suportado"):
            ContentExtractorFactory.create_extractor("test.txt")
        
        with pytest.raises(ValueError, match="Formato não suportado"):
            ContentExtractorFactory.create_extractor("test.epub", "docx")


class TestIntegration:
    """Testes de integração para extratores."""
    
    @patch('extractors.epub.read_epub')
    def test_epub_to_chapters_workflow(self, mock_read_epub, mock_epub_book):
        """Testa fluxo completo EPUB -> capítulos."""
        mock_read_epub.return_value = mock_epub_book
        
        # Cria extrator via factory
        extractor = ContentExtractorFactory.create_extractor("book.epub")
        
        with patch('os.path.exists', return_value=True):
            chapters = extractor.extract_content("book.epub")
        
        # Verifica estrutura dos capítulos
        assert len(chapters) > 0
        
        for chapter in chapters:
            # Cada capítulo deve ter campos obrigatórios
            assert 'title' in chapter
            assert 'content' in chapter
            assert 'id' in chapter
            assert 'file_name' in chapter
            
            # Conteúdo deve estar limpo
            assert chapter['content'].strip()
            assert '\n\n\n' not in chapter['content']  # Não deve ter múltiplas quebras
    
    def test_error_handling_chain(self):
        """Testa cadeia de tratamento de erros."""
        extractor = EPUBExtractor()
        
        # Arquivo não existe
        with pytest.raises(FileNotFoundError):
            extractor.extract_content("inexistente.epub")
        
        # Formato não suportado na factory
        with pytest.raises(ValueError):
            ContentExtractorFactory.create_extractor("arquivo.xyz")
    
    @patch('extractors.logger')
    def test_logging_integration(self, mock_logger):
        """Testa integração com sistema de logging."""
        with patch('extractors.epub.read_epub') as mock_read:
            mock_book = Mock()
            mock_book.get_items.return_value = []  # Sem itens
            mock_read.return_value = mock_book
            
            extractor = EPUBExtractor()
            
            with patch('os.path.exists', return_value=True):
                chapters = extractor.extract_content("test.epub")
            
            # Deve logar informação sobre extração
            mock_logger.info.assert_called_with(
                "Extraídos 0 capítulos do EPUB: test.epub"
            )