# Configuração de testes para o projeto Tradutor
# Este arquivo configura o pytest e disponibiliza fixtures comuns

import os
import sys
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch

# Adiciona o diretório src ao path para importações
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


@pytest.fixture
def temp_dir():
    """Cria um diretório temporário para testes."""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def sample_text():
    """Texto de exemplo para testes."""
    return """
    Capítulo 1: O Início da Jornada
    
    Era uma vez, em uma terra distante, um jovem herói chamado Rand al'Thor. 
    Ele vivia em uma pequena vila chamada Emond's Field, onde os dias passavam 
    tranquilamente até que eventos extraordinários mudaram sua vida para sempre.
    
    O vento não era um início. Não existem inícios ou fins na roda do tempo. 
    Mas aquele era um início.
    
    Mat Cauthon e Perrin Aybara eram seus melhores amigos desde a infância. 
    Juntos, eles enfrentariam perigos inimagináveis e descobririam poderes 
    que mudariam o destino do mundo.
    """.strip()


@pytest.fixture
def sample_chapters():
    """Lista de capítulos de exemplo para testes."""
    return [
        {
            'id': 'cap1',
            'title': 'Capítulo 1: O Início',
            'content': 'Era uma vez um jovem herói. Ele tinha um destino grandioso.'
        },
        {
            'id': 'cap2', 
            'title': 'Capítulo 2: A Jornada',
            'content': 'A jornada começou com um passo. Depois outro. E mais outro.'
        },
        {
            'id': 'cap3',
            'title': 'Capítulo 3: O Destino',
            'content': 'O destino aguardava. O herói estava pronto para enfrentá-lo.'
        }
    ]


@pytest.fixture
def mock_epub_book():
    """Mock de um livro EPUB para testes."""
    import ebooklib
    
    mock_book = Mock()
    
    # Mock items do EPUB
    mock_item1 = Mock()
    mock_item1.get_type.return_value = ebooklib.ITEM_DOCUMENT  # Valor correto: 9
    mock_item1.get_content.return_value = b'''
    <!DOCTYPE html>
    <html>
    <head><title>Chapter 1</title></head>
    <body>
        <h1>Chapter 1: The Beginning</h1>
        <p>This is the first chapter of our story.</p>
        <p>It was a dark and stormy night...</p>
    </body>
    </html>
    '''
    mock_item1.get_name.return_value = 'chapter1.xhtml'
    mock_item1.get_id.return_value = 'ch1'
    
    mock_item2 = Mock()
    mock_item2.get_type.return_value = ebooklib.ITEM_DOCUMENT  # Valor correto: 9
    mock_item2.get_content.return_value = b'''
    <!DOCTYPE html>
    <html>
    <body>
        <h2>Chapter 2: The Journey</h2>
        <p>The journey begins here.</p>
    </body>
    </html>
    '''
    mock_item2.get_name.return_value = 'chapter2.xhtml'
    mock_item2.get_id.return_value = 'ch2'
    
    mock_book.get_items.return_value = [mock_item1, mock_item2]
    return mock_book


@pytest.fixture
def mock_translation_response():
    """Mock de resposta de tradução da API."""
    return {
        'choices': [{
            'message': {
                'content': 'Este é o texto traduzido para português.'
            }
        }],
        'usage': {
            'prompt_tokens': 100,
            'completion_tokens': 50,
            'total_tokens': 150
        }
    }


# Configuração global do pytest
def pytest_configure(config):
    """Configuração global do pytest."""
    # Suprime warnings específicos se necessário
    import warnings
    warnings.filterwarnings("ignore", category=DeprecationWarning)