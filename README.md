# Newsletter Content Generator

A macOS Python application that aggregates tech newsletters, synthesizes content using an LLM, and generates blog posts and TikTok scripts saved to Apple Notes.

## Features

- **Newsletter Aggregation**: Collect newsletters from email (IMAP), RSS feeds, and local files
- **AI-Powered Synthesis**: Use LLM to analyze, group by topic, and summarize content
- **Blog Post Generation**: Create formatted blog posts in Markdown (long-form, summary, or listicle)
- **TikTok Script Generation**: Generate short-form video scripts optimized for 15, 30, or 60 seconds
- **Apple Notes Integration**: Save all generated content directly to Apple Notes

## Installation

```bash
# Using uv (recommended)
uv sync --all-extras

# Or using pip
pip install -e ".[dev]"
```

## Quick Start

1. Create a configuration file (see `config.example.yaml`)
2. Set required environment variables for API keys
3. Run the generator:

```bash
newsletter-generator run --config config.yaml
```

## Configuration

See `config.example.yaml` for a complete configuration reference.

## Development

```bash
# Install development dependencies
uv sync --all-extras

# Run tests
pytest

# Run property-based tests with more examples
HYPOTHESIS_PROFILE=ci pytest -m property
```

## License

MIT
