#!/bin/bash
# Script Interativo do Tradutor de Livros
# Solicita informações do usuário e executa a tradução

set -e  # Para em caso de erro

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Função para imprimir com cor
print_color() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Função para validar arquivo
validate_file() {
    local file=$1
    if [[ ! -f "$file" ]]; then
        print_color $RED "❌ Arquivo não encontrado: $file"
        return 1
    fi
    return 0
}

# Função para validar extensão
validate_extension() {
    local file=$1
    local ext="${file##*.}"
    if [[ "$ext" != "epub" && "$ext" != "pdf" ]]; then
        print_color $RED "❌ Formato não suportado. Use arquivos .epub ou .pdf"
        return 1
    fi
    return 0
}

# Cabeçalho
clear
print_color $PURPLE "╔══════════════════════════════════════════════════════════╗"
print_color $PURPLE "║                                                          ║"
print_color $PURPLE "║           📚 TRADUTOR DE LIVROS INTERATIVO 🤖            ║"
print_color $PURPLE "║                                                          ║"
print_color $PURPLE "║    Tradução automática de EPUB/PDF usando IA            ║"
print_color $PURPLE "║                                                          ║"
print_color $PURPLE "╚══════════════════════════════════════════════════════════╝"
echo ""

# Ativa ambiente virtual
print_color $CYAN "🔧 Ativando ambiente virtual..."
if [[ -d "venv" ]]; then
    source venv/bin/activate
    print_color $GREEN "✅ Ambiente virtual ativado"
else
    print_color $RED "❌ Ambiente virtual não encontrado. Execute 'python -m venv venv' primeiro."
    exit 1
fi
echo ""

# 1. Arquivo de entrada
print_color $BLUE "📖 ARQUIVO DE ENTRADA"
print_color $YELLOW "Arquivos disponíveis no diretório atual:"
ls -la *.epub *.pdf 2>/dev/null || print_color $YELLOW "Nenhum arquivo EPUB/PDF encontrado no diretório atual"
echo ""

while true; do
    read -p "Digite o caminho do arquivo de entrada (EPUB ou PDF): " INPUT_FILE
    
    if validate_file "$INPUT_FILE" && validate_extension "$INPUT_FILE"; then
        print_color $GREEN "✅ Arquivo de entrada: $INPUT_FILE"
        break
    fi
done
echo ""

# 2. Arquivo de saída
print_color $BLUE "📝 ARQUIVO DE SAÍDA"
read -p "Digite o nome do arquivo de saída (ex: traducao.md): " OUTPUT_FILE

# Adiciona extensão .md se não fornecida
if [[ "$OUTPUT_FILE" != *.md ]]; then
    OUTPUT_FILE="${OUTPUT_FILE}.md"
fi

# Cria diretório se necessário
OUTPUT_DIR=$(dirname "$OUTPUT_FILE")
if [[ "$OUTPUT_DIR" != "." ]]; then
    mkdir -p "$OUTPUT_DIR"
    print_color $CYAN "📁 Diretório criado: $OUTPUT_DIR"
fi

print_color $GREEN "✅ Arquivo de saída: $OUTPUT_FILE"
echo ""

# 3. Modelo de IA
print_color $BLUE "🤖 MODELO DE IA"
print_color $YELLOW "Modelos populares:"
echo "1. openai/gpt-4-turbo (Recomendado)"
echo "2. openai/gpt-4"
echo "3. openai/gpt-5 (⚠️ força temperature=1.0)"
echo "4. anthropic/claude-3.5-sonnet"
echo "5. anthropic/claude-3-sonnet"
echo "6. google/gemini-1.5-pro"
echo "7. Outro (digite manualmente)"
echo ""

read -p "Escolha o modelo (1-7): " MODEL_CHOICE

case $MODEL_CHOICE in
    1) MODEL="openai/gpt-4-turbo" ;;
    2) MODEL="openai/gpt-4" ;;
    3) MODEL="openai/gpt-5" ;;
    4) MODEL="anthropic/claude-3.5-sonnet" ;;
    5) MODEL="anthropic/claude-3-sonnet" ;;
    6) MODEL="google/gemini-1.5-pro" ;;
    7) read -p "Digite o nome do modelo: " MODEL ;;
    *) MODEL="openai/gpt-4-turbo" ;;
esac

print_color $GREEN "✅ Modelo selecionado: $MODEL"
echo ""

# 4. Chave da API
print_color $BLUE "🔑 CHAVE DA API"
print_color $YELLOW "A chave da API será mantida segura e não será salva em arquivos."

# Verifica se já existe uma variável de ambiente
if [[ -n "$API_KEY" ]]; then
    print_color $CYAN "🔍 Chave da API encontrada na variável de ambiente"
    read -p "Usar a chave existente? (s/N): " USE_EXISTING
    if [[ "$USE_EXISTING" =~ ^[Ss]$ ]]; then
        print_color $GREEN "✅ Usando chave da API existente"
    else
        read -s -p "Digite sua chave da API: " API_KEY
        echo ""
    fi
else
    read -s -p "Digite sua chave da API: " API_KEY
    echo ""
fi

if [[ -z "$API_KEY" ]]; then
    print_color $RED "❌ Chave da API é obrigatória"
    exit 1
fi

print_color $GREEN "✅ Chave da API configurada"
echo ""

# 5. Idioma alvo
print_color $BLUE "🌍 IDIOMA DE TRADUÇÃO"
print_color $YELLOW "Idiomas populares:"
echo "1. pt-BR (Português Brasileiro)"
echo "2. pt-PT (Português Europeu)"
echo "3. en-US (Inglês Americano)"
echo "4. es-ES (Espanhol)"
echo "5. fr-FR (Francês)"
echo "6. de-DE (Alemão)"
echo "7. it-IT (Italiano)"
echo "8. Outro (digite manualmente)"
echo ""

read -p "Escolha o idioma (1-8): " LANG_CHOICE

case $LANG_CHOICE in
    1) TARGET_LANG="pt-BR" ;;
    2) TARGET_LANG="pt-PT" ;;
    3) TARGET_LANG="en-US" ;;
    4) TARGET_LANG="es-ES" ;;
    5) TARGET_LANG="fr-FR" ;;
    6) TARGET_LANG="de-DE" ;;
    7) TARGET_LANG="it-IT" ;;
    8) read -p "Digite o código do idioma (ex: ja-JP): " TARGET_LANG ;;
    *) TARGET_LANG="pt-BR" ;;
esac

print_color $GREEN "✅ Idioma alvo: $TARGET_LANG"
echo ""

# 6. Contexto personalizado
print_color $BLUE "📋 CONTEXTO PERSONALIZADO (Opcional)"
print_color $YELLOW "Arquivos de contexto disponíveis:"
ls -la *.txt 2>/dev/null || print_color $YELLOW "Nenhum arquivo .txt encontrado"
echo ""

read -p "Arquivo de contexto (opcional, deixe vazio para pular): " CONTEXT_FILE

CONTEXT_PARAM=""
if [[ -n "$CONTEXT_FILE" && -f "$CONTEXT_FILE" ]]; then
    CONTEXT_PARAM="--context-file $CONTEXT_FILE"
    print_color $GREEN "✅ Contexto: $CONTEXT_FILE"
elif [[ -n "$CONTEXT_FILE" ]]; then
    print_color $YELLOW "⚠️  Arquivo não encontrado, continuando sem contexto"
else
    print_color $CYAN "ℹ️  Continuando sem contexto personalizado"
fi
echo ""

# 7. Configurações avançadas
print_color $BLUE "⚙️ CONFIGURAÇÕES AVANÇADAS"
read -p "Usar configurações padrão? (S/n): " USE_DEFAULTS

if [[ "$USE_DEFAULTS" =~ ^[Nn]$ ]]; then
    echo ""
    read -p "Número de workers paralelos (padrão: 4): " MAX_WORKERS
    MAX_WORKERS=${MAX_WORKERS:-4}
    
    read -p "Limite de requisições por segundo (padrão: 2.0): " RATE_LIMIT
    RATE_LIMIT=${RATE_LIMIT:-2.0}
    
    read -p "Tamanho do chunk em caracteres (padrão: 4000): " CHUNK_SIZE
    CHUNK_SIZE=${CHUNK_SIZE:-4000}
    
    read -p "Temperatura (0.0-2.0, padrão: 0.3): " TEMPERATURE
    TEMPERATURE=${TEMPERATURE:-0.3}
    
    read -p "Timeout em segundos (padrão: 60): " TIMEOUT
    TIMEOUT=${TIMEOUT:-60}
else
    MAX_WORKERS=4
    RATE_LIMIT=2.0
    CHUNK_SIZE=4000
    TEMPERATURE=0.3
    TIMEOUT=60
fi

print_color $GREEN "✅ Configurações:"
print_color $CYAN "   Workers: $MAX_WORKERS"
print_color $CYAN "   Rate Limit: $RATE_LIMIT/s"
print_color $CYAN "   Chunk Size: $CHUNK_SIZE chars"
print_color $CYAN "   Temperatura: $TEMPERATURE"
print_color $CYAN "   Timeout: ${TIMEOUT}s"
echo ""

# 8. Resumo e confirmação
print_color $PURPLE "╔══════════════════════════════════════════════════════════╗"
print_color $PURPLE "║                      📋 RESUMO                           ║"
print_color $PURPLE "╚══════════════════════════════════════════════════════════╝"
print_color $CYAN "📖 Entrada: $INPUT_FILE"
print_color $CYAN "📝 Saída: $OUTPUT_FILE"
print_color $CYAN "🤖 Modelo: $MODEL"
print_color $CYAN "🌍 Idioma: $TARGET_LANG"
[[ -n "$CONTEXT_PARAM" ]] && print_color $CYAN "📋 Contexto: $CONTEXT_FILE"
print_color $CYAN "⚙️  Workers: $MAX_WORKERS | Rate: $RATE_LIMIT/s | Temp: $TEMPERATURE"
echo ""

read -p "Confirma a execução? (S/n): " CONFIRM
if [[ "$CONFIRM" =~ ^[Nn]$ ]]; then
    print_color $YELLOW "❌ Execução cancelada pelo usuário"
    exit 0
fi

# 9. Teste de conexão
print_color $BLUE "🔍 TESTANDO CONEXÃO..."
python tradutor.py --test-connection --model "$MODEL" --api-key "$API_KEY"

if [[ $? -ne 0 ]]; then
    print_color $RED "❌ Falha na conexão. Verifique sua API key e modelo."
    read -p "Continuar mesmo assim? (s/N): " FORCE_CONTINUE
    if [[ ! "$FORCE_CONTINUE" =~ ^[Ss]$ ]]; then
        exit 1
    fi
fi
echo ""

# 10. Construção do comando
COMMAND="python tradutor.py \
  --input \"$INPUT_FILE\" \
  --output-md \"$OUTPUT_FILE\" \
  --model \"$MODEL\" \
  --target-lang \"$TARGET_LANG\" \
  --max-workers $MAX_WORKERS \
  --rate-limit $RATE_LIMIT \
  --chunk-size $CHUNK_SIZE \
  --temperature $TEMPERATURE \
  --timeout $TIMEOUT \
  --api-key \"$API_KEY\""

# Adiciona contexto se especificado  
if [[ -n "$CONTEXT_PARAM" ]]; then
    COMMAND="$COMMAND $CONTEXT_PARAM"
fi

# 11. Execução
print_color $PURPLE "╔══════════════════════════════════════════════════════════╗"
print_color $PURPLE "║                 🚀 INICIANDO TRADUÇÃO                    ║"
print_color $PURPLE "╚══════════════════════════════════════════════════════════╝"
print_color $YELLOW "Comando que será executado:"
print_color $CYAN "$COMMAND"
echo ""

print_color $GREEN "🚀 Iniciando tradução..."
print_color $YELLOW "💡 Dica: Use Ctrl+C para pausar (progresso será salvo)"
echo ""

# Executa o comando
eval $COMMAND

# 12. Finalização
EXIT_CODE=$?
echo ""

if [[ $EXIT_CODE -eq 0 ]]; then
    print_color $PURPLE "╔══════════════════════════════════════════════════════════╗"
    print_color $PURPLE "║                  ✅ TRADUÇÃO CONCLUÍDA!                  ║"
    print_color $PURPLE "╚══════════════════════════════════════════════════════════╝"
    print_color $GREEN "📄 Arquivo traduzido: $OUTPUT_FILE"
    print_color $GREEN "📊 Logs disponíveis em: logs/"
    
    if [[ -f "$OUTPUT_FILE" ]]; then
        FILE_SIZE=$(du -h "$OUTPUT_FILE" | cut -f1)
        print_color $CYAN "📏 Tamanho do arquivo: $FILE_SIZE"
    fi
elif [[ $EXIT_CODE -eq 130 ]]; then
    print_color $YELLOW "⏸️  Tradução pausada pelo usuário"
    print_color $CYAN "💾 Progresso salvo em: ${OUTPUT_FILE}.progress.json"
    print_color $CYAN "🔄 Para retomar, execute novamente este script com os mesmos parâmetros"
else
    print_color $RED "❌ Erro durante a tradução (Código: $EXIT_CODE)"
    print_color $CYAN "📊 Verifique os logs em: logs/"
fi

echo ""
print_color $PURPLE "Obrigado por usar o Tradutor de Livros! 📚🤖"