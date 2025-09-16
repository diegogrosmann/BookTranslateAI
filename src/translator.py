"""Cliente de Tradução usando LiteLLM.

Este módulo fornece um cliente unificado para tradução de texto usando 
múltiplos provedores de IA através da biblioteca LiteLLM.

O cliente suporta:
    - Múltiplos provedores (OpenAI, Anthropic, Google, Cohere, etc.)
    - Configuração automática de chaves de API
    - Retry automático com backoff exponencial
    - Logging detalhado de requisições e respostas
    - Configuração flexível de prompt e contexto
    - Processamento de chunks de texto em lote

Classes:
    TranslationConfig: Configurações para tradução
    TranslationClient: Cliente principal para tradução

Example:
    Uso básico do cliente de tradução:
    
    >>> config = TranslationConfig(
    ...     model="gpt-3.5-turbo",
    ...     target_language="pt-BR",
    ...     context="Livro de ficção científica"
    ... )
    >>> client = TranslationClient(config, api_key="sua-chave-aqui")
    >>> 
    >>> # Teste de conexão
    >>> success, message = await client.test_connection()
    >>> if success:
    ...     translated = await client.translate_text("Hello, world!")
    ...     print(translated)  # "Olá, mundo!"

Note:
    Requer configuração adequada das chaves de API dos provedores.
    Consulte a documentação do LiteLLM para detalhes específicos.
"""
import os
import logging
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
import json

import litellm
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type


logger = logging.getLogger(__name__)
translation_logger = logging.getLogger('translation_requests')


@dataclass
class TranslationConfig:
    """Configurações para o cliente de tradução.
    
    Esta classe encapsula todas as configurações necessárias para 
    personalizar o comportamento do cliente de tradução.
    
    Attributes:
        model: Nome do modelo de IA a ser usado (ex: "gpt-3.5-turbo")
        target_language: Idioma alvo para tradução (ex: "pt-BR", "en", "es")
        context: Contexto adicional sobre o conteúdo sendo traduzido
        custom_instructions: Instruções específicas para o tradutor
        
    Example:
        >>> config = TranslationConfig(
        ...     model="claude-3-sonnet",
        ...     target_language="pt-BR",
        ...     context="Romance histórico ambientado no século XIX",
        ...     custom_instructions="Mantenha o tom formal e eloquente"
        ... )
    """
    model: str
    target_language: str = "pt-BR"
    context: str = ""
    custom_instructions: str = ""


class TranslationClient:
    """Cliente unificado para tradução usando LiteLLM.
    
    Esta classe fornece uma interface consistente para tradução de texto
    usando diferentes provedores de IA através do LiteLLM. Inclui recursos
    avançados como retry automático, logging detalhado e configuração
    flexível de prompts.
    
    Attributes:
        config: Configurações de tradução
        api_key: Chave da API do provedor (opcional)
        
    Methods:
        test_connection: Testa conectividade com o provedor
        translate_text: Traduz um texto individual
        translate_chunks: Traduz múltiplos chunks em lote
        get_model_info: Retorna informações do modelo configurado
        list_available_models: Lista modelos suportados (estático)
        
    Example:
        >>> config = TranslationConfig(model="gpt-4", target_language="pt-BR")
        >>> client = TranslationClient(config)
        >>> 
        >>> # Verifica conexão
        >>> success, msg = await client.test_connection()
        >>> 
        >>> # Traduz texto
        >>> if success:
        ...     result = await client.translate_text("Hello world")
        ...     print(result)  # "Olá mundo"
    """
    
    def __init__(self, config: TranslationConfig, api_key: Optional[str] = None):
        """
        Inicializa o cliente de tradução.
        
        Args:
            config: Configurações de tradução
            api_key: Chave da API (opcional, pode usar variável de ambiente)
        """
        self.config = config
        self.api_key = api_key
        
        # Configura chave da API se fornecida
        if api_key:
            # LiteLLM pode usar diferentes variáveis de ambiente
            self._set_api_key(api_key)
        
        # Configura LiteLLM
        litellm.set_verbose = False  # Evita logs desnecessários no terminal
        litellm.drop_params = True   # Ignora parâmetros não suportados pelos modelos
        
        # Configuração adicional para suprimir logs verbosos
        import logging
        current_level = logging.getLogger().getEffectiveLevel()
        if current_level >= logging.WARNING:
            litellm.set_verbose = False
            os.environ['LITELLM_LOG'] = 'WARNING'
        
        logger.info(f"Cliente de tradução inicializado para modelo: {self.config.model}")
    
    def _set_api_key(self, api_key: str) -> None:
        """Define a chave da API baseada no provedor."""
        model_lower = self.config.model.lower()
        
        if 'openai' in model_lower or 'gpt' in model_lower:
            os.environ['OPENAI_API_KEY'] = api_key
        elif 'anthropic' in model_lower or 'claude' in model_lower:
            os.environ['ANTHROPIC_API_KEY'] = api_key
        elif 'google' in model_lower or 'gemini' in model_lower:
            os.environ['GOOGLE_API_KEY'] = api_key
        elif 'cohere' in model_lower:
            os.environ['COHERE_API_KEY'] = api_key
        else:
            # Para outros provedores, tenta algumas variáveis comuns
            os.environ['API_KEY'] = api_key
            os.environ['LITELLM_API_KEY'] = api_key
    
    async def test_connection(self) -> Tuple[bool, str]:
        """
        Testa a conexão com o provedor de IA.
        
        Returns:
            Tupla (sucesso, mensagem)
        """
        logger.info("=== TESTE DE CONEXÃO ===")
        logger.info(f"Modelo: {self.config.model}")
        logger.debug("Enviando mensagem de teste...")
        
        try:
            test_messages = [
                {"role": "user", "content": "Test connection. Please respond with 'OK'."}
            ]
            
            # Log parâmetros da requisição de teste
            logger.debug(f"Parâmetros do teste: model={self.config.model}")
            
            response = await litellm.acompletion(
                model=self.config.model,
                messages=test_messages
            )
            
            if response and response.choices:
                response_text = response.choices[0].message.content.strip() if response.choices[0].message else "N/A"
                logger.info(f"Resposta do modelo: '{response_text}'")
                logger.info(f"Conexão com {self.config.model} testada com sucesso")
                
                # Log estatísticas se disponível
                if hasattr(response, 'usage') and response.usage:
                    logger.debug(f"Tokens utilizados no teste: {response.usage.total_tokens}")
                
                return True, "Conexão estabelecida com sucesso"
            else:
                logger.error("Resposta vazia ou inválida do modelo durante teste")
                return False, "Resposta vazia do modelo"
                
        except Exception as e:
            error_msg = f"Erro ao testar conexão: {str(e)}"
            logger.error(f"Falha no teste de conexão: {error_msg}")
            logger.debug(f"Tipo do erro: {type(e).__name__}")
            return False, error_msg
    
    def _build_system_prompt(self, additional_context: str = "") -> str:
        """Constrói o prompt do sistema para tradução.
        
        Cria um prompt abrangente que inclui instruções base, contexto
        personalizado e instruções específicas para guiar o modelo de IA
        durante a tradução.
        
        Args:
            additional_context: Contexto específico para este trecho de texto
            
        Returns:
            Prompt completo formatado para o sistema
            
        Note:
            O prompt é construído de forma hierárquica:
            1. Instruções principais de tradução
            2. Contexto geral (se configurado)
            3. Contexto adicional (se fornecido)
            4. Instruções customizadas (se configuradas)
        """
        base_prompt = f"""Você é um tradutor profissional especializado em traduzir textos para {self.config.target_language}.

INSTRUÇÕES PRINCIPAIS:
1. Traduza o texto fornecido mantendo o significado, tom e estilo originais
2. Preserve formatação, quebras de linha e estrutura do texto
3. Mantenha nomes próprios, títulos de obras e termos técnicos quando apropriado
4. Use linguagem natural e fluente em {self.config.target_language}
5. NÃO adicione comentários, explicações ou texto extra além da tradução

"""
        
        # Adiciona contexto personalizado se fornecido
        if self.config.context:
            base_prompt += f"CONTEXTO ADICIONAL:\n{self.config.context}\n\n"
        
        if additional_context:
            base_prompt += f"CONTEXTO DO TRECHO:\n{additional_context}\n\n"
        
        # Adiciona instruções customizadas
        if self.config.custom_instructions:
            base_prompt += f"INSTRUÇÕES ESPECÍFICAS:\n{self.config.custom_instructions}\n\n"
        
        base_prompt += "Traduza o seguinte texto:"
        
        return base_prompt
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((Exception,))
    )
    async def translate_text(self, text: str, additional_context: str = "") -> str:
        """
        Traduz um texto usando o modelo configurado.
        
        Args:
            text: Texto a ser traduzido
            additional_context: Contexto adicional para este trecho específico
            
        Returns:
            Texto traduzido
        """
        if not text.strip():
            return ""
        
        try:
            # Constrói mensagens
            system_prompt = self._build_system_prompt(additional_context)
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ]
            
            # Parâmetros da requisição
            params = {
                "model": self.config.model,
                "messages": messages,
                "reasoning_effort": "low"
            }
            
            # Log da solicitação
            translation_logger.info("=" * 80)
            translation_logger.info("NOVA SOLICITAÇÃO DE TRADUÇÃO")
            translation_logger.info("=" * 80)
            translation_logger.info(f"Modelo: {self.config.model}")
            translation_logger.info(f"Idioma alvo: {self.config.target_language}")
            translation_logger.info(f"Tamanho do texto: {len(text)} caracteres")
            translation_logger.info("-" * 40)
            translation_logger.info("PROMPT DO SISTEMA:")
            translation_logger.info(system_prompt)
            translation_logger.info("-" * 40)
            translation_logger.info("TEXTO A TRADUZIR:")
            translation_logger.info(text)
            translation_logger.info("-" * 40)
            
            # Faz a requisição
            response = await litellm.acompletion(**params)
            
            if response and response.choices and response.choices[0].message:
                translated_text = response.choices[0].message.content.strip()
                
                # Log da resposta
                translation_logger.info("RESPOSTA RECEBIDA:")
                translation_logger.info(translated_text)
                translation_logger.info("-" * 40)
                translation_logger.info(f"Status: SUCESSO")
                translation_logger.info(f"Tamanho da resposta: {len(translated_text)} caracteres")
                translation_logger.info(f"Redução/expansão: {((len(translated_text) - len(text)) / len(text) * 100):+.1f}%")
                
                # Log de estatísticas se disponível
                if hasattr(response, 'usage') and response.usage:
                    translation_logger.info(f"Tokens usados - Prompt: {response.usage.prompt_tokens}, Completion: {response.usage.completion_tokens}, Total: {response.usage.total_tokens}")
                
                translation_logger.info("=" * 80)
                
                return translated_text
            else:
                translation_logger.error("ERRO: Resposta vazia do modelo")
                translation_logger.info("=" * 80)
                raise Exception("Resposta vazia do modelo")
                
        except Exception as e:
            translation_logger.error("ERRO NA SOLICITAÇÃO:")
            translation_logger.error(f"Tipo do erro: {type(e).__name__}")
            translation_logger.error(f"Mensagem: {str(e)}")
            translation_logger.error(f"Modelo: {self.config.model}")
            translation_logger.error(f"Tamanho do texto: {len(text)} caracteres")
            
            # Log do texto que causou erro (limitado para não poluir)
            if len(text) < 500:
                translation_logger.error(f"Texto que causou erro: {text}")
            else:
                translation_logger.error(f"Início do texto: {text[:250]}...")
                translation_logger.error(f"Final do texto: ...{text[-250:]}")
            
            translation_logger.error("=" * 80)
            raise
    
    async def translate_chunks(
        self, 
        chunks: List[str], 
        progress_callback: Optional[callable] = None
    ) -> List[str]:
        """Traduz múltiplos chunks de texto em sequência.
        
        Esta função processa uma lista de chunks de texto, traduzindo cada
        um individualmente e reportando progresso através de callback.
        Em caso de erro em um chunk, mantém o texto original.
        
        Args:
            chunks: Lista de strings com textos para traduzir
            progress_callback: Função opcional para reportar progresso.
                Assinatura: callback(chunk_atual: int, total_chunks: int)
            
        Returns:
            Lista de strings com os textos traduzidos na mesma ordem
            
        Raises:
            Exception: Se houver erro crítico no processamento
            
        Example:
            >>> chunks = ["Hello", "How are you?", "Goodbye"]
            >>> def progress(current, total):
            ...     print(f"Progresso: {current}/{total}")
            >>> 
            >>> translated = await client.translate_chunks(chunks, progress)
            >>> print(translated)  # ["Olá", "Como você está?", "Tchau"]
        """
        translated_chunks = []
        
        for i, chunk in enumerate(chunks):
            try:
                translated = await self.translate_text(chunk)
                translated_chunks.append(translated)
                
                if progress_callback:
                    progress_callback(i + 1, len(chunks))
                    
            except Exception as e:
                logger.error(f"Erro ao traduzir chunk {i}: {e}")
                # Em caso de erro, mantém o texto original
                translated_chunks.append(chunk)
        
        return translated_chunks
    
    def get_model_info(self) -> Dict[str, Any]:
        """Retorna informações sobre o modelo configurado.
        
        Returns:
            Dicionário contendo informações do modelo atual:
            - model: Nome do modelo
            - target_language: Idioma alvo configurado
            
        Example:
            >>> info = client.get_model_info()
            >>> print(info['model'])  # "gpt-3.5-turbo"
            >>> print(info['target_language'])  # "pt-BR"
        """
        info = {
            "model": self.config.model,
            "target_language": self.config.target_language
        }
        
        return info
    
    @staticmethod
    def list_available_models() -> List[str]:
        """Lista modelos comumente disponíveis no LiteLLM.
        
        Esta função retorna uma lista de modelos que são tipicamente
        suportados pelo LiteLLM. A disponibilidade real depende das
        configurações de API e permissões do usuário.
        
        Returns:
            Lista de strings com nomes de modelos suportados
            
        Note:
            Esta é uma lista básica. O LiteLLM suporta muito mais modelos.
            Consulte a documentação oficial para lista completa e atualizada.
            
        Example:
            >>> models = TranslationClient.list_available_models()
            >>> print("Modelos OpenAI:", [m for m in models if "gpt" in m])
            >>> print("Modelos Anthropic:", [m for m in models if "claude" in m])
        """
        # Esta é uma lista básica - LiteLLM suporta muitos mais
        return [
            # OpenAI
            "openai/gpt-3.5-turbo",
            "openai/gpt-4",
            "openai/gpt-4-turbo",
            "openai/gpt-5",
            "gpt-3.5-turbo",
            "gpt-4",
            "gpt-4-turbo",
            "gpt-5",
            
            # Anthropic
            "anthropic/claude-3-haiku",
            "anthropic/claude-3-sonnet",
            "anthropic/claude-3.5-sonnet",
            "claude-3-haiku",
            "claude-3-sonnet", 
            "claude-3.5-sonnet",
            
            # Google
            "google/gemini-pro",
            "google/gemini-1.5-pro",
            "gemini-pro",
            "gemini-1.5-pro",
            
            # Outros
            "cohere/command-r",
            "cohere/command-r-plus",
        ]