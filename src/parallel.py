"""
Sistema de processamento paralelo e coordenação de workers.
"""

import asyncio
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from src.chunker import TextChunker
from src.progress import OutputManager, ProgressManager
from src.translator import TranslationClient, TranslationConfig

logger = logging.getLogger(__name__)


@dataclass
class WorkerStats:
    """Estatísticas de um worker."""

    worker_id: int
    chapters_processed: int = 0
    chunks_processed: int = 0
    errors_count: int = 0
    total_processing_time: float = 0.0
    last_activity: str | None = None


class RateLimiter:
    """Rate limiter simples para controlar requisições por segundo."""

    def __init__(self, calls_per_second: float):
        """
        Inicializa o rate limiter.

        Args:
            calls_per_second: Número máximo de chamadas por segundo
        """
        self.calls_per_second = calls_per_second
        self.min_interval = 1.0 / calls_per_second if calls_per_second > 0 else 0
        self.last_call_time = 0.0

    async def acquire(self):
        """Aguarda se necessário para respeitar o rate limit."""
        if self.min_interval <= 0:
            return

        current_time = time.time()
        time_since_last_call = current_time - self.last_call_time

        if time_since_last_call < self.min_interval:
            sleep_time = self.min_interval - time_since_last_call
            await asyncio.sleep(sleep_time)

        self.last_call_time = time.time()


class ChapterWorker:
    """Worker para processar capítulos individuais."""

    def __init__(
        self,
        worker_id: int,
        translator: TranslationClient,
        chunker: TextChunker,
        progress_manager: ProgressManager,
        output_manager: OutputManager,
        rate_limiter: RateLimiter | None = None,
    ):
        """
        Inicializa o worker.

        Args:
            worker_id: ID único do worker
            translator: Cliente de tradução
            chunker: Fragmentador de texto
            progress_manager: Gerenciador de progresso
            output_manager: Gerenciador de saída
            rate_limiter: Limitador de taxa (opcional)
        """
        self.worker_id = worker_id
        self.translator = translator
        self.chunker = chunker
        self.progress_manager = progress_manager
        self.output_manager = output_manager
        self.rate_limiter = rate_limiter
        self.stats = WorkerStats(worker_id)

    async def process_chapter(
        self, chapter: dict[str, Any], progress_callback: Callable | None = None
    ) -> bool:
        """
        Processa um capítulo completo.

        Args:
            chapter: Dados do capítulo
            progress_callback: Callback para reportar progresso

        Returns:
            True se processado com sucesso, False caso contrário
        """
        chapter_id = chapter.get("id", "unknown")
        chapter_title = chapter.get("title", "Sem título")
        content = chapter.get("content", "")

        start_time = time.time()

        try:
            logger.info(f"Worker {self.worker_id}: ===== INICIANDO CAPÍTULO =====")
            logger.info(f"Worker {self.worker_id}: Capítulo: {chapter_title}")
            logger.info(f"Worker {self.worker_id}: ID: {chapter_id}")
            logger.info(
                f"Worker {self.worker_id}: Tamanho do conteúdo: {len(content):,} caracteres"
            )

            # Marca capítulo como iniciado
            logger.debug(f"Worker {self.worker_id}: Marcando capítulo como iniciado...")
            if not self.progress_manager.start_chapter(chapter_id):
                logger.warning(
                    f"Worker {self.worker_id}: Capítulo {chapter_id} já foi iniciado"
                )
                return False
            logger.debug(f"Worker {self.worker_id}: Capítulo marcado como iniciado")

            # Fragmenta o texto
            logger.info(f"Worker {self.worker_id}: Fragmentando texto...")
            chunks = self.chunker.chunk_text(content, chapter_id)
            logger.info(
                f"Worker {self.worker_id}: Fragmentação concluída - {len(chunks) if chunks else 0} chunks gerados"
            )
            if not chunks:
                logger.warning(
                    f"Worker {self.worker_id}: Capítulo {chapter_id} não gerou chunks"
                )
                self.progress_manager.complete_chapter(chapter_id)
                return True

            # Atualiza progresso com número de chunks
            self.progress_manager.update_chapter_chunks(chapter_id, len(chunks))

            # Traduz cada chunk
            logger.info(
                f"Worker {self.worker_id}: Iniciando tradução de {len(chunks)} chunks..."
            )
            translated_chunks = []

            for i, chunk in enumerate(chunks):
                chunk_start_time = time.time()
                chunk_size = len(chunk.content)

                try:
                    logger.debug(
                        f"Worker {self.worker_id}: Traduzindo chunk {i + 1}/{len(chunks)} ({chunk_size} chars)"
                    )

                    # Rate limiting
                    if self.rate_limiter:
                        logger.debug(
                            f"Worker {self.worker_id}: Aplicando rate limit..."
                        )
                        await self.rate_limiter.acquire()

                    # Traduz o chunk
                    logger.debug(
                        f"Worker {self.worker_id}: Enviando chunk para tradução..."
                    )
                    translated_text = await self.translator.translate_text(
                        chunk.content
                    )
                    translated_chunks.append(translated_text)

                    # Atualiza progresso
                    self.progress_manager.complete_chunk(chapter_id, translated_text)
                    self.stats.chunks_processed += 1

                    # Callback de progresso
                    if progress_callback:
                        progress_callback(
                            self.worker_id, chapter_id, i + 1, len(chunks)
                        )

                    chunk_time = time.time() - chunk_start_time
                    logger.info(
                        f"Worker {self.worker_id}: Chunk {i + 1}/{len(chunks)} traduzido em {chunk_time:.1f}s ({chunk_size} → {len(translated_text)} chars)"
                    )

                except Exception as e:
                    chunk_time = time.time() - chunk_start_time
                    logger.error(
                        f"Worker {self.worker_id}: ERRO ao traduzir chunk {i + 1}/{len(chunks)}: {e}"
                    )
                    logger.error(
                        f"Worker {self.worker_id}: Chunk falhado após {chunk_time:.1f}s, tamanho: {chunk_size} chars"
                    )
                    logger.debug(
                        f"Worker {self.worker_id}: Conteúdo do chunk com erro: {chunk.content[:200]}{'...' if len(chunk.content) > 200 else ''}"
                    )

                    self.stats.errors_count += 1
                    # Em caso de erro, mantém o texto original
                    translated_chunks.append(chunk.content)
                    logger.warning(
                        f"Worker {self.worker_id}: Usando texto original para chunk {i + 1}"
                    )

            # Junta todos os chunks traduzidos
            logger.debug(
                f"Worker {self.worker_id}: Juntando {len(translated_chunks)} chunks traduzidos..."
            )
            full_translated_content = "\n\n".join(translated_chunks)
            final_size = len(full_translated_content)
            original_size = len(content)
            size_change = (
                ((final_size - original_size) / original_size * 100)
                if original_size > 0
                else 0
            )

            logger.info(
                f"Worker {self.worker_id}: Conteúdo final: {original_size:,} → {final_size:,} chars ({size_change:+.1f}%)"
            )

            # Salva o capítulo no arquivo de saída
            logger.debug(
                f"Worker {self.worker_id}: Salvando capítulo no arquivo de saída..."
            )
            self.output_manager.append_chapter(
                chapter_title, full_translated_content, chapter_id
            )
            logger.debug(f"Worker {self.worker_id}: Capítulo salvo com sucesso")

            # Marca capítulo como completado
            logger.debug(
                f"Worker {self.worker_id}: Marcando capítulo como completado..."
            )
            self.progress_manager.complete_chapter(chapter_id)

            # Atualiza estatísticas
            processing_time = time.time() - start_time
            self.stats.chapters_processed += 1
            self.stats.total_processing_time += processing_time
            self.stats.last_activity = f"Completado: {chapter_title}"

            chunks_per_sec = len(chunks) / processing_time if processing_time > 0 else 0
            chars_per_sec = (
                original_size / processing_time if processing_time > 0 else 0
            )

            logger.info(f"Worker {self.worker_id}: ===== CAPÍTULO CONCLUÍDO =====")
            logger.info(f"Worker {self.worker_id}: Título: {chapter_title}")
            logger.info(f"Worker {self.worker_id}: Tempo total: {processing_time:.1f}s")
            logger.info(f"Worker {self.worker_id}: Chunks processados: {len(chunks)}")
            logger.info(
                f"Worker {self.worker_id}: Velocidade: {chunks_per_sec:.1f} chunks/s, {chars_per_sec:.0f} chars/s"
            )
            logger.info(
                f"Worker {self.worker_id}: Erros neste capítulo: {self.stats.errors_count}"
            )

            return True

        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Worker {self.worker_id}: ===== ERRO FATAL NO CAPÍTULO =====")
            logger.error(f"Worker {self.worker_id}: Capítulo: {chapter_title}")
            logger.error(f"Worker {self.worker_id}: ID: {chapter_id}")
            logger.error(
                f"Worker {self.worker_id}: Tempo até erro: {processing_time:.1f}s"
            )
            logger.error(f"Worker {self.worker_id}: Tipo do erro: {type(e).__name__}")
            logger.error(f"Worker {self.worker_id}: Mensagem: {e!s}")
            logger.error(
                f"Worker {self.worker_id}: Tamanho do conteúdo: {len(content):,} chars"
            )

            # Salva informações sobre o erro
            self.progress_manager.mark_chapter_error(chapter_id, str(e))
            self.stats.errors_count += 1
            self.stats.last_activity = f"Erro: {chapter_title}"

            return False


class ParallelProcessor:
    """Coordenador de processamento paralelo."""

    def __init__(
        self,
        translator_config: TranslationConfig,
        chunker: TextChunker,
        progress_manager: ProgressManager,
        output_manager: OutputManager,
        max_workers: int = 4,
        rate_limit: float = 2.0,  # requisições por segundo
    ):
        """
        Inicializa o processador paralelo.

        Args:
            translator_config: Configuração do tradutor
            chunker: Fragmentador de texto
            progress_manager: Gerenciador de progresso
            output_manager: Gerenciador de saída
            max_workers: Número máximo de workers paralelos
            rate_limit: Limite de requisições por segundo (total)
        """
        self.translator_config = translator_config
        self.chunker = chunker
        self.progress_manager = progress_manager
        self.output_manager = output_manager
        self.max_workers = max_workers

        # Rate limiter compartilhado entre todos os workers
        self.rate_limiter = RateLimiter(rate_limit) if rate_limit > 0 else None

        self.workers: list[ChapterWorker] = []
        self.worker_stats: dict[int, WorkerStats] = {}

    async def create_workers(self, api_key: str | None = None) -> None:
        """
        Cria workers para processamento paralelo.

        Args:
            api_key: Chave da API
        """
        self.workers = []
        self.worker_stats = {}

        for worker_id in range(self.max_workers):
            # Cada worker tem seu próprio cliente tradutor
            translator = TranslationClient(self.translator_config, api_key)

            # Testa conexão do primeiro worker
            if worker_id == 0:
                success, message = await translator.test_connection()
                if not success:
                    raise Exception(f"Falha na conexão com o modelo: {message}")

            worker = ChapterWorker(
                worker_id=worker_id,
                translator=translator,
                chunker=self.chunker,
                progress_manager=self.progress_manager,
                output_manager=self.output_manager,
                rate_limiter=self.rate_limiter,
            )

            self.workers.append(worker)
            self.worker_stats[worker_id] = worker.stats

        logger.info(f"Criados {len(self.workers)} workers para processamento paralelo")

    async def process_chapters(
        self,
        chapters: list[dict[str, Any]],
        progress_callback: Callable | None = None,
        resume: bool = False,
    ) -> dict[str, Any]:
        """
        Processa capítulos em paralelo.

        Args:
            chapters: Lista de capítulos para processar
            progress_callback: Callback para reportar progresso
            resume: Se True, retoma apenas capítulos pendentes

        Returns:
            Dicionário com estatísticas do processamento
        """
        if not self.workers:
            raise RuntimeError(
                "Workers não foram criados. Chame create_workers() primeiro."
            )

        start_time = time.time()

        # Determina quais capítulos processar
        if resume:
            pending_chapter_ids = self.progress_manager.get_pending_chapters()
            chapters_to_process = [
                ch
                for i, ch in enumerate(chapters)
                if ch.get("id", f"chapter_{i}") in pending_chapter_ids
            ]
            logger.info(
                f"Retomando processamento: {len(chapters_to_process)} capítulos pendentes"
            )
        else:
            chapters_to_process = chapters
            logger.info(
                f"Iniciando processamento: {len(chapters_to_process)} capítulos"
            )

        if not chapters_to_process:
            logger.info("Nenhum capítulo para processar")
            return self._get_processing_stats(0)

        # Cria semáforo para controlar número de workers ativos
        semaphore = asyncio.Semaphore(self.max_workers)

        async def process_with_semaphore(
            worker: ChapterWorker, chapter: dict[str, Any]
        ):
            """Processa capítulo com controle de semáforo."""
            async with semaphore:
                return await worker.process_chapter(chapter, progress_callback)

        # Cria tasks para processamento
        tasks = []
        for i, chapter in enumerate(chapters_to_process):
            worker = self.workers[i % len(self.workers)]  # Round-robin entre workers
            task = asyncio.create_task(process_with_semaphore(worker, chapter))
            tasks.append(task)

        # Aguarda conclusão de todos os tasks
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Conta sucessos e falhas
            successes = sum(1 for result in results if result is True)
            failures = len(results) - successes

            processing_time = time.time() - start_time

            logger.info(
                f"Processamento concluído: {successes} sucessos, {failures} falhas em {processing_time:.1f}s"
            )

            return self._get_processing_stats(processing_time)

        except Exception as e:
            logger.error(f"Erro durante processamento paralelo: {e}")
            raise

    def _get_processing_stats(self, total_time: float) -> dict[str, Any]:
        """Coleta estatísticas de processamento."""
        total_chapters = sum(
            stats.chapters_processed for stats in self.worker_stats.values()
        )
        total_chunks = sum(
            stats.chunks_processed for stats in self.worker_stats.values()
        )
        total_errors = sum(stats.errors_count for stats in self.worker_stats.values())

        worker_details = {}
        for worker_id, stats in self.worker_stats.items():
            worker_details[f"worker_{worker_id}"] = {
                "chapters_processed": stats.chapters_processed,
                "chunks_processed": stats.chunks_processed,
                "errors_count": stats.errors_count,
                "processing_time": stats.total_processing_time,
                "last_activity": stats.last_activity,
            }

        return {
            "total_time": total_time,
            "total_chapters_processed": total_chapters,
            "total_chunks_processed": total_chunks,
            "total_errors": total_errors,
            "workers_used": len(self.workers),
            "average_time_per_chapter": total_time / max(total_chapters, 1),
            "worker_details": worker_details,
        }

    async def cleanup(self):
        """Limpa recursos dos workers."""
        # Por enquanto não há recursos específicos para limpar
        # mas pode ser útil no futuro
        logger.info("Limpeza dos workers concluída")
