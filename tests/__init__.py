# Arquivo __init__.py para o diretório de testes
# Este arquivo permite que Python reconheça o diretório tests como um pacote

"""
Suíte de testes para o projeto Tradutor.

Este pacote contém testes abrangentes para todos os módulos do sistema:

- test_chunker.py: Testes para fragmentação de texto
- test_extractors.py: Testes para extração de conteúdo de arquivos
- test_translator.py: Testes para tradução usando LLMs
- test_parallel.py: Testes para processamento paralelo
- test_progress.py: Testes para sistema de progresso e persistência
- test_logging_config.py: Testes para configuração de logging

Para executar todos os testes:
    pytest tests/

Para executar testes específicos:
    pytest tests/test_chunker.py

Para executar com cobertura:
    pytest tests/ --cov=src --cov-report=html
"""

__version__ = "1.0.0"
__author__ = "Tradutor Project"