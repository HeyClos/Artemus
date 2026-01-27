# Implementation Plan: Newsletter Content Generator

## Overview

This plan implements a macOS Python application that aggregates tech newsletters, synthesizes content using an LLM, and generates blog posts and TikTok scripts saved to Apple Notes. The implementation follows a pipeline architecture with incremental, testable steps.

## Tasks

- [ ] 1. Set up project structure and dependencies
  - [x] 1.1 Create Python project with pyproject.toml
    - Initialize project with uv or poetry
    - Add dependencies: pyyaml, feedparser, beautifulsoup4, openai, macnotesapp, hypothesis, pytest
    - Configure pytest and hypothesis settings
    - _Requirements: 8.1, 8.2_

  - [x] 1.2 Create directory structure and base modules
    - Create src/newsletter_generator/ package
    - Create modules: config.py, models.py, aggregator.py, synthesizer.py, generators.py, exporter.py, cli.py
    - Create tests/ directory structure
    - _Requirements: 8.1_

- [ ] 2. Implement configuration management
  - [x] 2.1 Define configuration dataclasses in config.py
    - Implement EmailSourceConfig, RSSSourceConfig, FileSourceConfig
    - Implement LLMConfig, BlogConfig, TikTokConfig, NotesConfig
    - Implement AppConfig as the root configuration
    - _Requirements: 8.1, 8.2, 8.3_

  - [x] 2.2 Implement ConfigManager class
    - Implement load() method for YAML/JSON parsing
    - Implement validate() method with descriptive error messages
    - Implement environment variable resolution for sensitive fields
    - _Requirements: 8.1, 8.4, 8.5_

  - [x] 2.3 Write property test for configuration round-trip
    - **Property 1: Configuration Round-Trip**
    - **Validates: Requirements 8.1**

  - [x] 2.4 Write property test for configuration validation errors
    - **Property 2: Configuration Validation Errors**
    - **Validates: Requirements 8.4**

  - [x] 2.5 Write property test for environment variable resolution
    - **Property 14: Environment Variable Resolution**
    - **Validates: Requirements 8.5**

- [ ] 3. Implement data models
  - [x] 3.1 Define core data models in models.py
    - Implement NewsletterItem dataclass
    - Implement TopicGroup and SynthesizedContent dataclasses
    - Implement BlogPost and TikTokScript dataclasses
    - Implement ExportResult and ExecutionResult dataclasses
    - _Requirements: 2.4, 4.2, 5.3_

- [x] 4. Checkpoint - Verify foundation
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 5. Implement newsletter aggregator
  - [x] 5.1 Implement ContentParser class
    - Implement extract_text() for HTML to plain text conversion
    - Implement clean_content() for removing boilerplate
    - Use BeautifulSoup for HTML parsing
    - _Requirements: 2.2, 2.3_

  - [x] 5.2 Write property test for content normalization
    - **Property 4: Content Normalization**
    - **Validates: Requirements 2.4, 1.4**

  - [x] 5.3 Implement EmailFetcher class
    - Implement IMAP connection with SSL support
    - Implement fetch() method to retrieve emails from specified folder
    - Parse email content using email.message module
    - _Requirements: 1.1, 2.2_

  - [ ] 5.4 Implement RSSFetcher class
    - Use feedparser library to fetch and parse RSS feeds
    - Extract title, summary, content, and published date
    - _Requirements: 1.2, 2.3_

  - [ ] 5.5 Implement FileFetcher class
    - Read files matching glob pattern
    - Support HTML and plain text files
    - _Requirements: 1.3_

  - [ ] 5.6 Implement NewsletterAggregator class
    - Coordinate multiple fetchers
    - Implement date range filtering
    - Handle source failures gracefully, continue with remaining sources
    - _Requirements: 1.4, 1.5, 2.1, 2.5_

  - [ ] 5.7 Write property test for date range filtering
    - **Property 3: Date Range Filtering**
    - **Validates: Requirements 2.1**

  - [ ] 5.8 Write property test for source failure resilience
    - **Property 5: Source Failure Resilience**
    - **Validates: Requirements 1.5, 2.5**

- [ ] 6. Checkpoint - Verify aggregator
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 7. Implement content synthesizer
  - [ ] 7.1 Implement LLMClient protocol and OpenAIClient
    - Define LLMClient protocol with complete() method
    - Implement OpenAIClient using openai library
    - Handle API errors and rate limiting with retries
    - _Requirements: 3.4_

  - [ ] 7.2 Implement ContentSynthesizer class
    - Implement group_by_topic() using LLM to cluster content
    - Implement extract_key_points() for each topic group
    - Implement generate_summary() for overall synthesis
    - Implement synthesize() to orchestrate the full pipeline
    - Handle duplicate content detection and merging
    - _Requirements: 3.1, 3.2, 3.3, 3.5_

- [ ] 8. Implement content generators
  - [ ] 8.1 Implement BlogGenerator class
    - Implement generate() method with format-specific prompts
    - Support long-form, summary, and listicle formats
    - Include source attribution in generated content
    - Target configurable word count
    - Output in Markdown format
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

  - [ ] 8.2 Write property test for blog post structure
    - **Property 6: Blog Post Structure**
    - **Validates: Requirements 4.2, 4.3**

  - [ ] 8.3 Write property test for blog word count targeting
    - **Property 7: Blog Word Count Targeting**
    - **Validates: Requirements 4.4**

  - [ ] 8.4 Implement TikTokScriptGenerator class
    - Implement generate() method with duration-specific prompts
    - Structure output with hook, main points, call-to-action
    - Include visual cues when configured
    - Target script length based on duration (15/30/60 seconds)
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

  - [ ] 8.5 Write property test for TikTok script structure
    - **Property 8: TikTok Script Structure**
    - **Validates: Requirements 5.2, 5.3**

  - [ ] 8.6 Write property test for TikTok duration targeting
    - **Property 9: TikTok Duration Targeting**
    - **Validates: Requirements 5.1**

  - [ ] 8.7 Write property test for visual cues conditional
    - **Property 10: Visual Cues Conditional**
    - **Validates: Requirements 5.5**

- [ ] 9. Checkpoint - Verify generators
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 10. Implement Apple Notes exporter
  - [ ] 10.1 Implement NotesExporter class
    - Initialize macnotesapp.NotesApp
    - Implement _ensure_folder() to create folders if needed
    - Implement _format_for_notes() to prepare content with metadata
    - Implement export_blog() and export_tiktok() methods
    - Implement _fallback_save() for local file backup
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

  - [ ] 10.2 Write property test for notes content formatting
    - **Property 11: Notes Content Formatting**
    - **Validates: Requirements 6.3, 6.4**

  - [ ] 10.3 Write property test for fallback on notes failure
    - **Property 12: Fallback on Notes Failure**
    - **Validates: Requirements 6.5**

- [ ] 11. Implement application orchestrator and CLI
  - [ ] 11.1 Implement NewsletterContentGenerator orchestrator
    - Implement _setup_components() to initialize all pipeline components
    - Implement run() method to execute full pipeline
    - Implement _report_progress() for user feedback
    - Support dry-run mode
    - _Requirements: 7.1, 7.3, 7.4_

  - [ ] 11.2 Write property test for dry-run mode
    - **Property 13: Dry-Run Mode**
    - **Validates: Requirements 7.4**

  - [ ] 11.3 Implement CLI using argparse or click
    - Add run command with --config, --dry-run options
    - Add validate command to check configuration
    - Provide progress output during execution
    - _Requirements: 7.1, 7.3_

- [ ] 12. Create example configuration and documentation
  - [ ] 12.1 Create example config.yaml
    - Include all configuration options with comments
    - Provide sensible defaults
    - Document environment variable usage
    - _Requirements: 8.1, 8.2, 8.3, 8.5_

  - [ ] 12.2 Create README.md with usage instructions
    - Installation steps
    - Configuration guide
    - CLI usage examples
    - _Requirements: 7.1_

- [ ] 13. Final checkpoint - Full integration verification
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- All tasks including property tests are required for comprehensive validation
- Each task references specific requirements for traceability
- Property tests use Hypothesis library with minimum 100 iterations
- LLM-dependent tests may need mocking for deterministic results
- Apple Notes integration requires macOS and Notes.app access
