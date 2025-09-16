"""Sistema de Fragmentação Inteligente de Texto.

Este módulo implementa um sistema sofisticado para dividir textos longos
em fragmentos (chunks) menores, mantendo contexto através de overlap e
respeitando quebras naturais como parágrafos e sentenças.

O sistema é essencial para tradução de textos longos com modelos de IA
que têm limitações de contexto. Oferece:

    - Fragmentação com overlap configurável para manter contexto
    - Detecção de quebras naturais (parágrafos, sentenças)
    - Ajuste automático para diferentes modelos de IA
    - Logging detalhado do processo de fragmentação
    - Estimativa de tokens para planejamento

Classes:
    TextChunk: Representa um fragmento de texto com metadados
    TextChunker: Engine principal de fragmentação

Example:
    Uso básico do fragmentador:
    
    >>> chunker = TextChunker(
    ...     chunk_size=4000,
    ...     overlap_size=200,
    ...     preserve_sentences=True
    ... )
    >>> 
    >>> chunks = chunker.chunk_text(long_text, "chapter_1")
    >>> print(f"Texto dividido em {len(chunks)} chunks")
    >>> 
    >>> # Processa múltiplos capítulos
    >>> all_chunks = chunker.chunk_chapters(chapters)

Note:
    O sistema prioriza quebras naturais sobre tamanho exato dos chunks
    para manter qualidade da tradução.
"""
import logging
import re
from typing import List, Dict, Tuple
from dataclasses import dataclass


logger = logging.getLogger(__name__)


@dataclass
class TextChunk:
    """Representa um fragmento de texto com metadados de posição.
    
    Esta classe encapsula um fragmento de texto junto com informações
    sobre sua posição original, overlaps e identificação dentro do
    contexto maior (capítulo/documento).
    
    Attributes:
        content: Texto do fragmento
        start_pos: Posição inicial no texto original
        end_pos: Posição final no texto original  
        chunk_id: ID único do chunk dentro do capítulo
        chapter_id: ID do capítulo ao qual este chunk pertence
        overlap_start: Tamanho do overlap no início (caracteres)
        overlap_end: Tamanho do overlap no final (caracteres)
        
    Example:
        >>> chunk = TextChunk(
        ...     content="Era uma vez...",
        ...     start_pos=0,
        ...     end_pos=13,
        ...     chunk_id=0,
        ...     chapter_id="cap1"
        ... )
        >>> print(f"Chunk {chunk.chunk_id}: {len(chunk.content)} chars")
    """
    content: str
    start_pos: int
    end_pos: int
    chunk_id: int
    chapter_id: str
    overlap_start: int = 0
    overlap_end: int = 0


class TextChunker:
    """Engine de fragmentação inteligente de texto.
    
    Esta classe implementa algoritmos sofisticados para dividir textos
    longos em fragmentos menores, otimizados para tradução com IA.
    
    O fragmentador:
    - Respeita limites de tamanho configuráveis
    - Adiciona overlap entre chunks para manter contexto
    - Prioriza quebras naturais (parágrafos, sentenças)
    - Ajusta automaticamente para diferentes modelos de IA
    - Fornece logging detalhado do processo
    
    Attributes:
        chunk_size: Tamanho máximo de cada chunk em caracteres
        overlap_size: Tamanho do overlap entre chunks
        preserve_sentences: Se deve evitar quebrar sentenças
        preserve_paragraphs: Se deve priorizar quebras entre parágrafos
        
    Example:
        >>> # Configuração básica
        >>> chunker = TextChunker(chunk_size=4000, overlap_size=200)
        >>> 
        >>> # Configuração avançada
        >>> chunker = TextChunker(
        ...     chunk_size=3000,
        ...     overlap_size=300,
        ...     preserve_sentences=True,
        ...     preserve_paragraphs=True
        ... )
        >>> 
        >>> # Ajuste automático para modelo
        >>> chunker.adjust_chunk_size_for_model("gpt-4")
    """
    
    def __init__(
        self,
        chunk_size: int = 4000,
        overlap_size: int = 200,
        preserve_sentences: bool = True,
        preserve_paragraphs: bool = True
    ):
        """
        Inicializa o chunker.
        
        Args:
            chunk_size: Tamanho máximo de cada chunk em caracteres
            overlap_size: Tamanho do overlap entre chunks em caracteres
            preserve_sentences: Se True, tenta não quebrar sentenças
            preserve_paragraphs: Se True, prioriza quebras entre parágrafos
        """
        self.chunk_size = chunk_size
        self.overlap_size = overlap_size
        self.preserve_sentences = preserve_sentences
        self.preserve_paragraphs = preserve_paragraphs
        
        # Padrões regex para identificar quebras naturais
        self.sentence_pattern = re.compile(r'[.!?]+\s+')
        self.paragraph_pattern = re.compile(r'\n\s*\n')
    
    def chunk_text(self, text: str, chapter_id: str) -> List[TextChunk]:
        """
        Fragmenta um texto em chunks com overlap.
        
        Args:
            text: Texto a ser fragmentado
            chapter_id: ID do capítulo/seção
            
        Returns:
            Lista de TextChunk objects
        """
        logger.info(f"=== FRAGMENTANDO TEXTO ===")
        logger.info(f"Capítulo ID: {chapter_id}")
        logger.info(f"Tamanho do texto: {len(text):,} caracteres")
        logger.info(f"Chunk size: {self.chunk_size:,}")
        logger.info(f"Overlap size: {self.overlap_size:,}")
        logger.debug(f"Preservar sentenças: {self.preserve_sentences}")
        logger.debug(f"Preservar parágrafos: {self.preserve_paragraphs}")
        
        if not text.strip():
            logger.warning("Texto vazio ou apenas espaços - retornando lista vazia")
            return []
        
        chunks = []
        current_pos = 0
        chunk_id = 0
        natural_breaks_found = 0
        forced_breaks = 0
        
        estimated_chunks = (len(text) // self.chunk_size) + 1
        logger.debug(f"Chunks estimados: {estimated_chunks}")
        
        while current_pos < len(text):
            logger.debug(f"--- Processando chunk {chunk_id + 1} ---")
            logger.debug(f"Posição atual: {current_pos:,}/{len(text):,}")
            
            # Calcula o fim do chunk atual
            chunk_end = min(current_pos + self.chunk_size, len(text))
            original_chunk_end = chunk_end
            
            # Se não é o último chunk, tenta encontrar uma quebra natural
            if chunk_end < len(text):
                logger.debug(f"Buscando quebra natural próxima à posição {chunk_end}")
                chunk_end = self._find_natural_break(text, current_pos, chunk_end)
                
                if chunk_end != original_chunk_end:
                    natural_breaks_found += 1
                    logger.debug(f"Quebra natural encontrada: {original_chunk_end} → {chunk_end}")
                else:
                    forced_breaks += 1
                    logger.debug(f"Quebra forçada na posição {chunk_end}")
            
            # Extrai o conteúdo do chunk
            chunk_content = text[current_pos:chunk_end].strip()
            chunk_size_actual = len(chunk_content)
            
            logger.debug(f"Chunk {chunk_id + 1}: {current_pos}-{chunk_end} ({chunk_size_actual:,} chars)")
            
            if chunk_content:
                # Calcula overlaps
                overlap_start = 0
                overlap_end = 0
                
                if chunks:  # Não é o primeiro chunk
                    overlap_start = min(self.overlap_size, current_pos)
                    logger.debug(f"Overlap início: {overlap_start} chars")
                
                if chunk_end < len(text):  # Não é o último chunk
                    overlap_end = self.overlap_size
                    logger.debug(f"Overlap fim: {overlap_end} chars")
                
                # Cria o chunk
                chunk = TextChunk(
                    content=chunk_content,
                    start_pos=current_pos,
                    end_pos=chunk_end,
                    chunk_id=chunk_id,
                    chapter_id=chapter_id,
                    overlap_start=overlap_start,
                    overlap_end=overlap_end
                )
                
                chunks.append(chunk)
                logger.debug(f"Chunk {chunk_id + 1} criado com sucesso")
                chunk_id += 1
            else:
                logger.warning(f"Chunk vazio ignorado na posição {current_pos}")
            
            # Move para a próxima posição, considerando o overlap
            if chunk_end >= len(text):
                logger.debug("Último chunk processado")
                break
                
            # Calcula próxima posição com overlap
            next_pos = chunk_end - self.overlap_size
            if next_pos <= current_pos:
                next_pos = current_pos + 1  # Evita loop infinito
                logger.debug(f"Ajustando posição para evitar loop: {current_pos} → {next_pos}")
            
            logger.debug(f"Próxima posição: {next_pos} (overlap: {self.overlap_size})")
            current_pos = next_pos
        
        total_chars_in_chunks = sum(len(chunk.content) for chunk in chunks)
        avg_chunk_size = total_chars_in_chunks // len(chunks) if chunks else 0
        
        logger.info(f"=== FRAGMENTAÇÃO CONCLUÍDA ===")
        logger.info(f"Chunks gerados: {len(chunks)}")
        logger.info(f"Quebras naturais: {natural_breaks_found}")
        logger.info(f"Quebras forçadas: {forced_breaks}")
        logger.info(f"Total de caracteres em chunks: {total_chars_in_chunks:,}")
        logger.info(f"Tamanho médio dos chunks: {avg_chunk_size:,} chars")
        
        if chunks:
            min_size = min(len(chunk.content) for chunk in chunks)
            max_size = max(len(chunk.content) for chunk in chunks)
            logger.info(f"Tamanho dos chunks: {min_size:,} - {max_size:,} chars")
        
        return chunks
    
    def _find_natural_break(self, text: str, start_pos: int, target_end: int) -> int:
        """
        Encontra uma quebra natural próxima ao target_end.
        
        Args:
            text: Texto completo
            start_pos: Posição inicial do chunk
            target_end: Posição alvo para o fim do chunk
            
        Returns:
            Posição ajustada para quebra natural
        """
        # Define uma janela de busca para quebras naturais
        search_window = min(200, self.chunk_size // 10)
        search_start = max(target_end - search_window, start_pos)
        search_end = min(target_end + search_window, len(text))
        
        logger.debug(f"Buscando quebra natural: janela {search_start}-{search_end} (alvo: {target_end})")
        
        search_text = text[search_start:search_end]
        
        # Primeira prioridade: quebra de parágrafo
        if self.preserve_paragraphs:
            paragraph_breaks = list(self.paragraph_pattern.finditer(search_text))
            logger.debug(f"Quebras de parágrafo encontradas: {len(paragraph_breaks)}")
            
            if paragraph_breaks:
                # Pega a quebra mais próxima do target
                best_break = min(
                    paragraph_breaks,
                    key=lambda m: abs((search_start + m.end()) - target_end)
                )
                final_pos = search_start + best_break.end()
                logger.debug(f"Quebra de parágrafo selecionada na posição {final_pos} (distância: {abs(final_pos - target_end)})")
                return final_pos
        
        # Segunda prioridade: quebra de sentença
        if self.preserve_sentences:
            sentence_breaks = list(self.sentence_pattern.finditer(search_text))
            logger.debug(f"Quebras de sentença encontradas: {len(sentence_breaks)}")
            
            if sentence_breaks:
                # Pega a quebra mais próxima do target
                best_break = min(
                    sentence_breaks,
                    key=lambda m: abs((search_start + m.end()) - target_end)
                )
                final_pos = search_start + best_break.end()
                logger.debug(f"Quebra de sentença selecionada na posição {final_pos} (distância: {abs(final_pos - target_end)})")
                return final_pos
        
        # Se não encontrou quebra natural, usa a posição original
        logger.debug(f"Nenhuma quebra natural encontrada, usando posição original: {target_end}")
        return target_end
    
    def chunk_chapters(self, chapters: List[Dict[str, str]]) -> List[List[TextChunk]]:
        """
        Fragmenta múltiplos capítulos.
        
        Args:
            chapters: Lista de capítulos com 'content' e identificadores
            
        Returns:
            Lista de listas de chunks (uma lista por capítulo)
        """
        all_chunks = []
        
        for i, chapter in enumerate(chapters):
            chapter_id = chapter.get('id', f'chapter_{i}')
            content = chapter.get('content', '')
            
            if content.strip():
                chunks = self.chunk_text(content, chapter_id)
                all_chunks.append(chunks)
            else:
                logger.warning(f"Capítulo {chapter_id} está vazio, pulando")
                all_chunks.append([])
        
        total_chunks = sum(len(chunks) for chunks in all_chunks)
        logger.info(f"Total de {total_chunks} chunks criados para {len(chapters)} capítulos")
        
        return all_chunks
    
    def get_chunk_with_context(self, chunk: TextChunk, text: str) -> str:
        """
        Retorna o chunk com contexto de overlap.
        
        Args:
            chunk: Chunk original
            text: Texto completo do capítulo
            
        Returns:
            Texto do chunk com contexto de overlap
        """
        # Calcula posições com overlap
        start_with_overlap = max(0, chunk.start_pos - chunk.overlap_start)
        end_with_overlap = min(len(text), chunk.end_pos + chunk.overlap_end)
        
        # Extrai texto com contexto
        context_text = text[start_with_overlap:end_with_overlap]
        
        # Adiciona marcadores para indicar o chunk principal
        if chunk.overlap_start > 0:
            main_start = chunk.overlap_start
        else:
            main_start = 0
            
        if chunk.overlap_end > 0:
            main_end = len(context_text) - chunk.overlap_end
        else:
            main_end = len(context_text)
        
        # Retorna com marcadores (opcional, pode ser removido se não necessário)
        return context_text
    
    def estimate_tokens(self, text: str, tokens_per_char: float = 0.25) -> int:
        """Estima número de tokens baseado no número de caracteres.
        
        Fornece uma estimativa aproximada do número de tokens que um texto
        ocupará quando processado por modelos de IA. Útil para planejamento
        e verificação de limites.
        
        Args:
            text: Texto a ser estimado
            tokens_per_char: Razão média de tokens por caractere.
                Default 0.25 é conservador para texto em português.
                
        Returns:
            Número estimado de tokens (inteiro)
            
        Note:
            Esta é uma estimativa. Diferentes modelos podem ter 
            tokenizações ligeiramente diferentes. O valor padrão
            é conservador para evitar exceder limites.
            
        Example:
            >>> chunker = TextChunker()
            >>> tokens = chunker.estimate_tokens("Olá mundo!")
            >>> print(f"Tokens estimados: {tokens}")
        """
        return int(len(text) * tokens_per_char)
    
    def adjust_chunk_size_for_model(self, model_name: str, max_tokens: int = None) -> None:
        """Ajusta tamanho dos chunks para modelo específico.
        
        Automaticamente ajusta o tamanho dos chunks baseado nos limites
        de contexto conhecidos de diferentes modelos de IA. Reserva espaço
        para prompt do sistema, instruções e resposta.
        
        Args:
            model_name: Nome do modelo (ex: 'gpt-4', 'claude-3-sonnet').
                Suporta detecção automática baseada em palavras-chave.
            max_tokens: Limite máximo de tokens (opcional).
                Se fornecido, sobrescreve detecção automática.
                
        Note:
            O ajuste é conservador, usando apenas ~60-70% do limite
            disponível para garantir espaço para prompt e resposta.
            O overlap também é ajustado proporcionalmente.
            
        Example:
            >>> chunker = TextChunker()
            >>> 
            >>> # Ajuste automático
            >>> chunker.adjust_chunk_size_for_model("gpt-4-turbo")
            >>> 
            >>> # Limite manual
            >>> chunker.adjust_chunk_size_for_model("custom-model", 50000)
        """
        # Estimativas conservadoras para diferentes modelos
        model_limits = {
            'gpt-3.5': 16000,
            'gpt-4': 32000,
            'gpt-4-turbo': 128000,
            'gpt-5': 200000,
            'claude-3': 200000,
            'claude-3.5': 200000,
        }
        
        # Encontra limite baseado no nome do modelo
        limit = max_tokens
        if not limit:
            for model_key, model_limit in model_limits.items():
                if model_key in model_name.lower():
                    limit = model_limit
                    break
            else:
                limit = 8000  # Padrão conservador
        
        # Reserve espaço para prompt do sistema, instruções e resposta
        available_tokens = limit - 2000
        
        # Converte tokens para caracteres (aproximação)
        chars_per_token = 4  # Média conservadora
        new_chunk_size = int(available_tokens * chars_per_token * 0.8)  # 80% do disponível
        
        if new_chunk_size != self.chunk_size:
            logger.info(f"Ajustando chunk_size de {self.chunk_size} para {new_chunk_size} para modelo {model_name}")
            self.chunk_size = new_chunk_size
            
            # Ajusta overlap proporcionalmente
            self.overlap_size = min(self.overlap_size, self.chunk_size // 20)