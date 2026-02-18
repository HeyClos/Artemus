"""
Tests for configuration management.

This module contains unit tests and property-based tests for the
ConfigManager and configuration dataclasses.

Property tests:
- Property 1: Configuration Round-Trip (Validates: Requirements 8.1)
- Property 2: Configuration Validation Errors (Validates: Requirements 8.4)
- Property 14: Environment Variable Resolution (Validates: Requirements 8.5)
"""

import json
import os
import tempfile
from pathlib import Path

import pytest
import yaml
from hypothesis import given, settings
from hypothesis import strategies as st

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


# =============================================================================
# Hypothesis Strategies for Configuration Objects
# =============================================================================

# Strategy for generating valid non-empty strings (for required fields)
def non_empty_text(min_size: int = 1, max_size: int = 50) -> st.SearchStrategy[str]:
    """Generate non-empty text strings without problematic characters."""
    # Use printable ASCII characters, excluding control characters and YAML special chars
    alphabet = st.characters(
        whitelist_categories=("L", "N", "P", "S"),
        blacklist_characters="\x00\n\r\t{}[]|>:@`\"'\\#&*!%",
    )
    return st.text(alphabet=alphabet, min_size=min_size, max_size=max_size).filter(
        lambda s: s.strip() == s and len(s.strip()) >= min_size
    )


# Strategy for generating valid hostnames
@st.composite
def valid_hostname(draw: st.DrawFn) -> str:
    """Generate valid hostname strings."""
    subdomain = draw(st.text(
        alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="-"),
        min_size=1,
        max_size=20,
    ).filter(lambda s: s and not s.startswith("-") and not s.endswith("-")))
    domain = draw(st.sampled_from(["com", "org", "net", "io", "example.com"]))
    return f"{subdomain}.{domain}"


# Strategy for generating valid URLs
@st.composite
def valid_url(draw: st.DrawFn) -> str:
    """Generate valid HTTP/HTTPS URLs."""
    scheme = draw(st.sampled_from(["http", "https"]))
    hostname = draw(valid_hostname())
    path = draw(st.text(
        alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="/-_"),
        min_size=0,
        max_size=30,
    ))
    return f"{scheme}://{hostname}/{path}"


# Strategy for generating valid file paths
@st.composite
def valid_file_path(draw: st.DrawFn) -> str:
    """Generate valid file path strings."""
    parts = draw(st.lists(
        st.text(
            alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="_-"),
            min_size=1,
            max_size=15,
        ).filter(lambda s: s and s.strip() == s),
        min_size=1,
        max_size=4,
    ))
    return "/".join(parts)


# Strategy for generating valid glob patterns
@st.composite
def valid_glob_pattern(draw: st.DrawFn) -> str:
    """Generate valid glob patterns."""
    return draw(st.sampled_from([
        "*.html",
        "*.txt",
        "*.md",
        "**/*.html",
        "newsletter_*.txt",
        "*.json",
    ]))


# Strategy for EmailSourceConfig
@st.composite
def valid_email_source_config(draw: st.DrawFn) -> EmailSourceConfig:
    """Generate valid EmailSourceConfig objects."""
    return EmailSourceConfig(
        host=draw(valid_hostname()),
        port=draw(st.integers(min_value=1, max_value=65535)),
        username=draw(non_empty_text(min_size=3, max_size=30)),
        password=draw(non_empty_text(min_size=4, max_size=30)),
        folder=draw(non_empty_text(min_size=1, max_size=20)),
        use_ssl=draw(st.booleans()),
    )


# Strategy for RSSSourceConfig
@st.composite
def valid_rss_source_config(draw: st.DrawFn) -> RSSSourceConfig:
    """Generate valid RSSSourceConfig objects."""
    return RSSSourceConfig(
        url=draw(valid_url()),
        name=draw(non_empty_text(min_size=1, max_size=30)),
    )


# Strategy for FileSourceConfig
@st.composite
def valid_file_source_config(draw: st.DrawFn) -> FileSourceConfig:
    """Generate valid FileSourceConfig objects."""
    return FileSourceConfig(
        path=draw(valid_file_path()),
        pattern=draw(valid_glob_pattern()),
    )


# Strategy for LLMConfig
@st.composite
def valid_llm_config(draw: st.DrawFn) -> LLMConfig:
    """Generate valid LLMConfig objects."""
    return LLMConfig(
        provider=draw(st.sampled_from(["openai", "anthropic", "cohere", "local"])),
        model=draw(non_empty_text(min_size=3, max_size=30)),
        api_key_env=draw(st.text(
            alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="_"),
            min_size=3,
            max_size=30,
        ).filter(lambda s: s and s[0].isalpha())),
        max_tokens=draw(st.integers(min_value=100, max_value=100000)),
    )


# Strategy for BlogConfig (with valid format enum)
@st.composite
def valid_blog_config(draw: st.DrawFn) -> BlogConfig:
    """Generate valid BlogConfig objects with valid format enum values."""
    return BlogConfig(
        format=draw(st.sampled_from(["long-form", "summary", "listicle"])),
        target_words=draw(st.integers(min_value=100, max_value=10000)),
        include_sources=draw(st.booleans()),
    )


# Strategy for TikTokConfig (with valid duration and style enums)
@st.composite
def valid_tiktok_config(draw: st.DrawFn) -> TikTokConfig:
    """Generate valid TikTokConfig objects with valid enum values."""
    return TikTokConfig(
        duration=draw(st.sampled_from([15, 30, 60])),
        include_visual_cues=draw(st.booleans()),
        style=draw(st.sampled_from(["educational", "entertaining", "news"])),
    )


# Strategy for NotesConfig
@st.composite
def valid_notes_config(draw: st.DrawFn) -> NotesConfig:
    """Generate valid NotesConfig objects."""
    return NotesConfig(
        account=draw(non_empty_text(min_size=1, max_size=30)),
        blog_folder=draw(non_empty_text(min_size=1, max_size=30)),
        tiktok_folder=draw(non_empty_text(min_size=1, max_size=30)),
    )


# Strategy for AppConfig (combining all the above)
@st.composite
def valid_app_config(draw: st.DrawFn) -> AppConfig:
    """Generate valid AppConfig objects combining all sub-configurations."""
    return AppConfig(
        llm=draw(valid_llm_config()),
        blog=draw(valid_blog_config()),
        tiktok=draw(valid_tiktok_config()),
        notes=draw(valid_notes_config()),
        email_sources=draw(st.lists(valid_email_source_config(), min_size=0, max_size=3)),
        rss_sources=draw(st.lists(valid_rss_source_config(), min_size=0, max_size=3)),
        file_sources=draw(st.lists(valid_file_source_config(), min_size=0, max_size=3)),
        date_range_days=draw(st.integers(min_value=1, max_value=365)),
    )


def create_valid_config_dict() -> dict:
    """Create a valid configuration dictionary for testing."""
    return {
        "llm": {
            "provider": "openai",
            "model": "gpt-4o",
            "api_key_env": "OPENAI_API_KEY",
            "max_tokens": 4096,
        },
        "blog": {
            "format": "long-form",
            "target_words": 1000,
            "include_sources": True,
        },
        "tiktok": {
            "duration": 60,
            "include_visual_cues": True,
            "style": "educational",
        },
        "notes": {
            "account": "iCloud",
            "blog_folder": "Blog Posts",
            "tiktok_folder": "TikTok Scripts",
        },
        "rss_sources": [
            {"url": "https://example.com/feed", "name": "Example Feed"},
        ],
        "email_sources": [],
        "file_sources": [],
        "date_range_days": 7,
    }


def create_valid_config() -> AppConfig:
    """Create a valid AppConfig object for testing."""
    return AppConfig.from_dict(create_valid_config_dict())


class TestConfigDataclasses:
    """Unit tests for configuration dataclasses."""
    
    def test_email_source_config_to_dict(self):
        """Test EmailSourceConfig serialization."""
        config = EmailSourceConfig(
            host="imap.example.com",
            port=993,
            username="user@example.com",
            password="secret",
            folder="INBOX",
            use_ssl=True,
        )
        result = config.to_dict()
        assert result["host"] == "imap.example.com"
        assert result["port"] == 993
        assert result["use_ssl"] is True
    
    def test_email_source_config_from_dict(self):
        """Test EmailSourceConfig deserialization."""
        data = {
            "host": "imap.example.com",
            "port": 993,
            "username": "user@example.com",
            "password": "secret",
            "folder": "INBOX",
        }
        config = EmailSourceConfig.from_dict(data)
        assert config.host == "imap.example.com"
        assert config.use_ssl is True  # Default value
    
    def test_rss_source_config_round_trip(self):
        """Test RSSSourceConfig serialization round-trip."""
        original = RSSSourceConfig(url="https://example.com/feed", name="Test")
        data = original.to_dict()
        restored = RSSSourceConfig.from_dict(data)
        assert restored.url == original.url
        assert restored.name == original.name
    
    def test_app_config_from_dict(self):
        """Test AppConfig creation from dictionary."""
        data = create_valid_config_dict()
        config = AppConfig.from_dict(data)
        assert config.llm.provider == "openai"
        assert config.blog.format == "long-form"
        assert len(config.rss_sources) == 1


class TestConfigManager:
    """Unit tests for ConfigManager."""
    
    def test_load_yaml_file(self, tmp_path: Path):
        """Test loading configuration from YAML file."""
        config_data = create_valid_config_dict()
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump(config_data))
        
        manager = ConfigManager()
        config = manager.load(str(config_file))
        
        assert config.llm.provider == "openai"
        assert config.blog.format == "long-form"
    
    def test_load_yml_file(self, tmp_path: Path):
        """Test loading configuration from .yml file."""
        config_data = create_valid_config_dict()
        config_file = tmp_path / "config.yml"
        config_file.write_text(yaml.dump(config_data))
        
        manager = ConfigManager()
        config = manager.load(str(config_file))
        
        assert config.llm.provider == "openai"
    
    def test_load_json_file(self, tmp_path: Path):
        """Test loading configuration from JSON file."""
        config_data = create_valid_config_dict()
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config_data))
        
        manager = ConfigManager()
        config = manager.load(str(config_file))
        
        assert config.llm.provider == "openai"
    
    def test_load_file_not_found(self):
        """Test that FileNotFoundError is raised for missing file."""
        manager = ConfigManager()
        with pytest.raises(FileNotFoundError) as exc_info:
            manager.load("/nonexistent/config.yaml")
        assert "not found" in str(exc_info.value).lower()
    
    def test_load_invalid_yaml(self, tmp_path: Path):
        """Test that ValueError is raised for invalid YAML."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("invalid: yaml: content: [")
        
        manager = ConfigManager()
        with pytest.raises(ValueError) as exc_info:
            manager.load(str(config_file))
        assert "parse" in str(exc_info.value).lower()
    
    def test_load_invalid_json(self, tmp_path: Path):
        """Test that ValueError is raised for invalid JSON."""
        config_file = tmp_path / "config.json"
        config_file.write_text("{invalid json}")
        
        manager = ConfigManager()
        with pytest.raises(ValueError) as exc_info:
            manager.load(str(config_file))
        assert "parse" in str(exc_info.value).lower()
    
    def test_load_unsupported_format(self, tmp_path: Path):
        """Test that ValueError is raised for unsupported file format."""
        config_file = tmp_path / "config.txt"
        config_file.write_text("some content")
        
        manager = ConfigManager()
        with pytest.raises(ValueError) as exc_info:
            manager.load(str(config_file))
        assert "unsupported" in str(exc_info.value).lower()
    
    def test_load_empty_file(self, tmp_path: Path):
        """Test that ValueError is raised for empty file."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("")
        
        manager = ConfigManager()
        with pytest.raises(ValueError) as exc_info:
            manager.load(str(config_file))
        assert "empty" in str(exc_info.value).lower()
    
    def test_load_missing_required_field(self, tmp_path: Path):
        """Test that ValueError is raised for missing required field."""
        config_data = create_valid_config_dict()
        del config_data["llm"]  # Remove required field
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump(config_data))
        
        manager = ConfigManager()
        with pytest.raises(ValueError) as exc_info:
            manager.load(str(config_file))
        assert "missing" in str(exc_info.value).lower() or "llm" in str(exc_info.value).lower()
    
    def test_validate_valid_config(self):
        """Test that valid config returns no errors."""
        config = create_valid_config()
        manager = ConfigManager()
        errors = manager.validate(config)
        assert errors == []
    
    def test_validate_no_sources(self):
        """Test validation error when no sources configured."""
        config_data = create_valid_config_dict()
        config_data["rss_sources"] = []
        config = AppConfig.from_dict(config_data)
        
        manager = ConfigManager()
        errors = manager.validate(config)
        
        assert len(errors) == 1
        assert "source" in errors[0].lower()
    
    def test_validate_invalid_blog_format(self):
        """Test validation error for invalid blog format."""
        config_data = create_valid_config_dict()
        config_data["blog"]["format"] = "invalid-format"
        config = AppConfig.from_dict(config_data)
        
        manager = ConfigManager()
        errors = manager.validate(config)
        
        assert any("blog.format" in e for e in errors)
        assert any("invalid-format" in e for e in errors)
    
    def test_validate_invalid_tiktok_duration(self):
        """Test validation error for invalid TikTok duration."""
        config_data = create_valid_config_dict()
        config_data["tiktok"]["duration"] = 45  # Invalid duration
        config = AppConfig.from_dict(config_data)
        
        manager = ConfigManager()
        errors = manager.validate(config)
        
        assert any("tiktok.duration" in e for e in errors)
    
    def test_validate_invalid_tiktok_style(self):
        """Test validation error for invalid TikTok style."""
        config_data = create_valid_config_dict()
        config_data["tiktok"]["style"] = "invalid-style"
        config = AppConfig.from_dict(config_data)
        
        manager = ConfigManager()
        errors = manager.validate(config)
        
        assert any("tiktok.style" in e for e in errors)
    
    def test_validate_invalid_port(self):
        """Test validation error for invalid port number."""
        config_data = create_valid_config_dict()
        config_data["email_sources"] = [{
            "host": "imap.example.com",
            "port": 70000,  # Invalid port
            "username": "user@example.com",
            "password": "secret",
            "folder": "INBOX",
        }]
        config = AppConfig.from_dict(config_data)
        
        manager = ConfigManager()
        errors = manager.validate(config)
        
        assert any("port" in e.lower() for e in errors)
    
    def test_validate_invalid_rss_url(self):
        """Test validation error for invalid RSS URL."""
        config_data = create_valid_config_dict()
        config_data["rss_sources"] = [
            {"url": "not-a-valid-url", "name": "Test"},
        ]
        config = AppConfig.from_dict(config_data)
        
        manager = ConfigManager()
        errors = manager.validate(config)
        
        assert any("url" in e.lower() for e in errors)
    
    def test_validate_empty_required_fields(self):
        """Test validation errors for empty required fields."""
        config_data = create_valid_config_dict()
        config_data["llm"]["provider"] = ""
        config_data["llm"]["model"] = ""
        config = AppConfig.from_dict(config_data)
        
        manager = ConfigManager()
        errors = manager.validate(config)
        
        assert any("llm.provider" in e for e in errors)
        assert any("llm.model" in e for e in errors)
    
    def test_resolve_env_vars_llm_api_key(self, monkeypatch):
        """Test resolving LLM API key from environment variable."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-123")
        
        config = create_valid_config()
        manager = ConfigManager()
        resolved = manager.resolve_env_vars(config)
        
        assert hasattr(resolved.llm, "_resolved_api_key")
        assert resolved.llm._resolved_api_key == "test-api-key-123"
    
    def test_resolve_env_vars_missing_api_key(self, monkeypatch):
        """Test error when LLM API key env var is not set."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        
        config = create_valid_config()
        manager = ConfigManager()
        
        with pytest.raises(ValueError) as exc_info:
            manager.resolve_env_vars(config)
        assert "OPENAI_API_KEY" in str(exc_info.value)
    
    def test_resolve_env_vars_email_password(self, monkeypatch):
        """Test resolving email password from ${ENV_VAR} format."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key")
        monkeypatch.setenv("EMAIL_PASSWORD", "secret-password")
        
        config_data = create_valid_config_dict()
        config_data["email_sources"] = [{
            "host": "imap.example.com",
            "port": 993,
            "username": "user@example.com",
            "password": "${EMAIL_PASSWORD}",
            "folder": "INBOX",
        }]
        config = AppConfig.from_dict(config_data)
        
        manager = ConfigManager()
        resolved = manager.resolve_env_vars(config)
        
        assert resolved.email_sources[0].password == "secret-password"
    
    def test_resolve_env_vars_missing_email_password(self, monkeypatch):
        """Test error when email password env var is not set."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key")
        monkeypatch.delenv("EMAIL_PASSWORD", raising=False)
        
        config_data = create_valid_config_dict()
        config_data["email_sources"] = [{
            "host": "imap.example.com",
            "port": 993,
            "username": "user@example.com",
            "password": "${EMAIL_PASSWORD}",
            "folder": "INBOX",
        }]
        config = AppConfig.from_dict(config_data)
        
        manager = ConfigManager()
        
        with pytest.raises(ValueError) as exc_info:
            manager.resolve_env_vars(config)
        assert "EMAIL_PASSWORD" in str(exc_info.value)
    
    def test_resolve_env_vars_literal_password(self, monkeypatch):
        """Test that literal passwords are not modified."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key")
        
        config_data = create_valid_config_dict()
        config_data["email_sources"] = [{
            "host": "imap.example.com",
            "port": 993,
            "username": "user@example.com",
            "password": "literal-password",  # Not an env var reference
            "folder": "INBOX",
        }]
        config = AppConfig.from_dict(config_data)
        
        manager = ConfigManager()
        resolved = manager.resolve_env_vars(config)
        
        assert resolved.email_sources[0].password == "literal-password"
    
    def test_resolve_env_vars_does_not_modify_original(self, monkeypatch):
        """Test that resolve_env_vars doesn't modify the original config."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key")
        monkeypatch.setenv("EMAIL_PASSWORD", "secret-password")
        
        config_data = create_valid_config_dict()
        config_data["email_sources"] = [{
            "host": "imap.example.com",
            "port": 993,
            "username": "user@example.com",
            "password": "${EMAIL_PASSWORD}",
            "folder": "INBOX",
        }]
        config = AppConfig.from_dict(config_data)
        original_password = config.email_sources[0].password
        
        manager = ConfigManager()
        resolved = manager.resolve_env_vars(config)
        
        # Original should be unchanged
        assert config.email_sources[0].password == original_password
        # Resolved should have the actual value
        assert resolved.email_sources[0].password == "secret-password"


class TestConfigProperties:
    """Property-based tests for configuration.
    
    These tests use Hypothesis to verify properties hold across
    many randomly generated inputs.
    """
    
    @pytest.mark.property
    @given(config=valid_app_config())
    @settings(max_examples=20, deadline=5000)
    def test_configuration_round_trip(self, config: AppConfig):
        """
        Property 1: Configuration Round-Trip
        
        **Validates: Requirements 8.1**
        
        For any valid configuration object, serializing it to YAML and
        parsing it back should produce an equivalent configuration object.
        """
        # Serialize to YAML
        config_dict = config.to_dict()
        yaml_str = yaml.dump(config_dict)
        
        # Parse back from YAML
        parsed_dict = yaml.safe_load(yaml_str)
        restored_config = AppConfig.from_dict(parsed_dict)
        
        # Assert equivalence for all fields
        # LLM config
        assert restored_config.llm.provider == config.llm.provider
        assert restored_config.llm.model == config.llm.model
        assert restored_config.llm.api_key_env == config.llm.api_key_env
        assert restored_config.llm.max_tokens == config.llm.max_tokens
        
        # Blog config
        assert restored_config.blog.format == config.blog.format
        assert restored_config.blog.target_words == config.blog.target_words
        assert restored_config.blog.include_sources == config.blog.include_sources
        
        # TikTok config
        assert restored_config.tiktok.duration == config.tiktok.duration
        assert restored_config.tiktok.include_visual_cues == config.tiktok.include_visual_cues
        assert restored_config.tiktok.style == config.tiktok.style
        
        # Notes config
        assert restored_config.notes.account == config.notes.account
        assert restored_config.notes.blog_folder == config.notes.blog_folder
        assert restored_config.notes.tiktok_folder == config.notes.tiktok_folder
        
        # Date range
        assert restored_config.date_range_days == config.date_range_days
        
        # Email sources
        assert len(restored_config.email_sources) == len(config.email_sources)
        for orig, restored in zip(config.email_sources, restored_config.email_sources):
            assert restored.host == orig.host
            assert restored.port == orig.port
            assert restored.username == orig.username
            assert restored.password == orig.password
            assert restored.folder == orig.folder
            assert restored.use_ssl == orig.use_ssl
        
        # RSS sources
        assert len(restored_config.rss_sources) == len(config.rss_sources)
        for orig, restored in zip(config.rss_sources, restored_config.rss_sources):
            assert restored.url == orig.url
            assert restored.name == orig.name
        
        # File sources
        assert len(restored_config.file_sources) == len(config.file_sources)
        for orig, restored in zip(config.file_sources, restored_config.file_sources):
            assert restored.path == orig.path
            assert restored.pattern == orig.pattern

    @pytest.mark.property
    @given(config=st.data())
    @settings(max_examples=20, deadline=5000)
    def test_configuration_validation_errors(self, config: st.DataObject):
        """
        Property 2: Configuration Validation Errors
        
        **Validates: Requirements 8.4**
        
        For any invalid configuration (missing required fields, invalid values),
        the ConfigManager should return a non-empty list of descriptive error messages.
        """
        # Choose which type of invalid configuration to generate
        invalid_type = config.draw(st.sampled_from([
            "no_sources",
            "invalid_blog_format",
            "invalid_tiktok_duration",
            "invalid_tiktok_style",
            "invalid_port_low",
            "invalid_port_high",
            "invalid_rss_url",
            "empty_llm_provider",
            "empty_llm_model",
            "empty_notes_account",
            "empty_notes_blog_folder",
            "empty_notes_tiktok_folder",
            "invalid_target_words",
        ]))
        
        # Start with a valid base configuration
        base_config_dict = create_valid_config_dict()
        
        # Apply the specific invalid modification based on the type
        expected_field = ""
        
        if invalid_type == "no_sources":
            # No sources configured (empty email_sources, rss_sources, file_sources)
            base_config_dict["email_sources"] = []
            base_config_dict["rss_sources"] = []
            base_config_dict["file_sources"] = []
            expected_field = "source"
            
        elif invalid_type == "invalid_blog_format":
            # Invalid blog format (not in "long-form", "summary", "listicle")
            invalid_format = config.draw(st.text(min_size=1, max_size=20).filter(
                lambda s: s not in ("long-form", "summary", "listicle")
            ))
            base_config_dict["blog"]["format"] = invalid_format
            expected_field = "blog.format"
            
        elif invalid_type == "invalid_tiktok_duration":
            # Invalid TikTok duration (not in 15, 30, 60)
            invalid_duration = config.draw(st.integers().filter(
                lambda d: d not in (15, 30, 60)
            ))
            base_config_dict["tiktok"]["duration"] = invalid_duration
            expected_field = "tiktok.duration"
            
        elif invalid_type == "invalid_tiktok_style":
            # Invalid TikTok style (not in "educational", "entertaining", "news")
            invalid_style = config.draw(st.text(min_size=1, max_size=20).filter(
                lambda s: s not in ("educational", "entertaining", "news")
            ))
            base_config_dict["tiktok"]["style"] = invalid_style
            expected_field = "tiktok.style"
            
        elif invalid_type == "invalid_port_low":
            # Invalid port number (< 1)
            invalid_port = config.draw(st.integers(max_value=0))
            base_config_dict["email_sources"] = [{
                "host": "imap.example.com",
                "port": invalid_port,
                "username": "user@example.com",
                "password": "secret",
                "folder": "INBOX",
            }]
            expected_field = "port"
            
        elif invalid_type == "invalid_port_high":
            # Invalid port number (> 65535)
            invalid_port = config.draw(st.integers(min_value=65536))
            base_config_dict["email_sources"] = [{
                "host": "imap.example.com",
                "port": invalid_port,
                "username": "user@example.com",
                "password": "secret",
                "folder": "INBOX",
            }]
            expected_field = "port"
            
        elif invalid_type == "invalid_rss_url":
            # Invalid RSS URLs (not http/https)
            invalid_url = config.draw(st.sampled_from([
                "not-a-url",
                "ftp://example.com/feed",
                "file:///path/to/file",
                "example.com/feed",
                "://missing-scheme.com",
                "",
            ]))
            base_config_dict["rss_sources"] = [
                {"url": invalid_url, "name": "Test Feed"},
            ]
            expected_field = "url"
            
        elif invalid_type == "empty_llm_provider":
            # Empty required field: provider
            base_config_dict["llm"]["provider"] = ""
            expected_field = "llm.provider"
            
        elif invalid_type == "empty_llm_model":
            # Empty required field: model
            base_config_dict["llm"]["model"] = ""
            expected_field = "llm.model"
            
        elif invalid_type == "empty_notes_account":
            # Empty required field: notes account
            base_config_dict["notes"]["account"] = ""
            expected_field = "notes.account"
            
        elif invalid_type == "empty_notes_blog_folder":
            # Empty required field: notes blog_folder
            base_config_dict["notes"]["blog_folder"] = ""
            expected_field = "notes.blog_folder"
            
        elif invalid_type == "empty_notes_tiktok_folder":
            # Empty required field: notes tiktok_folder
            base_config_dict["notes"]["tiktok_folder"] = ""
            expected_field = "notes.tiktok_folder"
            
        elif invalid_type == "invalid_target_words":
            # Invalid target_words (non-positive)
            invalid_words = config.draw(st.integers(max_value=0))
            base_config_dict["blog"]["target_words"] = invalid_words
            expected_field = "target_words"
        
        # Create the invalid config
        invalid_config = AppConfig.from_dict(base_config_dict)
        
        # Validate the configuration
        manager = ConfigManager()
        errors = manager.validate(invalid_config)
        
        # Assert the error list is non-empty
        assert len(errors) > 0, (
            f"Expected validation errors for invalid config type '{invalid_type}', "
            f"but got empty error list"
        )
        
        # Assert error messages are descriptive (contain relevant field names)
        all_errors_text = " ".join(errors).lower()
        assert expected_field.lower() in all_errors_text, (
            f"Expected error message to contain '{expected_field}' for invalid type "
            f"'{invalid_type}', but got errors: {errors}"
        )

    @pytest.mark.property
    @given(data=st.data())
    @settings(max_examples=20, deadline=5000)
    def test_environment_variable_resolution(self, data: st.DataObject):
        """
        Property 14: Environment Variable Resolution
        
        **Validates: Requirements 8.5**
        
        For any configuration containing environment variable references
        (e.g., `password_env: MY_VAR`), when that environment variable is set,
        the resolved configuration should contain the actual value.
        """
        # Strategy for generating valid environment variable names
        # Must start with letter or underscore, followed by alphanumeric or underscore
        # Use only ASCII characters (letters A-Z, a-z, digits 0-9, underscore)
        # Use a prefix to avoid conflicts with real env vars
        ascii_identifier_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_"
        ascii_start_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz_"
        
        valid_env_var_name = st.builds(
            lambda first, rest: f"TEST_PBT_{first}{rest}",
            first=st.sampled_from(list(ascii_start_chars)),
            rest=st.text(alphabet=ascii_identifier_chars, min_size=2, max_size=15),
        )
        
        # Strategy for generating environment variable values (non-empty strings)
        valid_env_var_value = st.text(
            alphabet=st.characters(
                whitelist_categories=("L", "N", "P", "S"),
                blacklist_characters="\x00\n\r",
            ),
            min_size=1,
            max_size=100,
        ).filter(lambda s: s.strip() == s and len(s) > 0)
        
        # Generate random env var names and values for LLM API key
        llm_api_key_env_name = data.draw(valid_env_var_name, label="llm_api_key_env_name")
        llm_api_key_value = data.draw(valid_env_var_value, label="llm_api_key_value")
        
        # Choose test scenario
        scenario = data.draw(st.sampled_from([
            "llm_api_key_only",
            "email_password_only",
            "multiple_env_vars",
        ]), label="scenario")
        
        # Track env vars to clean up
        env_vars_to_cleanup = []
        
        try:
            # Start with a valid base configuration
            base_config_dict = create_valid_config_dict()
            
            # Set up the LLM API key env var name in config
            base_config_dict["llm"]["api_key_env"] = llm_api_key_env_name
            
            # Set the LLM API key environment variable
            os.environ[llm_api_key_env_name] = llm_api_key_value
            env_vars_to_cleanup.append(llm_api_key_env_name)
            
            if scenario == "llm_api_key_only":
                # Test only LLM API key resolution
                config = AppConfig.from_dict(base_config_dict)
                manager = ConfigManager()
                resolved = manager.resolve_env_vars(config)
                
                # Assert the resolved API key matches the env var value
                assert hasattr(resolved.llm, "_resolved_api_key"), (
                    "Resolved config should have _resolved_api_key attribute"
                )
                assert resolved.llm._resolved_api_key == llm_api_key_value, (
                    f"Expected resolved API key to be '{llm_api_key_value}', "
                    f"but got '{resolved.llm._resolved_api_key}'"
                )
                
            elif scenario == "email_password_only":
                # Test email password with ${ENV_VAR} format resolution
                email_password_env_name = data.draw(
                    valid_env_var_name.filter(lambda s: s != llm_api_key_env_name),
                    label="email_password_env_name"
                )
                email_password_value = data.draw(valid_env_var_value, label="email_password_value")
                
                # Set the email password environment variable
                os.environ[email_password_env_name] = email_password_value
                env_vars_to_cleanup.append(email_password_env_name)
                
                # Configure email source with ${ENV_VAR} format password
                base_config_dict["email_sources"] = [{
                    "host": "imap.example.com",
                    "port": 993,
                    "username": "user@example.com",
                    "password": f"${{{email_password_env_name}}}",
                    "folder": "INBOX",
                }]
                
                config = AppConfig.from_dict(base_config_dict)
                manager = ConfigManager()
                resolved = manager.resolve_env_vars(config)
                
                # Assert the resolved email password matches the env var value
                assert len(resolved.email_sources) == 1, (
                    "Resolved config should have one email source"
                )
                assert resolved.email_sources[0].password == email_password_value, (
                    f"Expected resolved email password to be '{email_password_value}', "
                    f"but got '{resolved.email_sources[0].password}'"
                )
                
                # Also verify LLM API key was resolved
                assert resolved.llm._resolved_api_key == llm_api_key_value
                
            elif scenario == "multiple_env_vars":
                # Test multiple env vars in same config
                # Generate unique env var names for multiple email sources
                email_password_env_name_1 = data.draw(
                    valid_env_var_name.filter(lambda s: s != llm_api_key_env_name),
                    label="email_password_env_name_1"
                )
                email_password_value_1 = data.draw(valid_env_var_value, label="email_password_value_1")
                
                email_password_env_name_2 = data.draw(
                    valid_env_var_name.filter(
                        lambda s: s != llm_api_key_env_name and s != email_password_env_name_1
                    ),
                    label="email_password_env_name_2"
                )
                email_password_value_2 = data.draw(valid_env_var_value, label="email_password_value_2")
                
                # Set the email password environment variables
                os.environ[email_password_env_name_1] = email_password_value_1
                env_vars_to_cleanup.append(email_password_env_name_1)
                os.environ[email_password_env_name_2] = email_password_value_2
                env_vars_to_cleanup.append(email_password_env_name_2)
                
                # Configure multiple email sources with different ${ENV_VAR} format passwords
                base_config_dict["email_sources"] = [
                    {
                        "host": "imap.example1.com",
                        "port": 993,
                        "username": "user1@example.com",
                        "password": f"${{{email_password_env_name_1}}}",
                        "folder": "INBOX",
                    },
                    {
                        "host": "imap.example2.com",
                        "port": 993,
                        "username": "user2@example.com",
                        "password": f"${{{email_password_env_name_2}}}",
                        "folder": "Newsletters",
                    },
                ]
                
                config = AppConfig.from_dict(base_config_dict)
                manager = ConfigManager()
                resolved = manager.resolve_env_vars(config)
                
                # Assert all env vars were resolved correctly
                assert resolved.llm._resolved_api_key == llm_api_key_value, (
                    f"Expected resolved LLM API key to be '{llm_api_key_value}', "
                    f"but got '{resolved.llm._resolved_api_key}'"
                )
                
                assert len(resolved.email_sources) == 2, (
                    "Resolved config should have two email sources"
                )
                
                assert resolved.email_sources[0].password == email_password_value_1, (
                    f"Expected first email password to be '{email_password_value_1}', "
                    f"but got '{resolved.email_sources[0].password}'"
                )
                
                assert resolved.email_sources[1].password == email_password_value_2, (
                    f"Expected second email password to be '{email_password_value_2}', "
                    f"but got '{resolved.email_sources[1].password}'"
                )
        finally:
            # Clean up environment variables
            for env_var in env_vars_to_cleanup:
                os.environ.pop(env_var, None)
