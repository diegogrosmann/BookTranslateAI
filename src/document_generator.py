"""
Módulo para gerar documentos EPUB e PDF a partir do texto traduzido.
"""

import os
import logging
from pathlib import Path
from typing import Optional, List, Tuple
import re
from datetime import datetime

try:
    from ebooklib import epub
    EPUB_AVAILABLE = True
except ImportError:
    EPUB_AVAILABLE = False
    logging.warning("ebooklib não disponível. Geração de EPUB desabilitada.")

try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    logging.warning("reportlab não disponível. Geração de PDF desabilitada.")

logger = logging.getLogger(__name__)


class DocumentGenerator:
    """Classe base para geradores de documentos."""
    
    def __init__(self, output_dir: str, base_filename: str):
        self.output_dir = Path(output_dir)
        self.base_filename = base_filename
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def _sanitize_filename(self, filename: str) -> str:
        """Remove caracteres inválidos do nome do arquivo."""
        # Remove ou substitui caracteres problemáticos
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
        # Remove espaços extras e limita o tamanho
        sanitized = re.sub(r'\s+', '_', sanitized.strip())
        return sanitized[:200]  # Limita a 200 caracteres


class EpubGenerator(DocumentGenerator):
    """Gera arquivos EPUB a partir do texto traduzido."""
    
    def __init__(self, output_dir: str, base_filename: str):
        super().__init__(output_dir, base_filename)
        if not EPUB_AVAILABLE:
            raise ImportError("ebooklib não está disponível")
    
    def generate(self, content: str, title: str = "Livro Traduzido", 
                author: str = "Autor Desconhecido", language: str = "pt") -> str:
        """
        Gera um arquivo EPUB a partir do conteúdo.
        
        Args:
            content: Texto completo do livro
            title: Título do livro
            author: Autor do livro
            language: Idioma do livro
            
        Returns:
            Caminho para o arquivo EPUB gerado
        """
        logger.info(f"Gerando EPUB: {title}")
        
        # Cria o livro EPUB
        book = epub.EpubBook()
        book.set_identifier(f"traduzido_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        book.set_title(title)
        book.set_language(language)
        book.add_author(author)
        
        # Divide o conteúdo em capítulos
        chapters = self._split_into_chapters(content)
        epub_chapters = []
        
        for i, (chapter_title, chapter_content) in enumerate(chapters, 1):
            # Cria capítulo EPUB
            chapter = epub.EpubHtml(
                title=chapter_title,
                file_name=f'chapter_{i:03d}.xhtml',
                lang=language
            )
            
            # Formata o conteúdo do capítulo
            chapter_html = self._format_chapter_html(chapter_title, chapter_content)
            chapter.content = chapter_html
            
            book.add_item(chapter)
            epub_chapters.append(chapter)
        
        # Adiciona CSS básico
        style = epub.EpubItem(
            uid="style",
            file_name="style/default.css",
            media_type="text/css",
            content=self._get_epub_css()
        )
        book.add_item(style)
        
        # Cria índice
        book.toc = [(epub.Link(f"chapter_{i:03d}.xhtml", title, f"chapter_{i:03d}")) 
                    for i, (title, _) in enumerate(chapters, 1)]
        
        # Adiciona páginas de navegação
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())
        
        # Define ordem de leitura
        book.spine = ['nav'] + epub_chapters
        
        # Salva o arquivo
        output_path = self.output_dir / f"{self._sanitize_filename(self.base_filename)}.epub"
        epub.write_epub(str(output_path), book, {})
        
        logger.info(f"EPUB gerado: {output_path}")
        return str(output_path)
    
    def _split_into_chapters(self, content: str) -> List[Tuple[str, str]]:
        """Divide o conteúdo em capítulos baseado em padrões comuns."""
        chapters = []
        
        # Padrões para identificar capítulos (incluindo padrões Markdown)
        chapter_patterns = [
            r'^##\s+(.*?)$',  # Markdown H2
            r'^(Capítulo\s+\d+.*?)$',
            r'^(Chapter\s+\d+.*?)$',
            r'^(CAPÍTULO\s+\d+.*?)$',
            r'^(\d+\.\s+.*?)$',
            r'^(Parte\s+\d+.*?)$',
        ]
        
        lines = content.split('\n')
        current_chapter_title = "Introdução"
        current_chapter_content = []
        found_first_chapter = False
        
        for line in lines:
            original_line = line
            line = line.strip()
            
            # Pula linhas vazias no início
            if not line and not found_first_chapter and not current_chapter_content:
                continue
                
            # Verifica se é um novo capítulo
            is_chapter_start = False
            for pattern in chapter_patterns:
                match = re.match(pattern, line, re.IGNORECASE)
                if match:
                    # Salva capítulo anterior se houver conteúdo
                    if current_chapter_content and any(c.strip() for c in current_chapter_content):
                        chapters.append((current_chapter_title, '\n'.join(current_chapter_content).strip()))
                    
                    # Inicia novo capítulo
                    if pattern.startswith(r'^##\s+'):
                        current_chapter_title = match.group(1).strip()
                    else:
                        current_chapter_title = line
                    current_chapter_content = []
                    is_chapter_start = True
                    found_first_chapter = True
                    break
            
            if not is_chapter_start:
                # Adiciona linha ao conteúdo atual
                if found_first_chapter or line:  # Só adiciona se já encontrou um capítulo ou não é linha vazia
                    current_chapter_content.append(original_line.rstrip())
        
        # Adiciona último capítulo
        if current_chapter_content and any(c.strip() for c in current_chapter_content):
            chapters.append((current_chapter_title, '\n'.join(current_chapter_content).strip()))
        
        # Se não encontrou capítulos, divide por seções baseado em marcadores Markdown
        if not chapters:
            # Tenta dividir por linha horizontal (---)
            sections = content.split('---')
            if len(sections) > 1:
                for i, section in enumerate(sections, 1):
                    section = section.strip()
                    if section:
                        title = f"Seção {i}"
                        # Tenta extrair título da primeira linha
                        lines = section.split('\n')
                        if lines and lines[0].strip():
                            first_line = lines[0].strip()
                            if first_line.startswith('#'):
                                title = first_line.lstrip('#').strip()
                                section = '\n'.join(lines[1:]).strip()
                        chapters.append((title, section))
            else:
                # Último recurso: usa todo o conteúdo como um capítulo
                chapters.append(("Livro Completo", content.strip()))
        
        # Remove capítulos vazios
        chapters = [(title, content) for title, content in chapters if content.strip()]
        
        return chapters
    
    def _format_chapter_html(self, title: str, content: str) -> str:
        """Formata o conteúdo do capítulo em HTML."""
        # Escapa caracteres HTML
        content = content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        
        # Converte quebras de linha em parágrafos
        paragraphs = []
        for paragraph in content.split('\n\n'):
            paragraph = paragraph.strip()
            if paragraph:
                # Converte quebras de linha simples em <br>
                paragraph = paragraph.replace('\n', '<br/>')
                paragraphs.append(f'<p>{paragraph}</p>')
        
        content_html = '\n'.join(paragraphs)
        
        return f'''<?xml version='1.0' encoding='utf-8'?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
  <title>{title}</title>
  <link rel="stylesheet" type="text/css" href="../style/default.css"/>
</head>
<body>
  <h1>{title}</h1>
  {content_html}
</body>
</html>'''
    
    def _get_epub_css(self) -> str:
        """Retorna CSS básico para o EPUB."""
        return '''
body {
    font-family: Georgia, serif;
    line-height: 1.6;
    margin: 1em;
    text-align: justify;
}

h1 {
    font-size: 1.5em;
    font-weight: bold;
    margin-bottom: 1em;
    text-align: center;
    page-break-before: always;
}

p {
    margin-bottom: 1em;
    text-indent: 1.5em;
}

p:first-of-type {
    text-indent: 0;
}
'''


class PdfGenerator(DocumentGenerator):
    """Gera arquivos PDF a partir do texto traduzido."""
    
    def __init__(self, output_dir: str, base_filename: str):
        super().__init__(output_dir, base_filename)
        if not REPORTLAB_AVAILABLE:
            raise ImportError("reportlab não está disponível")
    
    def generate(self, content: str, title: str = "Livro Traduzido", 
                author: str = "Autor Desconhecido") -> str:
        """
        Gera um arquivo PDF a partir do conteúdo.
        
        Args:
            content: Texto completo do livro
            title: Título do livro
            author: Autor do livro
            
        Returns:
            Caminho para o arquivo PDF gerado
        """
        logger.info(f"Gerando PDF: {title}")
        
        output_path = self.output_dir / f"{self._sanitize_filename(self.base_filename)}.pdf"
        
        # Cria documento PDF
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )
        
        # Configura estilos
        styles = self._get_pdf_styles()
        story = []
        
        # Página de título
        story.append(Spacer(1, 2*inch))
        story.append(Paragraph(title, styles['BookTitle']))
        story.append(Spacer(1, 0.5*inch))
        story.append(Paragraph(f"por {author}", styles['Author']))
        story.append(Spacer(1, 1*inch))
        story.append(Paragraph(f"Traduzido em {datetime.now().strftime('%d/%m/%Y')}", styles['Date']))
        story.append(PageBreak())
        
        # Divide conteúdo em capítulos
        chapters = self._split_into_chapters(content)
        
        for chapter_title, chapter_content in chapters:
            # Título do capítulo
            story.append(Paragraph(chapter_title, styles['ChapterTitle']))
            story.append(Spacer(1, 0.3*inch))
            
            # Conteúdo do capítulo
            paragraphs = chapter_content.split('\n\n')
            for paragraph in paragraphs:
                paragraph = paragraph.strip()
                if paragraph:
                    # Remove quebras de linha extras
                    paragraph = ' '.join(paragraph.split())
                    story.append(Paragraph(paragraph, styles['Normal']))
                    story.append(Spacer(1, 12))
            
            story.append(PageBreak())
        
        # Gera o PDF
        doc.build(story)
        
        logger.info(f"PDF gerado: {output_path}")
        return str(output_path)
    
    def _split_into_chapters(self, content: str) -> List[Tuple[str, str]]:
        """Reutiliza a mesma lógica do EpubGenerator."""
        epub_gen = EpubGenerator("", "")
        return epub_gen._split_into_chapters(content)
    
    def _get_pdf_styles(self):
        """Configura estilos para o PDF."""
        styles = getSampleStyleSheet()
        
        # Estilo para título principal (sobrescreve o existente)
        styles.add(ParagraphStyle(
            name='BookTitle',
            parent=styles['Normal'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        # Estilo para autor
        styles.add(ParagraphStyle(
            name='Author',
            parent=styles['Normal'],
            fontSize=16,
            alignment=TA_CENTER,
            fontName='Helvetica'
        ))
        
        # Estilo para data
        styles.add(ParagraphStyle(
            name='Date',
            parent=styles['Normal'],
            fontSize=12,
            alignment=TA_CENTER,
            fontName='Helvetica',
            textColor='gray'
        ))
        
        # Estilo para títulos de capítulos
        styles.add(ParagraphStyle(
            name='ChapterTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=12,
            spaceBefore=24,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        # Modifica estilo normal para justificado
        styles['Normal'].alignment = TA_JUSTIFY
        styles['Normal'].fontSize = 11
        styles['Normal'].leading = 14
        
        return styles


def generate_documents(content_file: str, output_dir: str, base_filename: str,
                      title: str = "Livro Traduzido", author: str = "Autor Desconhecido") -> List[str]:
    """
    Gera tanto EPUB quanto PDF a partir de um arquivo de conteúdo.
    
    Args:
        content_file: Caminho para o arquivo com o conteúdo traduzido
        output_dir: Diretório onde salvar os documentos
        base_filename: Nome base para os arquivos
        title: Título do livro
        author: Autor do livro
        
    Returns:
        Lista com caminhos dos arquivos gerados
    """
    generated_files = []
    
    # Lê o conteúdo
    try:
        with open(content_file, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        logger.error(f"Erro ao ler arquivo de conteúdo {content_file}: {e}")
        return generated_files
    
    # Gera EPUB
    if EPUB_AVAILABLE:
        try:
            epub_gen = EpubGenerator(output_dir, base_filename)
            epub_path = epub_gen.generate(content, title, author)
            generated_files.append(epub_path)
        except Exception as e:
            logger.error(f"Erro ao gerar EPUB: {e}")
    
    # Gera PDF
    if REPORTLAB_AVAILABLE:
        try:
            pdf_gen = PdfGenerator(output_dir, base_filename)
            pdf_path = pdf_gen.generate(content, title, author)
            generated_files.append(pdf_path)
        except Exception as e:
            logger.error(f"Erro ao gerar PDF: {e}")
    
    return generated_files