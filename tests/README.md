# Arquivo README para os testes do projeto Tradutor

## Testes do Projeto Tradutor

Este diretório contém a suíte completa de testes para o sistema de tradução de livros usando IA.

### Estrutura dos Testes

```
tests/
├── __init__.py              # Inicialização do pacote de testes
├── conftest.py              # Configurações e fixtures compartilhadas
├── test_chunker.py          # Testes para fragmentação de texto
├── test_extractors.py       # Testes para extração de arquivos
├── test_translator.py       # Testes para sistema de tradução
├── test_parallel.py         # Testes para processamento paralelo
├── test_progress.py         # Testes para controle de progresso
├── test_logging_config.py   # Testes para sistema de logging
└── coverage_html/           # Relatórios de cobertura (gerado)
```

### Tipos de Testes

#### 🔧 Testes Unitários
- Testam funções e classes individuais
- Executam rapidamente
- Usam mocks para dependências externas
- Cobrem casos de borda e tratamento de erros

#### 🔗 Testes de Integração  
- Testam interação entre módulos
- Simulam fluxos completos do sistema
- Verificam comportamento end-to-end
- Podem ser mais lentos

#### ⚡ Testes Assíncronos
- Testam funções async/await
- Verificam processamento paralelo
- Testam rate limiting e timeouts

### Como Executar

#### Opção 1: Script Bash (Linux/Mac)
```bash
# Todos os testes
./run_tests.sh

# Apenas testes unitários
./run_tests.sh unit

# Testes de integração
./run_tests.sh integration

# Testes específicos
./run_tests.sh specific test_chunker.py

# Com cobertura
./run_tests.sh coverage

# Instalar dependências
./run_tests.sh install
```

#### Opção 2: Script Python (Multiplataforma)
```bash
# Todos os testes
python run_tests.py

# Apenas testes unitários  
python run_tests.py unit

# Testes específicos
python run_tests.py specific test_chunker.py

# Com cobertura
python run_tests.py coverage
```

#### Opção 3: Pytest Direto
```bash
# Todos os testes
pytest tests/

# Testes específicos
pytest tests/test_chunker.py

# Com cobertura
pytest tests/ --cov=src --cov-report=html

# Apenas testes rápidos
pytest tests/ -m "not slow"

# Verbose com traceback curto
pytest tests/ -v --tb=short
```

### Fixtures Disponíveis

Definidas em `conftest.py`:

- `temp_dir`: Diretório temporário para testes
- `sample_text`: Texto de exemplo para testes
- `sample_chapters`: Lista de capítulos exemplo
- `mock_epub_book`: Mock de livro EPUB
- `mock_translation_response`: Mock de resposta de tradução

### Marcadores Personalizados

- `@pytest.mark.slow`: Testes que demoram para executar
- `@pytest.mark.integration`: Testes de integração
- `@pytest.mark.unit`: Testes unitários
- `@pytest.mark.asyncio`: Testes assíncronos

### Cobertura de Código

Meta: **≥ 80% de cobertura**

Relatórios gerados em:
- Terminal: Sumário com linhas faltantes
- HTML: `tests/coverage_html/index.html`
- XML: `tests/coverage.xml` (para CI/CD)

### Configuração

#### pytest.ini
Configurações principais do pytest:
- Diretórios de teste
- Padrões de nomenclatura
- Marcadores personalizados
- Configurações de cobertura
- Filtros de warnings

#### requirements.txt
Dependências de teste adicionadas:
- pytest>=7.4.0
- pytest-asyncio>=0.21.0
- pytest-mock>=3.11.0
- pytest-cov>=4.1.0

### Boas Práticas Implementadas

#### ✅ Estrutura dos Testes
- Classes de teste por módulo/funcionalidade
- Métodos de teste descritivos
- Setup/teardown adequados
- Isolamento entre testes

#### ✅ Testes Robustos
- Mocking de dependências externas
- Testes de casos de erro
- Validação de edge cases
- Cleanup automático

#### ✅ Legibilidade
- Nomes descritivos
- Comentários explicativos
- Fixtures reutilizáveis
- Assertions claras

#### ✅ Performance
- Testes rápidos por padrão
- Marcação de testes lentos
- Execução paralela quando possível
- Cleanup eficiente

### Troubleshooting

#### Problema: Imports não funcionam
```bash
# Solução: Adicionar src ao PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:./src"
pytest tests/
```

#### Problema: Testes assíncronos falham
```bash
# Solução: Instalar pytest-asyncio
pip install pytest-asyncio
```

#### Problema: Cobertura baixa
```bash
# Solução: Ver relatório detalhado
pytest tests/ --cov=src --cov-report=html
# Abrir tests/coverage_html/index.html
```

#### Problema: Testes lentos
```bash
# Solução: Executar apenas testes rápidos
pytest tests/ -m "not slow"
```

### Integração CI/CD

Os testes estão preparados para integração com sistemas de CI/CD:

```yaml
# Exemplo GitHub Actions
- name: Run tests
  run: |
    pip install -r requirements.txt
    pytest tests/ --cov=src --cov-report=xml
    
- name: Upload coverage
  uses: codecov/codecov-action@v1
  with:
    file: ./tests/coverage.xml
```

### Contribuindo

Ao adicionar novos módulos:

1. Criar arquivo `test_novo_modulo.py`
2. Seguir padrão de nomenclatura
3. Adicionar fixtures necessárias ao `conftest.py`
4. Marcar testes apropriadamente
5. Verificar cobertura ≥ 80%
6. Executar toda suíte antes de commit

### Estatísticas

- **Módulos testados**: 6
- **Arquivos de teste**: 6
- **Cobertura alvo**: ≥ 80%
- **Tipos de teste**: Unit, Integration, Async
- **Fixtures**: 5+ compartilhadas
- **Scripts de execução**: 2 (bash + python)