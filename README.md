# Newsletter Content Generator

A macOS Python application that aggregates tech newsletters, synthesizes content using an LLM, and generates blog posts and TikTok scripts saved to Apple Notes.

## Features

- **Newsletter Aggregation**: Collect newsletters from email (IMAP), RSS feeds, and local files
- **AI-Powered Synthesis**: Use LLM to analyze, group by topic, and summarize content
- **Blog Post Generation**: Create formatted blog posts in Markdown (long-form, summary, or listicle)
- **TikTok Script Generation**: Generate short-form video scripts optimized for 15, 30, or 60 seconds
- **Apple Notes Integration**: Save all generated content directly to Apple Notes

## Requirements

- macOS (required for Apple Notes integration)
- Python 3.11 or higher
- OpenAI API key (or other supported LLM provider)
- Apple Notes.app

## Installation

### Using uv (Recommended)

[uv](https://docs.astral.sh/uv/) is a fast Python package manager. Install it first if you haven't:

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then install the newsletter generator:

```bash
# Clone the repository
git clone https://github.com/your-username/newsletter-content-generator.git
cd newsletter-content-generator

# Install dependencies
uv sync --all-extras
```

### Using pip

```bash
# Clone the repository
git clone https://github.com/your-username/newsletter-content-generator.git
cd newsletter-content-generator

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate

# Install the package with development dependencies
pip install -e ".[dev]"
```

## Configuration

### 1. Create Configuration File

Copy the example configuration file and customize it:

```bash
cp config.example.yaml config.yaml
```

### 2. Set Environment Variables

The application uses environment variables for sensitive data like API keys. Set the required variables:

```bash
# Required: OpenAI API key
export OPENAI_API_KEY="your-openai-api-key"

# Optional: Email password (if using email sources)
export GMAIL_APP_PASSWORD="your-gmail-app-password"
```

For Gmail, you'll need to create an [App Password](https://support.google.com/accounts/answer/185833) since regular passwords won't work with IMAP.

### 3. Configure Newsletter Sources

Edit `config.yaml` to add your newsletter sources. You can use any combination of:

**Email Sources** (IMAP):
```yaml
email_sources:
  - host: imap.gmail.com
    port: 993
    username: your.email@gmail.com
    password: ${GMAIL_APP_PASSWORD}
    folder: Newsletters
    use_ssl: true
```

**RSS Feeds**:
```yaml
rss_sources:
  - name: TechCrunch
    url: https://techcrunch.com/feed/
  - name: Hacker News
    url: https://news.ycombinator.com/rss
```

**Local Files**:
```yaml
file_sources:
  - path: ~/newsletters
    pattern: "*.html"
```

### 4. Configure Output Preferences

Customize how blog posts and TikTok scripts are generated:

```yaml
blog:
  format: long-form    # Options: long-form, summary, listicle
  target_words: 1000
  include_sources: true

tiktok:
  duration: 60         # Options: 15, 30, 60 (seconds)
  include_visual_cues: true
  style: educational   # Options: educational, entertaining, news
```

### 5. Configure Apple Notes

Specify where to save generated content:

```yaml
notes:
  account: iCloud              # Your Apple Notes account
  blog_folder: Generated Blog Posts
  tiktok_folder: TikTok Scripts
```

## Usage

### Validate Configuration

Before running, validate your configuration file:

```bash
newsletter-generator validate --config config.yaml
```

This will check for:
- Valid YAML syntax
- Required fields
- Valid option values
- Environment variable availability

### Run the Generator

Execute the full pipeline:

```bash
newsletter-generator run --config config.yaml
```

The generator will:
1. Fetch newsletters from all configured sources
2. Parse and normalize the content
3. Use the LLM to synthesize and group content by topic
4. Generate a blog post and TikTok script
5. Save both to Apple Notes

### Dry Run Mode

Preview generated content without saving to Apple Notes:

```bash
newsletter-generator run --config config.yaml --dry-run
```

This is useful for testing your configuration and seeing what content would be generated.

### Command Reference

```
newsletter-generator --help

Commands:
  run       Run the newsletter content generation pipeline
  validate  Validate configuration file

Run Options:
  --config, -c    Path to configuration file (default: config.yaml)
  --dry-run       Preview content without saving to Apple Notes

Validate Options:
  --config, -c    Path to configuration file (default: config.yaml)
```

## Example Workflow

1. **Set up your environment**:
   ```bash
   export OPENAI_API_KEY="sk-..."
   ```

2. **Create and customize configuration**:
   ```bash
   cp config.example.yaml config.yaml
   # Edit config.yaml with your sources and preferences
   ```

3. **Validate configuration**:
   ```bash
   newsletter-generator validate -c config.yaml
   ```

4. **Test with dry run**:
   ```bash
   newsletter-generator run -c config.yaml --dry-run
   ```

5. **Run the full pipeline**:
   ```bash
   newsletter-generator run -c config.yaml
   ```

6. **Check Apple Notes** for your generated content!

## Troubleshooting

### "Configuration file not found"

Make sure you've created a `config.yaml` file or specify the correct path:
```bash
newsletter-generator run --config /path/to/your/config.yaml
```

### "Environment variable not set"

Ensure all required environment variables are exported:
```bash
export OPENAI_API_KEY="your-key"
```

### "IMAP connection failed"

- Verify your email credentials
- For Gmail, use an App Password instead of your regular password
- Check that IMAP is enabled in your email settings

### "Apple Notes unavailable"

- Ensure Notes.app is installed and accessible
- The application will fall back to saving files locally if Notes is unavailable

## Development

### Install Development Dependencies

```bash
uv sync --all-extras
```

### Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=newsletter_generator

# Run property-based tests only
pytest -m property

# Run with more examples (CI profile)
HYPOTHESIS_PROFILE=ci pytest -m property
```

### Code Quality

```bash
# Format code
ruff format src tests

# Lint code
ruff check src tests

# Type checking
mypy src
```

## License

MIT
