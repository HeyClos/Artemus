"""
Newsletter Content Generator

A macOS application that aggregates tech newsletters, synthesizes content
using an LLM, and generates blog posts and TikTok scripts saved to Apple Notes.
"""

__version__ = "0.1.0"

# Configuration
from newsletter_generator.config import (
    AppConfig,
    BlogConfig,
    ConfigManager,
    EmailSourceConfig,
    FileSourceConfig,
    LLMConfig,
    NotesConfig,
    RSSSourceConfig,
    TikTokConfig,
)

# Data models
from newsletter_generator.models import (
    BlogPost,
    ExecutionResult,
    ExportResult,
    NewsletterItem,
    SynthesizedContent,
    TikTokScript,
    TopicGroup,
)

# Aggregation
from newsletter_generator.aggregator import (
    ContentParser,
    EmailFetcher,
    FileFetcher,
    NewsletterAggregator,
    RSSFetcher,
    SourceFetcher,
)

# Synthesis
from newsletter_generator.synthesizer import (
    ContentSynthesizer,
    LLMAPIError,
    LLMClient,
    LLMError,
    LLMRateLimitError,
    OpenAIClient,
)

# Generation
from newsletter_generator.generators import (
    BlogGenerator,
    TikTokScriptGenerator,
)

# Export
from newsletter_generator.exporter import NotesExporter

# CLI
from newsletter_generator.cli import main

__all__ = [
    # Version
    "__version__",
    # Configuration
    "AppConfig",
    "BlogConfig",
    "ConfigManager",
    "EmailSourceConfig",
    "FileSourceConfig",
    "LLMConfig",
    "NotesConfig",
    "RSSSourceConfig",
    "TikTokConfig",
    # Models
    "BlogPost",
    "ExecutionResult",
    "ExportResult",
    "NewsletterItem",
    "SynthesizedContent",
    "TikTokScript",
    "TopicGroup",
    # Aggregation
    "ContentParser",
    "EmailFetcher",
    "FileFetcher",
    "NewsletterAggregator",
    "RSSFetcher",
    "SourceFetcher",
    # Synthesis
    "ContentSynthesizer",
    "LLMAPIError",
    "LLMClient",
    "LLMError",
    "LLMRateLimitError",
    "OpenAIClient",
    # Generation
    "BlogGenerator",
    "TikTokScriptGenerator",
    # Export
    "NotesExporter",
    # CLI
    "main",
]
