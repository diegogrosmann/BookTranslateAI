"""
Testes para o módulo translator.py
"""
import pytest
import os
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from dataclasses import asdict

from translator import (
    TranslationConfig, ModelRestrictions, TranslationClient
)


class TestTranslationConfig:
    """Testes para a classe TranslationConfig."""
    
    def test_default_config(self):
        """Testa configuração padrão."""
        config = TranslationConfig(model="gpt-4")
        
        assert config.model == "gpt-4"
        assert config.target_language == "pt-BR"
        assert config.temperature == 0.3
        assert config.max_tokens == 4000
        assert config.timeout == 60
        assert config.context == ""
        assert config.custom_instructions == ""
    
    def test_custom_config(self):
        """Testa configuração personalizada."""
        config = TranslationConfig(
            model="claude-3.5-sonnet",
            target_language="es-ES",
            temperature=0.5,
            max_tokens=8000,
            timeout=120,
            context="Contexto específico",
            custom_instructions="Instruções personalizadas"
        )
        
        assert config.model == "claude-3.5-sonnet"
        assert config.target_language == "es-ES"
        assert config.temperature == 0.5
        assert config.max_tokens == 8000
        assert config.timeout == 120
        assert config.context == "Contexto específico"
        assert config.custom_instructions == "Instruções personalizadas"


class TestModelRestrictions:
    """Testes para a classe ModelRestrictions."""
    
    def test_default_restrictions(self):
        """Testa restrições padrão."""
        restrictions = ModelRestrictions()
        
        assert restrictions.forced_temperature is None
        assert restrictions.max_temperature is None
        assert restrictions.min_temperature is None
        assert restrictions.forbidden_params == []
        assert restrictions.required_params == {}
    
    def test_custom_restrictions(self):
        """Testa restrições personalizadas."""
        restrictions = ModelRestrictions(
            forced_temperature=1.0,
            max_temperature=0.8,
            min_temperature=0.1,
            forbidden_params=['top_p'],
            required_params={'frequency_penalty': 0.0}
        )
        
        assert restrictions.forced_temperature == 1.0
        assert restrictions.max_temperature == 0.8
        assert restrictions.min_temperature == 0.1
        assert restrictions.forbidden_params == ['top_p']
        assert restrictions.required_params == {'frequency_penalty': 0.0}


class TestTranslationClient:
    """Testes para a classe TranslationClient."""
    
    def setup_method(self):
        """Configuração para cada teste."""
        self.config = TranslationConfig(model="gpt-4")
        self.client = TranslationClient(self.config)
    
    def test_client_initialization(self):
        """Testa inicialização do cliente."""
        assert self.client.config == self.config
        assert self.client.api_key is None
    
    def test_client_with_api_key(self):
        """Testa inicialização com chave da API."""
        with patch.dict(os.environ, {}, clear=True):
            client = TranslationClient(self.config, api_key="test-key")
            
            assert client.api_key == "test-key"
            # Deve configurar a variável de ambiente apropriada
            assert os.environ.get('OPENAI_API_KEY') == "test-key"
    
    def test_set_api_key_openai(self):
        """Testa configuração de chave para OpenAI."""
        config = TranslationConfig(model="openai/gpt-4")
        
        with patch.dict(os.environ, {}, clear=True):
            client = TranslationClient(config, api_key="openai-key")
            assert os.environ.get('OPENAI_API_KEY') == "openai-key"
    
    def test_set_api_key_anthropic(self):
        """Testa configuração de chave para Anthropic."""
        config = TranslationConfig(model="anthropic/claude-3.5-sonnet")
        
        with patch.dict(os.environ, {}, clear=True):
            client = TranslationClient(config, api_key="anthropic-key")
            assert os.environ.get('ANTHROPIC_API_KEY') == "anthropic-key"
    
    def test_set_api_key_google(self):
        """Testa configuração de chave para Google."""
        config = TranslationConfig(model="google/gemini-pro")
        
        with patch.dict(os.environ, {}, clear=True):
            client = TranslationClient(config, api_key="google-key")
            assert os.environ.get('GOOGLE_API_KEY') == "google-key"
    
    def test_set_api_key_unknown_provider(self):
        """Testa configuração de chave para provedor desconhecido."""
        config = TranslationConfig(model="unknown/model")
        
        with patch.dict(os.environ, {}, clear=True):
            client = TranslationClient(config, api_key="unknown-key")
            assert os.environ.get('API_KEY') == "unknown-key"
            assert os.environ.get('LITELLM_API_KEY') == "unknown-key"
    
    def test_apply_model_restrictions_gpt5(self):
        """Testa aplicação de restrições para GPT-5."""
        config = TranslationConfig(model="gpt-5", temperature=0.5)
        client = TranslationClient(config)
        
        # GPT-5 deve ter temperature forçada para 1.0
        assert client.config.temperature == 1.0
    
    def test_apply_model_restrictions_claude(self):
        """Testa aplicação de restrições para Claude."""
        config = TranslationConfig(model="claude-3.5-sonnet", temperature=1.5)
        client = TranslationClient(config)
        
        # Claude deve ter temperature limitada a 1.0
        assert client.config.temperature == 1.0
    
    def test_apply_model_restrictions_no_restrictions(self):
        """Testa que modelos sem restrições mantêm configuração original."""
        config = TranslationConfig(model="gpt-4", temperature=0.7)
        client = TranslationClient(config)
        
        # GPT-4 não tem restrições, deve manter temperatura original
        assert client.config.temperature == 0.7
    
    @patch('translator.litellm.completion')
    async def test_translate_text_success(self, mock_completion):
        """Testa tradução bem-sucedida."""
        # Mock da resposta da API
        mock_response = {
            'choices': [{
                'message': {
                    'content': 'Texto traduzido para português'
                }
            }],
            'usage': {
                'prompt_tokens': 50,
                'completion_tokens': 30,
                'total_tokens': 80
            }
        }
        mock_completion.return_value = mock_response
        
        result = await self.client.translate_text("Text to translate")
        
        assert result['translated_text'] == 'Texto traduzido para português'
        assert result['usage']['total_tokens'] == 80
        
        # Verifica se foi chamado com parâmetros corretos
        mock_completion.assert_called_once()
        call_args = mock_completion.call_args[1]
        assert call_args['model'] == 'gpt-4'
        assert call_args['temperature'] == 0.3
        assert call_args['max_tokens'] == 4000
    
    @patch('translator.litellm.completion')
    async def test_translate_text_with_context(self, mock_completion):
        """Testa tradução com contexto."""
        mock_response = {
            'choices': [{'message': {'content': 'Tradução com contexto'}}],
            'usage': {'total_tokens': 100}
        }
        mock_completion.return_value = mock_response
        
        config = TranslationConfig(
            model="gpt-4",
            context="Contexto específico",
            custom_instructions="Instruções personalizadas"
        )
        client = TranslationClient(config)
        
        await client.translate_text("Text with context")
        
        # Verifica se o prompt incluiu contexto e instruções
        call_args = mock_completion.call_args[1]
        messages = call_args['messages']
        
        # Deve ter mensagem do sistema com contexto e instruções
        system_message = next(msg for msg in messages if msg['role'] == 'system')
        assert 'Contexto específico' in system_message['content']
        assert 'Instruções personalizadas' in system_message['content']
    
    @patch('translator.litellm.completion')
    async def test_translate_text_api_error(self, mock_completion):
        """Testa tratamento de erro da API."""
        mock_completion.side_effect = Exception("API Error")
        
        with pytest.raises(Exception, match="API Error"):
            await self.client.translate_text("Text to translate")
    
    @patch('translator.litellm.completion')
    async def test_translate_text_empty_response(self, mock_completion):
        """Testa tratamento de resposta vazia."""
        mock_response = {
            'choices': [{'message': {'content': ''}}],
            'usage': {'total_tokens': 10}
        }
        mock_completion.return_value = mock_response
        
        result = await self.client.translate_text("Text to translate")
        
        assert result['translated_text'] == ''
        assert 'usage' in result
    
    @patch('translator.litellm.completion')
    async def test_translate_chunks_success(self, mock_completion):
        """Testa tradução de múltiplos chunks."""
        # Mock das respostas
        responses = [
            {
                'choices': [{'message': {'content': f'Chunk {i} traduzido'}}],
                'usage': {'total_tokens': 50}
            }
            for i in range(1, 4)
        ]
        mock_completion.side_effect = responses
        
        chunks = [
            {'content': 'Chunk 1 content', 'id': 1},
            {'content': 'Chunk 2 content', 'id': 2},
            {'content': 'Chunk 3 content', 'id': 3}
        ]
        
        results = await self.client.translate_chunks(chunks)
        
        assert len(results) == 3
        for i, result in enumerate(results, 1):
            assert result['translated_text'] == f'Chunk {i} traduzido'
            assert result['chunk_id'] == i
            assert 'usage' in result
    
    @patch('translator.litellm.completion')
    async def test_translate_chunks_partial_failure(self, mock_completion):
        """Testa tradução com falha parcial."""
        # Primeiro chunk sucesso, segundo falha, terceiro sucesso
        responses = [
            {'choices': [{'message': {'content': 'Chunk 1 ok'}}], 'usage': {'total_tokens': 50}},
            Exception("Erro no chunk 2"),
            {'choices': [{'message': {'content': 'Chunk 3 ok'}}], 'usage': {'total_tokens': 50}}
        ]
        mock_completion.side_effect = responses
        
        chunks = [
            {'content': 'Chunk 1', 'id': 1},
            {'content': 'Chunk 2', 'id': 2},
            {'content': 'Chunk 3', 'id': 3}
        ]
        
        results = await self.client.translate_chunks(chunks)
        
        # Deve retornar resultados para chunks bem-sucedidos
        successful_results = [r for r in results if 'error' not in r]
        failed_results = [r for r in results if 'error' in r]
        
        assert len(successful_results) == 2
        assert len(failed_results) == 1
        assert failed_results[0]['chunk_id'] == 2
    
    def test_build_system_prompt_default(self):
        """Testa construção do prompt do sistema padrão."""
        prompt = self.client._build_system_prompt()
        
        assert 'tradutor literário profissional' in prompt.lower()
        assert 'pt-br' in prompt.lower()
        assert 'roda do tempo' in prompt.lower()
    
    def test_build_system_prompt_with_context(self):
        """Testa construção do prompt com contexto personalizado."""
        config = TranslationConfig(
            model="gpt-4",
            target_language="es-ES",
            context="Contexto específico",
            custom_instructions="Instruções especiais"
        )
        client = TranslationClient(config)
        
        prompt = client._build_system_prompt()
        
        assert 'es-es' in prompt.lower()
        assert 'contexto específico' in prompt.lower()
        assert 'instruções especiais' in prompt.lower()
    
    @patch('translator.litellm.completion')
    async def test_retry_mechanism(self, mock_completion):
        """Testa mecanismo de retry em falhas temporárias."""
        # Primeiro tenta falha, segundo tenta sucesso
        mock_completion.side_effect = [
            Exception("Temporary error"),
            {
                'choices': [{'message': {'content': 'Tradução bem-sucedida'}}],
                'usage': {'total_tokens': 50}
            }
        ]
        
        # O decorator @retry deve tentar novamente
        result = await self.client.translate_text("Text to translate")
        
        assert result['translated_text'] == 'Tradução bem-sucedida'
        assert mock_completion.call_count == 2
    
    async def test_rate_limiting(self):
        """Testa rate limiting entre requisições."""
        import time
        
        with patch('translator.litellm.completion') as mock_completion:
            mock_completion.return_value = {
                'choices': [{'message': {'content': 'Traduzido'}}],
                'usage': {'total_tokens': 50}
            }
            
            # Configura rate limiting
            self.client.rate_limiter = self.client._create_rate_limiter(2.0)  # 2 req/sec max
            
            start_time = time.time()
            
            # Faz duas requisições
            await self.client.translate_text("Text 1")
            await self.client.translate_text("Text 2")
            
            end_time = time.time()
            elapsed = end_time - start_time
            
            # Deve ter demorado pelo menos 0.5 segundos (1/2 req/sec)
            assert elapsed >= 0.4  # Margem para variações de timing
    
    def test_estimate_cost(self):
        """Testa estimativa de custo."""
        usage = {
            'prompt_tokens': 1000,
            'completion_tokens': 500,
            'total_tokens': 1500
        }
        
        cost = self.client.estimate_cost(usage)
        
        # Deve retornar um custo positivo
        assert cost > 0
        assert isinstance(cost, float)
    
    def test_get_model_info(self):
        """Testa obtenção de informações do modelo."""
        info = self.client.get_model_info()
        
        assert 'model' in info
        assert 'provider' in info
        assert 'max_tokens' in info
        assert info['model'] == 'gpt-4'


class TestIntegration:
    """Testes de integração para o módulo translator."""
    
    @patch('translator.litellm.completion')
    async def test_complete_translation_workflow(self, mock_completion):
        """Testa fluxo completo de tradução."""
        # Mock das respostas
        mock_completion.return_value = {
            'choices': [{'message': {'content': 'Texto traduzido'}}],
            'usage': {'prompt_tokens': 100, 'completion_tokens': 80, 'total_tokens': 180}
        }
        
        # Configura cliente
        config = TranslationConfig(
            model="gpt-4",
            target_language="pt-BR",
            context="Fantasy literature",
            custom_instructions="Maintain epic tone"
        )
        client = TranslationClient(config, api_key="test-key")
        
        # Simula chunks de um capítulo
        chunks = [
            {'content': 'Chapter 1: The beginning of the journey.', 'id': 1, 'chapter': 'ch1'},
            {'content': 'The wind was not a beginning. But it was a beginning.', 'id': 2, 'chapter': 'ch1'}
        ]
        
        # Executa tradução
        results = await client.translate_chunks(chunks)
        
        # Verifica resultados
        assert len(results) == 2
        
        for result in results:
            assert 'translated_text' in result
            assert 'usage' in result
            assert 'chunk_id' in result
            assert result['translated_text'] == 'Texto traduzido'
    
    def test_model_restrictions_integration(self):
        """Testa integração das restrições de modelo."""
        # Testa diferentes modelos e suas restrições
        test_cases = [
            ("gpt-5", 0.5, 1.0),  # Deve forçar temperature = 1.0
            ("openai/gpt-5", 0.3, 1.0),  # Deve forçar temperature = 1.0
            ("claude-3.5-sonnet", 1.5, 1.0),  # Deve limitar a 1.0
            ("gpt-4", 0.7, 0.7),  # Não deve alterar
        ]
        
        for model, input_temp, expected_temp in test_cases:
            config = TranslationConfig(model=model, temperature=input_temp)
            client = TranslationClient(config)
            
            assert client.config.temperature == expected_temp, \
                f"Modelo {model}: esperado {expected_temp}, obtido {client.config.temperature}"
    
    @patch('translator.logger')
    async def test_logging_integration(self, mock_logger):
        """Testa integração com sistema de logging."""
        with patch('translator.litellm.completion') as mock_completion:
            mock_completion.return_value = {
                'choices': [{'message': {'content': 'Traduzido'}}],
                'usage': {'total_tokens': 100}
            }
            
            client = TranslationClient(self.config)
            await client.translate_text("Test text")
            
            # Deve fazer logs das operações
            assert mock_logger.info.called or mock_logger.debug.called