#!/usr/bin/env python3
"""
Tradutor de Livros - Tradução automática de EPUB e PDF usando IA.

Este aplicativo traduz livros em formato EPUB ou PDF usando modelos de IA
através da biblioteca LiteLLM, com suporte a processamento paralelo,
retomada de progresso e salvamento incremental.
"""
import os
import sys
import asyncio
import logging
import traceback
import click
from pathlib import Path
from typing import Optional, Dict, Any
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.panel import Panel

# Adiciona src ao path para imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.extractors import ContentExtractorFactory
from src.chunker import TextChunker
from src.translator import TranslationClient, TranslationConfig
from src.progress import ProgressManager, OutputManager
from src.parallel import ParallelProcessor
from src.chapter_manager import ChapterFileManager
from src.logging_config import setup_logging, get_log_file_path, progress_logger


console = Console()


def load_context_from_file(context_file: str) -> str:
    """
    Carrega contexto customizado de um arquivo.
    
    Args:
        context_file: Caminho para o arquivo de contexto
        
    Returns:
        Conteúdo do arquivo como string
    """
    try:
        with open(context_file, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        console.print(f"✓ Contexto carregado de {context_file} ({len(content)} caracteres)", style="green")
        return content
    except Exception as e:
        console.print(f"✗ Erro ao carregar contexto de {context_file}: {e}", style="red")
        return ""


def validate_model_name(model: str) -> str:
    """
    Valida e normaliza nome do modelo.
    
    Args:
        model: Nome do modelo fornecido
        
    Returns:
        Nome do modelo normalizado
    """
    # Lista de modelos conhecidos com prefixos
    known_models = {
        'gpt-3.5-turbo': 'openai/gpt-3.5-turbo',
        'gpt-4': 'openai/gpt-4',
        'gpt-4-turbo': 'openai/gpt-4-turbo',
        'gpt-5': 'openai/gpt-5',
        'claude-3-haiku': 'anthropic/claude-3-haiku',
        'claude-3-sonnet': 'anthropic/claude-3-sonnet',
        'claude-3.5-sonnet': 'anthropic/claude-3.5-sonnet',
        'gemini-pro': 'gemini/gemini-pro',
        'gemini-1.5-pro': 'gemini/gemini-1.5-pro',
        'gemini-2.5-flash': 'gemini/gemini-2.5-flash',
    }
    
    # Se já tem prefixo, verifica se precisa corrigir
    if '/' in model:
        # Corrige prefixo do Gemini se necessário
        if model.startswith('google/gemini'):
            return model.replace('google/gemini', 'gemini/gemini')
        return model
    
    # Busca por modelo conhecido
    if model in known_models:
        return known_models[model]
    
    # Se não encontrou, mantém como fornecido
    return model


class ProgressDisplay:
    """Gerenciador de exibição de progresso em tempo real."""
    
    def __init__(self):
        self.console = Console()
        self.current_progress = None
        self.active_chapters = {}
    
    def start_progress(self, total_chapters: int):
        """Inicia a exibição de progresso."""
        self.current_progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=self.console
        )
        self.main_task = self.current_progress.add_task(
            "[cyan]Traduzindo capítulos...", total=total_chapters
        )
        self.current_progress.start()
    
    def update_chapter_progress(self, worker_id: int, chapter_id: str, completed_chunks: int, total_chunks: int):
        """Atualiza progresso de um capítulo específico."""
        if not self.current_progress:
            return
        
        # Atualiza ou cria task para o capítulo
        chapter_desc = f"Worker {worker_id}: {chapter_id}"
        if chapter_id not in self.active_chapters:
            self.active_chapters[chapter_id] = self.current_progress.add_task(
                f"[blue]{chapter_desc}", total=total_chunks
            )
        
        task_id = self.active_chapters[chapter_id]
        self.current_progress.update(task_id, completed=completed_chunks)
        
        # Se completou, remove da lista ativa e atualiza progresso geral
        if completed_chunks >= total_chunks:
            self.current_progress.update(task_id, description=f"[green]✓ {chapter_desc}")
            self.current_progress.advance(self.main_task)
            del self.active_chapters[chapter_id]
    
    def stop_progress(self):
        """Para a exibição de progresso."""
        if self.current_progress:
            self.current_progress.stop()
            self.current_progress = None


@click.command()
@click.option('--input', '--in', 'input_file', type=click.Path(exists=True),
              help='Arquivo de entrada (EPUB ou PDF)')
@click.option('--output-md', '--out-md', 'output_file', type=click.Path(),
              help='Arquivo de saída em Markdown')
@click.option('--model', default='openai/gpt-4-turbo', 
              help='Modelo de IA para tradução (ex: openai/gpt-4, anthropic/claude-3.5-sonnet)')
@click.option('--target-lang', default='pt-BR',
              help='Idioma alvo da tradução (ex: pt-BR, en-US, es-ES)')
@click.option('--api-key', envvar='API_KEY',
              help='Chave da API do provedor (ou use variável de ambiente API_KEY)')
@click.option('--context', default='',
              help='Contexto adicional para orientar a tradução')
@click.option('--context-file', type=click.Path(exists=True),
              help='Arquivo com contexto adicional para tradução')
@click.option('--chunk-size', default=4000, type=int,
              help='Tamanho máximo de cada chunk em caracteres')
@click.option('--overlap-size', default=200, type=int,
              help='Tamanho do overlap entre chunks em caracteres')
@click.option('--max-workers', default=4, type=int,
              help='Número máximo de workers paralelos')
@click.option('--rate-limit', default=2.0, type=float,
              help='Limite de requisições por segundo (0 = sem limite)')
@click.option('--format', 'format_override', type=click.Choice(['epub', 'pdf']),
              help='Força formato específico (auto-detectado se não especificado)')
@click.option('--resume/--no-resume', default=True,
              help='Retomar tradução existente se possível')
@click.option('--log-level', default='INFO', type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR']),
              help='Nível de logging')
@click.option('--log-file', type=click.Path(),
              help='Arquivo para logs detalhados (auto-gerado se não especificado)')
@click.option('--clean-terminal/--verbose-terminal', default=True,
              help='Terminal limpo (apenas progresso) vs. verbose')
@click.option('--test-connection', is_flag=True,
              help='Apenas testa conexão com o modelo e sai')
@click.option('--list-models', is_flag=True,
              help='Lista modelos disponíveis e sai')
@click.option('--save-chapters-separately', is_flag=True,
              help='Salva cada capítulo em arquivo separado antes de consolidar')
@click.option('--output-dir', type=click.Path(),
              help='Diretório de saída para capítulos separados (padrão: mesmo dir do arquivo final)')
@click.option('--keep-chapter-files/--cleanup-chapter-files', default=True,
              help='Manter arquivos de capítulos individuais após consolidação')
def main(
    input_file: str,
    output_file: str,
    model: str,
    target_lang: str,
    api_key: Optional[str],
    context: str,
    context_file: Optional[str],
    chunk_size: int,
    overlap_size: int,
    max_workers: int,
    rate_limit: float,
    format_override: Optional[str],
    resume: bool,
    log_level: str,
    log_file: Optional[str],
    clean_terminal: bool,
    test_connection: bool,
    list_models: bool,
    save_chapters_separately: bool,
    output_dir: Optional[str],
    keep_chapter_files: bool
):
    """
    Tradutor de Livros - Traduz EPUB e PDF usando IA.
    
    Exemplos de uso:
    
    \b
    # Tradução básica
    python tradutor.py --input livro.epub --output-md traducao.md --api-key sua_chave
    
    \b  
    # Com contexto personalizado
    python tradutor.py --input livro.epub --output-md traducao.md \\
        --model anthropic/claude-3.5-sonnet --context-file instrucoes.txt \\
        --target-lang pt-BR --max-workers 8
    
    \b
    # Teste de conexão
    python tradutor.py --test-connection --model openai/gpt-4 --api-key sua_chave
    """
    
    # Configura logging
    if not log_file:
        log_file = get_log_file_path()
    
    setup_logging(
        log_level=log_level,
        log_file=log_file,
        clean_terminal=clean_terminal
    )
    
    # Lista modelos se solicitado
    if list_models:
        console.print("\n[bold]Modelos disponíveis:[/bold]")
        models = TranslationClient.list_available_models()
        
        table = Table(show_header=True, header_style="bold blue")
        table.add_column("Provedor", style="cyan")
        table.add_column("Modelo", style="green") 
        table.add_column("Nome Alternativo", style="yellow")
        
        for model_name in models:
            if '/' in model_name:
                provider, model = model_name.split('/', 1)
                alt_name = model
            else:
                provider = "Direto"
                model = model_name
                alt_name = f"provider/{model_name}"
            
            table.add_row(provider, model, alt_name)
        
        console.print(table)
        console.print(f"\n[dim]Use qualquer um dos nomes na coluna 'Modelo' ou 'Nome Alternativo'[/dim]")
        return
    
    # Normaliza nome do modelo
    model = validate_model_name(model)
    
    # Carrega contexto de arquivo se especificado
    if context_file:
        file_context = load_context_from_file(context_file)
        if file_context:
            context = file_context if not context else f"{context}\n\n{file_context}"
    
    # Configura tradução
    translation_config = TranslationConfig(
        model=model,
        target_language=target_lang,
        context=context
    )
    
    # Teste de conexão se solicitado
    if test_connection:
        console.print(f"\n[yellow]Testando conexão com {model}...[/yellow]")
        
        try:
            translator = TranslationClient(translation_config, api_key)
            success, message = asyncio.run(translator.test_connection())
            
            if success:
                console.print(f"✓ [green]{message}[/green]")
                
                # Mostra informações do modelo
                info = translator.get_model_info()
                
                panel_content = f"""[bold]Modelo:[/bold] {info['model']}
[bold]Idioma Alvo:[/bold] {info['target_language']}"""
                
                console.print(Panel(panel_content, title="Configuração do Modelo", border_style="green"))
                
            else:
                console.print(f"✗ [red]{message}[/red]")
                sys.exit(1)
                
        except Exception as e:
            console.print(f"✗ [red]Erro: {e}[/red]")
            sys.exit(1)
        
        return
    
    # Validações de parâmetros obrigatórios (não necessários para flags especiais)
    if not input_file:
        console.print("✗ [red]Arquivo de entrada é obrigatório. Use --input[/red]")
        sys.exit(1)
    
    if not output_file:
        console.print("✗ [red]Arquivo de saída é obrigatório. Use --output-md[/red]")
        sys.exit(1)
    
    if not api_key:
        console.print("✗ [red]Chave da API é obrigatória. Use --api-key ou defina API_KEY[/red]")
        sys.exit(1)
    
    # Executa tradução
    asyncio.run(translate_book(
        input_file=input_file,
        output_file=output_file,
        translation_config=translation_config,
        api_key=api_key,
        chunk_size=chunk_size,
        overlap_size=overlap_size,
        max_workers=max_workers,
        rate_limit=rate_limit,
        format_override=format_override,
        resume=resume,
        save_chapters_separately=save_chapters_separately,
        output_dir=output_dir,
        keep_chapter_files=keep_chapter_files
    ))


async def translate_book(
    input_file: str,
    output_file: str,
    translation_config: TranslationConfig,
    api_key: str,
    chunk_size: int,
    overlap_size: int,
    max_workers: int,
    rate_limit: float,
    format_override: Optional[str],
    resume: bool,
    save_chapters_separately: bool = False,
    output_dir: Optional[str] = None,
    keep_chapter_files: bool = True
):
    """Função principal de tradução."""
    
    logger = logging.getLogger(__name__)
    
    console.print(f"\n[bold blue]🚀 Iniciando Tradutor de Livros[/bold blue]")
    logger.info(f"========== INICIANDO TRADUÇÃO ==========")
    logger.info(f"Arquivo de entrada: {input_file}")
    logger.info(f"Arquivo de saída: {output_file}")
    logger.info(f"Modelo: {translation_config.model}")
    logger.info(f"Idioma alvo: {translation_config.target_language}")
    logger.info(f"Chunk size: {chunk_size}, Overlap: {overlap_size}")
    logger.info(f"Max workers: {max_workers}, Rate limit: {rate_limit}")
    logger.info(f"Retomar: {resume}, Formato override: {format_override}")
    logger.info(f"=========================================")
    
    try:
        # Configura gerenciadores
        logger.info("=== CONFIGURANDO GERENCIADORES ===")
        progress_file = f"{output_file}.progress.json"
        logger.debug(f"Arquivo de progresso: {progress_file}")
        
        progress_manager = ProgressManager(progress_file)
        logger.debug("ProgressManager criado")
        
        # Configura chapter manager se necessário
        chapter_manager = None
        if save_chapters_separately:
            # Define diretório de saída
            if output_dir:
                chapters_output_dir = output_dir
            else:
                chapters_output_dir = os.path.dirname(output_file) or "."
            
            # Título do livro para nomeação
            book_title = Path(input_file).stem
            
            chapter_manager = ChapterFileManager(chapters_output_dir, book_title)
            logger.info(f"ChapterFileManager criado - Diretório: {chapters_output_dir}")
            console.print(f"📁 [cyan]Capítulos serão salvos separadamente em: {chapter_manager.chapters_dir}[/cyan]")
        
        # Título e autor do livro para documentos
        book_title = Path(input_file).stem
        book_author = "Autor Desconhecido"  # Poderia ser extraído dos metadados se disponível
        
        output_manager = OutputManager(
            output_file, 
            chapter_manager,
            generate_documents=True,  # Sempre gerar documentos
            book_title=book_title,
            book_author=book_author
        )
        logger.debug(f"OutputManager criado para: {output_file}")
        logger.info("Gerenciadores configurados com sucesso")
        console.print(f"📚 [green]Documentos EPUB e PDF serão gerados automaticamente[/green]")
        
        # Tenta carregar progresso existente
        logger.info("=== VERIFICANDO PROGRESSO EXISTENTE ===")
        existing_progress = None
        if resume:
            logger.info("Modo de retomada ativado - tentando carregar progresso")
            existing_progress = progress_manager.load_progress()
            
            if existing_progress:
                logger.info(f"Progresso encontrado: {len(existing_progress.chapters)} capítulos")
                
                can_resume = progress_manager.can_resume(
                    input_file, translation_config.model, translation_config.target_language
                )
                logger.debug(f"Pode retomar: {can_resume}")
                
                if can_resume:
                    pending_chapters = progress_manager.get_pending_chapters()
                    console.print(f"📋 [green]Retomando tradução existente...[/green]")
                    logger.info(f"Retomando tradução - {len(pending_chapters)} capítulos pendentes")
                    progress_logger.log_resume(len(pending_chapters))
                else:
                    existing_progress = None
                    logger.warning("Progresso incompatível - parâmetros diferentes detectados")
                    console.print(f"⚠ [yellow]Não foi possível retomar - iniciando nova tradução[/yellow]")
            else:
                logger.info("Nenhum progresso anterior encontrado")
                if resume:
                    console.print(f"⚠ [yellow]Não foi possível retomar - iniciando nova tradução[/yellow]")
        else:
            logger.info("Modo de retomada desativado - iniciando nova tradução")
        
        # Extrai conteúdo se necessário
        if not existing_progress:
            console.print(f"📖 [cyan]Extraindo conteúdo de {input_file}...[/cyan]")
            logger.info("=== EXTRAINDO CONTEÚDO ===")
            logger.info(f"Arquivo de entrada: {input_file}")
            logger.debug(f"Formato override: {format_override}")
            
            try:
                extractor = ContentExtractorFactory.create_extractor(input_file, format_override)
                logger.info(f"Extrator criado: {type(extractor).__name__}")
                
                chapters = extractor.extract_content(input_file)
                logger.info(f"Extração concluída - {len(chapters) if chapters else 0} capítulos encontrados")
                
                if chapters:
                    total_chars = sum(len(ch.get('content', '')) for ch in chapters)
                    logger.info(f"Total de caracteres extraídos: {total_chars:,}")
                    
                    for i, chapter in enumerate(chapters):
                        title = chapter.get('title', f'Capítulo {i+1}')
                        content_length = len(chapter.get('content', ''))
                        logger.debug(f"Capítulo {i+1}: '{title}' - {content_length:,} caracteres")
                
            except Exception as e:
                logger.error(f"Erro durante extração: {e}")
                logger.debug(f"Traceback: {traceback.format_exc()}")
                raise
            
            if not chapters:
                logger.error("Nenhum conteúdo foi extraído do arquivo")
                console.print("✗ [red]Nenhum conteúdo encontrado no arquivo[/red]")
                return
            
            console.print(f"✓ [green]Extraídos {len(chapters)} capítulos/seções[/green]")
            logger.info("Extração de conteúdo concluída com sucesso")
            
            # Cria novo progresso
            progress_manager.create_progress(
                input_file=input_file,
                output_file=output_file,
                model=translation_config.model,
                target_language=translation_config.target_language,
                chapters=chapters
            )
            
            # Inicializa arquivo de saída se não existir
            if not output_manager.file_exists():
                book_title = Path(input_file).stem
                output_manager.initialize_file(f"Tradução: {book_title}")
        else:
            # Carrega capítulos do progresso existente
            console.print(f"📋 [cyan]Carregando capítulos do progresso salvo...[/cyan]")
            
            # Para retomar, precisamos reextrair os capítulos
            extractor = ContentExtractorFactory.create_extractor(input_file, format_override)
            chapters = extractor.extract_content(input_file)
        
        # Configura chunker
        logger.info("=== CONFIGURANDO CHUNKER ===")
        logger.debug(f"Chunk size inicial: {chunk_size}")
        logger.debug(f"Overlap size: {overlap_size}")
        
        chunker = TextChunker(
            chunk_size=chunk_size,
            overlap_size=overlap_size,
            preserve_sentences=True,
            preserve_paragraphs=True
        )
        logger.info("TextChunker criado com preservação de sentenças e parágrafos")
        
        # Ajusta chunk size para o modelo
        old_chunk_size = chunker.chunk_size
        chunker.adjust_chunk_size_for_model(translation_config.model)
        new_chunk_size = chunker.chunk_size
        
        if old_chunk_size != new_chunk_size:
            logger.info(f"Chunk size ajustado para modelo {translation_config.model}: {old_chunk_size} → {new_chunk_size}")
        else:
            logger.debug(f"Chunk size mantido: {chunk_size}")
        
        logger.info("Chunker configurado com sucesso")
        
        # Configura processador paralelo
        logger.info("=== CONFIGURANDO PROCESSADOR PARALELO ===")
        logger.debug(f"Max workers: {max_workers}")
        logger.debug(f"Rate limit: {rate_limit} req/s")
        
        processor = ParallelProcessor(
            translator_config=translation_config,
            chunker=chunker,
            progress_manager=progress_manager,
            output_manager=output_manager,
            max_workers=max_workers,
            rate_limit=rate_limit
        )
        logger.info("ParallelProcessor criado")
        
        # Cria workers
        console.print(f"⚙️ [cyan]Configurando {max_workers} workers...[/cyan]")
        logger.info(f"Criando {max_workers} workers...")
        
        try:
            await processor.create_workers(api_key)
            logger.info("Workers criados com sucesso")
        except Exception as e:
            logger.error(f"Erro ao criar workers: {e}")
            logger.debug(f"Traceback: {traceback.format_exc()}")
            raise
        
        # Configura display de progresso
        progress_display = ProgressDisplay()
        
        def progress_callback(worker_id: int, chapter_id: str, completed_chunks: int, total_chunks: int):
            progress_display.update_chapter_progress(worker_id, chapter_id, completed_chunks, total_chunks)
        
        # Inicia processamento
        logger.info("=== INICIANDO PROCESSAMENTO ===")
        total_chapters = len(chapters)
        logger.info(f"Total de capítulos para processar: {total_chapters}")
        
        progress_display.start_progress(total_chapters)
        progress_logger.log_start(input_file, output_file, translation_config.model, total_chapters)
        
        try:
            # Processa capítulos
            logger.info("Iniciando processamento de capítulos...")
            stats = await processor.process_chapters(
                chapters=chapters,
                progress_callback=progress_callback,
                resume=bool(existing_progress)
            )
            logger.info("Processamento de capítulos concluído")
            
            # Para display de progresso
            progress_display.stop_progress()
            
            # Consolida capítulos se necessário
            if save_chapters_separately:
                logger.info("=== CONSOLIDANDO CAPÍTULOS ===")
                console.print(f"\n📚 [cyan]Consolidando capítulos em arquivo único...[/cyan]")
                
                success = output_manager.consolidate_chapters_if_needed()
                if success:
                    # Mostra status dos capítulos
                    if chapter_manager:
                        status = chapter_manager.get_status()
                        console.print(f"✓ [green]{status['completed_chapters']} capítulos consolidados[/green]")
                        console.print(f"📁 [blue]Capítulos individuais em: {status['chapters_dir']}[/blue]")
                        
                        # Limpeza de arquivos se solicitado
                        if not keep_chapter_files:
                            console.print(f"🧹 [yellow]Removendo arquivos de capítulos individuais...[/yellow]")
                            chapter_manager.cleanup_temp_files(keep_chapters=False)
                            console.print(f"✓ [green]Arquivos temporários removidos[/green]")
                else:
                    console.print(f"⚠ [yellow]Erro durante consolidação - arquivo de saída pode estar incompleto[/yellow]")
            
            # Mostra estatísticas finais
            logger.info("=== TRADUÇÃO CONCLUÍDA ===")
            logger.info(f"Tempo total: {stats['total_time']:.1f}s")
            logger.info(f"Capítulos processados: {stats['total_chapters_processed']}")
            logger.info(f"Chunks processados: {stats['total_chunks_processed']}")
            logger.info(f"Erros: {stats['total_errors']}")
            logger.info(f"Workers utilizados: {stats['workers_used']}")
            logger.info(f"Tempo médio por capítulo: {stats['average_time_per_chapter']:.1f}s")
            
            console.print(f"\n[bold green]✅ Tradução Concluída![/bold green]")
            
            # Painel com estatísticas
            stats_content = f"""[bold]Tempo Total:[/bold] {stats['total_time']:.1f}s
[bold]Capítulos Processados:[/bold] {stats['total_chapters_processed']}
[bold]Chunks Processados:[/bold] {stats['total_chunks_processed']}
[bold]Erros:[/bold] {stats['total_errors']}
[bold]Workers Utilizados:[/bold] {stats['workers_used']}
[bold]Tempo Médio por Capítulo:[/bold] {stats['average_time_per_chapter']:.1f}s"""
            
            console.print(Panel(stats_content, title="Estatísticas", border_style="green"))
            
            console.print(f"\n📄 [green]Arquivo traduzido salvo em: {output_file}[/green]")
            console.print(f"📊 [blue]Log detalhado em: {get_log_file_path()}[/blue]")
            
            # Log estatísticas
            progress_logger.log_completion(
                stats['total_time'],
                stats['total_chapters_processed'],
                stats['total_chunks_processed']
            )
            progress_logger.log_stats(stats)
            
        except KeyboardInterrupt:
            logger.warning("Tradução interrompida pelo usuário")
            progress_display.stop_progress()
            console.print(f"\n[yellow]⏸️ Tradução interrompida pelo usuário[/yellow]")
            console.print(f"💾 [cyan]Progresso salvo em: {progress_file}[/cyan]")
            console.print(f"🔄 [cyan]Use --resume para continuar[/cyan]")
            
        except Exception as process_error:
            logger.error(f"Erro durante processamento: {process_error}")
            logger.debug(f"Traceback do processamento: {traceback.format_exc()}")
            progress_display.stop_progress()
            console.print(f"\n✗ [red]Erro durante processamento: {process_error}[/red]")
            raise
            
        finally:
            logger.info("Executando limpeza final...")
            await processor.cleanup()
            
            # Finaliza o ProgressManager para garantir que progresso seja salvo
            if 'progress_manager' in locals():
                progress_manager.finalize()
            
            logger.info("Limpeza concluída")
    
    except Exception as e:
        logger.error(f"Erro fatal na tradução: {e}")
        logger.error(f"Traceback completo: {traceback.format_exc()}")
        console.print(f"\n✗ [red]Erro fatal: {e}[/red]")
        progress_logger.log_error("Tradutor Principal", str(e))
        sys.exit(1)


if __name__ == '__main__':
    main()