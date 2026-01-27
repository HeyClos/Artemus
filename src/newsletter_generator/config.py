"""
Configuration management for Newsletter Content Generator.

This module provides configuration dataclasses and the ConfigManager class
for loading, validating, and managing application configuration from YAML/JSON files.

Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5
"""

from __future__ import annotations

import copy
import json
import os
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

import yaml

if TYPE_CHECKING:
    pass


@dataclass
class EmailSourceConfig:
    """Configuration for an email newsletter source.
    
    Attributes:
        host: IMAP server hostname
        port: IMAP server port
        username: Email account username
        password: Email account password (or resolved from env var)
        folder: Email folder to fetch newsletters from
        use_ssl: Whether to use SSL for connection
    """
    host: str
    port: int
    username: str
    password: str
    folder: str
    use_ssl: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Serialize configuration to dictionary for YAML export."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EmailSourceConfig:
        """Create configuration from dictionary (YAML import)."""
        return cls(
            host=data["host"],
            port=data["port"],
            username=data["username"],
            password=data["password"],
            folder=data["folder"],
            use_ssl=data.get("use_ssl", True),
        )


@dataclass
class RSSSourceConfig:
    """Configuration for an RSS feed newsletter source.
    
    Attributes:
        url: RSS feed URL
        name: Human-readable name for the source
    """
    url: str
    name: str

    def to_dict(self) -> dict[str, Any]:
        """Serialize configuration to dictionary for YAML export."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RSSSourceConfig:
        """Create configuration from dictionary (YAML import)."""
        return cls(
            url=data["url"],
            name=data["name"],
        )


@dataclass
class FileSourceConfig:
    """Configuration for a local file newsletter source.
    
    Attributes:
        path: Directory path containing newsletter files
        pattern: Glob pattern for matching files (e.g., "*.html")
    """
    path: str
    pattern: str

    def to_dict(self) -> dict[str, Any]:
        """Serialize configuration to dictionary for YAML export."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FileSourceConfig:
        """Create configuration from dictionary (YAML import)."""
        return cls(
            path=data["path"],
            pattern=data["pattern"],
        )


@dataclass
class LLMConfig:
    """Configuration for the LLM provider.
    
    Attributes:
        provider: LLM provider name (e.g., "openai", "anthropic")
        model: Model identifier to use
        api_key_env: Environment variable name containing the API key
        max_tokens: Maximum tokens for LLM responses
    """
    provider: str
    model: str
    api_key_env: str
    max_tokens: int = 4096

    def to_dict(self) -> dict[str, Any]:
        """Serialize configuration to dictionary for YAML export."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LLMConfig:
        """Create configuration from dictionary (YAML import)."""
        return cls(
            provider=data["provider"],
            model=data["model"],
            api_key_env=data["api_key_env"],
            max_tokens=data.get("max_tokens", 4096),
        )


@dataclass
class BlogConfig:
    """Configuration for blog post generation.
    
    Attributes:
        format: Blog format type ("long-form", "summary", "listicle")
        target_words: Target word count for generated posts
        include_sources: Whether to include source attributions
    """
    format: str
    target_words: int
    include_sources: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Serialize configuration to dictionary for YAML export."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BlogConfig:
        """Create configuration from dictionary (YAML import)."""
        return cls(
            format=data["format"],
            target_words=data["target_words"],
            include_sources=data.get("include_sources", True),
        )


@dataclass
class TikTokConfig:
    """Configuration for TikTok script generation.
    
    Attributes:
        duration: Target duration in seconds (15, 30, or 60)
        include_visual_cues: Whether to include visual direction cues
        style: Script style ("educational", "entertaining", "news")
    """
    duration: int
    include_visual_cues: bool = True
    style: str = "educational"

    def to_dict(self) -> dict[str, Any]:
        """Serialize configuration to dictionary for YAML export."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TikTokConfig:
        """Create configuration from dictionary (YAML import)."""
        return cls(
            duration=data["duration"],
            include_visual_cues=data.get("include_visual_cues", True),
            style=data.get("style", "educational"),
        )


@dataclass
class NotesConfig:
    """Configuration for Apple Notes export.
    
    Attributes:
        account: Apple Notes account name
        blog_folder: Folder name for blog posts
        tiktok_folder: Folder name for TikTok scripts
    """
    account: str
    blog_folder: str
    tiktok_folder: str

    def to_dict(self) -> dict[str, Any]:
        """Serialize configuration to dictionary for YAML export."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> NotesConfig:
        """Create configuration from dictionary (YAML import)."""
        return cls(
            account=data["account"],
            blog_folder=data["blog_folder"],
            tiktok_folder=data["tiktok_folder"],
        )


@dataclass
class AppConfig:
    """Root application configuration.
    
    Attributes:
        email_sources: List of email source configurations
        rss_sources: List of RSS feed source configurations
        file_sources: List of file source configurations
        llm: LLM provider configuration
        blog: Blog generation configuration
        tiktok: TikTok script generation configuration
        notes: Apple Notes export configuration
        date_range_days: Number of days to look back for newsletters
    """
    llm: LLMConfig
    blog: BlogConfig
    tiktok: TikTokConfig
    notes: NotesConfig
    email_sources: list[EmailSourceConfig] = field(default_factory=list)
    rss_sources: list[RSSSourceConfig] = field(default_factory=list)
    file_sources: list[FileSourceConfig] = field(default_factory=list)
    date_range_days: int = 7

    def to_dict(self) -> dict[str, Any]:
        """Serialize configuration to dictionary for YAML export."""
        return {
            "llm": self.llm.to_dict(),
            "blog": self.blog.to_dict(),
            "tiktok": self.tiktok.to_dict(),
            "notes": self.notes.to_dict(),
            "email_sources": [src.to_dict() for src in self.email_sources],
            "rss_sources": [src.to_dict() for src in self.rss_sources],
            "file_sources": [src.to_dict() for src in self.file_sources],
            "date_range_days": self.date_range_days,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AppConfig:
        """Create configuration from dictionary (YAML import)."""
        return cls(
            llm=LLMConfig.from_dict(data["llm"]),
            blog=BlogConfig.from_dict(data["blog"]),
            tiktok=TikTokConfig.from_dict(data["tiktok"]),
            notes=NotesConfig.from_dict(data["notes"]),
            email_sources=[
                EmailSourceConfig.from_dict(src)
                for src in data.get("email_sources", [])
            ],
            rss_sources=[
                RSSSourceConfig.from_dict(src)
                for src in data.get("rss_sources", [])
            ],
            file_sources=[
                FileSourceConfig.from_dict(src)
                for src in data.get("file_sources", [])
            ],
            date_range_days=data.get("date_range_days", 7),
        )


class ConfigManager:
    """Manages loading and validation of application configuration.
    
    The ConfigManager handles:
    - Loading configuration from YAML or JSON files
    - Validating configuration values
    - Resolving environment variables for sensitive fields
    
    Example:
        >>> manager = ConfigManager()
        >>> config = manager.load("config.yaml")
        >>> errors = manager.validate(config)
    """
    
    # Valid enum values for validation
    VALID_BLOG_FORMATS = {"long-form", "summary", "listicle"}
    VALID_TIKTOK_DURATIONS = {15, 30, 60}
    VALID_TIKTOK_STYLES = {"educational", "entertaining", "news"}
    
    # Pattern for environment variable references: ${VAR_NAME}
    ENV_VAR_PATTERN = re.compile(r"^\$\{([A-Za-z_][A-Za-z0-9_]*)\}$")
    
    def load(self, path: str) -> AppConfig:
        """Load and validate configuration from a YAML or JSON file.
        
        Args:
            path: Path to the configuration file
            
        Returns:
            Parsed and validated AppConfig object
            
        Raises:
            FileNotFoundError: If the configuration file doesn't exist
            ValueError: If the configuration is invalid
        """
        file_path = Path(path)
        
        # Check if file exists
        if not file_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {path}")
        
        # Read file content
        content = file_path.read_text(encoding="utf-8")
        
        # Detect file type by extension and parse
        suffix = file_path.suffix.lower()
        try:
            if suffix in (".yaml", ".yml"):
                data = yaml.safe_load(content)
            elif suffix == ".json":
                data = json.loads(content)
            else:
                raise ValueError(
                    f"Unsupported configuration file format: {suffix}. "
                    "Supported formats: .yaml, .yml, .json"
                )
        except yaml.YAMLError as e:
            raise ValueError(f"Failed to parse YAML configuration: {e}") from e
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON configuration: {e}") from e
        
        # Handle empty file
        if data is None:
            raise ValueError("Configuration file is empty")
        
        # Create AppConfig from parsed data
        try:
            config = AppConfig.from_dict(data)
        except KeyError as e:
            raise ValueError(f"Missing required configuration field: {e}") from e
        except (TypeError, ValueError) as e:
            raise ValueError(f"Invalid configuration value: {e}") from e
        
        return config
    
    def validate(self, config: AppConfig) -> list[str]:
        """Validate a configuration object.
        
        Args:
            config: The configuration object to validate
            
        Returns:
            List of validation error messages (empty if valid)
        """
        errors: list[str] = []
        
        # Validate at least one source is configured
        total_sources = (
            len(config.email_sources) +
            len(config.rss_sources) +
            len(config.file_sources)
        )
        if total_sources == 0:
            errors.append(
                "At least one newsletter source must be configured "
                "(email_sources, rss_sources, or file_sources)"
            )
        
        # Validate email sources
        for i, email_src in enumerate(config.email_sources):
            prefix = f"email_sources[{i}]"
            
            # Validate required fields
            if not email_src.host:
                errors.append(f"{prefix}.host: Host is required")
            if not email_src.username:
                errors.append(f"{prefix}.username: Username is required")
            if not email_src.password:
                errors.append(f"{prefix}.password: Password is required")
            if not email_src.folder:
                errors.append(f"{prefix}.folder: Folder is required")
            
            # Validate port number
            if not (1 <= email_src.port <= 65535):
                errors.append(
                    f"{prefix}.port: Port must be between 1 and 65535, "
                    f"got {email_src.port}"
                )
        
        # Validate RSS sources
        for i, rss_src in enumerate(config.rss_sources):
            prefix = f"rss_sources[{i}]"
            
            # Validate required fields
            if not rss_src.url:
                errors.append(f"{prefix}.url: URL is required")
            elif not self._is_valid_url(rss_src.url):
                errors.append(
                    f"{prefix}.url: Invalid URL format: {rss_src.url}"
                )
            
            if not rss_src.name:
                errors.append(f"{prefix}.name: Name is required")
        
        # Validate file sources
        for i, file_src in enumerate(config.file_sources):
            prefix = f"file_sources[{i}]"
            
            if not file_src.path:
                errors.append(f"{prefix}.path: Path is required")
            if not file_src.pattern:
                errors.append(f"{prefix}.pattern: Pattern is required")
        
        # Validate LLM config
        if not config.llm.provider:
            errors.append("llm.provider: Provider is required")
        if not config.llm.model:
            errors.append("llm.model: Model is required")
        if not config.llm.api_key_env:
            errors.append("llm.api_key_env: API key environment variable name is required")
        
        # Validate blog config
        if config.blog.format not in self.VALID_BLOG_FORMATS:
            errors.append(
                f"blog.format: Invalid format '{config.blog.format}'. "
                f"Valid options: {', '.join(sorted(self.VALID_BLOG_FORMATS))}"
            )
        if config.blog.target_words <= 0:
            errors.append(
                f"blog.target_words: Must be a positive integer, "
                f"got {config.blog.target_words}"
            )
        
        # Validate TikTok config
        if config.tiktok.duration not in self.VALID_TIKTOK_DURATIONS:
            errors.append(
                f"tiktok.duration: Invalid duration {config.tiktok.duration}. "
                f"Valid options: {', '.join(str(d) for d in sorted(self.VALID_TIKTOK_DURATIONS))}"
            )
        if config.tiktok.style not in self.VALID_TIKTOK_STYLES:
            errors.append(
                f"tiktok.style: Invalid style '{config.tiktok.style}'. "
                f"Valid options: {', '.join(sorted(self.VALID_TIKTOK_STYLES))}"
            )
        
        # Validate notes config
        if not config.notes.account:
            errors.append("notes.account: Account name is required")
        if not config.notes.blog_folder:
            errors.append("notes.blog_folder: Blog folder name is required")
        if not config.notes.tiktok_folder:
            errors.append("notes.tiktok_folder: TikTok folder name is required")
        
        return errors
    
    def resolve_env_vars(self, config: AppConfig) -> AppConfig:
        """Resolve environment variable references in configuration.
        
        For fields that reference environment variables (e.g., api_key_env),
        this method resolves the actual values from the environment.
        
        Args:
            config: Configuration with environment variable references
            
        Returns:
            Configuration with resolved values
            
        Raises:
            ValueError: If a required environment variable is not set
        """
        # Create a deep copy to avoid modifying the original
        resolved_config = copy.deepcopy(config)
        
        # Resolve LLM API key from environment variable
        api_key_env = resolved_config.llm.api_key_env
        if api_key_env:
            api_key = os.environ.get(api_key_env)
            if api_key is None:
                raise ValueError(
                    f"Environment variable '{api_key_env}' is not set "
                    "(required for LLM API key)"
                )
            # Store the resolved API key in a new attribute
            # Note: We keep api_key_env as-is since it's the env var name
            # The resolved value would be used by the LLM client
            resolved_config.llm._resolved_api_key = api_key  # type: ignore[attr-defined]
        
        # Resolve password fields in email sources that use ${ENV_VAR} format
        for email_src in resolved_config.email_sources:
            resolved_password = self._resolve_env_var_reference(
                email_src.password,
                f"email source '{email_src.host}' password"
            )
            if resolved_password is not None:
                email_src.password = resolved_password
        
        return resolved_config
    
    def _resolve_env_var_reference(self, value: str, field_description: str) -> str | None:
        """Resolve a ${ENV_VAR} reference to its actual value.
        
        Args:
            value: The value that may contain an env var reference
            field_description: Description of the field for error messages
            
        Returns:
            The resolved value if it was an env var reference, None otherwise
            
        Raises:
            ValueError: If the referenced environment variable is not set
        """
        match = self.ENV_VAR_PATTERN.match(value)
        if match:
            env_var_name = match.group(1)
            env_value = os.environ.get(env_var_name)
            if env_value is None:
                raise ValueError(
                    f"Environment variable '{env_var_name}' is not set "
                    f"(required for {field_description})"
                )
            return env_value
        return None
    
    def _is_valid_url(self, url: str) -> bool:
        """Check if a URL has a valid format.
        
        Args:
            url: The URL to validate
            
        Returns:
            True if the URL is valid, False otherwise
        """
        try:
            result = urlparse(url)
            # Must have scheme (http/https) and netloc (domain)
            return all([result.scheme in ("http", "https"), result.netloc])
        except Exception:
            return False
