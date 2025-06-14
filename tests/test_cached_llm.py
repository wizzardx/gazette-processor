import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
from icecream import ic

from src.ongoing_convo_with_bronn_2025_06_10.cached_llm import (
    CachedLLM,
    CacheManager,
    ClaudeConfig,
    SimpleClaudeSummarizer,
)


class TestClaudeConfig:
    """Tests for ClaudeConfig class"""

    def test_config_with_env_file(self):
        """Test config loading from env file"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("ANTHROPIC_API_KEY=test_key\n")
            f.write("ANTHROPIC_MODEL=test_model\n")
            f.write("MAX_TOKENS=500\n")
            f.write("TEMPERATURE=0.5\n")
            f.flush()

            try:
                config = ClaudeConfig(env_file=f.name)
                assert config.api_key == "test_key"
                assert config.model == "test_model"
                assert config.max_tokens == 500
                assert config.temperature == 0.5
            finally:
                os.unlink(f.name)

    def test_config_defaults(self):
        """Test config with defaults when env file doesn't exist"""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test_key"}, clear=True):
            config = ClaudeConfig(env_file="nonexistent.env")
            assert config.api_key == "test_key"
            assert config.model == "claude-3-haiku-20240307"
            assert config.max_tokens == 250
            assert config.temperature == 0.1

    def test_config_missing_api_key(self):
        """Test config raises error when API key is missing"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="ANTHROPIC_API_KEY is required"):
                ClaudeConfig(env_file="nonexistent.env")


class TestSimpleClaudeSummarizer:
    """Tests for SimpleClaudeSummarizer class"""

    def test_summarizer_initialization(self):
        """Test summarizer initialization with config"""
        config = MagicMock()
        config.api_key = "test_key"

        summarizer = SimpleClaudeSummarizer(config)
        assert summarizer.config == config
        assert hasattr(summarizer, "client")

    @patch("anthropic.Anthropic")
    def test_summarize_success(self, mock_anthropic):
        """Test successful summarization"""
        config = MagicMock()
        config.api_key = "test_key"
        config.model = "test_model"
        config.max_tokens = 250
        config.temperature = 0.1

        mock_client = MagicMock()
        mock_response = MagicMock()
        # Create a proper TextBlock mock
        from anthropic.types import TextBlock

        mock_text_block = MagicMock(spec=TextBlock)
        mock_text_block.text = "This is a summary"
        mock_response.content = [mock_text_block]
        mock_response.stop_reason = "end_turn"
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client

        summarizer = SimpleClaudeSummarizer(config)
        result = summarizer.summarize("Long text to summarize")

        assert result == "This is a summary"
        mock_client.messages.create.assert_called_once()

    @patch("anthropic.Anthropic")
    def test_summarize_truncated_retry(self, mock_anthropic):
        """Test retry when summary is truncated"""
        config = MagicMock()
        config.api_key = "test_key"
        config.model = "test_model"
        config.max_tokens = 250
        config.temperature = 0.1

        mock_client = MagicMock()

        # First response - truncated
        from anthropic.types import TextBlock

        mock_response1 = MagicMock()
        mock_text_block1 = MagicMock(spec=TextBlock)
        mock_text_block1.text = "This is a truncated summary that doesn't end properly"
        mock_response1.content = [mock_text_block1]
        mock_response1.stop_reason = "max_tokens"

        # Second response - complete
        mock_response2 = MagicMock()
        mock_text_block2 = MagicMock(spec=TextBlock)
        mock_text_block2.text = "This is a complete summary."
        mock_response2.content = [mock_text_block2]
        mock_response2.stop_reason = "end_turn"

        mock_client.messages.create.side_effect = [mock_response1, mock_response2]
        mock_anthropic.return_value = mock_client

        summarizer = SimpleClaudeSummarizer(config)
        result = summarizer.summarize("Long text to summarize")

        assert result == "This is a complete summary."
        assert mock_client.messages.create.call_count == 2

    @patch("anthropic.Anthropic")
    def test_summarize_api_error(self, mock_anthropic):
        """Test API error handling"""
        config = MagicMock()
        config.api_key = "test_key"
        config.max_tokens = 250

        mock_client = MagicMock()
        mock_client.messages.create.side_effect = Exception("API Error")
        mock_anthropic.return_value = mock_client

        summarizer = SimpleClaudeSummarizer(config)

        with pytest.raises(RuntimeError, match="Claude API error"):
            summarizer.summarize("Text to summarize")


class TestCacheManager:
    """Tests for CacheManager class"""

    def test_cache_manager_initialization(self):
        """Test cache manager initialization"""
        manager = CacheManager(max_cache_size=100)
        assert manager.max_cache_size == 100
        assert manager.cache == {}
        assert manager.cache_file is None

    def test_compute_hash(self):
        """Test MD5 hash computation"""
        manager = CacheManager()
        hash1 = manager._compute_hash("test text")
        hash2 = manager._compute_hash("test text")
        hash3 = manager._compute_hash("different text")

        assert hash1 == hash2
        assert hash1 != hash3

    def test_cache_get_set(self):
        """Test cache get and set operations"""
        manager = CacheManager()

        # Test cache miss
        assert manager.get("test text") is None

        # Test cache set and hit
        manager.set("test text", "summary")
        assert manager.get("test text") == "summary"

        # Verify metadata is updated
        text_hash = manager._compute_hash("test text")
        assert manager.cache[text_hash]["access_count"] == 2  # 1 set + 1 get

    def test_cache_eviction(self):
        """Test cache eviction when full"""
        manager = CacheManager(max_cache_size=3)

        # Fill cache
        manager.set("text1", "summary1")
        manager.set("text2", "summary2")
        manager.set("text3", "summary3")

        # Access text2 to make it more recent
        manager.get("text2")

        # Add new item - should evict least recently used
        manager.set("text4", "summary4")

        assert len(manager.cache) == 3
        assert manager.get("text1") is None  # Should be evicted
        assert manager.get("text2") == "summary2"
        assert manager.get("text3") == "summary3"
        assert manager.get("text4") == "summary4"

    def test_cache_file_operations(self):
        """Test cache file save and load"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            cache_file = f.name

        try:
            # Create cache with file
            manager = CacheManager(cache_file=cache_file)
            manager.set("test", "summary")

            # Verify file was created
            assert os.path.exists(cache_file)

            # Load from file
            manager2 = CacheManager(cache_file=cache_file)
            assert manager2.get("test") == "summary"

        finally:
            if os.path.exists(cache_file):
                os.unlink(cache_file)

    def test_cache_file_load_error(self):
        """Test cache file load with corrupted file"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("invalid json{")
            cache_file = f.name

        try:
            # Should handle error gracefully
            manager = CacheManager(cache_file=cache_file)
            assert manager.cache == {}
        finally:
            os.unlink(cache_file)

    def test_cache_stats(self):
        """Test cache statistics"""
        manager = CacheManager()

        # Empty cache stats
        stats = manager.get_stats()
        assert stats["size"] == 0
        assert stats["total_accesses"] == 0

        # Add items and check stats
        manager.set("text1", "summary1")
        manager.set("text2", "summary2")
        manager.get("text1")

        stats = manager.get_stats()
        assert stats["size"] == 2
        assert stats["max_size"] == 1000
        assert stats["total_accesses"] == 3  # 2 sets + 1 get

    def test_cache_clear(self):
        """Test cache clearing"""
        manager = CacheManager()
        manager.set("text1", "summary1")
        manager.set("text2", "summary2")

        assert len(manager.cache) == 2

        manager.clear()
        assert len(manager.cache) == 0
        assert manager.get("text1") is None


class TestCachedLLM:
    """Tests for CachedLLM class"""

    @patch("src.ongoing_convo_with_bronn_2025_06_10.cached_llm.ClaudeConfig")
    def test_cached_llm_initialization(self, mock_config_class):
        """Test CachedLLM initialization"""
        mock_config = MagicMock()
        mock_config.api_key = "test_key"
        mock_config.model = "test_model"
        mock_config_class.return_value = mock_config

        llm = CachedLLM(cache_file=None)

        assert llm.stats["total_requests"] == 0
        assert llm.stats["cache_hits"] == 0
        assert llm.stats["api_calls"] == 0

    @patch("src.ongoing_convo_with_bronn_2025_06_10.cached_llm.SimpleClaudeSummarizer")
    @patch("src.ongoing_convo_with_bronn_2025_06_10.cached_llm.ClaudeConfig")
    def test_summarize_empty_text(self, mock_config_class, mock_summarizer_class):
        """Test summarize with empty text"""
        mock_config = MagicMock()
        mock_config.api_key = "test_key"
        mock_config_class.return_value = mock_config

        llm = CachedLLM(cache_file=None)

        assert llm.summarize("") == ""
        assert llm.summarize("   ") == ""
        assert llm.stats["total_requests"] == 0  # Empty requests don't count

    @patch("src.ongoing_convo_with_bronn_2025_06_10.cached_llm.SimpleClaudeSummarizer")
    @patch("src.ongoing_convo_with_bronn_2025_06_10.cached_llm.ClaudeConfig")
    def test_summarize_cache_miss(self, mock_config_class, mock_summarizer_class):
        """Test summarize with cache miss"""
        mock_config = MagicMock()
        mock_config.api_key = "test_key"
        mock_config_class.return_value = mock_config

        mock_summarizer = MagicMock()
        mock_summarizer.summarize.return_value = "Test summary"
        mock_summarizer_class.return_value = mock_summarizer

        llm = CachedLLM(cache_file=None)
        result = llm.summarize("Test text")

        assert result == "Test summary"
        assert llm.stats["total_requests"] == 1
        assert llm.stats["cache_hits"] == 0
        assert llm.stats["api_calls"] == 1

    @patch("src.ongoing_convo_with_bronn_2025_06_10.cached_llm.SimpleClaudeSummarizer")
    @patch("src.ongoing_convo_with_bronn_2025_06_10.cached_llm.ClaudeConfig")
    def test_summarize_cache_hit(self, mock_config_class, mock_summarizer_class):
        """Test summarize with cache hit"""
        mock_config = MagicMock()
        mock_config.api_key = "test_key"
        mock_config_class.return_value = mock_config

        mock_summarizer = MagicMock()
        mock_summarizer.summarize.return_value = "Test summary"
        mock_summarizer_class.return_value = mock_summarizer

        llm = CachedLLM(cache_file=None)

        # First call - cache miss
        result1 = llm.summarize("Test text")
        assert result1 == "Test summary"

        # Second call - cache hit
        result2 = llm.summarize("Test text")
        assert result2 == "Test summary"

        assert llm.stats["total_requests"] == 2
        assert llm.stats["cache_hits"] == 1
        assert llm.stats["api_calls"] == 1
        mock_summarizer.summarize.assert_called_once()

    @patch("src.ongoing_convo_with_bronn_2025_06_10.cached_llm.SimpleClaudeSummarizer")
    @patch("src.ongoing_convo_with_bronn_2025_06_10.cached_llm.ClaudeConfig")
    def test_summarize_error_handling(self, mock_config_class, mock_summarizer_class):
        """Test summarize error handling"""
        mock_config = MagicMock()
        mock_config.api_key = "test_key"
        mock_config_class.return_value = mock_config

        mock_summarizer = MagicMock()
        mock_summarizer.summarize.side_effect = Exception("API Error")
        mock_summarizer_class.return_value = mock_summarizer

        llm = CachedLLM(cache_file=None)

        with pytest.raises(Exception, match="API Error"):
            llm.summarize("Test text")

    @patch("src.ongoing_convo_with_bronn_2025_06_10.cached_llm.ClaudeConfig")
    def test_get_stats(self, mock_config_class):
        """Test getting statistics"""
        mock_config = MagicMock()
        mock_config.api_key = "test_key"
        mock_config.model = "test_model"
        mock_config_class.return_value = mock_config

        llm = CachedLLM(cache_file=None)
        stats = llm.get_stats()

        assert stats["requests"]["total"] == 0
        assert stats["requests"]["hit_rate_percent"] == 0
        assert stats["model"] == "test_model"
        assert "cache" in stats
        assert "estimated_cost_saved" in stats

    @patch("src.ongoing_convo_with_bronn_2025_06_10.cached_llm.ClaudeConfig")
    def test_clear_cache(self, mock_config_class):
        """Test cache clearing"""
        mock_config = MagicMock()
        mock_config.api_key = "test_key"
        mock_config_class.return_value = mock_config

        llm = CachedLLM(cache_file=None)
        llm.cache.set("test", "summary")

        assert llm.cache.get("test") == "summary"

        llm.clear_cache()
        assert llm.cache.get("test") is None

    @patch("src.ongoing_convo_with_bronn_2025_06_10.cached_llm.ClaudeConfig")
    def test_str_representation(self, mock_config_class):
        """Test string representation"""
        mock_config = MagicMock()
        mock_config.api_key = "test_key"
        mock_config.model = "test_model"
        mock_config_class.return_value = mock_config

        llm = CachedLLM(cache_file=None)
        str_repr = str(llm)

        assert "CachedLLM" in str_repr
        assert "test_model" in str_repr
        assert "requests=0" in str_repr
        assert "hit_rate=0%" in str_repr


class TestMain:
    """Test the main function"""

    @patch("src.ongoing_convo_with_bronn_2025_06_10.cached_llm.CachedLLM")
    def test_main_success(self, mock_cached_llm_class):
        """Test successful main function execution"""
        mock_llm = MagicMock()
        mock_llm.summarize.return_value = "Test summary"
        mock_llm.get_stats.return_value = {
            "requests": {
                "total": 3,
                "cache_hits": 1,
                "api_calls": 2,
                "hit_rate_percent": 33.3,
            },
            "cache": {"size": 2},
            "estimated_cost_saved": 0.0001,
        }
        mock_cached_llm_class.return_value = mock_llm

        from src.ongoing_convo_with_bronn_2025_06_10.cached_llm import main

        # Should not raise any exceptions
        ic()
        main()
        ic()

        # Verify summarize was called 3 times (as per sample_texts)
        assert mock_llm.summarize.call_count == 3

    @patch("src.ongoing_convo_with_bronn_2025_06_10.cached_llm.CachedLLM")
    def test_main_config_error(self, mock_cached_llm_class):
        """Test main function with configuration error"""
        mock_cached_llm_class.side_effect = ValueError("ANTHROPIC_API_KEY is required")

        from src.ongoing_convo_with_bronn_2025_06_10.cached_llm import main

        # Should handle error gracefully
        main()

    @patch("src.ongoing_convo_with_bronn_2025_06_10.cached_llm.CachedLLM")
    def test_main_general_error(self, mock_cached_llm_class):
        """Test main function with general error"""
        mock_cached_llm_class.side_effect = Exception("Unexpected error")

        from src.ongoing_convo_with_bronn_2025_06_10.cached_llm import main

        # Should handle error gracefully
        main()
