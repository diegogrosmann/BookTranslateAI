"""
Sistema de progresso e persistência para tradução de livros.
"""
import json
import logging
import os
import threading
import queue
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict, field
from pathlib import Path

try:
    from .document_generator import generate_documents
    DOCUMENT_GENERATOR_AVAILABLE = True
except ImportError:
    DOCUMENT_GENERATOR_AVAILABLE = False
    logging.warning("document_generator não disponível. Geração de EPUB/PDF desabilitada.")

logger = logging.getLogger(__name__)


@dataclass
class ChapterProgress:
    """Estado de progresso de um capítulo."""
    chapter_id: str
    title: str
    total_chunks: int
    original_index: int = 0  # Índice original do capítulo no livro
    completed_chunks: int = 0
    translated_chunks: List[str] = field(default_factory=list)
    status: str = "pending"  # pending, in_progress, completed, error
    error: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None


@dataclass 
class TranslationProgress:
    """Estado geral de progresso da tradução."""
    input_file: str
    output_file: str
    model: str
    target_language: str
    total_chapters: int
    completed_chapters: int = 0
    chapters: Dict[str, ChapterProgress] = field(default_factory=dict)
    start_time: str = field(default_factory=lambda: datetime.now().isoformat())
    last_update: str = field(default_factory=lambda: datetime.now().isoformat())
    status: str = "in_progress"  # in_progress, completed, error, paused
    error: Optional[str] = None
    
    def update_timestamp(self):
        """Atualiza timestamp da última modificação."""
        self.last_update = datetime.now().isoformat()


class ProgressManager:
    """Gerenciador de progresso com persistência thread-safe."""
    
    def __init__(self, progress_file: str):
        """
        Inicializa o gerenciador de progresso.
        
        Args:
            progress_file: Caminho para o arquivo de progresso JSON
        """
        self.progress_file = progress_file
        self.progress: Optional[TranslationProgress] = None
        self._lock = threading.Lock()
        
        # Sistema de salvamento assíncrono
        self._save_queue = queue.Queue()
        self._save_thread = None
        self._stop_saving = threading.Event()
        self._last_save_time = 0
        self._save_debounce_interval = 2.0  # Salva no máximo a cada 2 segundos para chunks
        self._pending_important_save = False  # Flag para salvamentos importantes
        
        # Cria diretório se não existir
        os.makedirs(os.path.dirname(progress_file), exist_ok=True)
        
        # Inicia thread de salvamento
        self._start_save_thread()
    
    def _start_save_thread(self):
        """Inicia a thread de salvamento em background."""
        if self._save_thread is None or not self._save_thread.is_alive():
            self._stop_saving.clear()
            self._save_thread = threading.Thread(target=self._save_worker, daemon=True)
            self._save_thread.start()
            logger.debug("Thread de salvamento iniciada")
    
    def _save_worker(self):
        """Worker que executa salvamentos em background."""
        while not self._stop_saving.is_set():
            try:
                # Aguarda por requisição de salvamento ou timeout
                try:
                    save_type = self._save_queue.get(timeout=0.5)
                except queue.Empty:
                    continue
                
                # Debounce: evita salvamentos muito frequentes
                current_time = time.time()
                time_since_last_save = current_time - self._last_save_time
                
                # Salvamentos importantes (início/fim de capítulo) têm prioridade
                if save_type == "important" or self._pending_important_save:
                    self._pending_important_save = True
                    if time_since_last_save < 0.5:  # Aguarda menos para operações importantes
                        time.sleep(0.5 - time_since_last_save)
                elif time_since_last_save < self._save_debounce_interval:
                    # Aguarda um pouco mais antes de salvar chunks normais
                    time.sleep(self._save_debounce_interval - time_since_last_save)
                
                # Executa o salvamento
                self._save_to_disk()
                self._last_save_time = time.time()
                self._pending_important_save = False
                
            except Exception as e:
                logger.error(f"Erro na thread de salvamento: {e}")
    
    def _save_to_disk(self):
        """Salva progresso no disco de forma síncrona (chamado pela thread de background)."""
        if not self.progress:
            return
        
        # Cria cópia dos dados para evitar modificações durante salvamento
        with self._lock:
            progress_copy = asdict(self.progress)
        
        try:
            # Atualiza timestamp
            progress_copy['last_update'] = datetime.now().isoformat()
            
            # Salva atomicamente (escreve em arquivo temporário e depois move)
            temp_file = f"{self.progress_file}.tmp"
            
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(progress_copy, f, indent=2, ensure_ascii=False)
            
            # Move arquivo temporário para o final
            os.replace(temp_file, self.progress_file)
            
        except Exception as e:
            logger.error(f"Erro ao salvar progresso no disco: {e}")
    
    def _queue_save(self, important: bool = False):
        """
        Envia uma requisição de salvamento para a queue (não-bloqueante).
        
        Args:
            important: Se True, o salvamento terá prioridade e menor debounce
        """
        try:
            # Adiciona na queue sem bloquear (descarta se queue estiver cheia)
            save_type = "important" if important else "normal"
            self._save_queue.put_nowait(save_type)
        except queue.Full:
            # Queue cheia, ignora (já há salvamento pendente)
            pass
    
    def stop_save_thread(self):
        """Para a thread de salvamento e força um salvamento final."""
        if self._save_thread and self._save_thread.is_alive():
            # Força salvamento final
            self._save_to_disk()
            
            # Para a thread
            self._stop_saving.set()
            self._save_thread.join(timeout=2.0)
            logger.debug("Thread de salvamento parada")
    
    def create_progress(
        self,
        input_file: str,
        output_file: str,
        model: str,
        target_language: str,
        chapters: List[Dict[str, Any]]
    ) -> TranslationProgress:
        """
        Cria um novo estado de progresso.
        
        Args:
            input_file: Arquivo de entrada
            output_file: Arquivo de saída
            model: Modelo de IA usado
            target_language: Idioma alvo
            chapters: Lista de capítulos extraídos
            
        Returns:
            Objeto TranslationProgress criado
        """
        with self._lock:
            progress = TranslationProgress(
                input_file=input_file,
                output_file=output_file,
                model=model,
                target_language=target_language,
                total_chapters=len(chapters)
            )
            
            # Cria progresso para cada capítulo
            for i, chapter in enumerate(chapters):
                chapter_id = chapter.get('id', f'chapter_{i}')
                chapter_title = chapter.get('title', f'Capítulo {i+1}')
                
                chapter_progress = ChapterProgress(
                    chapter_id=chapter_id,
                    title=chapter_title,
                    total_chunks=0,  # Será atualizado quando os chunks forem criados
                    original_index=i  # Preserva a ordem original
                )
                
                progress.chapters[chapter_id] = chapter_progress
            
            self.progress = progress
            self.progress.update_timestamp()
            # Salvamento prioritário para criação de progresso
            self._queue_save(important=True)
            logger.info(f"Novo progresso criado para {len(chapters)} capítulos")
            
            return progress
    
    def load_progress(self) -> Optional[TranslationProgress]:
        """
        Carrega progresso do arquivo JSON.
        
        Returns:
            TranslationProgress se existir, None caso contrário
        """
        if not os.path.exists(self.progress_file):
            return None
        
        try:
            with open(self.progress_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Reconstrói objetos a partir do JSON
            progress = TranslationProgress(**data)
            
            # Reconstrói progresso dos capítulos
            chapters_dict = {}
            for chapter_id, chapter_data in data.get('chapters', {}).items():
                # Adiciona original_index se não existir (compatibilidade com JSON antigo)
                if 'original_index' not in chapter_data:
                    chapter_data['original_index'] = 0  # Valor padrão
                    logger.debug(f"Adicionado original_index=0 para compatibilidade: {chapter_id}")
                
                chapters_dict[chapter_id] = ChapterProgress(**chapter_data)
            
            progress.chapters = chapters_dict
            self.progress = progress
            
            logger.info(f"Progresso carregado: {progress.completed_chapters}/{progress.total_chapters} capítulos")
            return progress
            
        except Exception as e:
            logger.error(f"Erro ao carregar progresso: {e}")
            return None
    
    def save_progress(self) -> None:
        """
        Solicita salvamento assíncrono do progresso (não-bloqueante).
        O salvamento real acontece em background thread.
        """
        if not self.progress:
            return
        
        # Atualiza timestamp na memória
        with self._lock:
            self.progress.update_timestamp()
        
        # Solicita salvamento assíncrono (não bloqueia)
        self._queue_save()
    
    def save_progress_sync(self) -> None:
        """
        Força salvamento síncrono imediato (usar apenas quando necessário).
        """
        if not self.progress:
            return
        
        with self._lock:
            self.progress.update_timestamp()
        
        self._save_to_disk()
    
    def update_chapter_chunks(self, chapter_id: str, total_chunks: int) -> None:
        """
        Atualiza o número total de chunks de um capítulo.
        
        Args:
            chapter_id: ID do capítulo
            total_chunks: Número total de chunks
        """
        if not self.progress or chapter_id not in self.progress.chapters:
            return
        
        with self._lock:
            self.progress.chapters[chapter_id].total_chunks = total_chunks
            self.progress.update_timestamp()
            # Salvamento normal para atualização de chunks
            self._queue_save(important=False)
    
    def start_chapter(self, chapter_id: str) -> bool:
        """
        Marca um capítulo como iniciado.
        
        Args:
            chapter_id: ID do capítulo
            
        Returns:
            True se foi possível iniciar, False caso contrário
        """
        if not self.progress or chapter_id not in self.progress.chapters:
            return False
        
        with self._lock:
            chapter = self.progress.chapters[chapter_id]
            if chapter.status == "pending":
                chapter.status = "in_progress"  
                chapter.start_time = datetime.now().isoformat()
                self.progress.update_timestamp()
                # Salvamento prioritário para início de capítulo
                self._queue_save(important=True)
                logger.info(f"Capítulo iniciado: {chapter.title}")
                return True
            
            return False
    
    def complete_chunk(self, chapter_id: str, chunk_text: str) -> None:
        """
        Marca um chunk como completado.
        
        Args:
            chapter_id: ID do capítulo
            chunk_text: Texto traduzido do chunk
        """
        if not self.progress or chapter_id not in self.progress.chapters:
            return
        
        with self._lock:
            chapter = self.progress.chapters[chapter_id]
            chapter.translated_chunks.append(chunk_text)
            chapter.completed_chunks = len(chapter.translated_chunks)
            self.progress.update_timestamp()
            # Salvamento normal para chunks (com debounce)
            self._queue_save(important=False)
    
    def complete_chapter(self, chapter_id: str) -> None:
        """
        Marca um capítulo como completado.
        
        Args:
            chapter_id: ID do capítulo
        """
        if not self.progress or chapter_id not in self.progress.chapters:
            return
        
        with self._lock:
            chapter = self.progress.chapters[chapter_id]
            chapter.status = "completed"
            chapter.end_time = datetime.now().isoformat()
            
            # Atualiza contador geral
            self.progress.completed_chapters = sum(
                1 for ch in self.progress.chapters.values() 
                if ch.status == "completed"
            )
            
            # Verifica se todos os capítulos foram completados
            if self.progress.completed_chapters >= self.progress.total_chapters:
                self.progress.status = "completed"
                logger.info("Tradução completada!")
            
            self.progress.update_timestamp()
            # Salvamento prioritário para conclusão de capítulo
            self._queue_save(important=True)
            logger.info(f"Capítulo completado: {chapter.title}")
    
    def mark_chapter_error(self, chapter_id: str, error: str) -> None:
        """
        Marca um capítulo com erro.
        
        Args:
            chapter_id: ID do capítulo  
            error: Mensagem de erro
        """
        if not self.progress or chapter_id not in self.progress.chapters:
            return
        
        with self._lock:
            chapter = self.progress.chapters[chapter_id]
            chapter.status = "error"
            chapter.error = error
            chapter.end_time = datetime.now().isoformat()
            self.progress.update_timestamp()
            # Salvamento prioritário para erros
            self._queue_save(important=True)
            logger.error(f"Erro no capítulo {chapter.title}: {error}")
    
    def get_pending_chapters(self) -> List[str]:
        """
        Retorna lista de IDs de capítulos pendentes.
        
        Returns:
            Lista de IDs de capítulos que ainda não foram completados
        """
        if not self.progress:
            return []
        
        return [
            chapter_id for chapter_id, chapter in self.progress.chapters.items()
            if chapter.status in ["pending", "error"]
        ]
    
    def get_progress_summary(self) -> Dict[str, Any]:
        """
        Retorna resumo do progresso atual.
        
        Returns:
            Dicionário com informações de progresso
        """
        if not self.progress:
            return {}
        
        # Conta capítulos por status
        status_counts = {"pending": 0, "in_progress": 0, "completed": 0, "error": 0}
        total_chunks = 0
        completed_chunks = 0
        
        for chapter in self.progress.chapters.values():
            status_counts[chapter.status] = status_counts.get(chapter.status, 0) + 1
            total_chunks += chapter.total_chunks
            completed_chunks += chapter.completed_chunks
        
        return {
            "status": self.progress.status,
            "total_chapters": self.progress.total_chapters,
            "completed_chapters": self.progress.completed_chapters,
            "chapters_by_status": status_counts,
            "total_chunks": total_chunks,
            "completed_chunks": completed_chunks,
            "progress_percentage": (completed_chunks / max(total_chunks, 1)) * 100,
            "start_time": self.progress.start_time,
            "last_update": self.progress.last_update,
            "input_file": self.progress.input_file,
            "output_file": self.progress.output_file,
            "model": self.progress.model,
            "target_language": self.progress.target_language
        }
    
    def reset_progress(self) -> None:
        """Reseta o progresso atual."""
        with self._lock:
            if os.path.exists(self.progress_file):
                os.remove(self.progress_file)
            self.progress = None
            logger.info("Progresso resetado")
    
    def can_resume(self, input_file: str, model: str, target_language: str) -> bool:
        """
        Verifica se é possível retomar uma tradução existente.
        
        Args:
            input_file: Arquivo de entrada atual
            model: Modelo atual
            target_language: Idioma alvo atual
            
        Returns:
            True se pode retomar, False caso contrário
        """
        if not self.progress:
            return False
        
        return (
            self.progress.input_file == input_file and
            self.progress.model == model and
            self.progress.target_language == target_language and
            self.progress.status in ["in_progress", "paused"]
        )
    
    def finalize(self):
        """
        Finaliza o ProgressManager, garantindo que todo progresso seja salvo.
        Deve ser chamado antes de encerrar o programa.
        """
        logger.debug("Finalizando ProgressManager...")
        self.stop_save_thread()
        logger.debug("ProgressManager finalizado")
    
    def __del__(self):
        """Destructor que garante limpeza da thread."""
        try:
            self.stop_save_thread()
        except:
            pass


class OutputManager:
    """Gerenciador de saída Markdown thread-safe."""
    
    def __init__(self, output_file: str, chapter_manager=None, generate_documents: bool = True,
                 book_title: str = "Livro Traduzido", book_author: str = "Autor Desconhecido"):
        """
        Inicializa o gerenciador de saída.
        
        Args:
            output_file: Caminho para o arquivo de saída Markdown
            chapter_manager: Gerenciador de capítulos individuais (opcional)
            generate_documents: Se deve gerar EPUB e PDF automaticamente
            book_title: Título do livro para documentos
            book_author: Autor do livro para documentos
        """
        self.output_file = output_file
        self.chapter_manager = chapter_manager
        self.generate_documents = generate_documents
        self.book_title = book_title
        self.book_author = book_author
        self._lock = threading.Lock()
        self._chapter_counter = 0
        
        # Cria diretório se não existir
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    def initialize_file(self, title: str = "Tradução") -> None:
        """
        Inicializa o arquivo de saída com cabeçalho.
        
        Args:
            title: Título do documento
        """
        with self._lock:
            header = f"""# {title}

*Traduzido automaticamente*

---

"""
            with open(self.output_file, 'w', encoding='utf-8') as f:
                f.write(header)
    
    def append_chapter(self, chapter_title: str, translated_content: str, chapter_id: str = None) -> None:
        """
        Registra um capítulo traduzido (não salva em arquivo ainda).
        A geração dos arquivos finais será feita apenas no final.
        
        Args:
            chapter_title: Título do capítulo
            translated_content: Conteúdo traduzido
            chapter_id: ID do capítulo
        """
        with self._lock:
            # Durante o processamento, apenas registra que o capítulo foi processado
            # O conteúdo já está sendo salvo no JSON de progresso
            logger.info(f"Capítulo registrado para geração final: {chapter_title}")
            # Não salva em arquivo ainda - será feito no final
    
    def _append_traditional(self, chapter_title: str, translated_content: str) -> None:
        """
        Adiciona capítulo usando método tradicional (arquivo único).
        
        Args:
            chapter_title: Título do capítulo
            translated_content: Conteúdo traduzido
        """
        chapter_md = f"""
## {chapter_title}

{translated_content}

---

"""
        with open(self.output_file, 'a', encoding='utf-8') as f:
            f.write(chapter_md)
        
        logger.info(f"Capítulo adicionado ao arquivo: {chapter_title}")
    
    def generate_final_documents_from_progress(self, progress_manager) -> bool:
        """
        Gera todos os arquivos finais (MD, EPUB, PDF) a partir do progresso JSON.
        
        Args:
            progress_manager: Instância do ProgressManager com os dados de tradução
            
        Returns:
            True se geração foi bem-sucedida
        """
        if not progress_manager.progress:
            logger.error("Nenhum progresso disponível para gerar documentos")
            return False
        
        try:
            logger.info("Gerando arquivos finais a partir do progresso JSON...")
            
            # Usa ordenação inteligente baseada nos padrões das partes
            chapters_by_index = self._sort_chapters_smartly(
                {chapter_id: chapter 
                 for chapter_id, chapter in progress_manager.progress.chapters.items()
                 if chapter.status == "completed"}
            )
            
            if not chapters_by_index:
                logger.warning("Nenhum capítulo completado encontrado")
                return False
            
            # Gera arquivo Markdown
            logger.info("Gerando arquivo Markdown...")
            success = self._generate_markdown_from_progress(chapters_by_index)
            if not success:
                return False
            
            # Gera documentos EPUB e PDF se habilitado
            if self.generate_documents and DOCUMENT_GENERATOR_AVAILABLE:
                logger.info("Gerando documentos EPUB e PDF...")
                self._generate_final_documents()
            
            logger.info(f"Arquivos finais gerados com sucesso em: {self.output_file}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao gerar arquivos finais: {e}")
            return False
    
    def _generate_markdown_from_progress(self, chapters_by_index) -> bool:
        """
        Gera arquivo Markdown a partir dos capítulos ordenados.
        
        Args:
            chapters_by_index: Lista de tuplas (index, chapter_id, chapter) ordenadas
            
        Returns:
            True se bem-sucedido
        """
        try:
            with self._lock:
                # Inicializa arquivo com cabeçalho simples
                header = f"""# {self.book_title}

*Traduzido automaticamente*

---

"""
                with open(self.output_file, 'w', encoding='utf-8') as f:
                    f.write(header)
                    
                    # Adiciona cada capítulo na ordem original
                    for original_index, chapter_id, chapter in chapters_by_index:
                        if chapter.translated_chunks:
                            # Junta todos os chunks traduzidos do capítulo
                            full_translated_content = '\n\n'.join(chapter.translated_chunks)
                            
                            # Formata título do capítulo (remove duplicatas de "Winter's Heart")
                            formatted_title = self._format_chapter_title(chapter.title, chapter_id)
                            
                            chapter_md = f"""
## {formatted_title}

{full_translated_content}

---

"""
                            f.write(chapter_md)
                            logger.debug(f"Capítulo adicionado ao MD: {formatted_title} (índice original: {original_index})")
                        else:
                            logger.warning(f"Capítulo sem conteúdo traduzido: {chapter.title}")
                
                logger.info(f"Arquivo Markdown gerado: {self.output_file}")
                return True
                
        except Exception as e:
            logger.error(f"Erro ao gerar arquivo Markdown: {e}")
            return False
    
    def _format_chapter_title(self, title: str, chapter_id: str) -> str:
        """
        Formata o título do capítulo de forma inteligente.
        
        Args:
            title: Título original
            chapter_id: ID do capítulo (ex: part142)
            
        Returns:
            Título formatado
        """
        import re
        
        # Se for um cabeçalho de capítulo específico (ex: "Chapter 3"), usa como está
        if re.match(r'Chapter \d+', title):
            return title
        
        # Se for um título genérico como "Winter's Heart", tenta melhorar baseado no part_id
        if title.strip() == "Winter's Heart" or title.strip() == "Coração do Inverno":
            match = re.match(r'part(\d+)', chapter_id)
            if match:
                part_num = int(match.group(1))
                
                if part_num < 10:
                    # Partes iniciais - usa nome do livro
                    if part_num == 1:
                        return "Coração do Inverno"
                    else:
                        return f"Parte {part_num}"
                
                elif part_num < 100:
                    # Divisores
                    return f"Divisor {part_num}"
                
                else:
                    # Capítulos de 3 dígitos
                    chapter_num = part_num // 10
                    section_type = part_num % 10
                    
                    if section_type == 2:
                        return f"Capítulo {chapter_num // 2 + 1}"  # Aproximação do número do capítulo
                    else:
                        return title  # Mantém o título original para o conteúdo
        
        return title

    def _decode_part_number(self, part_id: str) -> tuple:
        """
        Decodifica um part_id em uma tupla para ordenação inteligente.
        
        Args:
            part_id: ID da parte (ex: "part142", "part1", "part11")
            
        Returns:
            Tupla (chapter_group, chapter_order, section_type)
        """
        import re
        
        match = re.match(r'part(\d+)', part_id)
        if not match:
            return (0, 0, 0)
        
        part_num = int(match.group(1))
        
        if part_num < 10:
            # Partes simples (prefácio, etc.)
            return (0, part_num, 0)
        
        elif part_num < 100:
            # Divisores entre capítulos (part11, part13, etc.)
            return (part_num, 2, 0)  # Coloca após o conteúdo do capítulo
            
        else:
            # Partes de 3 dígitos (capítulos)
            chapter_num = part_num // 10  # Primeiros 2 dígitos
            section_type = part_num % 10  # Último dígito
            
            # section_type: 1=conteúdo, 2=cabeçalho
            # Queremos: cabeçalho primeiro (order=0), depois conteúdo (order=1)
            chapter_order = 0 if section_type == 2 else 1
            
            return (chapter_num, chapter_order, section_type)

    def _create_smart_ordering_key(self, chapter_data) -> tuple:
        """
        Cria chave de ordenação inteligente para capítulos.
        
        Args:
            chapter_data: Dados do capítulo do JSON
            
        Returns:
            Tupla para ordenação
        """
        chapter_id = chapter_data.chapter_id
        original_index = chapter_data.original_index
        
        # Se for um chapter_id com padrão "part", usa ordenação inteligente
        if chapter_id.startswith('part'):
            chapter_group, chapter_order, section_type = self._decode_part_number(chapter_id)
            return (chapter_group, chapter_order, section_type, original_index)
        else:
            # Para outros tipos, usa apenas o índice original
            return (original_index, 0, 0, 0)

    def _sort_chapters_smartly(self, chapters_dict) -> list:
        """
        Ordena capítulos de forma inteligente baseada nos padrões identificados.
        
        Args:
            chapters_dict: Dicionário com dados dos capítulos
            
        Returns:
            Lista de tuplas (original_index, chapter_id, chapter) ordenada
        """
        # Converte para lista com dados necessários para ordenação
        chapters_list = []
        for chapter_id, chapter_data in chapters_dict.items():
            # Pula part1 que contém apenas informações do livro (não conteúdo narrativo)
            if chapter_id == 'part1':
                continue
                
            smart_key = self._create_smart_ordering_key(chapter_data)
            chapters_list.append((smart_key, chapter_data.original_index, chapter_id, chapter_data))
        
        # Ordena usando chave inteligente
        chapters_list.sort(key=lambda x: x[0])
        
        # Retorna no formato esperado
        return [(original_index, chapter_id, chapter_data) 
                for smart_key, original_index, chapter_id, chapter_data in chapters_list]

    def consolidate_chapters_if_needed(self) -> bool:
        """
        OBSOLETO: Mantido para compatibilidade. Use generate_final_documents_from_progress().
        
        Returns:
            True (compatibilidade)
        """
        logger.warning("consolidate_chapters_if_needed() está obsoleto. Use generate_final_documents_from_progress()")
        return True
    
    def _generate_final_documents(self) -> None:
        """Gera documentos EPUB e PDF finais."""
        try:
            if not os.path.exists(self.output_file):
                logger.warning("Arquivo de saída não existe, pulando geração de documentos")
                return
            
            # Determina diretório e nome base para os documentos
            output_dir = os.path.dirname(self.output_file)
            base_filename = os.path.splitext(os.path.basename(self.output_file))[0]
            
            logger.info("Gerando documentos EPUB e PDF...")
            generated_files = generate_documents(
                content_file=self.output_file,
                output_dir=output_dir,
                base_filename=base_filename,
                title=self.book_title,
                author=self.book_author
            )
            
            if generated_files:
                logger.info("Documentos gerados com sucesso:")
                for file_path in generated_files:
                    logger.info(f"  - {file_path}")
            else:
                logger.warning("Nenhum documento foi gerado")
                
        except Exception as e:
            logger.error(f"Erro ao gerar documentos finais: {e}")
    
    def file_exists(self) -> bool:
        """Verifica se o arquivo de saída já existe."""
        return os.path.exists(self.output_file)