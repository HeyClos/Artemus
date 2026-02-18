"""
Tests for Apple Notes export components.

This module contains unit tests and property-based tests for the
NotesExporter.

Property tests:
- Property 11: Notes Content Formatting (Validates: Requirements 6.3, 6.4)
- Property 12: Fallback on Notes Failure (Validates: Requirements 6.5)
"""

import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from newsletter_generator.config import NotesConfig
from newsletter_generator.exporter import NotesExporter
from newsletter_generator.models import BlogPost, ExportResult, TikTokScript


# =============================================================================
# Hypothesis Strategies for Test Data Generation
# =============================================================================

@st.composite
def valid_blog_post(draw: st.DrawFn) -> BlogPost:
    """Generate valid BlogPost objects."""
    title = draw(st.text(min_size=1, max_size=100).filter(lambda s: s.strip()))
    content = draw(st.text(min_size=10, max_size=1000).filter(lambda s: s.strip()))
    
    # Generate markdown-like content with headers and lists
    markdown_content = f"# {title}\n\n{content}\n\n## Section\n\n- Point 1\n- Point 2"
    
    return BlogPost(
        title=title,
        content=markdown_content,
        word_count=len(markdown_content.split()),
        sources=draw(st.lists(
            st.text(min_size=1, max_size=30).filter(lambda s: s.strip()),
            min_size=1,
            max_size=5,
        )),
        generated_at=draw(st.datetimes(
            min_value=datetime(2020, 1, 1),
            max_value=datetime(2025, 12, 31),
        )),
    )


@st.composite
def valid_tiktok_script(draw: st.DrawFn) -> TikTokScript:
    """Generate valid TikTokScript objects."""
    hook = draw(st.text(min_size=5, max_size=100).filter(lambda s: s.strip()))
    main_points = draw(st.lists(
        st.text(min_size=5, max_size=100).filter(lambda s: s.strip()),
        min_size=1,
        max_size=5,
    ))
    cta = draw(st.text(min_size=5, max_size=100).filter(lambda s: s.strip()))
    
    full_script = f"{hook}\n\n" + "\n".join(main_points) + f"\n\n{cta}"
    
    include_visual = draw(st.booleans())
    visual_cues = None
    if include_visual:
        visual_cues = draw(st.lists(
            st.text(min_size=5, max_size=50).filter(lambda s: s.strip()),
            min_size=1,
            max_size=3,
        ))
    
    return TikTokScript(
        title=draw(st.text(min_size=1, max_size=50).filter(lambda s: s.strip())),
        hook=hook,
        main_points=main_points,
        call_to_action=cta,
        visual_cues=visual_cues,
        duration_seconds=draw(st.sampled_from([15, 30, 60])),
        full_script=full_script,
        generated_at=draw(st.datetimes(
            min_value=datetime(2020, 1, 1),
            max_value=datetime(2025, 12, 31),
        )),
    )


@st.composite
def valid_notes_config(draw: st.DrawFn) -> NotesConfig:
    """Generate valid NotesConfig objects."""
    return NotesConfig(
        account=draw(st.sampled_from(["iCloud", "Gmail", "Work", "Personal"])),
        blog_folder=draw(st.text(min_size=1, max_size=30).filter(lambda s: s.strip())),
        tiktok_folder=draw(st.text(min_size=1, max_size=30).filter(lambda s: s.strip())),
    )


# =============================================================================
# Unit Tests for NotesExporter
# =============================================================================

class TestNotesExporter:
    """Unit tests for NotesExporter."""
    
    @pytest.fixture
    def notes_config(self) -> NotesConfig:
        """Create a default notes configuration."""
        return NotesConfig(
            account="iCloud",
            blog_folder="Generated Blog Posts",
            tiktok_folder="TikTok Scripts",
        )
    
    @pytest.fixture
    def sample_blog_post(self) -> BlogPost:
        """Create a sample blog post for testing."""
        return BlogPost(
            title="Tech Trends This Week",
            content="# Tech Trends This Week\n\nContent here...\n\n## Section\n\n- Point 1",
            word_count=100,
            sources=["TechCrunch", "Hacker News"],
            generated_at=datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
        )
    
    @pytest.fixture
    def sample_tiktok_script(self) -> TikTokScript:
        """Create a sample TikTok script for testing."""
        return TikTokScript(
            title="Tech Update",
            hook="Stop scrolling!",
            main_points=["AI is changing everything", "New tools are here"],
            call_to_action="Follow for more!",
            visual_cues=["Show logos", "Display stats"],
            duration_seconds=60,
            full_script="Stop scrolling!\n\nAI is changing everything\nNew tools are here\n\nFollow for more!",
            generated_at=datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
        )
    
    def test_init_sets_config(self, notes_config: NotesConfig) -> None:
        """Test that __init__ correctly sets the configuration."""
        exporter = NotesExporter(notes_config)
        assert exporter.config == notes_config
    
    def test_init_sets_custom_fallback_dir(self, notes_config: NotesConfig, tmp_path: Path) -> None:
        """Test that __init__ accepts a custom fallback directory."""
        custom_dir = str(tmp_path / "custom_output")
        exporter = NotesExporter(notes_config, fallback_dir=custom_dir)
        assert exporter.fallback_dir == Path(custom_dir)
    
    def test_format_for_notes_includes_metadata(
        self, notes_config: NotesConfig
    ) -> None:
        """Test that _format_for_notes includes metadata header."""
        exporter = NotesExporter(notes_config)
        
        content = "Test content here"
        metadata = {
            "generated_at": datetime(2024, 1, 15, 12, 0, 0),
            "sources": ["Source1", "Source2"],
            "content_type": "Blog Post",
        }
        
        result = exporter._format_for_notes(content, metadata)
        
        assert "METADATA" in result
        assert "Generated:" in result
        assert "2024-01-15" in result
        assert "Sources:" in result
        assert "Source1" in result
        assert "Source2" in result
        assert "Type: Blog Post" in result
        assert content in result
    
    def test_format_for_notes_includes_word_count(
        self, notes_config: NotesConfig
    ) -> None:
        """Test that _format_for_notes includes word count for blog posts."""
        exporter = NotesExporter(notes_config)
        
        metadata = {
            "generated_at": datetime(2024, 1, 15),
            "word_count": 500,
            "content_type": "Blog Post",
        }
        
        result = exporter._format_for_notes("Content", metadata)
        
        assert "Word Count: 500" in result
    
    def test_format_for_notes_includes_duration(
        self, notes_config: NotesConfig
    ) -> None:
        """Test that _format_for_notes includes duration for TikTok scripts."""
        exporter = NotesExporter(notes_config)
        
        metadata = {
            "generated_at": datetime(2024, 1, 15),
            "duration_seconds": 60,
            "content_type": "TikTok Script",
        }
        
        result = exporter._format_for_notes("Content", metadata)
        
        assert "Duration: 60 seconds" in result
    
    def test_fallback_save_creates_file(
        self, notes_config: NotesConfig, tmp_path: Path
    ) -> None:
        """Test that _fallback_save creates a file with content."""
        exporter = NotesExporter(notes_config, fallback_dir=str(tmp_path))
        
        content = "Test content to save"
        filename = "test_file.md"
        
        result_path = exporter._fallback_save(content, filename)
        
        assert Path(result_path).exists()
        assert Path(result_path).read_text() == content
    
    def test_fallback_save_creates_directory(
        self, notes_config: NotesConfig, tmp_path: Path
    ) -> None:
        """Test that _fallback_save creates the directory if needed."""
        new_dir = tmp_path / "new_subdir"
        exporter = NotesExporter(notes_config, fallback_dir=str(new_dir))
        
        content = "Test content"
        filename = "test.md"
        
        result_path = exporter._fallback_save(content, filename)
        
        assert new_dir.exists()
        assert Path(result_path).exists()
    
    def test_generate_filename_sanitizes_title(
        self, notes_config: NotesConfig
    ) -> None:
        """Test that _generate_filename sanitizes special characters."""
        exporter = NotesExporter(notes_config)
        
        filename = exporter._generate_filename("Test: Title/With\\Special*Chars?", "blog")
        
        assert ":" not in filename
        assert "/" not in filename
        assert "\\" not in filename
        assert "*" not in filename
        assert "?" not in filename
        assert filename.startswith("blog_")
        assert filename.endswith(".md")
    
    def test_generate_filename_truncates_long_titles(
        self, notes_config: NotesConfig
    ) -> None:
        """Test that _generate_filename truncates very long titles."""
        exporter = NotesExporter(notes_config)
        
        long_title = "A" * 200
        filename = exporter._generate_filename(long_title, "blog")
        
        # Title portion should be truncated to 50 chars
        assert len(filename) < 100
    
    def test_export_blog_uses_fallback_when_notes_unavailable(
        self, notes_config: NotesConfig, sample_blog_post: BlogPost, tmp_path: Path
    ) -> None:
        """Test that export_blog uses fallback when Notes is unavailable."""
        exporter = NotesExporter(notes_config, fallback_dir=str(tmp_path))
        # Force notes to be unavailable
        exporter._notes_available = False
        
        result = exporter.export_blog(sample_blog_post)
        
        assert result.success is False
        assert result.error == "Apple Notes is not available"
        assert result.fallback_path is not None
        assert Path(result.fallback_path).exists()
    
    def test_export_tiktok_uses_fallback_when_notes_unavailable(
        self, notes_config: NotesConfig, sample_tiktok_script: TikTokScript, tmp_path: Path
    ) -> None:
        """Test that export_tiktok uses fallback when Notes is unavailable."""
        exporter = NotesExporter(notes_config, fallback_dir=str(tmp_path))
        # Force notes to be unavailable
        exporter._notes_available = False
        
        result = exporter.export_tiktok(sample_tiktok_script)
        
        assert result.success is False
        assert result.error == "Apple Notes is not available"
        assert result.fallback_path is not None
        assert Path(result.fallback_path).exists()


# =============================================================================
# Property-Based Tests for Export Functionality
# =============================================================================

class TestExporterProperties:
    """Property-based tests for export functionality."""
    
    @pytest.mark.property
    @given(
        blog_post=valid_blog_post(),
        config=valid_notes_config(),
    )
    @settings(max_examples=100, deadline=10000)
    def test_notes_content_formatting_blog(
        self, blog_post: BlogPost, config: NotesConfig
    ) -> None:
        """
        Property 11: Notes Content Formatting (Blog Posts)
        
        **Validates: Requirements 6.3, 6.4**
        
        For any content exported to Apple Notes, the formatted output should
        include the original content structure (headers, lists preserved) and
        metadata (generation date, source list).
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            exporter = NotesExporter(config, fallback_dir=tmp_dir)
            
            metadata = {
                "generated_at": blog_post.generated_at,
                "sources": blog_post.sources,
                "word_count": blog_post.word_count,
                "content_type": "Blog Post",
            }
            
            formatted = exporter._format_for_notes(blog_post.content, metadata)
            
            # Property: Metadata section must be present
            assert "METADATA" in formatted, "Formatted content must include METADATA section"
            assert "---" in formatted, "Metadata must be delimited"
            
            # Property: Generation date must be included
            assert "Generated:" in formatted, "Generation date must be included"
            
            # Property: Content type must be included
            assert "Type: Blog Post" in formatted, "Content type must be included"
            
            # Property: Sources must be included if present
            if blog_post.sources:
                assert "Sources:" in formatted, "Sources must be included when present"
                # At least one source should appear
                assert any(
                    source in formatted for source in blog_post.sources
                ), "At least one source should appear in formatted content"
            
            # Property: Word count must be included
            assert f"Word Count: {blog_post.word_count}" in formatted, "Word count must be included"
            
            # Property: Original content must be preserved
            assert blog_post.content in formatted, "Original content must be preserved"
            
            # Property: Markdown structure should be preserved (headers)
            if "#" in blog_post.content:
                # Count headers in original
                original_headers = blog_post.content.count("#")
                # Headers should still be present in formatted output
                assert formatted.count("#") >= original_headers, "Markdown headers should be preserved"
    
    @pytest.mark.property
    @given(
        tiktok_script=valid_tiktok_script(),
        config=valid_notes_config(),
    )
    @settings(max_examples=100, deadline=10000)
    def test_notes_content_formatting_tiktok(
        self, tiktok_script: TikTokScript, config: NotesConfig
    ) -> None:
        """
        Property 11: Notes Content Formatting (TikTok Scripts)
        
        **Validates: Requirements 6.3, 6.4**
        
        For any TikTok script exported to Apple Notes, the formatted output
        should include metadata (generation date, duration).
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            exporter = NotesExporter(config, fallback_dir=tmp_dir)
            
            metadata = {
                "generated_at": tiktok_script.generated_at,
                "duration_seconds": tiktok_script.duration_seconds,
                "content_type": "TikTok Script",
            }
            
            formatted = exporter._format_for_notes(tiktok_script.full_script, metadata)
            
            # Property: Metadata section must be present
            assert "METADATA" in formatted, "Formatted content must include METADATA section"
            
            # Property: Generation date must be included
            assert "Generated:" in formatted, "Generation date must be included"
            
            # Property: Content type must be included
            assert "Type: TikTok Script" in formatted, "Content type must be included"
            
            # Property: Duration must be included
            assert f"Duration: {tiktok_script.duration_seconds} seconds" in formatted, \
                "Duration must be included"
            
            # Property: Original script must be preserved
            assert tiktok_script.full_script in formatted, "Original script must be preserved"
    
    @pytest.mark.property
    @given(
        blog_post=valid_blog_post(),
        config=valid_notes_config(),
    )
    @settings(max_examples=100, deadline=10000)
    def test_fallback_on_notes_failure_blog(
        self, blog_post: BlogPost, config: NotesConfig
    ) -> None:
        """
        Property 12: Fallback on Notes Failure (Blog Posts)
        
        **Validates: Requirements 6.5**
        
        For any export attempt where Apple Notes is unavailable, the exporter
        should create a local file at the fallback path and the ExportResult
        should indicate success=False with a non-null fallback_path.
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            exporter = NotesExporter(config, fallback_dir=tmp_dir)
            # Force notes to be unavailable
            exporter._notes_available = False
            
            result = exporter.export_blog(blog_post)
            
            # Property: Success must be False when Notes is unavailable
            assert result.success is False, "Success must be False when Notes unavailable"
            
            # Property: Error message must be set
            assert result.error is not None, "Error message must be set"
            assert len(result.error) > 0, "Error message must not be empty"
            
            # Property: Fallback path must be set
            assert result.fallback_path is not None, "Fallback path must be set"
            
            # Property: Fallback file must exist
            fallback_file = Path(result.fallback_path)
            assert fallback_file.exists(), "Fallback file must exist"
            
            # Property: Fallback file must contain the content
            # Normalize line endings for comparison (file system may normalize \r\n to \n)
            file_content = fallback_file.read_text()
            normalized_content = blog_post.content.replace('\r\n', '\n').replace('\r', '\n')
            assert normalized_content in file_content, "Fallback file must contain original content"
            
            # Property: Fallback file must contain metadata
            assert "METADATA" in file_content, "Fallback file must contain metadata"
            assert "Generated:" in file_content, "Fallback file must contain generation date"
            
            # Property: Folder must be set correctly
            assert result.folder == config.blog_folder, "Folder must match config"
            
            # Property: note_id must be None
            assert result.note_id is None, "note_id must be None when using fallback"
    
    @pytest.mark.property
    @given(
        tiktok_script=valid_tiktok_script(),
        config=valid_notes_config(),
    )
    @settings(max_examples=100, deadline=10000)
    def test_fallback_on_notes_failure_tiktok(
        self, tiktok_script: TikTokScript, config: NotesConfig
    ) -> None:
        """
        Property 12: Fallback on Notes Failure (TikTok Scripts)
        
        **Validates: Requirements 6.5**
        
        For any TikTok script export where Apple Notes is unavailable,
        the exporter should create a local file at the fallback path.
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            exporter = NotesExporter(config, fallback_dir=tmp_dir)
            # Force notes to be unavailable
            exporter._notes_available = False
            
            result = exporter.export_tiktok(tiktok_script)
            
            # Property: Success must be False when Notes is unavailable
            assert result.success is False, "Success must be False when Notes unavailable"
            
            # Property: Error message must be set
            assert result.error is not None, "Error message must be set"
            
            # Property: Fallback path must be set
            assert result.fallback_path is not None, "Fallback path must be set"
            
            # Property: Fallback file must exist
            fallback_file = Path(result.fallback_path)
            assert fallback_file.exists(), "Fallback file must exist"
            
            # Property: Fallback file must contain the script
            # Normalize line endings for comparison (file system may normalize \r\n to \n)
            file_content = fallback_file.read_text()
            normalized_script = tiktok_script.full_script.replace('\r\n', '\n').replace('\r', '\n')
            assert normalized_script in file_content, \
                "Fallback file must contain original script"
            
            # Property: Folder must be set correctly
            assert result.folder == config.tiktok_folder, "Folder must match config"
            
            # Property: note_id must be None
            assert result.note_id is None, "note_id must be None when using fallback"
