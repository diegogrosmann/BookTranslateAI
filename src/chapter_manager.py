"""
Gerenciador de capítulos individuais - salva cada capítulo em arquivo separado.
"""

import logging
import os
import re
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ChapterFile:
    """Informações de um arquivo de capítulo."""

    chapter_number: int
    chapter_id: str
    title: str
    filename: str
    filepath: str
    completed: bool = False


class ChapterFileManager:
    """Gerenciador para salvar capítulos em arquivos separados."""

    def __init__(self, output_dir: str, book_title: str = "Traducao"):
        """
        Inicializa o gerenciador de arquivos de capítulos.

        Args:
            output_dir: Diretório onde os capítulos serão salvos
            book_title: Título do livro (usado para nomeação)
        """
        self.output_dir = Path(output_dir)
        self.book_title = self._sanitize_filename(book_title)
        self.chapters_dir = self.output_dir / "chapters"
        self._lock = threading.Lock()
        self.chapter_files: dict[str, ChapterFile] = {}

        # Cria diretórios se não existirem
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.chapters_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"ChapterFileManager inicializado - Diretório: {self.chapters_dir}")

    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitiza nome de arquivo removendo caracteres inválidos.

        Args:
            filename: Nome original

        Returns:
            Nome sanitizado
        """
        # Remove ou substitui caracteres inválidos
        sanitized = re.sub(r'[<>:"/\\|?*]', "_", filename)
        # Remove espaços múltiplos e substitui por _
        sanitized = re.sub(r"\s+", "_", sanitized)
        # Remove caracteres de controle
        sanitized = "".join(char for char in sanitized if ord(char) >= 32)
        # Limita tamanho
        return sanitized[:100] if sanitized else "Sem_Titulo"

    def register_chapter(
        self, chapter_number: int, chapter_id: str, title: str
    ) -> ChapterFile:
        """
        Registra um capítulo para salvamento.

        Args:
            chapter_number: Número do capítulo (para ordenação)
            chapter_id: ID único do capítulo
            title: Título do capítulo

        Returns:
            Objeto ChapterFile criado
        """
        with self._lock:
            sanitized_title = self._sanitize_filename(title)
            filename = f"{chapter_number:03d}_{sanitized_title}.md"
            filepath = str(self.chapters_dir / filename)

            chapter_file = ChapterFile(
                chapter_number=chapter_number,
                chapter_id=chapter_id,
                title=title,
                filename=filename,
                filepath=filepath,
            )

            self.chapter_files[chapter_id] = chapter_file
            logger.debug(
                f"Capítulo registrado: {chapter_number} - {title} -> {filename}"
            )

            return chapter_file

    def save_chapter(self, chapter_id: str, translated_content: str) -> bool:
        """
        Salva um capítulo traduzido em arquivo individual.

        Args:
            chapter_id: ID do capítulo
            translated_content: Conteúdo traduzido

        Returns:
            True se salvamento foi bem-sucedido
        """
        if chapter_id not in self.chapter_files:
            logger.error(f"Capítulo não registrado: {chapter_id}")
            return False

        chapter_file = self.chapter_files[chapter_id]

        with self._lock:
            try:
                # Conteúdo do arquivo com metadados
                file_content = f"""# {chapter_file.title}

*Capítulo {chapter_file.chapter_number} - Traduzido automaticamente*

---

{translated_content}
"""

                # Salva o arquivo
                with open(chapter_file.filepath, "w", encoding="utf-8") as f:
                    f.write(file_content)

                chapter_file.completed = True
                logger.info(f"Capítulo salvo: {chapter_file.filename}")
                return True

            except Exception as e:
                logger.error(f"Erro ao salvar capítulo {chapter_id}: {e}")
                return False

    def get_completed_chapters(self) -> list[ChapterFile]:
        """
        Retorna lista de capítulos completados ordenados por número.

        Returns:
            Lista ordenada de ChapterFile completados
        """
        with self._lock:
            completed = [cf for cf in self.chapter_files.values() if cf.completed]
            return sorted(completed, key=lambda x: x.chapter_number)

    def consolidate_chapters(self, final_output_file: str) -> bool:
        """
        Consolida todos os capítulos em um arquivo único.

        Args:
            final_output_file: Caminho para o arquivo final

        Returns:
            True se consolidação foi bem-sucedida
        """
        completed_chapters = self.get_completed_chapters()

        if not completed_chapters:
            logger.warning("Nenhum capítulo completado encontrado para consolidação")
            return False

        try:
            # Cria diretório de saída se não existir
            os.makedirs(os.path.dirname(final_output_file), exist_ok=True)

            with open(final_output_file, "w", encoding="utf-8") as output_file:
                # Cabeçalho do arquivo final
                output_file.write(
                    f"""# {self.book_title}

*Traduzido automaticamente*

---

"""
                )

                # Lê e escreve cada capítulo
                for chapter_file in completed_chapters:
                    logger.debug(f"Consolidando capítulo: {chapter_file.filename}")

                    try:
                        with open(chapter_file.filepath, encoding="utf-8") as chapter_f:
                            chapter_content = chapter_f.read()

                        # Remove cabeçalho individual e adiciona separador
                        lines = chapter_content.split("\n")
                        # Pula as primeiras linhas até encontrar o separador ---
                        content_start = 0
                        for i, line in enumerate(lines):
                            if line.strip() == "---":
                                content_start = i + 1
                                break

                        chapter_text = "\n".join(lines[content_start:]).strip()

                        # Adiciona ao arquivo final
                        output_file.write(
                            f"""
## {chapter_file.title}

{chapter_text}

---

"""
                        )

                    except Exception as e:
                        logger.error(
                            f"Erro ao ler capítulo {chapter_file.filename}: {e}"
                        )
                        continue

            logger.info(
                f"Consolidação concluída: {len(completed_chapters)} capítulos → {final_output_file}"
            )
            return True

        except Exception as e:
            logger.error(f"Erro durante consolidação: {e}")
            return False

    def get_status(self) -> dict[str, Any]:
        """
        Retorna status atual do gerenciador.

        Returns:
            Dicionário com informações de status
        """
        with self._lock:
            total_chapters = len(self.chapter_files)
            completed_chapters = sum(
                1 for cf in self.chapter_files.values() if cf.completed
            )

            return {
                "total_chapters": total_chapters,
                "completed_chapters": completed_chapters,
                "pending_chapters": total_chapters - completed_chapters,
                "chapters_dir": str(self.chapters_dir),
                "output_dir": str(self.output_dir),
            }

    def cleanup_temp_files(self, keep_chapters: bool = True) -> None:
        """
        Limpa arquivos temporários se necessário.

        Args:
            keep_chapters: Se False, remove arquivos de capítulos individuais
        """
        if not keep_chapters:
            try:
                for chapter_file in self.chapter_files.values():
                    if os.path.exists(chapter_file.filepath):
                        os.remove(chapter_file.filepath)
                        logger.debug(f"Arquivo removido: {chapter_file.filename}")

                # Remove diretório se estiver vazio
                if self.chapters_dir.exists() and not any(self.chapters_dir.iterdir()):
                    self.chapters_dir.rmdir()
                    logger.debug(f"Diretório removido: {self.chapters_dir}")

            except Exception as e:
                logger.warning(f"Erro durante limpeza: {e}")
