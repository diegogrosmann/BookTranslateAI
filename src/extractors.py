"""Extratores de Conteúdo para Múltiplos Formatos.

Este módulo fornece extratores especializados para diferentes formatos
de arquivo, permitindo que o sistema de tradução processe livros em
EPUB, PDF e potencialmente outros formatos.

O sistema de extratores:
    - Arquitetura baseada em Factory Pattern
    - Detecção automática de formato
    - Extração estruturada de capítulos/seções
    - Limpeza e normalização de texto
    - Tratamento de metadados
    - Logging detalhado do processo

Classes:
    ContentExtractor: Classe base abstrata
    EPUBExtractor: Extrator para arquivos EPUB
    PDFExtractor: Extrator para arquivos PDF  
    ContentExtractorFactory: Factory para criar extratores

Example:
    Uso básico dos extratores:
    
    >>> from extractors import ContentExtractorFactory
    >>> 
    >>> # Detecção automática do formato
    >>> extractor = ContentExtractorFactory.create_extractor("book.epub")
    >>> chapters = extractor.extract_content("book.epub")
    >>> 
    >>> for chapter in chapters:
    ...     print(f"Capítulo: {chapter['title']}")
    ...     print(f"Tamanho: {len(chapter['content'])} caracteres")

Note:
    Cada extrator retorna dados no mesmo formato padronizado,
    facilitando processamento posterior independente da fonte.
"""
import os
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Tuple
from pathlib import Path

import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import PyPDF2


logger = logging.getLogger(__name__)


class ContentExtractor(ABC):
    """Classe base abstrata para extratores de conteúdo.
    
    Define a interface comum que todos os extratores devem implementar.
    Garante consistência no formato de saída independente do formato
    de arquivo de entrada.
    
    Methods:
        extract_content: Método principal para extração (abstrato)
        detect_format: Detecta formato de arquivo (estático)
    """
    
    @abstractmethod
    def extract_content(self, file_path: str) -> List[Dict[str, str]]:
        """Extrai conteúdo estruturado do arquivo.
        
        Este método deve ser implementado por cada extrator específico
        e retornar uma lista padronizada de capítulos/seções.
        
        Args:
            file_path: Caminho para o arquivo a ser processado
            
        Returns:
            Lista de dicionários com estrutura padrão:
            - 'title': Título do capítulo/seção
            - 'content': Conteúdo textual limpo
            - 'id': Identificador único (opcional)
            
        Raises:
            FileNotFoundError: Se arquivo não existe
            Exception: Para erros específicos de formato
            
        Example:
            >>> extractor = SomeExtractor()
            >>> chapters = extractor.extract_content("book.ext")
            >>> print(chapters[0]['title'])  # "Capítulo 1"
        """
        pass
    
    @staticmethod
    def detect_format(file_path: str) -> str:
        """Detecta formato de arquivo baseado na extensão.
        
        Args:
            file_path: Caminho para o arquivo
            
        Returns:
            String identificando o formato ('epub', 'pdf', 'unknown')
            
        Example:
            >>> fmt = ContentExtractor.detect_format("book.epub")
            >>> print(fmt)  # "epub"
        """
        extension = Path(file_path).suffix.lower()
        if extension == '.epub':
            return 'epub'
        elif extension == '.pdf':
            return 'pdf'
        else:
            raise ValueError(f"Formato não suportado: {extension}")


class EPUBExtractor(ContentExtractor):
    """Extrator especializado para arquivos EPUB.
    
    Implementa extração completa de conteúdo de arquivos EPUB,
    incluindo processamento de HTML, extração de metadados
    e limpeza de texto para tradução.
    
    Recursos:
    - Processamento de todos os documentos HTML do EPUB
    - Extração automática de títulos de seções
    - Limpeza e normalização de texto
    - Tratamento de encoding e caracteres especiais
    - Logging detalhado do processo de extração
    
    Note:
        Este extrator depende das bibliotecas 'ebooklib' e 'beautifulsoup4'
        para processamento completo de arquivos EPUB.
    """
    
    def extract_content(self, file_path: str) -> List[Dict[str, str]]:
        """
        Extrai capítulos de um arquivo EPUB.
        
        Args:
            file_path: Caminho para o arquivo EPUB
            
        Returns:
            Lista de dicionários com informações dos capítulos
        """
        logger.info(f"=== EXTRAINDO CONTEÚDO EPUB ===")
        logger.info(f"Arquivo: {file_path}")
        
        if not os.path.exists(file_path):
            logger.error(f"Arquivo não encontrado: {file_path}")
            raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")
        
        file_size = os.path.getsize(file_path)
        logger.info(f"Tamanho do arquivo: {file_size:,} bytes")
        
        try:
            logger.debug("Abrindo arquivo EPUB...")
            book = epub.read_epub(file_path)
            
            # Obtém metadados
            title = book.get_metadata('DC', 'title')
            creator = book.get_metadata('DC', 'creator')
            if title:
                logger.info(f"Título do livro: {title[0][0] if title else 'N/A'}")
            if creator:
                logger.info(f"Autor: {creator[0][0] if creator else 'N/A'}")
            
            chapters = []
            total_items = len(list(book.get_items()))
            document_items = 0
            
            logger.info(f"Total de itens no EPUB: {total_items}")
            
            # Pega todos os documentos HTML do EPUB
            for i, item in enumerate(book.get_items()):
                if item.get_type() == ebooklib.ITEM_DOCUMENT:
                    document_items += 1
                    item_name = item.get_name()
                    item_id = item.get_id()
                    
                    logger.debug(f"Processando documento {document_items}: {item_name} (ID: {item_id})")
                    
                    # Extrai o texto HTML
                    try:
                        content = item.get_content().decode('utf-8')
                        logger.debug(f"HTML extraído: {len(content):,} caracteres")
                    except Exception as decode_error:
                        logger.warning(f"Erro ao decodificar item {item_name}: {decode_error}")
                        continue
                    
                    # Parse HTML para extrair texto limpo
                    soup = BeautifulSoup(content, 'html.parser')
                    
                    # Remove scripts e estilos
                    scripts_removed = len(soup(["script", "style"]))
                    for script in soup(["script", "style"]):
                        script.decompose()
                    if scripts_removed > 0:
                        logger.debug(f"Removidos {scripts_removed} elementos script/style")
                    
                    # Extrai texto limpo
                    text = soup.get_text()
                    raw_text_length = len(text)
                    
                    # Limpa e normaliza o texto
                    text = self._clean_text(text)
                    clean_text_length = len(text)
                    
                    logger.debug(f"Texto processado: {raw_text_length:,} → {clean_text_length:,} caracteres")
                    
                    if text.strip():  # Só adiciona se tiver conteúdo
                        # Tenta extrair título do primeiro h1, h2, etc., ou usa o nome do arquivo
                        title = self._extract_title(soup) or item.get_name()
                        
                        chapters.append({
                            'title': title,
                            'content': text,
                            'id': item.get_id(),
                            'file_name': item.get_name()
                        })
                        
                        logger.debug(f"Capítulo adicionado: '{title}' ({clean_text_length:,} chars)")
                    else:
                        logger.debug(f"Item {item_name} ignorado - sem conteúdo texto")
            
            total_chars = sum(len(ch['content']) for ch in chapters)
            logger.info(f"=== EXTRAÇÃO EPUB CONCLUÍDA ===")
            logger.info(f"Documentos processados: {document_items}")
            logger.info(f"Capítulos extraídos: {len(chapters)}")
            logger.info(f"Total de caracteres: {total_chars:,}")
            
            if chapters:
                avg_chars = total_chars // len(chapters)
                logger.info(f"Média de caracteres por capítulo: {avg_chars:,}")
            
            return chapters
            
        except Exception as e:
            logger.error(f"Erro ao extrair conteúdo do EPUB {file_path}: {e}")
            raise
    
    def _extract_title(self, soup: BeautifulSoup) -> Optional[str]:
        """Extrai título da seção HTML."""
        # Procura por tags de cabeçalho
        for tag in ['h1', 'h2', 'h3', 'title']:
            element = soup.find(tag)
            if element and element.get_text().strip():
                return element.get_text().strip()
        return None
    
    def _clean_text(self, text: str) -> str:
        """Limpa e normaliza o texto extraído."""
        # Remove múltiplas linhas em branco
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            cleaned_line = line.strip()
            if cleaned_line:
                cleaned_lines.append(cleaned_line)
        
        # Junta com quebras de linha simples
        return '\n'.join(cleaned_lines)


class PDFExtractor(ContentExtractor):
    """Extrator especializado para arquivos PDF.
    
    Implementa extração de texto de arquivos PDF página por página,
    com limpeza e normalização adequada para processamento posterior.
    
    Recursos:
    - Extração página por página
    - Limpeza de formatação e espaçamento
    - Filtragem de páginas vazias
    - Tratamento de encoding de caracteres
    - Estatísticas de processamento
    
    Note:
        Este extrator usa PyPDF2 para leitura de arquivos PDF.
        Arquivos com proteção ou formatação complexa podem ter
        resultados limitados.
    """
    
    def extract_content(self, file_path: str) -> List[Dict[str, str]]:
        """
        Extrai páginas de um arquivo PDF.
        
        Args:
            file_path: Caminho para o arquivo PDF
            
        Returns:
            Lista de dicionários com informações das páginas
        """
        logger.info(f"=== EXTRAINDO CONTEÚDO PDF ===")
        logger.info(f"Arquivo: {file_path}")
        
        if not os.path.exists(file_path):
            logger.error(f"Arquivo não encontrado: {file_path}")
            raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")
        
        file_size = os.path.getsize(file_path)
        logger.info(f"Tamanho do arquivo: {file_size:,} bytes")
        
        try:
            pages = []
            
            with open(file_path, 'rb') as file:
                logger.debug("Abrindo arquivo PDF...")
                pdf_reader = PyPDF2.PdfReader(file)
                total_pages = len(pdf_reader.pages)
                
                logger.info(f"Total de páginas no PDF: {total_pages}")
                
                # Obtém metadados se disponível
                if pdf_reader.metadata:
                    metadata = pdf_reader.metadata
                    if '/Title' in metadata:
                        logger.info(f"Título do PDF: {metadata['/Title']}")
                    if '/Author' in metadata:
                        logger.info(f"Autor: {metadata['/Author']}")
                    if '/Creator' in metadata:
                        logger.debug(f"Criador: {metadata['/Creator']}")
                
                pages_processed = 0
                pages_with_content = 0
                total_chars = 0
                
                for page_num, page in enumerate(pdf_reader.pages, 1):
                    try:
                        logger.debug(f"Processando página {page_num}/{total_pages}")
                        
                        # Extrai texto da página
                        text = page.extract_text()
                        raw_text_length = len(text) if text else 0
                        
                        # Limpa e normaliza o texto
                        text = self._clean_text(text)
                        clean_text_length = len(text) if text else 0
                        
                        logger.debug(f"Página {page_num}: {raw_text_length:,} → {clean_text_length:,} caracteres")
                        
                        if text.strip():  # Só adiciona se tiver conteúdo
                            pages.append({
                                'title': f'Página {page_num}',
                                'content': text,
                                'page_number': page_num
                            })
                            pages_with_content += 1
                            total_chars += clean_text_length
                        else:
                            logger.debug(f"Página {page_num} ignorada - sem conteúdo texto")
                        
                        pages_processed += 1
                    
                    except Exception as e:
                        logger.warning(f"Erro ao extrair página {page_num}: {e}")
                        continue
            
            logger.info(f"=== EXTRAÇÃO PDF CONCLUÍDA ===")
            logger.info(f"Páginas processadas: {pages_processed}/{total_pages}")
            logger.info(f"Páginas com conteúdo: {pages_with_content}")
            logger.info(f"Total de caracteres: {total_chars:,}")
            
            if pages_with_content > 0:
                avg_chars = total_chars // pages_with_content
                logger.info(f"Média de caracteres por página: {avg_chars:,}")
            
            return pages
            
        except Exception as e:
            logger.error(f"Erro ao extrair conteúdo do PDF {file_path}: {e}")
            raise
    
    def _clean_text(self, text: str) -> str:
        """Limpa e normaliza o texto extraído do PDF."""
        # Remove múltiplas linhas em branco e espaços
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            cleaned_line = ' '.join(line.split())  # Remove espaços múltiplos
            if cleaned_line:
                cleaned_lines.append(cleaned_line)
        
        return '\n'.join(cleaned_lines)


class ContentExtractorFactory:
    """Factory para criar extratores de conteúdo."""
    
    _extractors = {
        'epub': EPUBExtractor,
        'pdf': PDFExtractor
    }
    
    @classmethod
    def create_extractor(cls, file_path: str, format_override: Optional[str] = None) -> ContentExtractor:
        """
        Cria um extrator apropriado para o arquivo.
        
        Args:
            file_path: Caminho para o arquivo
            format_override: Força um formato específico (opcional)
            
        Returns:
            Instância do extrator apropriado
        """
        if format_override:
            format_type = format_override.lower()
        else:
            format_type = ContentExtractor.detect_format(file_path)
        
        if format_type not in cls._extractors:
            raise ValueError(f"Formato não suportado: {format_type}")
        
        return cls._extractors[format_type]()