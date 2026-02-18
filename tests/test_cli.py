"""
Tests for command-line interface.

This module contains unit tests for the CLI commands and argument parsing.
"""

import pytest
from unittest.mock import patch, MagicMock
import sys
import os

from newsletter_generator.cli import create_parser, run_command, validate_command, main


class TestCLIParser:
    """Unit tests for CLI argument parsing."""
    
    def test_create_parser_returns_parser(self) -> None:
        """Test that create_parser returns an ArgumentParser."""
        parser = create_parser()
        assert parser is not None
        assert parser.prog == "newsletter-generator"
    
    def test_run_command_parsing(self) -> None:
        """Test parsing of run command arguments."""
        parser = create_parser()
        
        # Test default values
        args = parser.parse_args(["run"])
        assert args.command == "run"
        assert args.config == "config.yaml"
        assert args.dry_run is False
        
        # Test custom config
        args = parser.parse_args(["run", "--config", "custom.yaml"])
        assert args.config == "custom.yaml"
        
        # Test short form
        args = parser.parse_args(["run", "-c", "custom.yaml"])
        assert args.config == "custom.yaml"
        
        # Test dry-run flag
        args = parser.parse_args(["run", "--dry-run"])
        assert args.dry_run is True
    
    def test_validate_command_parsing(self) -> None:
        """Test parsing of validate command arguments."""
        parser = create_parser()
        
        # Test default values
        args = parser.parse_args(["validate"])
        assert args.command == "validate"
        assert args.config == "config.yaml"
        
        # Test custom config
        args = parser.parse_args(["validate", "--config", "custom.yaml"])
        assert args.config == "custom.yaml"
    
    def test_no_command_returns_none(self) -> None:
        """Test that no command returns None for command."""
        parser = create_parser()
        args = parser.parse_args([])
        assert args.command is None


class TestCLICommands:
    """Unit tests for CLI commands."""
    
    def test_run_command_file_not_found(self, tmp_path) -> None:
        """Test run_command with non-existent config file."""
        result = run_command(str(tmp_path / "nonexistent.yaml"))
        assert result == 1
    
    def test_validate_command_file_not_found(self, tmp_path) -> None:
        """Test validate_command with non-existent config file."""
        result = validate_command(str(tmp_path / "nonexistent.yaml"))
        assert result == 1
    
    def test_validate_command_valid_config(self, tmp_path) -> None:
        """Test validate_command with a valid configuration file."""
        config_content = """
llm:
  provider: openai
  model: gpt-4o
  api_key_env: OPENAI_API_KEY
  max_tokens: 4096

blog:
  format: long-form
  target_words: 500
  include_sources: true

tiktok:
  duration: 60
  include_visual_cues: true
  style: educational

notes:
  account: iCloud
  blog_folder: Blog Posts
  tiktok_folder: TikTok Scripts

rss_sources:
  - name: Test Feed
    url: https://example.com/feed

date_range_days: 7
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_content)
        
        result = validate_command(str(config_file))
        assert result == 0
    
    def test_validate_command_invalid_config(self, tmp_path) -> None:
        """Test validate_command with an invalid configuration file."""
        # Missing required fields
        config_content = """
llm:
  provider: openai
  model: gpt-4o
  api_key_env: OPENAI_API_KEY

blog:
  format: invalid-format
  target_words: 500

tiktok:
  duration: 60
  style: educational

notes:
  account: iCloud
  blog_folder: Blog Posts
  tiktok_folder: TikTok Scripts
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_content)
        
        result = validate_command(str(config_file))
        assert result == 1
    
    def test_run_command_with_valid_config_dry_run(self, tmp_path) -> None:
        """Test run_command in dry-run mode with valid config."""
        config_content = """
llm:
  provider: openai
  model: gpt-4o
  api_key_env: OPENAI_API_KEY
  max_tokens: 4096

blog:
  format: long-form
  target_words: 500
  include_sources: true

tiktok:
  duration: 60
  include_visual_cues: true
  style: educational

notes:
  account: iCloud
  blog_folder: Blog Posts
  tiktok_folder: TikTok Scripts

rss_sources:
  - name: Test Feed
    url: https://example.com/feed

date_range_days: 7
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_content)
        
        # Mock the orchestrator to avoid actual execution
        with patch("newsletter_generator.orchestrator.NewsletterContentGenerator") as mock_gen:
            mock_instance = MagicMock()
            mock_gen.return_value = mock_instance
            
            # Create a mock result
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.newsletters_processed = 5
            mock_result.errors = []
            mock_result.blog_exported = MagicMock(success=True, folder="Blog", fallback_path=None)
            mock_result.tiktok_exported = MagicMock(success=True, folder="TikTok", fallback_path=None)
            mock_instance.run.return_value = mock_result
            
            with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
                result = run_command(str(config_file), dry_run=True)
            
            assert result == 0
            mock_instance.run.assert_called_once_with(dry_run=True)
    
    def test_main_no_command(self) -> None:
        """Test main with no command shows help."""
        with patch("sys.argv", ["newsletter-generator"]):
            result = main()
            assert result == 0
    
    def test_main_run_command(self, tmp_path) -> None:
        """Test main with run command."""
        config_content = """
llm:
  provider: openai
  model: gpt-4o
  api_key_env: OPENAI_API_KEY
  max_tokens: 4096

blog:
  format: long-form
  target_words: 500
  include_sources: true

tiktok:
  duration: 60
  include_visual_cues: true
  style: educational

notes:
  account: iCloud
  blog_folder: Blog Posts
  tiktok_folder: TikTok Scripts

rss_sources:
  - name: Test Feed
    url: https://example.com/feed

date_range_days: 7
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_content)
        
        with patch("newsletter_generator.orchestrator.NewsletterContentGenerator") as mock_gen:
            mock_instance = MagicMock()
            mock_gen.return_value = mock_instance
            
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.newsletters_processed = 5
            mock_result.errors = []
            mock_result.blog_exported = MagicMock(success=True, folder="Blog", fallback_path=None)
            mock_result.tiktok_exported = MagicMock(success=True, folder="TikTok", fallback_path=None)
            mock_instance.run.return_value = mock_result
            
            with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
                with patch("sys.argv", ["newsletter-generator", "run", "-c", str(config_file), "--dry-run"]):
                    result = main()
            
            assert result == 0
    
    def test_main_validate_command(self, tmp_path) -> None:
        """Test main with validate command."""
        config_content = """
llm:
  provider: openai
  model: gpt-4o
  api_key_env: OPENAI_API_KEY
  max_tokens: 4096

blog:
  format: long-form
  target_words: 500
  include_sources: true

tiktok:
  duration: 60
  include_visual_cues: true
  style: educational

notes:
  account: iCloud
  blog_folder: Blog Posts
  tiktok_folder: TikTok Scripts

rss_sources:
  - name: Test Feed
    url: https://example.com/feed

date_range_days: 7
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_content)
        
        with patch("sys.argv", ["newsletter-generator", "validate", "-c", str(config_file)]):
            result = main()
        
        assert result == 0
