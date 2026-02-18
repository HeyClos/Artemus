"""
Content generation components for Newsletter Content Generator.

This module provides generators for creating blog posts and TikTok scripts
from synthesized newsletter content.

Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5, 5.1, 5.2, 5.3, 5.4, 5.5
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from newsletter_generator.config import BlogConfig, TikTokConfig
    from newsletter_generator.models import BlogPost, SynthesizedContent, TikTokScript
    from newsletter_generator.synthesizer import LLMClient

logger = logging.getLogger(__name__)


class BlogGenerator:
    """Generates blog posts from synthesized newsletter content.
    
    Creates formatted blog posts in Markdown with configurable
    format (long-form, summary, listicle), word count targeting,
    and source attribution.
    
    Attributes:
        llm: LLM client for content generation
        config: Blog generation configuration
    """
    
    # Format-specific instructions for the LLM
    FORMAT_INSTRUCTIONS = {
        "long-form": (
            "Write a comprehensive, in-depth analysis article. "
            "Include detailed explanations, context, and analysis. "
            "Structure with clear sections: introduction, multiple body sections "
            "exploring different aspects, and a thoughtful conclusion."
        ),
        "summary": (
            "Write a concise summary article that captures the key points. "
            "Focus on the most important information without extensive analysis. "
            "Structure with a brief introduction, main points, and conclusion."
        ),
        "listicle": (
            "Write a list-style article with numbered or bulleted key points. "
            "Each point should have a clear heading and brief explanation. "
            "Include an engaging introduction and wrap-up conclusion."
        ),
    }
    
    def __init__(self, llm: LLMClient, config: BlogConfig) -> None:
        """Initialize the blog generator.
        
        Args:
            llm: LLM client to use for generation
            config: Blog generation configuration
        """
        self.llm = llm
        self.config = config
    
    def generate(self, content: SynthesizedContent) -> BlogPost:
        """Generate a blog post from synthesized content.
        
        Args:
            content: Synthesized newsletter content
            
        Returns:
            Generated blog post with title, Markdown content,
            word count, sources, and generation timestamp
        """
        from newsletter_generator.models import BlogPost
        
        # Build the prompt
        prompt = self._build_prompt(content)
        
        # System prompt for blog generation
        system_prompt = (
            "You are an expert tech blogger who writes engaging, informative content. "
            "Write in Markdown format with proper headers, lists, and formatting. "
            "Your writing should be professional yet accessible."
        )
        
        try:
            response = self.llm.complete(prompt, system_prompt)
            
            # Parse the response to extract title and content
            title, markdown_content = self._parse_response(response)
            
            # Add source attribution if configured
            if self.config.include_sources:
                sources = self._collect_sources(content)
                markdown_content = self._add_source_attribution(markdown_content, sources)
            else:
                sources = []
            
            # Calculate word count
            word_count = self._count_words(markdown_content)
            
            return BlogPost(
                title=title,
                content=markdown_content,
                word_count=word_count,
                sources=sources,
                generated_at=datetime.now(),
            )
            
        except Exception as e:
            logger.error(f"Failed to generate blog post: {e}")
            # Return a minimal blog post on failure
            return BlogPost(
                title="Tech Newsletter Roundup",
                content=f"# Tech Newsletter Roundup\n\n{content.overall_summary}",
                word_count=len(content.overall_summary.split()),
                sources=self._collect_sources(content),
                generated_at=datetime.now(),
            )
    
    def _build_prompt(self, content: SynthesizedContent) -> str:
        """Build the LLM prompt based on configured format.
        
        Args:
            content: Synthesized content to include in prompt
            
        Returns:
            Formatted prompt string
        """
        # Get format-specific instructions
        format_instruction = self.FORMAT_INSTRUCTIONS.get(
            self.config.format,
            self.FORMAT_INSTRUCTIONS["summary"]
        )
        
        # Build topic summaries
        topic_sections = []
        for topic in content.topics:
            key_points = "\n".join(f"  - {point}" for point in topic.key_points)
            topic_sections.append(
                f"**{topic.topic}**: {topic.description}\n"
                f"Key Points:\n{key_points}"
            )
        
        topics_text = "\n\n".join(topic_sections) if topic_sections else "No specific topics identified."
        
        # Build the prompt
        prompt = f"""Create a blog post based on the following synthesized newsletter content.

## Content Summary
{content.overall_summary}

## Topics Covered
{topics_text}

## Trending Themes
{', '.join(content.trending_themes) if content.trending_themes else 'Various tech topics'}

## Instructions
{format_instruction}

Target word count: approximately {self.config.target_words} words.

Format your response as follows:
1. Start with a compelling title on the first line (without any markdown header prefix)
2. Follow with the full blog post content in Markdown format
3. Include proper section headers (##), lists, and formatting
4. Ensure the content has a clear introduction, body sections, and conclusion

Write the blog post now:"""
        
        return prompt
    
    def _parse_response(self, response: str) -> tuple[str, str]:
        """Parse the LLM response to extract title and content.
        
        Args:
            response: Raw LLM response
            
        Returns:
            Tuple of (title, markdown_content)
        """
        lines = response.strip().split("\n")
        
        if not lines:
            return "Tech Newsletter Roundup", response
        
        # First non-empty line is the title
        title = ""
        content_start = 0
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped:
                # Remove markdown header prefix if present
                if stripped.startswith("#"):
                    title = stripped.lstrip("#").strip()
                else:
                    title = stripped
                content_start = i + 1
                break
        
        if not title:
            title = "Tech Newsletter Roundup"
        
        # Rest is the content
        content_lines = lines[content_start:]
        content = "\n".join(content_lines).strip()
        
        # Ensure content starts with the title as a header
        if not content.startswith("#"):
            content = f"# {title}\n\n{content}"
        
        return title, content
    
    def _collect_sources(self, content: SynthesizedContent) -> list[str]:
        """Collect unique source names from synthesized content.
        
        Args:
            content: Synthesized content
            
        Returns:
            List of unique source names
        """
        sources = set()
        for topic in content.topics:
            for item in topic.items:
                sources.add(item.source_name)
        return sorted(sources)
    
    def _add_source_attribution(self, content: str, sources: list[str]) -> str:
        """Add source attribution section to the blog post.
        
        Args:
            content: Blog post content
            sources: List of source names
            
        Returns:
            Content with source attribution added
        """
        if not sources:
            return content
        
        attribution = "\n\n---\n\n## Sources\n\n"
        attribution += "This article was compiled from the following newsletters:\n\n"
        for source in sources:
            attribution += f"- {source}\n"
        
        return content + attribution
    
    def _count_words(self, text: str) -> int:
        """Count words in text, excluding Markdown syntax.
        
        Args:
            text: Text to count words in
            
        Returns:
            Word count
        """
        # Remove Markdown syntax
        clean_text = re.sub(r"[#*_`\[\]()>-]", " ", text)
        # Remove URLs
        clean_text = re.sub(r"https?://\S+", "", clean_text)
        # Split and count non-empty words
        words = [w for w in clean_text.split() if w.strip()]
        return len(words)


class TikTokScriptGenerator:
    """Generates TikTok scripts from synthesized newsletter content.
    
    Creates short-form video scripts optimized for TikTok with
    configurable duration, visual cues, and style.
    
    Attributes:
        llm: LLM client for content generation
        config: TikTok script generation configuration
    """
    
    # Words per minute for script duration estimation (average speaking pace)
    WORDS_PER_MINUTE = 150
    
    # Style-specific instructions
    STYLE_INSTRUCTIONS = {
        "educational": (
            "Write in an informative, teaching style. "
            "Explain concepts clearly and provide value to viewers. "
            "Use phrases like 'Here's what you need to know' or 'Let me break this down'."
        ),
        "entertaining": (
            "Write in a fun, engaging style with personality. "
            "Use humor where appropriate and keep energy high. "
            "Make the content memorable and shareable."
        ),
        "news": (
            "Write in a news anchor style - authoritative but accessible. "
            "Focus on facts and breaking developments. "
            "Use phrases like 'Breaking news' or 'Here's the latest'."
        ),
    }
    
    def __init__(self, llm: LLMClient, config: TikTokConfig) -> None:
        """Initialize the TikTok script generator.
        
        Args:
            llm: LLM client to use for generation
            config: TikTok script generation configuration
        """
        self.llm = llm
        self.config = config
    
    def generate(self, content: SynthesizedContent) -> TikTokScript:
        """Generate a TikTok script from synthesized content.
        
        Args:
            content: Synthesized newsletter content
            
        Returns:
            Generated TikTok script with hook, main points,
            call-to-action, and optional visual cues
        """
        from newsletter_generator.models import TikTokScript
        
        # Build the prompt
        prompt = self._build_prompt(content)
        
        # System prompt for TikTok script generation
        system_prompt = (
            "You are a viral TikTok content creator specializing in tech content. "
            "You know how to grab attention quickly and deliver value in short-form video. "
            "Your scripts are punchy, engaging, and optimized for the platform."
        )
        
        try:
            response = self.llm.complete(prompt, system_prompt)
            
            # Parse the structured response
            script_data = self._parse_response(response)
            
            # Build the full script text
            full_script = self._build_full_script(script_data)
            
            # Handle visual cues based on config
            visual_cues = script_data.get("visual_cues") if self.config.include_visual_cues else None
            
            return TikTokScript(
                title=script_data.get("title", "Tech Update"),
                hook=script_data.get("hook", ""),
                main_points=script_data.get("main_points", []),
                call_to_action=script_data.get("call_to_action", ""),
                visual_cues=visual_cues,
                duration_seconds=self.config.duration,
                full_script=full_script,
                generated_at=datetime.now(),
            )
            
        except Exception as e:
            logger.error(f"Failed to generate TikTok script: {e}")
            # Return a minimal script on failure
            hook = f"Here's what's happening in tech this week!"
            main_points = content.trending_themes[:3] if content.trending_themes else ["Tech news update"]
            cta = "Follow for more tech updates!"
            
            return TikTokScript(
                title="Tech Update",
                hook=hook,
                main_points=main_points,
                call_to_action=cta,
                visual_cues=["Show trending topics"] if self.config.include_visual_cues else None,
                duration_seconds=self.config.duration,
                full_script=f"{hook}\n\n" + "\n".join(main_points) + f"\n\n{cta}",
                generated_at=datetime.now(),
            )
    
    def _build_prompt(self, content: SynthesizedContent) -> str:
        """Build the LLM prompt for script generation.
        
        Args:
            content: Synthesized content to include in prompt
            
        Returns:
            Formatted prompt string
        """
        # Calculate target word count based on duration
        target_words = int((self.config.duration / 60) * self.WORDS_PER_MINUTE)
        
        # Get style-specific instructions
        style_instruction = self.STYLE_INSTRUCTIONS.get(
            self.config.style,
            self.STYLE_INSTRUCTIONS["educational"]
        )
        
        # Build topic summaries
        topic_points = []
        for topic in content.topics:
            if topic.key_points:
                topic_points.append(f"- {topic.topic}: {topic.key_points[0]}")
            else:
                topic_points.append(f"- {topic.topic}: {topic.description}")
        
        topics_text = "\n".join(topic_points[:5]) if topic_points else "- General tech updates"
        
        # Visual cues instruction
        visual_instruction = ""
        if self.config.include_visual_cues:
            visual_instruction = """
Include visual cues for on-screen text and visual directions.
Format visual cues as a JSON array of strings describing what should appear on screen."""
        
        prompt = f"""Create a TikTok script based on the following tech newsletter content.

## Content Summary
{content.overall_summary}

## Key Topics
{topics_text}

## Script Requirements
- Duration: {self.config.duration} seconds (approximately {target_words} words)
- Style: {self.config.style}
{style_instruction}

## Structure Requirements
1. Hook: An attention-grabbing opening line (first 3 seconds are crucial!)
2. Main Points: 2-4 key points to cover
3. Call-to-Action: Engaging closing that encourages interaction
{visual_instruction}

## Response Format
Respond with a JSON object containing:
{{
  "title": "Short title for the script",
  "hook": "The attention-grabbing opening line",
  "main_points": ["Point 1", "Point 2", "Point 3"],
  "call_to_action": "The closing call-to-action",
  "visual_cues": ["Visual cue 1", "Visual cue 2"] // Only if visual cues requested
}}

Generate the TikTok script now:"""
        
        return prompt
    
    def _parse_response(self, response: str) -> dict:
        """Parse the LLM response to extract script components.
        
        Args:
            response: Raw LLM response
            
        Returns:
            Dictionary with script components
        """
        # Try to parse as JSON
        try:
            # Clean up response - remove markdown code blocks if present
            cleaned = response.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            elif cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()
            
            data = json.loads(cleaned)
            
            # Validate required fields
            if not isinstance(data, dict):
                raise ValueError("Response is not a JSON object")
            
            # Ensure main_points is a list
            if "main_points" in data and not isinstance(data["main_points"], list):
                data["main_points"] = [str(data["main_points"])]
            
            # Ensure visual_cues is a list if present
            if "visual_cues" in data and data["visual_cues"] is not None:
                if not isinstance(data["visual_cues"], list):
                    data["visual_cues"] = [str(data["visual_cues"])]
            
            return data
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse JSON response, extracting manually: {e}")
            return self._extract_from_text(response)
    
    def _extract_from_text(self, text: str) -> dict:
        """Extract script components from plain text response.
        
        Args:
            text: Plain text response
            
        Returns:
            Dictionary with extracted components
        """
        lines = text.strip().split("\n")
        
        # Default values
        result = {
            "title": "Tech Update",
            "hook": "",
            "main_points": [],
            "call_to_action": "",
            "visual_cues": [] if self.config.include_visual_cues else None,
        }
        
        # Try to extract components from text
        current_section = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            lower_line = line.lower()
            
            if "hook" in lower_line and ":" in line:
                result["hook"] = line.split(":", 1)[1].strip().strip('"')
                current_section = "hook"
            elif "call" in lower_line and "action" in lower_line and ":" in line:
                result["call_to_action"] = line.split(":", 1)[1].strip().strip('"')
                current_section = "cta"
            elif "title" in lower_line and ":" in line:
                result["title"] = line.split(":", 1)[1].strip().strip('"')
            elif "point" in lower_line or line.startswith("-") or line.startswith("•"):
                point = line.lstrip("-•").strip()
                if point and len(point) > 5:
                    result["main_points"].append(point)
            elif "visual" in lower_line and ":" in line:
                current_section = "visual"
            elif current_section == "visual" and (line.startswith("-") or line.startswith("•")):
                cue = line.lstrip("-•").strip()
                if cue and result["visual_cues"] is not None:
                    result["visual_cues"].append(cue)
        
        # If no hook found, use first non-empty line
        if not result["hook"] and lines:
            for line in lines:
                if line.strip() and len(line.strip()) > 10:
                    result["hook"] = line.strip()
                    break
        
        # If no main points, extract from content
        if not result["main_points"]:
            result["main_points"] = ["Check out the latest tech news!"]
        
        # If no CTA, use default
        if not result["call_to_action"]:
            result["call_to_action"] = "Follow for more tech updates!"
        
        return result
    
    def _build_full_script(self, script_data: dict) -> str:
        """Build the full script text from components.
        
        Args:
            script_data: Dictionary with script components
            
        Returns:
            Full script as a single string
        """
        parts = []
        
        # Hook
        if script_data.get("hook"):
            parts.append(script_data["hook"])
        
        # Main points
        for point in script_data.get("main_points", []):
            parts.append(point)
        
        # Call to action
        if script_data.get("call_to_action"):
            parts.append(script_data["call_to_action"])
        
        return "\n\n".join(parts)
