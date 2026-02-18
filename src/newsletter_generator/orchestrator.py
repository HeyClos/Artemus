"""
Application orchestrator for Newsletter Content Generator.

This module provides the NewsletterContentGenerator class that coordinates
the full pipeline execution: aggregation → synthesis → generation → export.

Validates: Requirements 7.1, 7.3, 7.4
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from newsletter_generator.config import AppConfig
    from newsletter_generator.models import (
        BlogPost,
        ExecutionResult,
        ExportResult,
        SynthesizedContent,
        TikTokScript,
    )

logger = logging.getLogger(__name__)


class NewsletterContentGenerator:
    """Orchestrates the full newsletter content generation pipeline.
    
    Coordinates all pipeline components:
    1. Newsletter aggregation from configured sources
    2. Content synthesis using LLM
    3. Blog post and TikTok script generation
    4. Export to Apple Notes (or fallback)
    
    Attributes:
        config: Application configuration
        progress_callback: Optional callback for progress reporting
    """
    
    def __init__(
        self,
        config: "AppConfig",
        progress_callback: Callable[[str, str], None] | None = None,
    ) -> None:
        """Initialize the orchestrator.
        
        Args:
            config: Application configuration
            progress_callback: Optional callback for progress updates.
                              Called with (stage, message) arguments.
        """
        self.config = config
        self.progress_callback = progress_callback
        
        # Components initialized lazily
        self._aggregator = None
        self._synthesizer = None
        self._blog_generator = None
        self._tiktok_generator = None
        self._exporter = None
        
        # Setup components
        self._setup_components()
    
    def _setup_components(self) -> None:
        """Initialize all pipeline components.
        
        Creates instances of:
        - NewsletterAggregator with configured fetchers
        - ContentSynthesizer with LLM client
        - BlogGenerator and TikTokScriptGenerator
        - NotesExporter
        """
        from newsletter_generator.aggregator import (
            ContentParser,
            EmailFetcher,
            FileFetcher,
            NewsletterAggregator,
            RSSFetcher,
        )
        from newsletter_generator.exporter import NotesExporter
        from newsletter_generator.generators import BlogGenerator, TikTokScriptGenerator
        from newsletter_generator.synthesizer import ContentSynthesizer, OpenAIClient
        
        # Create content parser
        parser = ContentParser()
        
        # Create fetchers for each configured source
        fetchers = []
        
        for email_config in self.config.email_sources:
            fetchers.append(EmailFetcher(email_config))
        
        for rss_config in self.config.rss_sources:
            fetchers.append(RSSFetcher(rss_config))
        
        for file_config in self.config.file_sources:
            fetchers.append(FileFetcher(file_config))
        
        # Create aggregator
        self._aggregator = NewsletterAggregator(fetchers, parser)
        
        # Create LLM client
        api_key = os.environ.get(self.config.llm.api_key_env, "")
        llm_client = OpenAIClient(
            api_key=api_key,
            model=self.config.llm.model,
            max_tokens=self.config.llm.max_tokens,
        )
        
        # Create synthesizer
        self._synthesizer = ContentSynthesizer(llm_client)
        
        # Create generators
        self._blog_generator = BlogGenerator(llm_client, self.config.blog)
        self._tiktok_generator = TikTokScriptGenerator(llm_client, self.config.tiktok)
        
        # Create exporter
        self._exporter = NotesExporter(self.config.notes)
    
    def run(self, dry_run: bool = False) -> "ExecutionResult":
        """Execute the full pipeline.
        
        Runs all stages of the pipeline:
        1. Aggregate newsletters from configured sources
        2. Synthesize content using LLM
        3. Generate blog post and TikTok script
        4. Export to Apple Notes (unless dry_run=True)
        
        Args:
            dry_run: If True, generate content but don't save to Notes.
                    The generated content will still be available in the
                    ExecutionResult, but note_id will be None.
        
        Returns:
            ExecutionResult with details of the pipeline execution
        """
        from newsletter_generator.models import ExecutionResult, ExportResult
        
        errors: list[str] = []
        blog_exported: ExportResult | None = None
        tiktok_exported: ExportResult | None = None
        newsletters_processed = 0
        
        try:
            # Stage 1: Aggregate newsletters
            self._report_progress("aggregation", "Fetching newsletters from configured sources...")
            
            since_date = datetime.now() - timedelta(days=self.config.date_range_days)
            items = self._aggregator.aggregate(since_date)
            newsletters_processed = len(items)
            
            self._report_progress(
                "aggregation",
                f"Fetched {newsletters_processed} newsletter items"
            )
            
            if not items:
                self._report_progress("aggregation", "No newsletters found in date range")
                return ExecutionResult(
                    success=True,
                    newsletters_processed=0,
                    errors=["No newsletters found in the configured date range"],
                    dry_run=dry_run,
                    blog_exported=None,
                    tiktok_exported=None,
                )
            
            # Stage 2: Synthesize content
            self._report_progress("synthesis", "Synthesizing newsletter content...")
            
            synthesized = self._synthesizer.synthesize(items)
            
            self._report_progress(
                "synthesis",
                f"Identified {len(synthesized.topics)} topics, "
                f"{len(synthesized.trending_themes)} trending themes"
            )
            
            # Stage 3: Generate blog post
            self._report_progress("generation", "Generating blog post...")
            
            blog_post = self._blog_generator.generate(synthesized)
            
            self._report_progress(
                "generation",
                f"Generated blog post: '{blog_post.title}' ({blog_post.word_count} words)"
            )
            
            # Stage 4: Generate TikTok script
            self._report_progress("generation", "Generating TikTok script...")
            
            tiktok_script = self._tiktok_generator.generate(synthesized)
            
            self._report_progress(
                "generation",
                f"Generated TikTok script: '{tiktok_script.title}' "
                f"({tiktok_script.duration_seconds}s)"
            )
            
            # Stage 5: Export to Apple Notes (or dry-run)
            if dry_run:
                self._report_progress("export", "Dry-run mode: skipping Apple Notes export")
                
                # Create dry-run export results with content but no note_id
                blog_exported = ExportResult(
                    success=True,
                    folder=self.config.notes.blog_folder,
                    note_id=None,  # None indicates dry-run
                    error=None,
                    fallback_path=None,
                )
                
                tiktok_exported = ExportResult(
                    success=True,
                    folder=self.config.notes.tiktok_folder,
                    note_id=None,  # None indicates dry-run
                    error=None,
                    fallback_path=None,
                )
            else:
                # Export blog post
                self._report_progress("export", "Exporting blog post to Apple Notes...")
                blog_exported = self._exporter.export_blog(blog_post)
                
                if blog_exported.success:
                    self._report_progress(
                        "export",
                        f"Blog post saved to '{blog_exported.folder}'"
                    )
                else:
                    error_msg = f"Blog export failed: {blog_exported.error}"
                    if blog_exported.fallback_path:
                        error_msg += f" (saved to {blog_exported.fallback_path})"
                    errors.append(error_msg)
                    self._report_progress("export", error_msg)
                
                # Export TikTok script
                self._report_progress("export", "Exporting TikTok script to Apple Notes...")
                tiktok_exported = self._exporter.export_tiktok(tiktok_script)
                
                if tiktok_exported.success:
                    self._report_progress(
                        "export",
                        f"TikTok script saved to '{tiktok_exported.folder}'"
                    )
                else:
                    error_msg = f"TikTok export failed: {tiktok_exported.error}"
                    if tiktok_exported.fallback_path:
                        error_msg += f" (saved to {tiktok_exported.fallback_path})"
                    errors.append(error_msg)
                    self._report_progress("export", error_msg)
            
            # Determine overall success
            # Success if we processed newsletters and generated content
            # Export failures don't make the whole run a failure if fallback worked
            success = newsletters_processed > 0
            
            self._report_progress(
                "complete",
                f"Pipeline complete. Processed {newsletters_processed} newsletters."
            )
            
            return ExecutionResult(
                success=success,
                newsletters_processed=newsletters_processed,
                errors=errors,
                dry_run=dry_run,
                blog_exported=blog_exported,
                tiktok_exported=tiktok_exported,
            )
            
        except Exception as e:
            error_msg = f"Pipeline failed: {str(e)}"
            logger.exception(error_msg)
            errors.append(error_msg)
            
            self._report_progress("error", error_msg)
            
            return ExecutionResult(
                success=False,
                newsletters_processed=newsletters_processed,
                errors=errors,
                dry_run=dry_run,
                blog_exported=blog_exported,
                tiktok_exported=tiktok_exported,
            )
    
    def _report_progress(self, stage: str, message: str) -> None:
        """Report progress to the user.
        
        Logs the progress message and calls the progress callback if set.
        
        Args:
            stage: Current pipeline stage (aggregation, synthesis, generation, export, complete, error)
            message: Progress message to report
        """
        logger.info(f"[{stage}] {message}")
        
        if self.progress_callback:
            try:
                self.progress_callback(stage, message)
            except Exception as e:
                logger.warning(f"Progress callback failed: {e}")
