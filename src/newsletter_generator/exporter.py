"""
Apple Notes export components for Newsletter Content Generator.

This module provides the NotesExporter class for saving generated
content to Apple Notes using the macnotesapp library.

Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from newsletter_generator.config import NotesConfig
    from newsletter_generator.models import BlogPost, ExportResult, TikTokScript


class NotesExporter:
    """Exports generated content to Apple Notes.
    
    Uses the macnotesapp library to create notes in Apple Notes,
    with fallback to local file storage if Notes is unavailable.
    
    Attributes:
        config: Notes export configuration
        fallback_dir: Directory for fallback file storage
    """
    
    # Default fallback directory for when Notes is unavailable
    DEFAULT_FALLBACK_DIR = "~/newsletter_generator_output"
    
    def __init__(
        self,
        config: "NotesConfig",
        fallback_dir: str | None = None,
    ) -> None:
        """Initialize the Notes exporter.
        
        Args:
            config: Notes export configuration
            fallback_dir: Optional custom fallback directory path
        """
        self.config = config
        self.fallback_dir = Path(
            os.path.expanduser(fallback_dir or self.DEFAULT_FALLBACK_DIR)
        )
        self._notes_app = None  # Lazy initialization
        self._notes_available: bool | None = None
    
    def _get_notes_app(self) -> Any:
        """Get or initialize the NotesApp instance.
        
        Returns:
            NotesApp instance or None if unavailable
        """
        if self._notes_app is None:
            try:
                from macnotesapp import NotesApp
                self._notes_app = NotesApp()
                self._notes_available = True
            except (ImportError, Exception):
                self._notes_available = False
                self._notes_app = None
        return self._notes_app
    
    def _is_notes_available(self) -> bool:
        """Check if Apple Notes is available.
        
        Returns:
            True if Notes is available, False otherwise
        """
        if self._notes_available is None:
            self._get_notes_app()
        return self._notes_available or False
    
    def export_blog(self, post: "BlogPost") -> "ExportResult":
        """Export a blog post to Apple Notes.
        
        Args:
            post: Blog post to export
            
        Returns:
            Result of the export operation
        """
        from newsletter_generator.models import ExportResult
        
        folder = self.config.blog_folder
        
        # Format content with metadata
        metadata = {
            "generated_at": post.generated_at,
            "sources": post.sources,
            "word_count": post.word_count,
            "content_type": "Blog Post",
        }
        formatted_content = self._format_for_notes(post.content, metadata)
        
        # Try to export to Apple Notes
        if self._is_notes_available():
            try:
                # Ensure folder exists
                if not self._ensure_folder(folder):
                    # Fall back if folder creation fails
                    fallback_path = self._fallback_save(
                        formatted_content,
                        self._generate_filename(post.title, "blog"),
                    )
                    return ExportResult(
                        success=False,
                        folder=folder,
                        note_id=None,
                        error="Failed to create folder in Apple Notes",
                        fallback_path=fallback_path,
                    )
                
                # Create the note
                notes_app = self._get_notes_app()
                note = notes_app.make_note(
                    name=post.title,
                    body=formatted_content,
                    folder=folder,
                    account=self.config.account,
                )
                
                return ExportResult(
                    success=True,
                    folder=folder,
                    note_id=note.id if hasattr(note, 'id') else str(note),
                    error=None,
                    fallback_path=None,
                )
            except Exception as e:
                # Fall back on any error
                fallback_path = self._fallback_save(
                    formatted_content,
                    self._generate_filename(post.title, "blog"),
                )
                return ExportResult(
                    success=False,
                    folder=folder,
                    note_id=None,
                    error=f"Failed to create note: {str(e)}",
                    fallback_path=fallback_path,
                )
        else:
            # Notes not available, use fallback
            fallback_path = self._fallback_save(
                formatted_content,
                self._generate_filename(post.title, "blog"),
            )
            return ExportResult(
                success=False,
                folder=folder,
                note_id=None,
                error="Apple Notes is not available",
                fallback_path=fallback_path,
            )
    
    def export_tiktok(self, script: "TikTokScript") -> "ExportResult":
        """Export a TikTok script to Apple Notes.
        
        Args:
            script: TikTok script to export
            
        Returns:
            Result of the export operation
        """
        from newsletter_generator.models import ExportResult
        
        folder = self.config.tiktok_folder
        
        # Format content with metadata
        metadata = {
            "generated_at": script.generated_at,
            "duration_seconds": script.duration_seconds,
            "content_type": "TikTok Script",
        }
        formatted_content = self._format_for_notes(script.full_script, metadata)
        
        # Try to export to Apple Notes
        if self._is_notes_available():
            try:
                # Ensure folder exists
                if not self._ensure_folder(folder):
                    # Fall back if folder creation fails
                    fallback_path = self._fallback_save(
                        formatted_content,
                        self._generate_filename(script.title, "tiktok"),
                    )
                    return ExportResult(
                        success=False,
                        folder=folder,
                        note_id=None,
                        error="Failed to create folder in Apple Notes",
                        fallback_path=fallback_path,
                    )
                
                # Create the note
                notes_app = self._get_notes_app()
                note = notes_app.make_note(
                    name=script.title,
                    body=formatted_content,
                    folder=folder,
                    account=self.config.account,
                )
                
                return ExportResult(
                    success=True,
                    folder=folder,
                    note_id=note.id if hasattr(note, 'id') else str(note),
                    error=None,
                    fallback_path=None,
                )
            except Exception as e:
                # Fall back on any error
                fallback_path = self._fallback_save(
                    formatted_content,
                    self._generate_filename(script.title, "tiktok"),
                )
                return ExportResult(
                    success=False,
                    folder=folder,
                    note_id=None,
                    error=f"Failed to create note: {str(e)}",
                    fallback_path=fallback_path,
                )
        else:
            # Notes not available, use fallback
            fallback_path = self._fallback_save(
                formatted_content,
                self._generate_filename(script.title, "tiktok"),
            )
            return ExportResult(
                success=False,
                folder=folder,
                note_id=None,
                error="Apple Notes is not available",
                fallback_path=fallback_path,
            )
    
    def _ensure_folder(self, folder_name: str) -> bool:
        """Ensure a folder exists in Apple Notes.
        
        Creates the folder if it doesn't exist.
        
        Args:
            folder_name: Name of the folder to ensure exists
            
        Returns:
            True if folder exists or was created, False on error
        """
        if not self._is_notes_available():
            return False
        
        try:
            notes_app = self._get_notes_app()
            
            # Check if folder exists in the specified account
            account = notes_app.account(self.config.account)
            existing_folders = [f.name for f in account.folders]
            
            if folder_name not in existing_folders:
                # Create the folder
                account.make_folder(folder_name)
            
            return True
        except Exception:
            return False
    
    def _format_for_notes(self, content: str, metadata: dict) -> str:
        """Format content with metadata for Apple Notes.
        
        Adds metadata (generation date, sources) and formats
        content for optimal display in Notes.
        
        Args:
            content: Main content to format
            metadata: Metadata to include (date, sources, etc.)
            
        Returns:
            Formatted content string
        """
        lines = []
        
        # Add metadata header
        lines.append("---")
        lines.append("METADATA")
        lines.append("---")
        
        # Add generation date
        if "generated_at" in metadata:
            generated_at = metadata["generated_at"]
            if isinstance(generated_at, datetime):
                date_str = generated_at.strftime("%Y-%m-%d %H:%M:%S")
            else:
                date_str = str(generated_at)
            lines.append(f"Generated: {date_str}")
        
        # Add content type
        if "content_type" in metadata:
            lines.append(f"Type: {metadata['content_type']}")
        
        # Add sources if present
        if "sources" in metadata and metadata["sources"]:
            sources = metadata["sources"]
            if isinstance(sources, list):
                lines.append(f"Sources: {', '.join(sources)}")
            else:
                lines.append(f"Sources: {sources}")
        
        # Add word count for blog posts
        if "word_count" in metadata:
            lines.append(f"Word Count: {metadata['word_count']}")
        
        # Add duration for TikTok scripts
        if "duration_seconds" in metadata:
            lines.append(f"Duration: {metadata['duration_seconds']} seconds")
        
        lines.append("---")
        lines.append("")
        
        # Add main content
        lines.append(content)
        
        return "\n".join(lines)
    
    def _fallback_save(self, content: str, filename: str) -> str:
        """Save content to a local file as fallback.
        
        Used when Apple Notes is unavailable.
        
        Args:
            content: Content to save
            filename: Name for the output file
            
        Returns:
            Path to the saved file
        """
        # Ensure fallback directory exists
        self.fallback_dir.mkdir(parents=True, exist_ok=True)
        
        # Create the file path
        file_path = self.fallback_dir / filename
        
        # Write content to file
        file_path.write_text(content, encoding="utf-8")
        
        return str(file_path)
    
    def _generate_filename(self, title: str, content_type: str) -> str:
        """Generate a safe filename from a title.
        
        Args:
            title: The title to convert to a filename
            content_type: Type of content ("blog" or "tiktok")
            
        Returns:
            Safe filename with timestamp
        """
        # Sanitize title for filename
        safe_title = "".join(
            c if c.isalnum() or c in (" ", "-", "_") else "_"
            for c in title
        )
        safe_title = safe_title.strip().replace(" ", "_")[:50]
        
        # Add timestamp for uniqueness
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        return f"{content_type}_{safe_title}_{timestamp}.md"
