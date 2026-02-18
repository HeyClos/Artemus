"""
Tests for application orchestrator.

This module contains unit tests and property-based tests for the
NewsletterContentGenerator orchestrator.

Property tests:
- Property 13: Dry-Run Mode (Validates: Requirements 7.4)
"""

from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from newsletter_generator.config import (
    AppConfig,
    BlogConfig,
    EmailSourceConfig,
    FileSourceConfig,
    LLMConfig,
    NotesConfig,
    RSSSourceConfig,
    TikTokConfig,
)
from newsletter_generator.models import (
    BlogPost,
    ExecutionResult,
    ExportResult,
    NewsletterItem,
    SynthesizedContent,
    TikTokScript,
    TopicGroup,
)
from newsletter_generator.orchestrator import NewsletterContentGenerator


# =============================================================================
# Mock Components for Testing
# =============================================================================

class MockLLMClient:
    """Mock LLM client for testing."""
    
    def complete(self, prompt: str, system: str | None = None) -> str:
        """Return deterministic responses based on prompt content."""
        import json
        
        if "TikTok" in prompt or "tiktok" in prompt.lower():
            return json.dumps({
                "title": "Tech Update",
                "hook": "Stop scrolling!",
                "main_points": ["AI is changing everything", "New tools are here"],
                "call_to_action": "Follow for more!",
                "visual_cues": ["Show tech logos", "Display stats"],
            })
        elif "topic" in prompt.lower() and "group" in prompt.lower():
            return json.dumps([
                {"topic": "AI Development", "description": "AI news", "item_indices": [0]}
            ])
        elif "key point" in prompt.lower():
            return json.dumps(["Key point 1", "Key point 2"])
        else:
            return "Tech Trends\n\n# Tech Trends\n\nThis week in tech..."


class MockAggregator:
    """Mock aggregator for testing."""
    
    def __init__(self, items: list[NewsletterItem] | None = None):
        self.items = items or []
        self.aggregate_called = False
    
    def aggregate(self, since: datetime) -> list[NewsletterItem]:
        self.aggregate_called = True
        return self.items


class MockSynthesizer:
    """Mock synthesizer for testing."""
    
    def __init__(self, content: SynthesizedContent | None = None):
        self.content = content
        self.synthesize_called = False
    
    def synthesize(self, items: list[NewsletterItem]) -> SynthesizedContent:
        self.synthesize_called = True
        if self.content:
            return self.content
        return SynthesizedContent(
            topics=[],
            overall_summary="Test summary",
            trending_themes=["AI"],
            source_count=len(items),
            date_range=(datetime.now(), datetime.now()),
        )


class MockBlogGenerator:
    """Mock blog generator for testing."""
    
    def __init__(self, post: BlogPost | None = None):
        self.post = post
        self.generate_called = False
    
    def generate(self, content: SynthesizedContent) -> BlogPost:
        self.generate_called = True
        if self.post:
            return self.post
        return BlogPost(
            title="Test Blog Post",
            content="# Test\n\nContent here",
            word_count=100,
            sources=["Source1"],
            generated_at=datetime.now(),
        )


class MockTikTokGenerator:
    """Mock TikTok generator for testing."""
    
    def __init__(self, script: TikTokScript | None = None):
        self.script = script
        self.generate_called = False
    
    def generate(self, content: SynthesizedContent) -> TikTokScript:
        self.generate_called = True
        if self.script:
            return self.script
        return TikTokScript(
            title="Test Script",
            hook="Stop scrolling!",
            main_points=["Point 1", "Point 2"],
            call_to_action="Follow!",
            visual_cues=["Cue 1"],
            duration_seconds=60,
            full_script="Stop scrolling! Point 1. Point 2. Follow!",
            generated_at=datetime.now(),
        )


class MockExporter:
    """Mock exporter for testing."""
    
    def __init__(self, blog_result: ExportResult | None = None, tiktok_result: ExportResult | None = None):
        self.blog_result = blog_result or ExportResult(
            success=True, folder="Blog", note_id="note-123"
        )
        self.tiktok_result = tiktok_result or ExportResult(
            success=True, folder="TikTok", note_id="note-456"
        )
        self.export_blog_called = False
        self.export_tiktok_called = False
    
    def export_blog(self, post: BlogPost) -> ExportResult:
        self.export_blog_called = True
        return self.blog_result
    
    def export_tiktok(self, script: TikTokScript) -> ExportResult:
        self.export_tiktok_called = True
        return self.tiktok_result


# =============================================================================
# Hypothesis Strategies
# =============================================================================

@st.composite
def valid_app_config(draw: st.DrawFn) -> AppConfig:
    """Generate valid AppConfig objects for testing."""
    return AppConfig(
        llm=LLMConfig(
            provider="openai",
            model="gpt-4o",
            api_key_env="OPENAI_API_KEY",
            max_tokens=4096,
        ),
        blog=BlogConfig(
            format=draw(st.sampled_from(["long-form", "summary", "listicle"])),
            target_words=draw(st.integers(min_value=200, max_value=2000)),
            include_sources=draw(st.booleans()),
        ),
        tiktok=TikTokConfig(
            duration=draw(st.sampled_from([15, 30, 60])),
            include_visual_cues=draw(st.booleans()),
            style=draw(st.sampled_from(["educational", "entertaining", "news"])),
        ),
        notes=NotesConfig(
            account="iCloud",
            blog_folder="Generated Blog Posts",
            tiktok_folder="TikTok Scripts",
        ),
        rss_sources=[
            RSSSourceConfig(url="https://example.com/feed", name="Test Feed")
        ],
        date_range_days=draw(st.integers(min_value=1, max_value=30)),
    )


@st.composite
def valid_newsletter_items(draw: st.DrawFn, min_items: int = 1, max_items: int = 5) -> list[NewsletterItem]:
    """Generate a list of valid NewsletterItem objects."""
    num_items = draw(st.integers(min_value=min_items, max_value=max_items))
    items = []
    for i in range(num_items):
        items.append(NewsletterItem(
            source_name=f"Source {i}",
            source_type=draw(st.sampled_from(["email", "rss", "file"])),
            title=f"Newsletter {i}",
            content=f"Content for newsletter {i} with some text.",
            published_date=datetime(2024, 1, 15, tzinfo=timezone.utc),
        ))
    return items


@st.composite
def valid_synthesized_content(draw: st.DrawFn) -> SynthesizedContent:
    """Generate valid SynthesizedContent for testing."""
    items = draw(valid_newsletter_items(min_items=1, max_items=3))
    topic = TopicGroup(
        topic="Test Topic",
        description="Test description",
        items=items,
        key_points=["Point 1", "Point 2"],
    )
    return SynthesizedContent(
        topics=[topic],
        overall_summary="Test summary of content",
        trending_themes=["AI", "Cloud"],
        source_count=len(items),
        date_range=(datetime(2024, 1, 14), datetime(2024, 1, 15)),
    )


# =============================================================================
# Unit Tests for NewsletterContentGenerator
# =============================================================================

class TestNewsletterContentGenerator:
    """Unit tests for NewsletterContentGenerator."""
    
    @pytest.fixture
    def sample_config(self) -> AppConfig:
        """Create a sample configuration for testing."""
        return AppConfig(
            llm=LLMConfig(
                provider="openai",
                model="gpt-4o",
                api_key_env="OPENAI_API_KEY",
                max_tokens=4096,
            ),
            blog=BlogConfig(
                format="long-form",
                target_words=500,
                include_sources=True,
            ),
            tiktok=TikTokConfig(
                duration=60,
                include_visual_cues=True,
                style="educational",
            ),
            notes=NotesConfig(
                account="iCloud",
                blog_folder="Blog Posts",
                tiktok_folder="TikTok Scripts",
            ),
            rss_sources=[
                RSSSourceConfig(url="https://example.com/feed", name="Test")
            ],
            date_range_days=7,
        )
    
    @pytest.fixture
    def sample_items(self) -> list[NewsletterItem]:
        """Create sample newsletter items for testing."""
        return [
            NewsletterItem(
                source_name="TechCrunch",
                source_type="rss",
                title="AI News",
                content="AI developments this week...",
                published_date=datetime(2024, 1, 15, tzinfo=timezone.utc),
            )
        ]
    
    def test_run_dry_run_does_not_export(self, sample_config: AppConfig, sample_items: list[NewsletterItem]) -> None:
        """Test that dry-run mode does not call export methods."""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            generator = NewsletterContentGenerator(sample_config)
            
            # Replace components with mocks
            mock_aggregator = MockAggregator(sample_items)
            mock_synthesizer = MockSynthesizer()
            mock_blog_gen = MockBlogGenerator()
            mock_tiktok_gen = MockTikTokGenerator()
            mock_exporter = MockExporter()
            
            generator._aggregator = mock_aggregator
            generator._synthesizer = mock_synthesizer
            generator._blog_generator = mock_blog_gen
            generator._tiktok_generator = mock_tiktok_gen
            generator._exporter = mock_exporter
            
            # Run in dry-run mode
            result = generator.run(dry_run=True)
            
            # Verify export was NOT called
            assert not mock_exporter.export_blog_called
            assert not mock_exporter.export_tiktok_called
            
            # Verify other stages were called
            assert mock_aggregator.aggregate_called
            assert mock_synthesizer.synthesize_called
            assert mock_blog_gen.generate_called
            assert mock_tiktok_gen.generate_called
    
    def test_run_dry_run_returns_none_note_ids(self, sample_config: AppConfig, sample_items: list[NewsletterItem]) -> None:
        """Test that dry-run mode returns None for note_id fields."""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            generator = NewsletterContentGenerator(sample_config)
            
            # Replace components with mocks
            generator._aggregator = MockAggregator(sample_items)
            generator._synthesizer = MockSynthesizer()
            generator._blog_generator = MockBlogGenerator()
            generator._tiktok_generator = MockTikTokGenerator()
            generator._exporter = MockExporter()
            
            result = generator.run(dry_run=True)
            
            # Verify note_id is None for both exports
            assert result.blog_exported is not None
            assert result.blog_exported.note_id is None
            assert result.tiktok_exported is not None
            assert result.tiktok_exported.note_id is None
    
    def test_run_normal_mode_exports(self, sample_config: AppConfig, sample_items: list[NewsletterItem]) -> None:
        """Test that normal mode calls export methods."""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            generator = NewsletterContentGenerator(sample_config)
            
            # Replace components with mocks
            mock_exporter = MockExporter()
            generator._aggregator = MockAggregator(sample_items)
            generator._synthesizer = MockSynthesizer()
            generator._blog_generator = MockBlogGenerator()
            generator._tiktok_generator = MockTikTokGenerator()
            generator._exporter = mock_exporter
            
            result = generator.run(dry_run=False)
            
            # Verify export WAS called
            assert mock_exporter.export_blog_called
            assert mock_exporter.export_tiktok_called
    
    def test_run_with_no_newsletters(self, sample_config: AppConfig) -> None:
        """Test behavior when no newsletters are found."""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            generator = NewsletterContentGenerator(sample_config)
            
            # Replace aggregator with one that returns empty list
            generator._aggregator = MockAggregator([])
            
            result = generator.run(dry_run=False)
            
            assert result.success is True
            assert result.newsletters_processed == 0
            assert "No newsletters found" in result.errors[0]
    
    def test_progress_callback_is_called(self, sample_config: AppConfig, sample_items: list[NewsletterItem]) -> None:
        """Test that progress callback is called during execution."""
        progress_calls: list[tuple[str, str]] = []
        
        def progress_callback(stage: str, message: str) -> None:
            progress_calls.append((stage, message))
        
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            generator = NewsletterContentGenerator(sample_config, progress_callback=progress_callback)
            
            # Replace components with mocks
            generator._aggregator = MockAggregator(sample_items)
            generator._synthesizer = MockSynthesizer()
            generator._blog_generator = MockBlogGenerator()
            generator._tiktok_generator = MockTikTokGenerator()
            generator._exporter = MockExporter()
            
            generator.run(dry_run=True)
            
            # Verify progress was reported
            assert len(progress_calls) > 0
            stages = [call[0] for call in progress_calls]
            assert "aggregation" in stages
            assert "synthesis" in stages
            assert "generation" in stages


# =============================================================================
# Property-Based Tests
# =============================================================================

class TestOrchestratorProperties:
    """Property-based tests for the orchestrator."""
    
    @pytest.mark.property
    @given(
        config=valid_app_config(),
        items=valid_newsletter_items(min_items=1, max_items=5),
    )
    @settings(max_examples=20, deadline=15000)
    def test_dry_run_mode(
        self, config: AppConfig, items: list[NewsletterItem]
    ) -> None:
        """
        Property 13: Dry-Run Mode
        
        **Validates: Requirements 7.4**
        
        For any execution with dry_run=True, the ExecutionResult should
        contain generated content (blog_exported and tiktok_exported with
        content) but no actual notes should be created (verified by note_id
        being None).
        """
        assume(len(items) > 0)
        
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            generator = NewsletterContentGenerator(config)
            
            # Replace components with mocks
            mock_exporter = MockExporter()
            generator._aggregator = MockAggregator(items)
            generator._synthesizer = MockSynthesizer()
            generator._blog_generator = MockBlogGenerator()
            generator._tiktok_generator = MockTikTokGenerator()
            generator._exporter = mock_exporter
            
            # Run in dry-run mode
            result = generator.run(dry_run=True)
            
            # Property: dry_run flag should be True in result
            assert result.dry_run is True, "ExecutionResult.dry_run should be True"
            
            # Property: Export results should exist
            assert result.blog_exported is not None, "blog_exported should not be None"
            assert result.tiktok_exported is not None, "tiktok_exported should not be None"
            
            # Property: note_id should be None (no actual notes created)
            assert result.blog_exported.note_id is None, (
                "blog_exported.note_id should be None in dry-run mode"
            )
            assert result.tiktok_exported.note_id is None, (
                "tiktok_exported.note_id should be None in dry-run mode"
            )
            
            # Property: Export methods should NOT have been called
            assert not mock_exporter.export_blog_called, (
                "export_blog should not be called in dry-run mode"
            )
            assert not mock_exporter.export_tiktok_called, (
                "export_tiktok should not be called in dry-run mode"
            )
            
            # Property: Newsletters should still be processed
            assert result.newsletters_processed == len(items), (
                f"Expected {len(items)} newsletters processed, got {result.newsletters_processed}"
            )
            
            # Property: Success should be True (content was generated)
            assert result.success is True, "Execution should succeed in dry-run mode"
