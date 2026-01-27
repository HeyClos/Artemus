"""
Tests for data models.

This module contains unit tests for the data model classes
defined in models.py.

Validates: Requirements 2.4, 4.2, 5.3
"""

from datetime import datetime

import pytest

from newsletter_generator.models import (
    BlogPost,
    ExecutionResult,
    ExportResult,
    NewsletterItem,
    SynthesizedContent,
    TikTokScript,
    TopicGroup,
)


class TestNewsletterItem:
    """Unit tests for NewsletterItem dataclass."""

    def test_create_with_required_fields(self):
        """Test creating a NewsletterItem with only required fields."""
        item = NewsletterItem(
            source_name="TechCrunch",
            source_type="rss",
            title="Test Article",
            content="This is the article content.",
            published_date=datetime(2024, 1, 15, 10, 30, 0),
        )
        
        assert item.source_name == "TechCrunch"
        assert item.source_type == "rss"
        assert item.title == "Test Article"
        assert item.content == "This is the article content."
        assert item.published_date == datetime(2024, 1, 15, 10, 30, 0)
        assert item.html_content is None
        assert item.author is None
        assert item.url is None

    def test_create_with_all_fields(self):
        """Test creating a NewsletterItem with all fields."""
        item = NewsletterItem(
            source_name="Newsletter Weekly",
            source_type="email",
            title="Weekly Digest",
            content="Plain text content here.",
            published_date=datetime(2024, 1, 15, 10, 30, 0),
            html_content="<p>HTML content here.</p>",
            author="John Doe",
            url="https://example.com/article",
        )
        
        assert item.html_content == "<p>HTML content here.</p>"
        assert item.author == "John Doe"
        assert item.url == "https://example.com/article"

    def test_to_dict(self):
        """Test serializing NewsletterItem to dictionary."""
        item = NewsletterItem(
            source_name="TechCrunch",
            source_type="rss",
            title="Test Article",
            content="Content here.",
            published_date=datetime(2024, 1, 15, 10, 30, 0),
            author="Jane Doe",
        )
        
        result = item.to_dict()
        
        assert result["source_name"] == "TechCrunch"
        assert result["source_type"] == "rss"
        assert result["title"] == "Test Article"
        assert result["content"] == "Content here."
        assert result["published_date"] == "2024-01-15T10:30:00"
        assert result["author"] == "Jane Doe"
        assert result["html_content"] is None
        assert result["url"] is None

    def test_from_dict(self):
        """Test deserializing NewsletterItem from dictionary."""
        data = {
            "source_name": "TechCrunch",
            "source_type": "rss",
            "title": "Test Article",
            "content": "Content here.",
            "published_date": "2024-01-15T10:30:00",
            "html_content": "<p>HTML</p>",
            "author": "Jane Doe",
            "url": "https://example.com",
        }
        
        item = NewsletterItem.from_dict(data)
        
        assert item.source_name == "TechCrunch"
        assert item.source_type == "rss"
        assert item.title == "Test Article"
        assert item.content == "Content here."
        assert item.published_date == datetime(2024, 1, 15, 10, 30, 0)
        assert item.html_content == "<p>HTML</p>"
        assert item.author == "Jane Doe"
        assert item.url == "https://example.com"

    def test_round_trip_serialization(self):
        """Test that to_dict and from_dict are inverse operations."""
        original = NewsletterItem(
            source_name="Test Source",
            source_type="file",
            title="Test Title",
            content="Test content.",
            published_date=datetime(2024, 6, 20, 14, 45, 30),
            html_content="<b>Bold</b>",
            author="Author Name",
            url="https://test.com",
        )
        
        serialized = original.to_dict()
        restored = NewsletterItem.from_dict(serialized)
        
        assert restored == original


class TestTopicGroup:
    """Unit tests for TopicGroup dataclass."""

    def test_create_topic_group(self):
        """Test creating a TopicGroup with items."""
        items = [
            NewsletterItem(
                source_name="Source1",
                source_type="rss",
                title="Article 1",
                content="Content 1",
                published_date=datetime(2024, 1, 15),
            ),
            NewsletterItem(
                source_name="Source2",
                source_type="email",
                title="Article 2",
                content="Content 2",
                published_date=datetime(2024, 1, 16),
            ),
        ]
        
        group = TopicGroup(
            topic="AI Technology",
            description="Articles about artificial intelligence",
            items=items,
            key_points=["Point 1", "Point 2", "Point 3"],
        )
        
        assert group.topic == "AI Technology"
        assert group.description == "Articles about artificial intelligence"
        assert len(group.items) == 2
        assert group.key_points == ["Point 1", "Point 2", "Point 3"]

    def test_to_dict(self):
        """Test serializing TopicGroup to dictionary."""
        items = [
            NewsletterItem(
                source_name="Source1",
                source_type="rss",
                title="Article 1",
                content="Content 1",
                published_date=datetime(2024, 1, 15),
            ),
        ]
        
        group = TopicGroup(
            topic="Tech News",
            description="Latest tech news",
            items=items,
            key_points=["Key point"],
        )
        
        result = group.to_dict()
        
        assert result["topic"] == "Tech News"
        assert result["description"] == "Latest tech news"
        assert len(result["items"]) == 1
        assert result["items"][0]["source_name"] == "Source1"
        assert result["key_points"] == ["Key point"]

    def test_from_dict(self):
        """Test deserializing TopicGroup from dictionary."""
        data = {
            "topic": "Tech News",
            "description": "Latest tech news",
            "items": [
                {
                    "source_name": "Source1",
                    "source_type": "rss",
                    "title": "Article 1",
                    "content": "Content 1",
                    "published_date": "2024-01-15T00:00:00",
                    "html_content": None,
                    "author": None,
                    "url": None,
                }
            ],
            "key_points": ["Key point"],
        }
        
        group = TopicGroup.from_dict(data)
        
        assert group.topic == "Tech News"
        assert group.description == "Latest tech news"
        assert len(group.items) == 1
        assert group.items[0].source_name == "Source1"
        assert group.key_points == ["Key point"]

    def test_round_trip_serialization(self):
        """Test that to_dict and from_dict are inverse operations."""
        items = [
            NewsletterItem(
                source_name="Source1",
                source_type="rss",
                title="Article 1",
                content="Content 1",
                published_date=datetime(2024, 1, 15),
            ),
        ]
        
        original = TopicGroup(
            topic="Tech News",
            description="Latest tech news",
            items=items,
            key_points=["Key point 1", "Key point 2"],
        )
        
        serialized = original.to_dict()
        restored = TopicGroup.from_dict(serialized)
        
        assert restored == original


class TestSynthesizedContent:
    """Unit tests for SynthesizedContent dataclass."""

    def test_create_synthesized_content(self):
        """Test creating SynthesizedContent."""
        items = [
            NewsletterItem(
                source_name="Source1",
                source_type="rss",
                title="Article 1",
                content="Content 1",
                published_date=datetime(2024, 1, 15),
            ),
        ]
        topics = [
            TopicGroup(
                topic="AI",
                description="AI articles",
                items=items,
                key_points=["Point 1"],
            ),
        ]
        
        content = SynthesizedContent(
            topics=topics,
            overall_summary="This week in tech...",
            trending_themes=["AI", "Cloud", "Security"],
            source_count=5,
            date_range=(datetime(2024, 1, 8), datetime(2024, 1, 15)),
        )
        
        assert len(content.topics) == 1
        assert content.overall_summary == "This week in tech..."
        assert content.trending_themes == ["AI", "Cloud", "Security"]
        assert content.source_count == 5
        assert content.date_range == (datetime(2024, 1, 8), datetime(2024, 1, 15))

    def test_to_dict(self):
        """Test serializing SynthesizedContent to dictionary."""
        items = [
            NewsletterItem(
                source_name="Source1",
                source_type="rss",
                title="Article 1",
                content="Content 1",
                published_date=datetime(2024, 1, 15),
            ),
        ]
        topics = [
            TopicGroup(
                topic="AI",
                description="AI articles",
                items=items,
                key_points=["Point 1"],
            ),
        ]
        
        content = SynthesizedContent(
            topics=topics,
            overall_summary="Summary",
            trending_themes=["AI"],
            source_count=3,
            date_range=(datetime(2024, 1, 8), datetime(2024, 1, 15)),
        )
        
        result = content.to_dict()
        
        assert len(result["topics"]) == 1
        assert result["overall_summary"] == "Summary"
        assert result["trending_themes"] == ["AI"]
        assert result["source_count"] == 3
        assert result["date_range"] == ["2024-01-08T00:00:00", "2024-01-15T00:00:00"]

    def test_from_dict(self):
        """Test deserializing SynthesizedContent from dictionary."""
        data = {
            "topics": [
                {
                    "topic": "AI",
                    "description": "AI articles",
                    "items": [
                        {
                            "source_name": "Source1",
                            "source_type": "rss",
                            "title": "Article 1",
                            "content": "Content 1",
                            "published_date": "2024-01-15T00:00:00",
                            "html_content": None,
                            "author": None,
                            "url": None,
                        }
                    ],
                    "key_points": ["Point 1"],
                }
            ],
            "overall_summary": "Summary",
            "trending_themes": ["AI"],
            "source_count": 3,
            "date_range": ["2024-01-08T00:00:00", "2024-01-15T00:00:00"],
        }
        
        content = SynthesizedContent.from_dict(data)
        
        assert len(content.topics) == 1
        assert content.topics[0].topic == "AI"
        assert content.overall_summary == "Summary"
        assert content.trending_themes == ["AI"]
        assert content.source_count == 3
        assert content.date_range == (datetime(2024, 1, 8), datetime(2024, 1, 15))

    def test_round_trip_serialization(self):
        """Test that to_dict and from_dict are inverse operations."""
        items = [
            NewsletterItem(
                source_name="Source1",
                source_type="rss",
                title="Article 1",
                content="Content 1",
                published_date=datetime(2024, 1, 15),
            ),
        ]
        topics = [
            TopicGroup(
                topic="AI",
                description="AI articles",
                items=items,
                key_points=["Point 1"],
            ),
        ]
        
        original = SynthesizedContent(
            topics=topics,
            overall_summary="Summary",
            trending_themes=["AI", "Cloud"],
            source_count=5,
            date_range=(datetime(2024, 1, 8), datetime(2024, 1, 15)),
        )
        
        serialized = original.to_dict()
        restored = SynthesizedContent.from_dict(serialized)
        
        assert restored == original


class TestBlogPost:
    """Unit tests for BlogPost dataclass."""

    def test_create_blog_post(self):
        """Test creating a BlogPost."""
        post = BlogPost(
            title="Weekly Tech Roundup",
            content="# Weekly Tech Roundup\n\nThis week...",
            word_count=500,
            sources=["TechCrunch", "Hacker News"],
            generated_at=datetime(2024, 1, 15, 12, 0, 0),
        )
        
        assert post.title == "Weekly Tech Roundup"
        assert post.content.startswith("# Weekly Tech Roundup")
        assert post.word_count == 500
        assert post.sources == ["TechCrunch", "Hacker News"]
        assert post.generated_at == datetime(2024, 1, 15, 12, 0, 0)

    def test_to_dict(self):
        """Test serializing BlogPost to dictionary."""
        post = BlogPost(
            title="Tech News",
            content="Content here",
            word_count=100,
            sources=["Source1"],
            generated_at=datetime(2024, 1, 15, 12, 0, 0),
        )
        
        result = post.to_dict()
        
        assert result["title"] == "Tech News"
        assert result["content"] == "Content here"
        assert result["word_count"] == 100
        assert result["sources"] == ["Source1"]
        assert result["generated_at"] == "2024-01-15T12:00:00"

    def test_from_dict(self):
        """Test deserializing BlogPost from dictionary."""
        data = {
            "title": "Tech News",
            "content": "Content here",
            "word_count": 100,
            "sources": ["Source1"],
            "generated_at": "2024-01-15T12:00:00",
        }
        
        post = BlogPost.from_dict(data)
        
        assert post.title == "Tech News"
        assert post.content == "Content here"
        assert post.word_count == 100
        assert post.sources == ["Source1"]
        assert post.generated_at == datetime(2024, 1, 15, 12, 0, 0)

    def test_round_trip_serialization(self):
        """Test that to_dict and from_dict are inverse operations."""
        original = BlogPost(
            title="Weekly Tech Roundup",
            content="# Weekly Tech Roundup\n\nThis week...",
            word_count=500,
            sources=["TechCrunch", "Hacker News"],
            generated_at=datetime(2024, 1, 15, 12, 0, 0),
        )
        
        serialized = original.to_dict()
        restored = BlogPost.from_dict(serialized)
        
        assert restored == original


class TestTikTokScript:
    """Unit tests for TikTokScript dataclass."""

    def test_create_tiktok_script_with_visual_cues(self):
        """Test creating a TikTokScript with visual cues."""
        script = TikTokScript(
            title="AI News This Week",
            hook="You won't believe what happened in AI this week!",
            main_points=["Point 1", "Point 2", "Point 3"],
            call_to_action="Follow for more tech updates!",
            visual_cues=["Show AI logo", "Display chart"],
            duration_seconds=60,
            full_script="Full script text here...",
            generated_at=datetime(2024, 1, 15, 12, 0, 0),
        )
        
        assert script.title == "AI News This Week"
        assert script.hook == "You won't believe what happened in AI this week!"
        assert len(script.main_points) == 3
        assert script.call_to_action == "Follow for more tech updates!"
        assert script.visual_cues == ["Show AI logo", "Display chart"]
        assert script.duration_seconds == 60
        assert script.full_script == "Full script text here..."
        assert script.generated_at == datetime(2024, 1, 15, 12, 0, 0)

    def test_create_tiktok_script_without_visual_cues(self):
        """Test creating a TikTokScript without visual cues."""
        script = TikTokScript(
            title="Quick Tech Update",
            hook="Here's what you need to know!",
            main_points=["Point 1"],
            call_to_action="Like and follow!",
            visual_cues=None,
            duration_seconds=15,
            full_script="Short script...",
            generated_at=datetime(2024, 1, 15, 12, 0, 0),
        )
        
        assert script.visual_cues is None

    def test_to_dict(self):
        """Test serializing TikTokScript to dictionary."""
        script = TikTokScript(
            title="AI News",
            hook="Hook text",
            main_points=["Point 1"],
            call_to_action="Follow!",
            visual_cues=["Cue 1"],
            duration_seconds=30,
            full_script="Full script",
            generated_at=datetime(2024, 1, 15, 12, 0, 0),
        )
        
        result = script.to_dict()
        
        assert result["title"] == "AI News"
        assert result["hook"] == "Hook text"
        assert result["main_points"] == ["Point 1"]
        assert result["call_to_action"] == "Follow!"
        assert result["visual_cues"] == ["Cue 1"]
        assert result["duration_seconds"] == 30
        assert result["full_script"] == "Full script"
        assert result["generated_at"] == "2024-01-15T12:00:00"

    def test_from_dict(self):
        """Test deserializing TikTokScript from dictionary."""
        data = {
            "title": "AI News",
            "hook": "Hook text",
            "main_points": ["Point 1"],
            "call_to_action": "Follow!",
            "visual_cues": ["Cue 1"],
            "duration_seconds": 30,
            "full_script": "Full script",
            "generated_at": "2024-01-15T12:00:00",
        }
        
        script = TikTokScript.from_dict(data)
        
        assert script.title == "AI News"
        assert script.hook == "Hook text"
        assert script.main_points == ["Point 1"]
        assert script.call_to_action == "Follow!"
        assert script.visual_cues == ["Cue 1"]
        assert script.duration_seconds == 30
        assert script.full_script == "Full script"
        assert script.generated_at == datetime(2024, 1, 15, 12, 0, 0)

    def test_from_dict_without_visual_cues(self):
        """Test deserializing TikTokScript without visual cues."""
        data = {
            "title": "AI News",
            "hook": "Hook text",
            "main_points": ["Point 1"],
            "call_to_action": "Follow!",
            "duration_seconds": 30,
            "full_script": "Full script",
            "generated_at": "2024-01-15T12:00:00",
        }
        
        script = TikTokScript.from_dict(data)
        
        assert script.visual_cues is None

    def test_round_trip_serialization(self):
        """Test that to_dict and from_dict are inverse operations."""
        original = TikTokScript(
            title="AI News This Week",
            hook="You won't believe what happened!",
            main_points=["Point 1", "Point 2"],
            call_to_action="Follow for more!",
            visual_cues=["Show logo", "Display chart"],
            duration_seconds=60,
            full_script="Full script text...",
            generated_at=datetime(2024, 1, 15, 12, 0, 0),
        )
        
        serialized = original.to_dict()
        restored = TikTokScript.from_dict(serialized)
        
        assert restored == original


class TestExportResult:
    """Unit tests for ExportResult dataclass."""

    def test_create_successful_export(self):
        """Test creating a successful ExportResult."""
        result = ExportResult(
            success=True,
            folder="Generated Blog Posts",
            note_id="note-123",
        )
        
        assert result.success is True
        assert result.folder == "Generated Blog Posts"
        assert result.note_id == "note-123"
        assert result.error is None
        assert result.fallback_path is None

    def test_create_failed_export_with_fallback(self):
        """Test creating a failed ExportResult with fallback."""
        result = ExportResult(
            success=False,
            folder="Generated Blog Posts",
            error="Apple Notes unavailable",
            fallback_path="/tmp/blog_post.md",
        )
        
        assert result.success is False
        assert result.folder == "Generated Blog Posts"
        assert result.note_id is None
        assert result.error == "Apple Notes unavailable"
        assert result.fallback_path == "/tmp/blog_post.md"

    def test_to_dict(self):
        """Test serializing ExportResult to dictionary."""
        result = ExportResult(
            success=True,
            folder="Blog Posts",
            note_id="note-123",
        )
        
        data = result.to_dict()
        
        assert data["success"] is True
        assert data["folder"] == "Blog Posts"
        assert data["note_id"] == "note-123"
        assert data["error"] is None
        assert data["fallback_path"] is None

    def test_from_dict(self):
        """Test deserializing ExportResult from dictionary."""
        data = {
            "success": False,
            "folder": "Blog Posts",
            "note_id": None,
            "error": "Connection failed",
            "fallback_path": "/tmp/backup.md",
        }
        
        result = ExportResult.from_dict(data)
        
        assert result.success is False
        assert result.folder == "Blog Posts"
        assert result.note_id is None
        assert result.error == "Connection failed"
        assert result.fallback_path == "/tmp/backup.md"

    def test_round_trip_serialization(self):
        """Test that to_dict and from_dict are inverse operations."""
        original = ExportResult(
            success=True,
            folder="Generated Blog Posts",
            note_id="note-456",
            error=None,
            fallback_path=None,
        )
        
        serialized = original.to_dict()
        restored = ExportResult.from_dict(serialized)
        
        assert restored == original


class TestExecutionResult:
    """Unit tests for ExecutionResult dataclass."""

    def test_create_successful_execution(self):
        """Test creating a successful ExecutionResult."""
        blog_export = ExportResult(
            success=True,
            folder="Blog Posts",
            note_id="blog-123",
        )
        tiktok_export = ExportResult(
            success=True,
            folder="TikTok Scripts",
            note_id="tiktok-456",
        )
        
        result = ExecutionResult(
            success=True,
            newsletters_processed=10,
            errors=[],
            dry_run=False,
            blog_exported=blog_export,
            tiktok_exported=tiktok_export,
        )
        
        assert result.success is True
        assert result.newsletters_processed == 10
        assert result.errors == []
        assert result.dry_run is False
        assert result.blog_exported is not None
        assert result.tiktok_exported is not None

    def test_create_dry_run_execution(self):
        """Test creating a dry-run ExecutionResult."""
        result = ExecutionResult(
            success=True,
            newsletters_processed=5,
            errors=[],
            dry_run=True,
        )
        
        assert result.success is True
        assert result.dry_run is True
        assert result.blog_exported is None
        assert result.tiktok_exported is None

    def test_create_failed_execution(self):
        """Test creating a failed ExecutionResult with errors."""
        result = ExecutionResult(
            success=False,
            newsletters_processed=0,
            errors=["Failed to connect to email", "RSS feed timeout"],
            dry_run=False,
        )
        
        assert result.success is False
        assert result.newsletters_processed == 0
        assert len(result.errors) == 2
        assert "Failed to connect to email" in result.errors

    def test_to_dict(self):
        """Test serializing ExecutionResult to dictionary."""
        blog_export = ExportResult(
            success=True,
            folder="Blog Posts",
            note_id="blog-123",
        )
        
        result = ExecutionResult(
            success=True,
            newsletters_processed=10,
            errors=[],
            dry_run=False,
            blog_exported=blog_export,
        )
        
        data = result.to_dict()
        
        assert data["success"] is True
        assert data["newsletters_processed"] == 10
        assert data["errors"] == []
        assert data["dry_run"] is False
        assert data["blog_exported"]["note_id"] == "blog-123"
        assert data["tiktok_exported"] is None

    def test_from_dict(self):
        """Test deserializing ExecutionResult from dictionary."""
        data = {
            "success": True,
            "newsletters_processed": 10,
            "errors": [],
            "dry_run": False,
            "blog_exported": {
                "success": True,
                "folder": "Blog Posts",
                "note_id": "blog-123",
                "error": None,
                "fallback_path": None,
            },
            "tiktok_exported": None,
        }
        
        result = ExecutionResult.from_dict(data)
        
        assert result.success is True
        assert result.newsletters_processed == 10
        assert result.errors == []
        assert result.dry_run is False
        assert result.blog_exported is not None
        assert result.blog_exported.note_id == "blog-123"
        assert result.tiktok_exported is None

    def test_round_trip_serialization(self):
        """Test that to_dict and from_dict are inverse operations."""
        blog_export = ExportResult(
            success=True,
            folder="Blog Posts",
            note_id="blog-123",
        )
        tiktok_export = ExportResult(
            success=True,
            folder="TikTok Scripts",
            note_id="tiktok-456",
        )
        
        original = ExecutionResult(
            success=True,
            newsletters_processed=10,
            errors=["Warning: slow connection"],
            dry_run=False,
            blog_exported=blog_export,
            tiktok_exported=tiktok_export,
        )
        
        serialized = original.to_dict()
        restored = ExecutionResult.from_dict(serialized)
        
        assert restored == original
