"""
Command-line interface for Newsletter Content Generator.

This module provides the CLI entry point for running the newsletter
content generation pipeline.

Validates: Requirements 7.1, 7.3
"""

from __future__ import annotations

import argparse
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from newsletter_generator.config import AppConfig


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser for the CLI.
    
    Returns:
        Configured argument parser
    """
    parser = argparse.ArgumentParser(
        prog="newsletter-generator",
        description="Aggregate tech newsletters, synthesize content, and generate blog posts and TikTok scripts.",
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Run command
    run_parser = subparsers.add_parser(
        "run",
        help="Run the newsletter content generation pipeline",
    )
    run_parser.add_argument(
        "--config", "-c",
        type=str,
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )
    run_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview generated content without saving to Apple Notes",
    )
    
    # Validate command
    validate_parser = subparsers.add_parser(
        "validate",
        help="Validate configuration file",
    )
    validate_parser.add_argument(
        "--config", "-c",
        type=str,
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )
    
    return parser


def _print_progress(stage: str, message: str) -> None:
    """Print progress message to stdout.
    
    Args:
        stage: Current pipeline stage
        message: Progress message
    """
    # Use emoji indicators for different stages
    stage_icons = {
        "aggregation": "📥",
        "synthesis": "🔄",
        "generation": "✍️",
        "export": "📤",
        "complete": "✅",
        "error": "❌",
    }
    icon = stage_icons.get(stage, "•")
    print(f"{icon} [{stage.upper()}] {message}")


def run_command(config_path: str, dry_run: bool = False) -> int:
    """Execute the newsletter content generation pipeline.
    
    Args:
        config_path: Path to the configuration file
        dry_run: If True, preview content without saving
        
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    from newsletter_generator.config import ConfigManager
    from newsletter_generator.orchestrator import NewsletterContentGenerator
    
    print(f"Newsletter Content Generator")
    print(f"{'=' * 40}")
    
    # Load configuration
    print(f"\n📄 Loading configuration from: {config_path}")
    
    config_manager = ConfigManager()
    
    try:
        config = config_manager.load(config_path)
    except FileNotFoundError:
        print(f"❌ Error: Configuration file not found: {config_path}")
        print("\nCreate a configuration file or specify a different path with --config")
        return 1
    except ValueError as e:
        print(f"❌ Error: Invalid configuration: {e}")
        return 1
    
    # Validate configuration
    errors = config_manager.validate(config)
    if errors:
        print(f"❌ Configuration validation failed:")
        for error in errors:
            print(f"   • {error}")
        return 1
    
    print("✅ Configuration loaded and validated")
    
    # Resolve environment variables
    try:
        config = config_manager.resolve_env_vars(config)
    except ValueError as e:
        print(f"❌ Error: {e}")
        return 1
    
    # Show mode
    if dry_run:
        print("\n🔍 Running in DRY-RUN mode (content will not be saved to Apple Notes)")
    
    print(f"\n{'=' * 40}")
    print("Starting pipeline execution...")
    print(f"{'=' * 40}\n")
    
    # Create and run the orchestrator
    try:
        generator = NewsletterContentGenerator(config, progress_callback=_print_progress)
        result = generator.run(dry_run=dry_run)
    except Exception as e:
        print(f"\n❌ Pipeline execution failed: {e}")
        return 1
    
    # Print results
    print(f"\n{'=' * 40}")
    print("Execution Summary")
    print(f"{'=' * 40}")
    
    print(f"\n📊 Newsletters processed: {result.newsletters_processed}")
    
    if result.blog_exported:
        if result.blog_exported.success:
            if dry_run:
                print(f"📝 Blog post: Generated (dry-run, not saved)")
            else:
                print(f"📝 Blog post: Saved to '{result.blog_exported.folder}'")
        else:
            print(f"📝 Blog post: {result.blog_exported.error}")
            if result.blog_exported.fallback_path:
                print(f"   Fallback: {result.blog_exported.fallback_path}")
    
    if result.tiktok_exported:
        if result.tiktok_exported.success:
            if dry_run:
                print(f"🎬 TikTok script: Generated (dry-run, not saved)")
            else:
                print(f"🎬 TikTok script: Saved to '{result.tiktok_exported.folder}'")
        else:
            print(f"🎬 TikTok script: {result.tiktok_exported.error}")
            if result.tiktok_exported.fallback_path:
                print(f"   Fallback: {result.tiktok_exported.fallback_path}")
    
    if result.errors:
        print(f"\n⚠️ Warnings/Errors:")
        for error in result.errors:
            print(f"   • {error}")
    
    if result.success:
        print(f"\n✅ Pipeline completed successfully!")
        return 0
    else:
        print(f"\n❌ Pipeline completed with errors")
        return 1


def validate_command(config_path: str) -> int:
    """Validate a configuration file.
    
    Args:
        config_path: Path to the configuration file
        
    Returns:
        Exit code (0 for valid, non-zero for invalid)
    """
    from newsletter_generator.config import ConfigManager
    
    print(f"Validating configuration: {config_path}")
    print(f"{'=' * 40}\n")
    
    config_manager = ConfigManager()
    
    # Try to load the configuration
    try:
        config = config_manager.load(config_path)
        print("✅ Configuration file parsed successfully")
    except FileNotFoundError:
        print(f"❌ Error: Configuration file not found: {config_path}")
        return 1
    except ValueError as e:
        print(f"❌ Error: Failed to parse configuration: {e}")
        return 1
    
    # Validate the configuration
    errors = config_manager.validate(config)
    
    if errors:
        print(f"\n❌ Validation failed with {len(errors)} error(s):\n")
        for error in errors:
            print(f"   • {error}")
        return 1
    
    print("✅ Configuration is valid")
    
    # Show configuration summary
    print(f"\n{'=' * 40}")
    print("Configuration Summary")
    print(f"{'=' * 40}\n")
    
    # Sources
    total_sources = (
        len(config.email_sources) +
        len(config.rss_sources) +
        len(config.file_sources)
    )
    print(f"📥 Sources configured: {total_sources}")
    if config.email_sources:
        print(f"   • Email sources: {len(config.email_sources)}")
    if config.rss_sources:
        print(f"   • RSS sources: {len(config.rss_sources)}")
        for rss in config.rss_sources:
            print(f"     - {rss.name}: {rss.url}")
    if config.file_sources:
        print(f"   • File sources: {len(config.file_sources)}")
    
    # LLM
    print(f"\n🤖 LLM Configuration:")
    print(f"   • Provider: {config.llm.provider}")
    print(f"   • Model: {config.llm.model}")
    print(f"   • API Key Env: {config.llm.api_key_env}")
    
    # Output
    print(f"\n📝 Blog Configuration:")
    print(f"   • Format: {config.blog.format}")
    print(f"   • Target words: {config.blog.target_words}")
    print(f"   • Include sources: {config.blog.include_sources}")
    
    print(f"\n🎬 TikTok Configuration:")
    print(f"   • Duration: {config.tiktok.duration}s")
    print(f"   • Style: {config.tiktok.style}")
    print(f"   • Visual cues: {config.tiktok.include_visual_cues}")
    
    # Notes
    print(f"\n📱 Apple Notes Configuration:")
    print(f"   • Account: {config.notes.account}")
    print(f"   • Blog folder: {config.notes.blog_folder}")
    print(f"   • TikTok folder: {config.notes.tiktok_folder}")
    
    # Settings
    print(f"\n⚙️ Settings:")
    print(f"   • Date range: {config.date_range_days} days")
    
    return 0


def main() -> int:
    """Main entry point for the CLI.
    
    Returns:
        Exit code
    """
    parser = create_parser()
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        return 0
    
    if args.command == "run":
        return run_command(args.config, args.dry_run)
    elif args.command == "validate":
        return validate_command(args.config)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
