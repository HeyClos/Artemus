"""
Content synthesis components for Newsletter Content Generator.

This module provides the LLM client interface and ContentSynthesizer
for analyzing, grouping, and summarizing newsletter content.

Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5
"""

from __future__ import annotations

import json
import logging
import time
from typing import TYPE_CHECKING, Protocol, runtime_checkable

import openai
from openai import APIConnectionError, APIStatusError, RateLimitError

if TYPE_CHECKING:
    from newsletter_generator.models import (
        NewsletterItem,
        SynthesizedContent,
        TopicGroup,
    )

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Base exception for LLM-related errors."""
    pass


class LLMRateLimitError(LLMError):
    """Raised when rate limit is exceeded after all retries."""
    pass


class LLMAPIError(LLMError):
    """Raised when API call fails after all retries."""
    pass


@runtime_checkable
class LLMClient(Protocol):
    """Protocol for LLM client implementations.
    
    Defines the interface that all LLM clients must implement
    to be used with the ContentSynthesizer.
    """
    
    def complete(self, prompt: str, system: str | None = None) -> str:
        """Send a prompt to the LLM and return the response.
        
        Args:
            prompt: The user prompt to send
            system: Optional system prompt for context
            
        Returns:
            The LLM's response text
        """
        ...


class OpenAIClient:
    """LLM client implementation using OpenAI's API.
    
    Handles API errors and rate limiting with exponential backoff retries.
    
    Attributes:
        model: The OpenAI model to use
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds for exponential backoff
    """
    
    def __init__(
        self,
        api_key: str,
        model: str,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_tokens: int = 4096,
    ) -> None:
        """Initialize the OpenAI client.
        
        Args:
            api_key: OpenAI API key
            model: Model identifier (e.g., "gpt-5-nano")
            max_retries: Maximum number of retry attempts (default: 3)
            base_delay: Base delay in seconds for exponential backoff (default: 1.0)
            max_tokens: Maximum tokens for response (default: 4096)
        """
        self.model = model
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_tokens = max_tokens
        self._client = openai.OpenAI(api_key=api_key)
    
    def complete(self, prompt: str, system: str | None = None) -> str:
        """Send a prompt to OpenAI and return the response.
        
        Implements exponential backoff retry logic for rate limits
        and transient API errors.
        
        Args:
            prompt: The user prompt to send
            system: Optional system prompt for context
            
        Returns:
            The model's response text
            
        Raises:
            LLMRateLimitError: If rate limit exceeded after all retries
            LLMAPIError: If API call fails after all retries
        """
        messages: list[dict[str, str]] = []
        
        if system:
            messages.append({"role": "system", "content": system})
        
        messages.append({"role": "user", "content": prompt})
        
        last_error: Exception | None = None
        
        for attempt in range(self.max_retries):
            try:
                response = self._client.chat.completions.create(
                    model=self.model,
                    messages=messages,  # type: ignore[arg-type]
                    max_tokens=self.max_tokens,
                )
                
                content = response.choices[0].message.content
                if content is None:
                    raise LLMAPIError("Empty response from OpenAI API")
                
                return content
                
            except RateLimitError as e:
                last_error = e
                delay = self.base_delay * (2 ** attempt)
                logger.warning(
                    f"Rate limit hit, retrying in {delay:.1f}s (attempt {attempt + 1}/{self.max_retries})"
                )
                time.sleep(delay)
                
            except APIConnectionError as e:
                last_error = e
                delay = self.base_delay * (2 ** attempt)
                logger.warning(
                    f"Connection error, retrying in {delay:.1f}s (attempt {attempt + 1}/{self.max_retries}): {e}"
                )
                time.sleep(delay)
                
            except APIStatusError as e:
                # Don't retry on client errors (4xx except 429)
                if 400 <= e.status_code < 500 and e.status_code != 429:
                    raise LLMAPIError(f"OpenAI API error: {e.message}") from e
                
                last_error = e
                delay = self.base_delay * (2 ** attempt)
                logger.warning(
                    f"API error {e.status_code}, retrying in {delay:.1f}s (attempt {attempt + 1}/{self.max_retries})"
                )
                time.sleep(delay)
        
        # All retries exhausted
        if isinstance(last_error, RateLimitError):
            raise LLMRateLimitError(
                f"Rate limit exceeded after {self.max_retries} retries"
            ) from last_error
        
        raise LLMAPIError(
            f"OpenAI API call failed after {self.max_retries} retries: {last_error}"
        ) from last_error


class ContentSynthesizer:
    """Synthesizes and summarizes newsletter content using an LLM.
    
    Analyzes aggregated newsletter content to identify topics,
    extract key points, and generate summaries.
    
    Attributes:
        llm: LLM client for content analysis
    """
    
    def __init__(self, llm: LLMClient) -> None:
        """Initialize the synthesizer.
        
        Args:
            llm: LLM client to use for content analysis
        """
        # Import here to avoid circular imports
        from newsletter_generator.models import (
            NewsletterItem,
            SynthesizedContent,
            TopicGroup,
        )
        self._NewsletterItem = NewsletterItem
        self._SynthesizedContent = SynthesizedContent
        self._TopicGroup = TopicGroup
        self.llm = llm
    
    def group_by_topic(self, items: list[NewsletterItem]) -> list[TopicGroup]:
        """Group newsletter items by topic using LLM analysis.
        
        Uses the LLM to identify common topics/themes across all items
        and groups related items together.
        
        Args:
            items: List of newsletter items to group
            
        Returns:
            List of topic groups with related items
        """
        from newsletter_generator.models import TopicGroup
        
        if not items:
            return []
        
        # Build content summary for LLM
        items_summary = self._build_items_summary(items)
        
        system_prompt = """You are a content analyst specializing in tech newsletters. 
Your task is to identify common topics/themes across newsletter items and group them.
Respond ONLY with valid JSON, no other text."""
        
        user_prompt = f"""Analyze these newsletter items and group them by topic/theme.

Newsletter Items:
{items_summary}

Respond with a JSON array of topic groups. Each group should have:
- "topic": A short topic name (2-4 words)
- "description": A brief description of the topic (1-2 sentences)
- "item_indices": Array of item indices (0-based) that belong to this topic

An item can belong to multiple topics if relevant.
Identify 2-5 main topics based on the content.

Example response format:
[
  {{"topic": "AI Development", "description": "Updates on AI tools and frameworks.", "item_indices": [0, 2, 4]}},
  {{"topic": "Cloud Computing", "description": "News about cloud services and infrastructure.", "item_indices": [1, 3]}}
]

Respond with ONLY the JSON array, no other text:"""
        
        try:
            response = self.llm.complete(user_prompt, system_prompt)
            topic_data = self._parse_json_response(response)
            
            if not isinstance(topic_data, list):
                logger.warning("LLM returned non-list response, creating single topic group")
                return [TopicGroup(
                    topic="General Tech News",
                    description="Mixed technology news and updates",
                    items=items,
                    key_points=[],
                )]
            
            # Build topic groups from LLM response
            topic_groups: list[TopicGroup] = []
            for group_data in topic_data:
                indices = group_data.get("item_indices", [])
                group_items = [items[i] for i in indices if 0 <= i < len(items)]
                
                if group_items:  # Only create group if it has items
                    topic_groups.append(TopicGroup(
                        topic=group_data.get("topic", "Unknown Topic"),
                        description=group_data.get("description", ""),
                        items=group_items,
                        key_points=[],  # Will be filled by extract_key_points
                    ))
            
            # Handle any items not assigned to a topic
            assigned_indices = set()
            for group_data in topic_data:
                assigned_indices.update(group_data.get("item_indices", []))
            
            unassigned = [items[i] for i in range(len(items)) if i not in assigned_indices]
            if unassigned:
                topic_groups.append(TopicGroup(
                    topic="Other News",
                    description="Additional tech news and updates",
                    items=unassigned,
                    key_points=[],
                ))
            
            return topic_groups if topic_groups else [TopicGroup(
                topic="General Tech News",
                description="Mixed technology news and updates",
                items=items,
                key_points=[],
            )]
            
        except (LLMError, json.JSONDecodeError) as e:
            logger.error(f"Failed to group by topic: {e}")
            # Fallback: put all items in one group
            return [TopicGroup(
                topic="General Tech News",
                description="Mixed technology news and updates",
                items=items,
                key_points=[],
            )]
    
    def extract_key_points(self, group: TopicGroup) -> list[str]:
        """Extract key points from a topic group.
        
        Uses the LLM to identify the most important points
        from the grouped newsletter items.
        
        Args:
            group: Topic group to analyze
            
        Returns:
            List of key points from the group
        """
        if not group.items:
            return []
        
        # Build content for analysis
        content_parts = []
        for item in group.items:
            content_parts.append(f"Title: {item.title}\nContent: {item.content[:1000]}")
        
        combined_content = "\n\n---\n\n".join(content_parts)
        
        system_prompt = """You are a content analyst. Extract the most important key points from the provided content.
Respond ONLY with valid JSON, no other text."""
        
        user_prompt = f"""Extract 3-7 key points from this content about "{group.topic}":

{combined_content}

Respond with a JSON array of strings, each being a concise key point (1-2 sentences).
Focus on:
- Important announcements or releases
- Key trends or insights
- Notable statistics or facts
- Actionable information

Example response format:
["Key point 1 about the topic.", "Key point 2 with important details.", "Key point 3 highlighting a trend."]

Respond with ONLY the JSON array, no other text:"""
        
        try:
            response = self.llm.complete(user_prompt, system_prompt)
            key_points = self._parse_json_response(response)
            
            if isinstance(key_points, list):
                return [str(point) for point in key_points if point]
            
            logger.warning("LLM returned non-list response for key points")
            return []
            
        except (LLMError, json.JSONDecodeError) as e:
            logger.error(f"Failed to extract key points: {e}")
            return []
    
    def generate_summary(self, topics: list[TopicGroup]) -> str:
        """Generate an overall summary of all topics.
        
        Creates a consolidated summary highlighting the most
        important information across all topic groups.
        
        Args:
            topics: List of topic groups to summarize
            
        Returns:
            Consolidated summary text
        """
        if not topics:
            return "No content available for summarization."
        
        # Build topic summaries
        topic_summaries = []
        for topic in topics:
            key_points_text = "\n".join(f"  - {point}" for point in topic.key_points) if topic.key_points else "  - No key points extracted"
            topic_summaries.append(f"**{topic.topic}**: {topic.description}\nKey Points:\n{key_points_text}")
        
        combined_topics = "\n\n".join(topic_summaries)
        
        system_prompt = """You are a tech content summarizer. Create a concise, engaging summary of the provided topics.
Write in a professional but accessible tone."""
        
        user_prompt = f"""Create an overall summary of these tech newsletter topics:

{combined_topics}

Write a 2-4 paragraph summary that:
1. Opens with the most significant trend or announcement
2. Covers the key themes across all topics
3. Highlights any notable connections between topics
4. Ends with forward-looking insights or implications

Keep the summary concise but informative (150-300 words)."""
        
        try:
            response = self.llm.complete(user_prompt, system_prompt)
            return response.strip()
            
        except LLMError as e:
            logger.error(f"Failed to generate summary: {e}")
            # Fallback: create a basic summary from topic descriptions
            fallback_parts = [f"Topics covered: {', '.join(t.topic for t in topics)}."]
            for topic in topics:
                if topic.key_points:
                    fallback_parts.append(f"{topic.topic}: {topic.key_points[0]}")
            return " ".join(fallback_parts)
    
    def synthesize(self, items: list[NewsletterItem]) -> SynthesizedContent:
        """Run the full synthesis pipeline.
        
        Groups items by topic, extracts key points, detects duplicates,
        and generates an overall summary.
        
        Args:
            items: List of newsletter items to synthesize
            
        Returns:
            Fully synthesized content ready for generation
        """
        from newsletter_generator.models import SynthesizedContent
        from datetime import datetime
        
        if not items:
            return SynthesizedContent(
                topics=[],
                overall_summary="No newsletter content available for synthesis.",
                trending_themes=[],
                source_count=0,
                date_range=(datetime.now(), datetime.now()),
            )
        
        # Detect and merge duplicates
        deduplicated_items = self._deduplicate_items(items)
        
        # Group by topic
        topic_groups = self.group_by_topic(deduplicated_items)
        
        # Extract key points for each group
        for group in topic_groups:
            group.key_points.extend(self.extract_key_points(group))
        
        # Generate overall summary
        overall_summary = self.generate_summary(topic_groups)
        
        # Extract trending themes
        trending_themes = self._extract_trending_themes(topic_groups)
        
        # Calculate date range
        dates = [item.published_date for item in items]
        date_range = (min(dates), max(dates))
        
        # Count unique sources
        source_count = len(set(item.source_name for item in items))
        
        return SynthesizedContent(
            topics=topic_groups,
            overall_summary=overall_summary,
            trending_themes=trending_themes,
            source_count=source_count,
            date_range=date_range,
        )
    
    def _build_items_summary(self, items: list[NewsletterItem]) -> str:
        """Build a summary of items for LLM analysis.
        
        Args:
            items: List of newsletter items
            
        Returns:
            Formatted string summary of items
        """
        summaries = []
        for i, item in enumerate(items):
            # Truncate content to avoid token limits
            content_preview = item.content[:500] + "..." if len(item.content) > 500 else item.content
            summaries.append(
                f"[{i}] Source: {item.source_name}\n"
                f"    Title: {item.title}\n"
                f"    Content: {content_preview}"
            )
        return "\n\n".join(summaries)
    
    def _parse_json_response(self, response: str) -> list | dict:
        """Parse JSON from LLM response, handling common issues.
        
        Args:
            response: Raw LLM response text
            
        Returns:
            Parsed JSON data
            
        Raises:
            json.JSONDecodeError: If JSON parsing fails
        """
        # Clean up response - remove markdown code blocks if present
        cleaned = response.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
        
        return json.loads(cleaned)
    
    def _deduplicate_items(self, items: list[NewsletterItem]) -> list[NewsletterItem]:
        """Detect and merge duplicate/overlapping content.
        
        Uses title similarity and content overlap to identify duplicates.
        When duplicates are found, keeps the item with more content and
        notes the additional sources.
        
        Args:
            items: List of newsletter items
            
        Returns:
            Deduplicated list of items
        """
        if len(items) <= 1:
            return items
        
        # Simple deduplication based on title similarity
        seen_titles: dict[str, NewsletterItem] = {}
        deduplicated: list[NewsletterItem] = []
        
        for item in items:
            # Normalize title for comparison
            normalized_title = item.title.lower().strip()
            
            # Check for similar titles (exact match or high overlap)
            is_duplicate = False
            for seen_title, seen_item in seen_titles.items():
                if self._titles_similar(normalized_title, seen_title):
                    # Keep the item with more content
                    if len(item.content) > len(seen_item.content):
                        # Replace with the more detailed item
                        deduplicated.remove(seen_item)
                        deduplicated.append(item)
                        seen_titles[normalized_title] = item
                        del seen_titles[seen_title]
                    is_duplicate = True
                    logger.debug(f"Duplicate detected: '{item.title}' similar to '{seen_item.title}'")
                    break
            
            if not is_duplicate:
                seen_titles[normalized_title] = item
                deduplicated.append(item)
        
        if len(deduplicated) < len(items):
            logger.info(f"Deduplicated {len(items)} items to {len(deduplicated)}")
        
        return deduplicated
    
    def _titles_similar(self, title1: str, title2: str) -> bool:
        """Check if two titles are similar enough to be duplicates.
        
        Args:
            title1: First normalized title
            title2: Second normalized title
            
        Returns:
            True if titles are similar
        """
        # Exact match
        if title1 == title2:
            return True
        
        # Check word overlap (simple Jaccard-like similarity)
        words1 = set(title1.split())
        words2 = set(title2.split())
        
        if not words1 or not words2:
            return False
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        # Consider similar if >70% word overlap
        return (intersection / union) > 0.7 if union > 0 else False
    
    def _extract_trending_themes(self, topics: list[TopicGroup]) -> list[str]:
        """Extract trending themes from topic groups.
        
        Args:
            topics: List of topic groups
            
        Returns:
            List of trending theme names
        """
        # Simple extraction: use topic names as themes, sorted by item count
        themes = sorted(topics, key=lambda t: len(t.items), reverse=True)
        return [t.topic for t in themes[:5]]  # Top 5 themes
