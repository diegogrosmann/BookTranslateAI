"""
Sistema de logging configurável com saída para arquivo e terminal limpo.
"""
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


class ColoredFormatter(logging.Formatter):
    """Formatter com cores para o terminal."""
    
    # Códigos de cor ANSI
    COLORS = {
        'DEBUG': '\033[36m',      # Ciano
        'INFO': '\033[32m',       # Verde
        'WARNING': '\033[33m',    # Amarelo
        'ERROR': '\033[31m',      # Vermelho
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }
    
    def format(self, record):
        """Formata o log com cores."""
        # Aplica cor baseada no nível
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        record.levelname = f"{color}{record.levelname}{self.COLORS['RESET']}"
        
        return super().format(record)


class CleanTerminalHandler(logging.Handler):
    """Handler que mostra apenas mensagens essenciais no terminal."""
    
    def __init__(self, show_debug: bool = False):
        """
        Inicializa o handler.
        
        Args:
            show_debug: Se True, mostra mensagens DEBUG no terminal
        """
        super().__init__()
        self.show_debug = show_debug
        self.last_message = ""
    
    def emit(self, record):
        """Emite log apenas para mensagens importantes."""
        # Define quais mensagens mostrar no terminal
        show_in_terminal = False
        
        if record.levelno >= logging.ERROR:
            # Sempre mostra erros
            show_in_terminal = True
        elif record.levelno >= logging.WARNING:
            # Mostra warnings importantes
            show_in_terminal = True
        elif record.levelno >= logging.INFO:
            # Mostra apenas infos específicos
            message = record.getMessage()
            important_keywords = [
                'iniciado', 'completado', 'concluído', 'criado', 'carregado',
                'testada', 'estabelecida', 'tradução', 'processamento',
                'capítulos', 'chunks', 'erro', 'falha'
            ]
            
            if any(keyword in message.lower() for keyword in important_keywords):
                show_in_terminal = True
        elif record.levelno >= logging.DEBUG and self.show_debug:
            # Mostra debug apenas se habilitado
            show_in_terminal = True
        
        if show_in_terminal:
            try:
                message = self.format(record)
                # Evita mensagens duplicadas consecutivas
                if message != self.last_message:
                    print(message, file=sys.stderr)
                    self.last_message = message
            except Exception:
                self.handleError(record)


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    clean_terminal: bool = True,
    show_debug_in_terminal: bool = False
) -> None:
    """
    Configura o sistema de logging.
    
    Args:
        log_level: Nível de log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Caminho para arquivo de log (opcional)
        clean_terminal: Se True, mostra apenas mensagens essenciais no terminal
        show_debug_in_terminal: Se True, mostra mensagens DEBUG no terminal
    """
    # Converte string para nível
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Remove handlers existentes
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Configura formato para arquivo (completo)
    file_formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Configura formato para terminal (simplificado)
    if clean_terminal:
        terminal_formatter = logging.Formatter(
            fmt='%(levelname)s: %(message)s'
        )
    else:
        terminal_formatter = ColoredFormatter(
            fmt='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
    
    # Handler para arquivo (se especificado)
    if log_file:
        # Cria diretório se não existir
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)  # Arquivo sempre em DEBUG
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
    
    # Handler para terminal
    if clean_terminal:
        terminal_handler = CleanTerminalHandler(show_debug_in_terminal)
        terminal_handler.setFormatter(terminal_formatter)
    else:
        terminal_handler = logging.StreamHandler(sys.stderr)
        terminal_handler.setFormatter(terminal_formatter)
    
    terminal_handler.setLevel(numeric_level)
    root_logger.addHandler(terminal_handler)
    
    # Define nível global
    root_logger.setLevel(logging.DEBUG)  # Sempre DEBUG para capturar tudo
    
    # Configura loggers de bibliotecas externas para serem menos verbosos
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    
    # Configuração específica para LiteLLM
    litellm_level = logging.WARNING if numeric_level >= logging.WARNING else logging.INFO
    logging.getLogger('litellm').setLevel(litellm_level)
    logging.getLogger('LiteLLM').setLevel(litellm_level)
    
    # Configuração adicional para controlar o verbose do LiteLLM
    try:
        import litellm
        if numeric_level >= logging.WARNING:
            litellm.set_verbose = False
            # Força nível de log interno do LiteLLM
            os.environ['LITELLM_LOG'] = 'WARNING'
        else:
            litellm.set_verbose = True
            os.environ['LITELLM_LOG'] = 'INFO'
    except ImportError:
        pass
    
    # Log inicial
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configurado - Nível: {log_level}, Arquivo: {log_file or 'Nenhum'}")


def get_log_file_path(base_name: str = "tradutor") -> str:
    """
    Gera caminho para arquivo de log com timestamp.
    
    Args:
        base_name: Nome base do arquivo
        
    Returns:
        Caminho completo para o arquivo de log
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{base_name}_{timestamp}.log"
    
    # Usa diretório logs na raiz do projeto
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    return str(log_dir / filename)


class ProgressLogger:
    """Logger especializado para progresso de tradução."""
    
    def __init__(self, name: str = "progress"):
        """
        Inicializa o logger de progresso.
        
        Args:
            name: Nome do logger
        """
        self.logger = logging.getLogger(name)
    
    def log_start(self, input_file: str, output_file: str, model: str, total_chapters: int):
        """Log do início da tradução."""
        self.logger.info(
            f"Iniciando tradução: {input_file} -> {output_file} "
            f"usando {model} ({total_chapters} capítulos)"
        )
    
    def log_chapter_start(self, chapter_title: str, worker_id: int):
        """Log do início de um capítulo."""
        self.logger.info(f"Worker {worker_id}: Iniciando '{chapter_title}'")
    
    def log_chapter_complete(self, chapter_title: str, worker_id: int, time_taken: float):
        """Log da conclusão de um capítulo."""
        self.logger.info(
            f"Worker {worker_id}: Completado '{chapter_title}' em {time_taken:.1f}s"
        )
    
    def log_chunk_progress(self, chapter_id: str, completed: int, total: int):
        """Log do progresso de chunks."""
        percentage = (completed / total) * 100 if total > 0 else 0
        self.logger.debug(f"Capítulo {chapter_id}: {completed}/{total} chunks ({percentage:.1f}%)")
    
    def log_error(self, context: str, error: str):
        """Log de erro."""
        self.logger.error(f"{context}: {error}")
    
    def log_completion(self, total_time: float, chapters_processed: int, chunks_processed: int):
        """Log da conclusão geral."""
        self.logger.info(
            f"Tradução concluída em {total_time:.1f}s: "
            f"{chapters_processed} capítulos, {chunks_processed} chunks processados"
        )
    
    def log_resume(self, pending_chapters: int):
        """Log de retomada."""
        self.logger.info(f"Retomando tradução: {pending_chapters} capítulos pendentes")
    
    def log_stats(self, stats: dict):
        """Log de estatísticas detalhadas."""
        self.logger.info("Estatísticas finais:")
        for key, value in stats.items():
            if isinstance(value, dict):
                self.logger.info(f"  {key}:")
                for sub_key, sub_value in value.items():
                    self.logger.info(f"    {sub_key}: {sub_value}")
            else:
                self.logger.info(f"  {key}: {value}")


# Instância global para facilitar uso
progress_logger = ProgressLogger()