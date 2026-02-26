"""
Data models for Newsletter Content Generator.

This module defines the core data structures used throughout the application
for representing newsletter content, synthesized data, and generated outputs.

Validates: Requirements 2.4, 4.2, 5.3
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    pass


@dataclass
class NewsletterItem:
    """Represents a single newsletter item from any source.
    
    This is the normalized internal format for newsletter content,
    regardless of whether it came from email, RSS, or file sources.
    
    Attributes:
        source_name: Human-readable name of the source
        source_type: Type of source ("email", "rss", "file")
        title: Title or subject of the newsletter item
        content: Plain text content of the newsletter
        published_date: When the newsletter was published
        html_content: Original HTML content if available
        author: Author name if available
        url: URL to the original content if available
    """
    source_name: str
    source_type: str
    title: str
    content: str
    published_date: datetime
    html_content: str | None = None
    author: str | None = None
    url: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize the NewsletterItem to a dictionary.
        
        Returns:
            Dictionary representation of the NewsletterItem with datetime
            converted to ISO format string.
        """
        return {
            "source_name": self.source_name,
            "source_type": self.source_type,
            "title": self.title,
            "content": self.content,
            "published_date": self.published_date.isoformat(),
            "html_content": self.html_content,
            "author": self.author,
            "url": self.url,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> NewsletterItem:
        """Create a NewsletterItem from a dictionary.
        
        Args:
            data: Dictionary containing NewsletterItem fields.
            
        Returns:
            A new NewsletterItem instance.
        """
        return cls(
            source_name=data["source_name"],
            source_type=data["source_type"],
            title=data["title"],
            content=data["content"],
            published_date=datetime.fromisoformat(data["published_date"]),
            html_content=data.get("html_content"),
            author=data.get("author"),
            url=data.get("url"),
        )


@dataclass
class TopicGroup:
    """Represents a group of related newsletter items by topic.
    
    Created by the ContentSynthesizer when grouping content by theme.
    
    Attributes:
        topic: The topic or theme name
        description: Brief description of the topic
        items: Newsletter items belonging to this topic
        key_points: Key points extracted from the grouped items
    """
    topic: str
    description: str
    items: list[NewsletterItem]
    key_points: list[str]

    def to_dict(self) -> dict[str, Any]:
        """Serialize the TopicGroup to a dictionary.
        
        Returns:
            Dictionary representation of the TopicGroup with nested
            NewsletterItems serialized.
        """
        return {
            "topic": self.topic,
            "description": self.description,
            "items": [item.to_dict() for item in self.items],
            "key_points": self.key_points,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TopicGroup:
        """Create a TopicGroup from a dictionary.
        
        Args:
            data: Dictionary containing TopicGroup fields.
            
        Returns:
            A new TopicGroup instance.
        """
        return cls(
            topic=data["topic"],
            description=data["description"],
            items=[NewsletterItem.from_dict(item) for item in data["items"]],
            key_points=data["key_points"],
        )


@dataclass
class SynthesizedContent:
    """Represents the fully synthesized newsletter content.
    
    This is the output of the ContentSynthesizer and serves as input
    to the content generators (BlogGenerator, TikTokScriptGenerator).
    
    Attributes:
        topics: List of topic groups with their content
        overall_summary: Consolidated summary of all content
        trending_themes: List of trending themes identified
        source_count: Number of sources processed
        date_range: Tuple of (start_date, end_date) for processed content
    """
    topics: list[TopicGroup]
    overall_summary: str
    trending_themes: list[str]
    source_count: int
    date_range: tuple[datetime, datetime]

    def to_dict(self) -> dict[str, Any]:
        """Serialize the SynthesizedContent to a dictionary.
        
        Returns:
            Dictionary representation of the SynthesizedContent with nested
            TopicGroups serialized and date_range converted to ISO format.
        """
        return {
            "topics": [topic.to_dict() for topic in self.topics],
            "overall_summary": self.overall_summary,
            "trending_themes": self.trending_themes,
            "source_count": self.source_count,
            "date_range": [
                self.date_range[0].isoformat(),
                self.date_range[1].isoformat(),
            ],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SynthesizedContent:
        """Create a SynthesizedContent from a dictionary.
        
        Args:
            data: Dictionary containing SynthesizedContent fields.
            
        Returns:
            A new SynthesizedContent instance.
        """
        return cls(
            topics=[TopicGroup.from_dict(topic) for topic in data["topics"]],
            overall_summary=data["overall_summary"],
            trending_themes=data["trending_themes"],
            source_count=data["source_count"],
            date_range=(
                datetime.fromisoformat(data["date_range"][0]),
                datetime.fromisoformat(data["date_range"][1]),
            ),
        )


@dataclass
class BlogPost:
    """Represents a generated blog post.
    
    Attributes:
        title: Blog post title
        content: Markdown-formatted blog content
        word_count: Number of words in the content
        sources: List of source names attributed in the post
        generated_at: When the post was generated
    """
    title: str
    content: str
    word_count: int
    sources: list[str]
    generated_at: datetime

    def to_dict(self) -> dict[str, Any]:
        """Serialize the BlogPost to a dictionary.
        
        Returns:
            Dictionary representation of the BlogPost with datetime
            converted to ISO format string.
        """
        return {
            "title": self.title,
            "content": self.content,
            "word_count": self.word_count,
            "sources": self.sources,
            "generated_at": self.generated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BlogPost:
        """Create a BlogPost from a dictionary.
        
        Args:
            data: Dictionary containing BlogPost fields.
            
        Returns:
            A new BlogPost instance.
        """
        return cls(
            title=data["title"],
            content=data["content"],
            word_count=data["word_count"],
            sources=data["sources"],
            generated_at=datetime.fromisoformat(data["generated_at"]),
        )


@dataclass
class TikTokScript:
    """Represents a generated TikTok script.
    
    Attributes:
        title: Script title
        hook: Attention-grabbing opening line
        main_points: List of main talking points
        call_to_action: Closing call-to-action
        visual_cues: List of visual direction cues (if enabled)
        duration_seconds: Target duration in seconds
        full_script: Complete script text
        generated_at: When the script was generated
    """
    title: str
    hook: str
    main_points: list[str]
    call_to_action: str
    visual_cues: list[str] | None
    duration_seconds: int
    full_script: str
    generated_at: datetime

    def to_dict(self) -> dict[str, Any]:
        """Serialize the TikTokScript to a dictionary.
        
        Returns:
            Dictionary representation of the TikTokScript with datetime
            converted to ISO format string.
        """
        return {
            "title": self.title,
            "hook": self.hook,
            "main_points": self.main_points,
            "call_to_action": self.call_to_action,
            "visual_cues": self.visual_cues,
            "duration_seconds": self.duration_seconds,
            "full_script": self.full_script,
            "generated_at": self.generated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TikTokScript:
        """Create a TikTokScript from a dictionary.
        
        Args:
            data: Dictionary containing TikTokScript fields.
            
        Returns:
            A new TikTokScript instance.
        """
        return cls(
            title=data["title"],
            hook=data["hook"],
            main_points=data["main_points"],
            call_to_action=data["call_to_action"],
            visual_cues=data.get("visual_cues"),
            duration_seconds=data["duration_seconds"],
            full_script=data["full_script"],
            generated_at=datetime.fromisoformat(data["generated_at"]),
        )


@dataclass
class ExportResult:
    """Represents the result of exporting content to Apple Notes.
    
    Attributes:
        success: Whether the export was successful
        note_id: ID of the created note (if successful)
        folder: Folder where the note was saved
        error: Error message if export failed
        fallback_path: Path to fallback file if Notes was unavailable
    """
    success: bool
    folder: str
    note_id: str | None = None
    error: str | None = None
    fallback_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize the ExportResult to a dictionary.
        
        Returns:
            Dictionary representation of the ExportResult.
        """
        return {
            "success": self.success,
            "folder": self.folder,
            "note_id": self.note_id,
            "error": self.error,
            "fallback_path": self.fallback_path,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExportResult:
        """Create an ExportResult from a dictionary.
        
        Args:
            data: Dictionary containing ExportResult fields.
            
        Returns:
            A new ExportResult instance.
        """
        return cls(
            success=data["success"],
            folder=data["folder"],
            note_id=data.get("note_id"),
            error=data.get("error"),
            fallback_path=data.get("fallback_path"),
        )


@dataclass
class ExecutionResult:
    """Represents the result of a full pipeline execution.
    
    Attributes:
        success: Whether the execution completed successfully
        newsletters_processed: Number of newsletters processed
        blog_exported: Result of blog post export
        tiktok_exported: Result of TikTok script export
        errors: List of errors encountered during execution
        dry_run: Whether this was a dry-run execution
    """
    success: bool
    newsletters_processed: int
    errors: list[str]
    dry_run: bool
    blog_exported: ExportResult | None = None
    tiktok_exported: ExportResult | None = None
    blog_content: "BlogPost | None" = None
    tiktok_content: "TikTokScript | None" = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize the ExecutionResult to a dictionary.
        
        Returns:
            Dictionary representation of the ExecutionResult with nested
            ExportResults serialized.
        """
        return {
            "success": self.success,
            "newsletters_processed": self.newsletters_processed,
            "errors": self.errors,
            "dry_run": self.dry_run,
            "blog_exported": self.blog_exported.to_dict() if self.blog_exported else None,
            "tiktok_exported": self.tiktok_exported.to_dict() if self.tiktok_exported else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExecutionResult:
        """Create an ExecutionResult from a dictionary.
        
        Args:
            data: Dictionary containing ExecutionResult fields.
            
        Returns:
            A new ExecutionResult instance.
        """
        return cls(
            success=data["success"],
            newsletters_processed=data["newsletters_processed"],
            errors=data["errors"],
            dry_run=data["dry_run"],
            blog_exported=ExportResult.from_dict(data["blog_exported"]) if data.get("blog_exported") else None,
            tiktok_exported=ExportResult.from_dict(data["tiktok_exported"]) if data.get("tiktok_exported") else None,
        )
