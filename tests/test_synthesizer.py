"""
Tests for content synthesis components.

This module contains unit tests for the LLMClient implementations
and ContentSynthesizer.
"""

from datetime import datetime
from unittest.mock import MagicMock, patch
import json

import pytest

from newsletter_generator.synthesizer import (
    ContentSynthesizer,
    LLMAPIError,
    LLMClient,
    LLMError,
    LLMRateLimitError,
    OpenAIClient,
)
from newsletter_generator.models import NewsletterItem, TopicGroup


class MockLLMClient:
    """Mock LLM client for testing."""
    
    def __init__(self, responses: list[str] | None = None):
        self.responses = responses or []
        self.call_count = 0
        self.prompts: list[str] = []
        self.systems: list[str | None] = []
    
    def complete(self, prompt: str, system: str | None = None) -> str:
        self.prompts.append(prompt)
        self.systems.append(system)
        if self.call_count < len(self.responses):
            response = self.responses[self.call_count]
            self.call_count += 1
            return response
        return "[]"


class TestLLMClientProtocol:
    """Tests for LLMClient protocol."""
    
    def test_mock_client_implements_protocol(self):
        """MockLLMClient should implement LLMClient protocol."""
        client = MockLLMClient()
        assert isinstance(client, LLMClient)
    
    def test_openai_client_implements_protocol(self):
        """OpenAIClient should implement LLMClient protocol."""
        # Just check the class structure, not actual API calls
        assert hasattr(OpenAIClient, 'complete')


class TestOpenAIClient:
    """Unit tests for OpenAIClient."""
    
    def test_init_stores_model(self):
        """OpenAIClient should store model name."""
        with patch('newsletter_generator.synthesizer.openai.OpenAI'):
            client = OpenAIClient(api_key="test-key", model="gpt-4o")
            assert client.model == "gpt-4o"
    
    def test_init_stores_retry_config(self):
        """OpenAIClient should store retry configuration."""
        with patch('newsletter_generator.synthesizer.openai.OpenAI'):
            client = OpenAIClient(
                api_key="test-key",
                model="gpt-4o",
                max_retries=5,
                base_delay=2.0,
            )
            assert client.max_retries == 5
            assert client.base_delay == 2.0
    
    def test_complete_builds_messages_with_system(self):
        """complete() should include system message when provided."""
        with patch('newsletter_generator.synthesizer.openai.OpenAI') as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client
            
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "Test response"
            mock_client.chat.completions.create.return_value = mock_response
            
            client = OpenAIClient(api_key="test-key", model="gpt-4o")
            result = client.complete("Hello", system="Be helpful")
            
            call_args = mock_client.chat.completions.create.call_args
            messages = call_args.kwargs['messages']
            
            assert len(messages) == 2
            assert messages[0]['role'] == 'system'
            assert messages[0]['content'] == 'Be helpful'
            assert messages[1]['role'] == 'user'
            assert messages[1]['content'] == 'Hello'
            assert result == "Test response"
    
    def test_complete_without_system(self):
        """complete() should work without system message."""
        with patch('newsletter_generator.synthesizer.openai.OpenAI') as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client
            
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "Test response"
            mock_client.chat.completions.create.return_value = mock_response
            
            client = OpenAIClient(api_key="test-key", model="gpt-4o")
            result = client.complete("Hello")
            
            call_args = mock_client.chat.completions.create.call_args
            messages = call_args.kwargs['messages']
            
            assert len(messages) == 1
            assert messages[0]['role'] == 'user'
            assert result == "Test response"
    
    def test_complete_raises_on_empty_response(self):
        """complete() should raise LLMAPIError on empty response."""
        with patch('newsletter_generator.synthesizer.openai.OpenAI') as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client
            
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = None
            mock_client.chat.completions.create.return_value = mock_response
            
            client = OpenAIClient(api_key="test-key", model="gpt-4o")
            
            with pytest.raises(LLMAPIError, match="Empty response"):
                client.complete("Hello")


class TestContentSynthesizer:
    """Unit tests for ContentSynthesizer."""
    
    @pytest.fixture
    def sample_items(self) -> list[NewsletterItem]:
        """Create sample newsletter items for testing."""
        return [
            NewsletterItem(
                source_name="TechCrunch",
                source_type="rss",
                title="New AI Model Released",
                content="A new AI model has been released with improved capabilities.",
                published_date=datetime(2024, 1, 15),
            ),
            NewsletterItem(
                source_name="Hacker News",
                source_type="rss",
                title="Cloud Computing Trends 2024",
                content="Cloud computing continues to evolve with new services.",
                published_date=datetime(2024, 1, 16),
            ),
            NewsletterItem(
                source_name="Tech Newsletter",
                source_type="email",
                title="AI in Healthcare",
                content="AI is transforming healthcare with new diagnostic tools.",
                published_date=datetime(2024, 1, 17),
            ),
        ]
    
    def test_group_by_topic_empty_items(self):
        """group_by_topic() should return empty list for empty input."""
        client = MockLLMClient()
        synthesizer = ContentSynthesizer(client)
        
        result = synthesizer.group_by_topic([])
        
        assert result == []
    
    def test_group_by_topic_creates_groups(self, sample_items):
        """group_by_topic() should create topic groups from LLM response."""
        llm_response = json.dumps([
            {"topic": "AI Development", "description": "AI news", "item_indices": [0, 2]},
            {"topic": "Cloud Computing", "description": "Cloud news", "item_indices": [1]},
        ])
        client = MockLLMClient(responses=[llm_response])
        synthesizer = ContentSynthesizer(client)
        
        result = synthesizer.group_by_topic(sample_items)
        
        assert len(result) == 2
        assert result[0].topic == "AI Development"
        assert len(result[0].items) == 2
        assert result[1].topic == "Cloud Computing"
        assert len(result[1].items) == 1
    
    def test_group_by_topic_handles_invalid_json(self, sample_items):
        """group_by_topic() should fallback on invalid JSON response."""
        client = MockLLMClient(responses=["not valid json"])
        synthesizer = ContentSynthesizer(client)
        
        result = synthesizer.group_by_topic(sample_items)
        
        # Should fallback to single group
        assert len(result) == 1
        assert result[0].topic == "General Tech News"
        assert len(result[0].items) == 3
    
    def test_extract_key_points_empty_group(self):
        """extract_key_points() should return empty list for empty group."""
        client = MockLLMClient()
        synthesizer = ContentSynthesizer(client)
        
        group = TopicGroup(
            topic="Test",
            description="Test topic",
            items=[],
            key_points=[],
        )
        
        result = synthesizer.extract_key_points(group)
        
        assert result == []
    
    def test_extract_key_points_returns_points(self, sample_items):
        """extract_key_points() should return key points from LLM."""
        llm_response = json.dumps([
            "AI models are improving rapidly",
            "Healthcare applications are growing",
        ])
        client = MockLLMClient(responses=[llm_response])
        synthesizer = ContentSynthesizer(client)
        
        group = TopicGroup(
            topic="AI",
            description="AI news",
            items=sample_items[:2],
            key_points=[],
        )
        
        result = synthesizer.extract_key_points(group)
        
        assert len(result) == 2
        assert "AI models are improving rapidly" in result
    
    def test_generate_summary_empty_topics(self):
        """generate_summary() should handle empty topics list."""
        client = MockLLMClient()
        synthesizer = ContentSynthesizer(client)
        
        result = synthesizer.generate_summary([])
        
        assert "No content available" in result
    
    def test_generate_summary_returns_llm_response(self, sample_items):
        """generate_summary() should return LLM-generated summary."""
        client = MockLLMClient(responses=["This week in tech saw major AI developments."])
        synthesizer = ContentSynthesizer(client)
        
        topics = [
            TopicGroup(
                topic="AI",
                description="AI news",
                items=sample_items,
                key_points=["AI is advancing"],
            )
        ]
        
        result = synthesizer.generate_summary(topics)
        
        assert result == "This week in tech saw major AI developments."
    
    def test_synthesize_empty_items(self):
        """synthesize() should handle empty items list."""
        client = MockLLMClient()
        synthesizer = ContentSynthesizer(client)
        
        result = synthesizer.synthesize([])
        
        assert result.topics == []
        assert result.source_count == 0
        assert "No newsletter content" in result.overall_summary
    
    def test_synthesize_full_pipeline(self, sample_items):
        """synthesize() should run full pipeline."""
        # Responses for: group_by_topic, extract_key_points (x groups), generate_summary
        responses = [
            json.dumps([
                {"topic": "AI", "description": "AI news", "item_indices": [0, 2]},
                {"topic": "Cloud", "description": "Cloud news", "item_indices": [1]},
            ]),
            json.dumps(["AI point 1", "AI point 2"]),
            json.dumps(["Cloud point 1"]),
            "Overall summary of tech news.",
        ]
        client = MockLLMClient(responses=responses)
        synthesizer = ContentSynthesizer(client)
        
        result = synthesizer.synthesize(sample_items)
        
        assert len(result.topics) == 2
        assert result.source_count == 3
        assert result.overall_summary == "Overall summary of tech news."
        assert len(result.trending_themes) > 0
    
    def test_deduplicate_items_removes_duplicates(self):
        """_deduplicate_items() should remove duplicate items."""
        client = MockLLMClient()
        synthesizer = ContentSynthesizer(client)
        
        items = [
            NewsletterItem(
                source_name="Source1",
                source_type="rss",
                title="Breaking News About AI",
                content="Short content",
                published_date=datetime(2024, 1, 15),
            ),
            NewsletterItem(
                source_name="Source2",
                source_type="rss",
                title="Breaking News About AI",  # Same title
                content="Longer content with more details about the AI news",
                published_date=datetime(2024, 1, 15),
            ),
        ]
        
        result = synthesizer._deduplicate_items(items)
        
        # Should keep the one with more content
        assert len(result) == 1
        assert "Longer content" in result[0].content
    
    def test_titles_similar_exact_match(self):
        """_titles_similar() should detect exact matches."""
        client = MockLLMClient()
        synthesizer = ContentSynthesizer(client)
        
        assert synthesizer._titles_similar("hello world", "hello world") is True
    
    def test_titles_similar_high_overlap(self):
        """_titles_similar() should detect high word overlap."""
        client = MockLLMClient()
        synthesizer = ContentSynthesizer(client)
        
        # 4 out of 5 unique words match = 80% overlap (above 70% threshold)
        # words1: {new, ai, model, released}
        # words2: {new, ai, model, announced}
        # intersection: 3, union: 5 -> 60% - not enough
        # Let's use: "new ai model" vs "new ai model update"
        # words1: {new, ai, model}, words2: {new, ai, model, update}
        # intersection: 3, union: 4 -> 75%
        assert synthesizer._titles_similar(
            "new ai model",
            "new ai model update"
        ) is True
    
    def test_titles_similar_low_overlap(self):
        """_titles_similar() should reject low word overlap."""
        client = MockLLMClient()
        synthesizer = ContentSynthesizer(client)
        
        assert synthesizer._titles_similar(
            "ai news today",
            "cloud computing trends"
        ) is False
    
    def test_parse_json_response_handles_markdown(self):
        """_parse_json_response() should handle markdown code blocks."""
        client = MockLLMClient()
        synthesizer = ContentSynthesizer(client)
        
        response = '```json\n["item1", "item2"]\n```'
        result = synthesizer._parse_json_response(response)
        
        assert result == ["item1", "item2"]
    
    def test_extract_trending_themes(self, sample_items):
        """_extract_trending_themes() should return top themes by item count."""
        client = MockLLMClient()
        synthesizer = ContentSynthesizer(client)
        
        topics = [
            TopicGroup(topic="AI", description="", items=sample_items[:2], key_points=[]),
            TopicGroup(topic="Cloud", description="", items=sample_items[2:], key_points=[]),
        ]
        
        result = synthesizer._extract_trending_themes(topics)
        
        # AI has more items, should be first
        assert result[0] == "AI"
        assert "Cloud" in result
