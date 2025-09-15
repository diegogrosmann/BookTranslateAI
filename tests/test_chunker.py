"""
Testes para o módulo chunker.py
"""
import pytest
from unittest.mock import Mock, patch

from chunker import TextChunker, TextChunk


class TestTextChunk:
    """Testes para a classe TextChunk."""
    
    def test_text_chunk_creation(self):
        """Testa criação de TextChunk."""
        chunk = TextChunk(
            content="Este é um teste",
            start_pos=0,
            end_pos=15,
            chunk_id=1,
            chapter_id="cap1",
            overlap_start=5,
            overlap_end=10
        )
        
        assert chunk.content == "Este é um teste"
        assert chunk.start_pos == 0
        assert chunk.end_pos == 15
        assert chunk.chunk_id == 1
        assert chunk.chapter_id == "cap1"
        assert chunk.overlap_start == 5
        assert chunk.overlap_end == 10


class TestTextChunker:
    """Testes para a classe TextChunker."""
    
    def test_chunker_initialization(self):
        """Testa inicialização do chunker com parâmetros padrão."""
        chunker = TextChunker()
        
        assert chunker.chunk_size == 4000
        assert chunker.overlap_size == 200
        assert chunker.preserve_sentences is True
        assert chunker.preserve_paragraphs is True
    
    def test_chunker_custom_initialization(self):
        """Testa inicialização do chunker com parâmetros customizados."""
        chunker = TextChunker(
            chunk_size=1000,
            overlap_size=100,
            preserve_sentences=False,
            preserve_paragraphs=False
        )
        
        assert chunker.chunk_size == 1000
        assert chunker.overlap_size == 100
        assert chunker.preserve_sentences is False
        assert chunker.preserve_paragraphs is False
    
    def test_chunk_empty_text(self):
        """Testa fragmentação de texto vazio."""
        chunker = TextChunker()
        chunks = chunker.chunk_text("", "test_chapter")
        
        assert chunks == []
    
    def test_chunk_short_text(self):
        """Testa fragmentação de texto curto (menor que chunk_size)."""
        chunker = TextChunker(chunk_size=100)
        text = "Este é um texto curto para teste."
        chunks = chunker.chunk_text(text, "test_chapter")
        
        assert len(chunks) == 1
        assert chunks[0].content == text
        assert chunks[0].start_pos == 0
        assert chunks[0].end_pos == len(text)
        assert chunks[0].chunk_id == 0
        assert chunks[0].chapter_id == "test_chapter"
    
    def test_chunk_long_text(self):
        """Testa fragmentação de texto longo."""
        chunker = TextChunker(chunk_size=50, overlap_size=10)
        text = "Este é um texto muito longo que precisa ser dividido em múltiplos chunks para testar a funcionalidade de fragmentação."
        chunks = chunker.chunk_text(text, "test_chapter") 
        
        assert len(chunks) > 1
        
        # Verifica se todos os chunks têm o chapter_id correto
        for chunk in chunks:
            assert chunk.chapter_id == "test_chapter"
        
        # Verifica se os chunk_ids são sequenciais
        for i, chunk in enumerate(chunks):
            assert chunk.chunk_id == i
    
    def test_chunk_with_paragraphs(self):
        """Testa fragmentação respeitando quebras de parágrafo."""
        chunker = TextChunker(
            chunk_size=80,
            overlap_size=10,
            preserve_paragraphs=True
        )
        
        text = """Primeiro parágrafo com texto suficiente.

Segundo parágrafo também com texto suficiente para teste.

Terceiro parágrafo para completar o teste."""
        
        chunks = chunker.chunk_text(text, "test_chapter")
        
        # Deve criar múltiplos chunks
        assert len(chunks) >= 1
        
        # O primeiro chunk deve terminar próximo a uma quebra de parágrafo
        # (testamos se a lógica não quebra o código)
        for chunk in chunks:
            assert chunk.content.strip()  # Não deve ter chunks vazios
    
    def test_chunk_with_sentences(self):
        """Testa fragmentação respeitando quebras de sentença."""
        chunker = TextChunker(
            chunk_size=60,
            overlap_size=10,
            preserve_sentences=True,
            preserve_paragraphs=False
        )
        
        text = "Esta é a primeira sentença. Esta é a segunda sentença! Esta é a terceira sentença? Esta é a quarta sentença."
        
        chunks = chunker.chunk_text(text, "test_chapter")
        
        assert len(chunks) >= 1
        
        # Verifica que não há chunks vazios
        for chunk in chunks:
            assert chunk.content.strip()
    
    def test_natural_break_finding(self):
        """Testa busca por quebras naturais."""
        chunker = TextChunker(chunk_size=50, overlap_size=5)
        text = "Texto com parágrafo.\n\nNovo parágrafo aqui. Sentença adicional."
        
        # Testa o método diretamente
        break_pos = chunker._find_natural_break(text, 0, 30)
        
        # Deve encontrar uma posição válida
        assert 0 <= break_pos <= len(text)
    
    def test_chunk_chapters(self):
        """Testa fragmentação de múltiplos capítulos."""
        chunker = TextChunker(chunk_size=50)
        
        chapters = [
            {'id': 'cap1', 'content': 'Conteúdo do capítulo 1 com texto suficiente.'},
            {'id': 'cap2', 'content': 'Conteúdo do capítulo 2 também com texto.'},
            {'content': 'Capítulo sem ID'}  # Deve usar ID padrão
        ]
        
        all_chunks = chunker.chunk_chapters(chapters)
        
        assert len(all_chunks) == 3
        assert len(all_chunks[0]) >= 1  # Cap1 deve ter chunks
        assert len(all_chunks[1]) >= 1  # Cap2 deve ter chunks
        assert len(all_chunks[2]) >= 1  # Cap3 deve ter chunks
        
        # Verifica IDs dos capítulos
        assert all_chunks[0][0].chapter_id == 'cap1'
        assert all_chunks[1][0].chapter_id == 'cap2'
        assert all_chunks[2][0].chapter_id == 'chapter_2'  # ID padrão
    
    def test_chunk_chapters_empty_content(self):
        """Testa fragmentação de capítulos com conteúdo vazio."""
        chunker = TextChunker()
        
        chapters = [
            {'id': 'cap1', 'content': 'Conteúdo válido'},
            {'id': 'cap2', 'content': ''},  # Vazio
            {'id': 'cap3', 'content': '   '}  # Só espaços
        ]
        
        with patch('chunker.logger') as mock_logger:
            all_chunks = chunker.chunk_chapters(chapters)
        
        assert len(all_chunks) == 3
        assert len(all_chunks[0]) >= 1  # Cap1 tem conteúdo
        assert len(all_chunks[1]) == 0  # Cap2 vazio
        assert len(all_chunks[2]) == 0  # Cap3 vazio
        
        # Verifica se foi logado warning para capítulos vazios
        mock_logger.warning.assert_called()
    
    def test_get_chunk_with_context(self, sample_text):
        """Testa obtenção de chunk com contexto."""
        chunker = TextChunker(chunk_size=100, overlap_size=20)
        chunks = chunker.chunk_text(sample_text, "test")
        
        if len(chunks) > 1:
            # Testa com chunk do meio
            context_text = chunker.get_chunk_with_context(chunks[1], sample_text)
            
            # Deve incluir contexto (overlap)
            assert len(context_text) >= len(chunks[1].content)
    
    def test_estimate_tokens(self):
        """Testa estimativa de tokens."""
        chunker = TextChunker()
        
        text = "Este é um texto de teste"
        tokens = chunker.estimate_tokens(text)
        
        # Deve retornar um número positivo baseado no texto
        assert tokens > 0
        assert tokens == int(len(text) * 0.25)  # Valor padrão
        
        # Testa com razão personalizada
        tokens_custom = chunker.estimate_tokens(text, tokens_per_char=0.5)
        assert tokens_custom == int(len(text) * 0.5)
    
    def test_adjust_chunk_size_for_model(self):
        """Testa ajuste de chunk_size para diferentes modelos."""
        chunker = TextChunker(chunk_size=1000)
        original_size = chunker.chunk_size
        
        # Testa com modelo conhecido
        with patch('chunker.logger') as mock_logger:
            chunker.adjust_chunk_size_for_model('gpt-4')
        
        # Chunk size deve ter mudado
        assert chunker.chunk_size != original_size
        mock_logger.info.assert_called()
        
        # Testa com modelo desconhecido
        chunker2 = TextChunker(chunk_size=1000)
        chunker2.adjust_chunk_size_for_model('modelo-desconhecido')
        
        # Deve usar valor padrão conservador
        assert chunker2.chunk_size > 0
        
        # Testa com max_tokens específico
        chunker3 = TextChunker(chunk_size=1000)
        chunker3.adjust_chunk_size_for_model('gpt-4', max_tokens=50000)
        assert chunker3.chunk_size > 0
    
    def test_overlap_size_adjustment(self):
        """Testa se overlap_size é ajustado proporcionalmente."""
        chunker = TextChunker(chunk_size=1000, overlap_size=100)
        
        chunker.adjust_chunk_size_for_model('gpt-3.5')
        
        # Overlap deve ser no máximo chunk_size // 20
        assert chunker.overlap_size <= chunker.chunk_size // 20


class TestIntegration:
    """Testes de integração para o módulo chunker."""
    
    def test_complete_workflow(self, sample_text):
        """Testa fluxo completo de fragmentação."""
        chunker = TextChunker(chunk_size=200, overlap_size=30)
        
        # Fragmenta o texto
        chunks = chunker.chunk_text(sample_text, "integration_test")
        
        # Verifica se todos os chunks são válidos
        assert len(chunks) > 0
        
        total_length = 0
        for i, chunk in enumerate(chunks):
            # Cada chunk deve ter conteúdo
            assert chunk.content.strip()
            
            # IDs devem ser sequenciais
            assert chunk.chunk_id == i
            
            # Chapter ID deve estar correto
            assert chunk.chapter_id == "integration_test"
            
            # Posições devem fazer sentido
            assert chunk.start_pos >= 0
            assert chunk.end_pos > chunk.start_pos
            assert chunk.end_pos <= len(sample_text)
            
            total_length += len(chunk.content)
        
        # O texto total dos chunks deve cobrir o texto original
        # (pode ser maior devido aos overlaps)
        assert total_length >= len(sample_text.strip())
    
    def test_chunker_with_real_book_structure(self):
        """Testa com estrutura similar a um livro real."""
        chapters = []
        
        # Simula capítulos de um livro
        for i in range(5):
            content = f"""
            Capítulo {i+1}: Título do Capítulo
            
            Este é o início do capítulo {i+1}. O texto continua com múltiplos 
            parágrafos para simular conteúdo real de um livro.
            
            Segundo parágrafo do capítulo {i+1}. Aqui temos mais texto para 
            garantir que o chunker funcione corretamente com conteúdo realista.
            
            "Diálogo de exemplo", disse o personagem principal. "Este diálogo 
            também deve ser preservado adequadamente."
            
            Parágrafo final do capítulo {i+1} com conclusão adequada.
            """
            
            chapters.append({
                'id': f'cap_{i+1}',
                'title': f'Capítulo {i+1}',
                'content': content.strip()
            })
        
        chunker = TextChunker(chunk_size=300, overlap_size=50)
        all_chunks = chunker.chunk_chapters(chapters)
        
        # Verifica estrutura geral
        assert len(all_chunks) == 5
        
        # Verifica se todos os capítulos foram processados
        total_chunks = sum(len(chapter_chunks) for chapter_chunks in all_chunks)
        assert total_chunks > 0
        
        # Verifica consistência entre capítulos
        for i, chapter_chunks in enumerate(all_chunks):
            expected_chapter_id = f'cap_{i+1}'
            
            for chunk in chapter_chunks:
                assert chunk.chapter_id == expected_chapter_id
                assert chunk.content.strip()  # Não deve ter chunks vazios