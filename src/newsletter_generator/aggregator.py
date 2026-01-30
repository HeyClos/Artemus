"""
Newsletter aggregation components for Newsletter Content Generator.

This module provides classes for fetching and parsing newsletters from
various sources (email, RSS feeds, local files) and aggregating them
into a normalized format.

Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.2, 2.3, 2.4, 2.5
"""

from __future__ import annotations

import email
import imaplib
import logging
import re
from datetime import datetime
from email.header import decode_header
from email.message import Message
from email.utils import parsedate_to_datetime
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from bs4 import BeautifulSoup

if TYPE_CHECKING:
    from newsletter_generator.config import (
        EmailSourceConfig,
        FileSourceConfig,
        RSSSourceConfig,
    )
    from newsletter_generator.models import NewsletterItem

# Configure logger for this module
logger = logging.getLogger(__name__)


class ContentParser:
    """Parses and cleans newsletter content from various formats.
    
    Handles extraction of main content from HTML, removal of boilerplate
    (headers, footers, advertisements), and normalization of text.
    
    Validates: Requirements 2.2, 2.3
    """
    
    # Tags to remove completely (including their content)
    REMOVE_TAGS = ['script', 'style', 'nav', 'footer', 'header', 'noscript', 'iframe']
    
    # Common boilerplate patterns to remove
    BOILERPLATE_PATTERNS = [
        # Unsubscribe patterns
        r'(?i)\bunsubscribe\b.*?(?:\.|$)',
        r'(?i)click\s+here\s+to\s+unsubscribe',
        r'(?i)to\s+unsubscribe\s+from\s+this\s+list',
        r'(?i)manage\s+your\s+subscription',
        r'(?i)update\s+your\s+preferences',
        # View in browser patterns
        r'(?i)view\s+(?:this\s+)?(?:email\s+)?in\s+(?:your\s+)?browser',
        r'(?i)view\s+online',
        r'(?i)read\s+online',
        r'(?i)having\s+trouble\s+viewing\s+this',
        # Copyright patterns
        r'(?i)©\s*\d{4}.*?(?:all\s+rights\s+reserved)?\.?',
        r'(?i)copyright\s*©?\s*\d{4}.*?(?:\.|$)',
        r'(?i)all\s+rights\s+reserved\.?',
        # Social media follow patterns
        r'(?i)follow\s+us\s+on\s+(?:twitter|facebook|instagram|linkedin)',
        r'(?i)connect\s+with\s+us\s+on',
        r'(?i)like\s+us\s+on\s+facebook',
        r'(?i)join\s+us\s+on\s+social\s+media',
        # Address/contact patterns often in footers
        r'(?i)sent\s+to\s+[\w.+-]+@[\w.-]+',
        r'(?i)you\s+are\s+receiving\s+this\s+(?:email|newsletter)',
        r'(?i)this\s+email\s+was\s+sent\s+to',
        # Forward patterns
        r'(?i)forward\s+this\s+email',
        r'(?i)share\s+with\s+a\s+friend',
    ]
    
    def __init__(self) -> None:
        """Initialize the content parser with compiled regex patterns."""
        self._boilerplate_regexes = [
            re.compile(pattern) for pattern in self.BOILERPLATE_PATTERNS
        ]
    
    def extract_text(self, html: str) -> str:
        """Extract main content text from HTML.
        
        Removes HTML tags, scripts, styles, nav, footer, and header elements,
        and extracts readable text while preserving paragraph structure.
        
        Args:
            html: Raw HTML content
            
        Returns:
            Extracted plain text content with paragraph structure preserved
            
        Validates: Requirements 2.2
        """
        if not html or not html.strip():
            return ""
        
        # Parse HTML with BeautifulSoup
        soup = BeautifulSoup(html, 'lxml')
        
        # Remove unwanted tags completely (including their content)
        for tag_name in self.REMOVE_TAGS:
            for tag in soup.find_all(tag_name):
                tag.decompose()
        
        # Also remove common ad/tracking elements by class or id patterns
        for element in soup.find_all(
            attrs={'class': re.compile(r'(?i)(ad|advertisement|tracking|social-share)')}
        ):
            element.decompose()
        
        for element in soup.find_all(
            attrs={'id': re.compile(r'(?i)(ad|advertisement|tracking|social-share)')}
        ):
            element.decompose()
        
        # Extract text with paragraph preservation
        # Process block-level elements to add newlines
        block_elements = ['p', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 
                         'li', 'tr', 'br', 'article', 'section']
        
        # Add newlines after block elements for structure preservation
        for tag_name in block_elements:
            for tag in soup.find_all(tag_name):
                if tag.string:
                    tag.string.replace_with(tag.string + '\n')
                else:
                    tag.append('\n')
        
        # Get text content
        text = soup.get_text(separator=' ')
        
        # Clean up the extracted text
        # Replace multiple spaces with single space
        text = re.sub(r'[ \t]+', ' ', text)
        
        # Normalize newlines - replace multiple newlines with double newline
        text = re.sub(r'\n\s*\n+', '\n\n', text)
        
        # Strip leading/trailing whitespace from each line
        lines = [line.strip() for line in text.split('\n')]
        text = '\n'.join(lines)
        
        # Remove leading/trailing whitespace from the whole text
        text = text.strip()
        
        return text
    
    def clean_content(self, text: str) -> str:
        """Clean and normalize text content.
        
        Removes excess whitespace, common newsletter boilerplate patterns
        (unsubscribe links, view in browser, copyright notices, social media
        follow prompts), and normalizes line endings.
        
        Args:
            text: Raw text content
            
        Returns:
            Cleaned and normalized text
            
        Validates: Requirements 2.3
        """
        if not text or not text.strip():
            return ""
        
        # Remove boilerplate patterns
        cleaned = text
        for pattern in self._boilerplate_regexes:
            cleaned = pattern.sub('', cleaned)
        
        # Normalize whitespace
        # Replace multiple spaces/tabs with single space
        cleaned = re.sub(r'[ \t]+', ' ', cleaned)
        
        # Normalize line endings (convert \r\n and \r to \n)
        cleaned = cleaned.replace('\r\n', '\n').replace('\r', '\n')
        
        # Remove excessive blank lines (more than 2 consecutive newlines -> 2)
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        
        # Strip whitespace from each line
        lines = [line.strip() for line in cleaned.split('\n')]
        
        # Remove empty lines at the start and end, but preserve internal structure
        # Filter out completely empty lines that are consecutive
        result_lines = []
        prev_empty = False
        for line in lines:
            if line:
                result_lines.append(line)
                prev_empty = False
            elif not prev_empty:
                result_lines.append(line)
                prev_empty = True
        
        cleaned = '\n'.join(result_lines)
        
        # Final strip
        cleaned = cleaned.strip()
        
        return cleaned


@runtime_checkable
class SourceFetcher(Protocol):
    """Protocol for newsletter source fetchers.
    
    All source fetchers must implement this protocol to be used
    with the NewsletterAggregator.
    """
    
    def fetch(self, since: datetime) -> list[NewsletterItem]:
        """Fetch newsletter items since the given date.
        
        Args:
            since: Only fetch items published after this date
            
        Returns:
            List of fetched newsletter items
        """
        ...


class EmailFetcher:
    """Fetches newsletters from an email account via IMAP.
    
    Connects to an IMAP server, retrieves emails from a specified folder,
    and parses them into NewsletterItem objects.
    
    Attributes:
        config: Email source configuration
        parser: ContentParser for extracting text from HTML emails
        
    Validates: Requirements 1.1, 2.2
    """
    
    def __init__(self, config: EmailSourceConfig) -> None:
        """Initialize the email fetcher.
        
        Args:
            config: Email source configuration
        """
        self.config = config
        self.parser = ContentParser()
    
    def fetch(self, since: datetime) -> list[NewsletterItem]:
        """Fetch emails from the configured folder since the given date.
        
        Connects to the IMAP server, searches for emails since the given date,
        parses each email, and returns a list of NewsletterItem objects.
        
        Args:
            since: Only fetch emails received after this date
            
        Returns:
            List of newsletter items parsed from emails. Returns empty list
            if connection fails or no emails are found.
            
        Validates: Requirements 1.1, 1.5, 2.2
        """
        # Import here to avoid circular imports
        from newsletter_generator.models import NewsletterItem
        
        items: list[NewsletterItem] = []
        connection: imaplib.IMAP4 | imaplib.IMAP4_SSL | None = None
        
        try:
            # Connect to IMAP server
            if self.config.use_ssl:
                connection = imaplib.IMAP4_SSL(
                    self.config.host,
                    self.config.port
                )
            else:
                connection = imaplib.IMAP4(
                    self.config.host,
                    self.config.port
                )
            
            # Login with credentials
            connection.login(self.config.username, self.config.password)
            
            # Select the configured folder
            status, _ = connection.select(self.config.folder, readonly=True)
            if status != "OK":
                logger.error(
                    f"Failed to select folder '{self.config.folder}' "
                    f"on {self.config.host}"
                )
                return items
            
            # Format date for IMAP SINCE search
            # IMAP date format: DD-Mon-YYYY (e.g., "01-Jan-2024")
            date_str = since.strftime("%d-%b-%Y")
            
            # Search for emails since the given date
            status, message_ids = connection.search(None, f'SINCE {date_str}')
            if status != "OK":
                logger.error(
                    f"Failed to search emails in folder '{self.config.folder}' "
                    f"on {self.config.host}"
                )
                return items
            
            # Get list of message IDs
            id_list = message_ids[0].split()
            
            # Fetch each email
            for msg_id in id_list:
                try:
                    # Fetch the email content
                    status, msg_data = connection.fetch(msg_id, "(RFC822)")
                    if status != "OK" or not msg_data or not msg_data[0]:
                        logger.warning(
                            f"Failed to fetch email {msg_id} from {self.config.host}"
                        )
                        continue
                    
                    # Parse the email message
                    raw_email = msg_data[0][1]
                    if isinstance(raw_email, bytes):
                        email_message = email.message_from_bytes(raw_email)
                    else:
                        email_message = email.message_from_string(raw_email)
                    
                    # Extract email fields
                    subject = self._decode_header(email_message.get("Subject", ""))
                    from_addr = self._decode_header(email_message.get("From", ""))
                    date_header = email_message.get("Date", "")
                    
                    # Parse the date
                    published_date = self._parse_date(date_header)
                    if published_date is None:
                        published_date = datetime.now()
                    
                    # Skip emails before the since date (IMAP SINCE is inclusive of the day)
                    # Handle timezone-aware vs naive datetime comparison
                    since_for_comparison = since
                    published_for_comparison = published_date
                    
                    # If one is timezone-aware and the other is not, make them comparable
                    if published_date.tzinfo is not None and since.tzinfo is None:
                        # Remove timezone info from published_date for comparison
                        published_for_comparison = published_date.replace(tzinfo=None)
                    elif published_date.tzinfo is None and since.tzinfo is not None:
                        # Remove timezone info from since for comparison
                        since_for_comparison = since.replace(tzinfo=None)
                    
                    if published_for_comparison < since_for_comparison:
                        continue
                    
                    # Extract email body
                    body_html, body_text = self._get_email_body(email_message)
                    
                    # Use HTML content if available, otherwise use plain text
                    if body_html:
                        content = self.parser.extract_text(body_html)
                        content = self.parser.clean_content(content)
                        html_content = body_html
                    else:
                        content = self.parser.clean_content(body_text or "")
                        html_content = None
                    
                    # Create NewsletterItem
                    item = NewsletterItem(
                        source_name=f"Email: {self.config.host}",
                        source_type="email",
                        title=subject or "(No Subject)",
                        content=content,
                        published_date=published_date,
                        html_content=html_content,
                        author=from_addr or None,
                        url=None,
                    )
                    items.append(item)
                    
                except Exception as e:
                    logger.warning(
                        f"Failed to parse email {msg_id} from {self.config.host}: {e}"
                    )
                    continue
            
        except imaplib.IMAP4.error as e:
            logger.error(
                f"IMAP error connecting to {self.config.host}: {e}"
            )
        except ConnectionRefusedError as e:
            logger.error(
                f"Connection refused to {self.config.host}:{self.config.port}: {e}"
            )
        except TimeoutError as e:
            logger.error(
                f"Connection timeout to {self.config.host}:{self.config.port}: {e}"
            )
        except Exception as e:
            logger.error(
                f"Unexpected error fetching emails from {self.config.host}: {e}"
            )
        finally:
            # Close connection properly
            if connection is not None:
                try:
                    connection.close()
                except Exception:
                    pass  # Ignore errors during close
                try:
                    connection.logout()
                except Exception:
                    pass  # Ignore errors during logout
        
        return items
    
    def _get_email_body(self, message: Message) -> tuple[str | None, str | None]:
        """Extract the body content from an email message.
        
        Handles both multipart and simple messages, extracting HTML and
        plain text content.
        
        Args:
            message: The email message to extract body from
            
        Returns:
            Tuple of (html_content, text_content), either may be None
        """
        html_content: str | None = None
        text_content: str | None = None
        
        if message.is_multipart():
            # Walk through all parts of the message
            for part in message.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", ""))
                
                # Skip attachments
                if "attachment" in content_disposition:
                    continue
                
                # Get the payload
                try:
                    payload = part.get_payload(decode=True)
                    if payload is None:
                        continue
                    
                    # Decode the payload
                    charset = part.get_content_charset() or "utf-8"
                    try:
                        decoded_payload = payload.decode(charset, errors="replace")
                    except (LookupError, UnicodeDecodeError):
                        decoded_payload = payload.decode("utf-8", errors="replace")
                    
                    if content_type == "text/html":
                        html_content = decoded_payload
                    elif content_type == "text/plain":
                        text_content = decoded_payload
                        
                except Exception as e:
                    logger.debug(f"Failed to decode email part: {e}")
                    continue
        else:
            # Simple message (not multipart)
            content_type = message.get_content_type()
            try:
                payload = message.get_payload(decode=True)
                if payload is not None:
                    charset = message.get_content_charset() or "utf-8"
                    try:
                        decoded_payload = payload.decode(charset, errors="replace")
                    except (LookupError, UnicodeDecodeError):
                        decoded_payload = payload.decode("utf-8", errors="replace")
                    
                    if content_type == "text/html":
                        html_content = decoded_payload
                    else:
                        text_content = decoded_payload
            except Exception as e:
                logger.debug(f"Failed to decode email payload: {e}")
        
        return html_content, text_content
    
    def _parse_date(self, date_str: str) -> datetime | None:
        """Parse an email date header into a datetime object.
        
        Args:
            date_str: The date string from the email header
            
        Returns:
            Parsed datetime or None if parsing fails
        """
        if not date_str:
            return None
        
        try:
            # Use email.utils.parsedate_to_datetime for RFC 2822 dates
            return parsedate_to_datetime(date_str)
        except (ValueError, TypeError):
            pass
        
        # Try common date formats as fallback
        date_formats = [
            "%a, %d %b %Y %H:%M:%S %z",
            "%a, %d %b %Y %H:%M:%S",
            "%d %b %Y %H:%M:%S %z",
            "%d %b %Y %H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except ValueError:
                continue
        
        logger.debug(f"Failed to parse email date: {date_str}")
        return None
    
    def _decode_header(self, header_value: str | None) -> str:
        """Decode an email header value that may be encoded.
        
        Handles RFC 2047 encoded headers (e.g., =?UTF-8?Q?...?=).
        
        Args:
            header_value: The raw header value
            
        Returns:
            Decoded header string
        """
        if not header_value:
            return ""
        
        try:
            decoded_parts = decode_header(header_value)
            result_parts = []
            
            for part, charset in decoded_parts:
                if isinstance(part, bytes):
                    if charset:
                        try:
                            result_parts.append(part.decode(charset, errors="replace"))
                        except (LookupError, UnicodeDecodeError):
                            result_parts.append(part.decode("utf-8", errors="replace"))
                    else:
                        result_parts.append(part.decode("utf-8", errors="replace"))
                else:
                    result_parts.append(str(part))
            
            return "".join(result_parts)
        except Exception:
            return str(header_value)


class RSSFetcher:
    """Fetches newsletters from an RSS feed.
    
    Uses feedparser to fetch and parse RSS/Atom feeds into
    NewsletterItem objects.
    
    Attributes:
        config: RSS source configuration
        parser: ContentParser for extracting text from HTML content
        
    Validates: Requirements 1.2, 2.3
    """
    
    def __init__(self, config: RSSSourceConfig) -> None:
        """Initialize the RSS fetcher.
        
        Args:
            config: RSS source configuration
        """
        self.config = config
        self.parser = ContentParser()
    
    def fetch(self, since: datetime) -> list[NewsletterItem]:
        """Fetch RSS feed entries since the given date.
        
        Connects to the RSS feed URL, parses entries, and returns
        NewsletterItem objects for entries published after the since date.
        
        Args:
            since: Only fetch entries published after this date
            
        Returns:
            List of newsletter items parsed from feed entries. Returns empty
            list if the feed cannot be fetched or parsed.
            
        Validates: Requirements 1.2, 1.5, 2.3
        """
        # Import here to avoid circular imports
        from newsletter_generator.models import NewsletterItem
        
        import feedparser
        
        items: list[NewsletterItem] = []
        
        try:
            # Fetch and parse the RSS feed
            feed = feedparser.parse(self.config.url)
            
            # Check for feed-level errors
            if feed.bozo and feed.bozo_exception:
                # bozo flag indicates a feed parsing issue
                # Log but continue - feedparser often recovers partial data
                logger.warning(
                    f"RSS feed '{self.config.name}' ({self.config.url}) "
                    f"has parsing issues: {feed.bozo_exception}"
                )
            
            # Check if feed has entries
            if not feed.entries:
                logger.info(
                    f"RSS feed '{self.config.name}' ({self.config.url}) "
                    "has no entries"
                )
                return items
            
            # Process each entry
            for entry in feed.entries:
                try:
                    # Extract published date
                    published_date = self._parse_entry_date(entry)
                    if published_date is None:
                        # Use current time if no date available
                        published_date = datetime.now()
                    
                    # Filter by date - skip entries before the since date
                    # Handle timezone-aware vs naive datetime comparison
                    since_for_comparison = since
                    published_for_comparison = published_date
                    
                    if published_date.tzinfo is not None and since.tzinfo is None:
                        published_for_comparison = published_date.replace(tzinfo=None)
                    elif published_date.tzinfo is None and since.tzinfo is not None:
                        since_for_comparison = since.replace(tzinfo=None)
                    
                    if published_for_comparison < since_for_comparison:
                        continue
                    
                    # Extract title
                    title = entry.get("title", "").strip()
                    if not title:
                        title = "(No Title)"
                    
                    # Extract content - try multiple fields
                    html_content, text_content = self._extract_entry_content(entry)
                    
                    # Parse HTML content if available
                    if html_content:
                        content = self.parser.extract_text(html_content)
                        content = self.parser.clean_content(content)
                    elif text_content:
                        content = self.parser.clean_content(text_content)
                    else:
                        # Use summary as fallback
                        summary = entry.get("summary", "")
                        if summary:
                            content = self.parser.extract_text(summary)
                            content = self.parser.clean_content(content)
                            html_content = summary if "<" in summary else None
                        else:
                            content = ""
                    
                    # Extract author
                    author = self._extract_author(entry)
                    
                    # Extract URL
                    url = entry.get("link", None)
                    
                    # Create NewsletterItem
                    item = NewsletterItem(
                        source_name=self.config.name,
                        source_type="rss",
                        title=title,
                        content=content,
                        published_date=published_date,
                        html_content=html_content,
                        author=author,
                        url=url,
                    )
                    items.append(item)
                    
                except Exception as e:
                    logger.warning(
                        f"Failed to parse RSS entry from '{self.config.name}': {e}"
                    )
                    continue
                    
        except Exception as e:
            logger.error(
                f"Failed to fetch RSS feed '{self.config.name}' "
                f"({self.config.url}): {e}"
            )
        
        return items
    
    def _parse_entry_date(self, entry: dict) -> datetime | None:
        """Parse the published date from an RSS entry.
        
        Tries multiple date fields commonly used in RSS/Atom feeds.
        
        Args:
            entry: The feedparser entry dict
            
        Returns:
            Parsed datetime or None if no valid date found
        """
        import time
        from calendar import timegm
        
        # Try different date fields in order of preference
        date_fields = [
            "published_parsed",
            "updated_parsed",
            "created_parsed",
        ]
        
        for field in date_fields:
            parsed_time = entry.get(field)
            if parsed_time:
                try:
                    # feedparser returns time.struct_time
                    # Convert to datetime
                    timestamp = timegm(parsed_time)
                    return datetime.utcfromtimestamp(timestamp)
                except (ValueError, TypeError, OverflowError):
                    continue
        
        # Try string date fields as fallback
        string_date_fields = ["published", "updated", "created"]
        for field in string_date_fields:
            date_str = entry.get(field)
            if date_str:
                parsed = self._parse_date_string(date_str)
                if parsed:
                    return parsed
        
        return None
    
    def _parse_date_string(self, date_str: str) -> datetime | None:
        """Parse a date string into a datetime object.
        
        Args:
            date_str: The date string to parse
            
        Returns:
            Parsed datetime or None if parsing fails
        """
        if not date_str:
            return None
        
        # Common date formats in RSS feeds
        date_formats = [
            "%a, %d %b %Y %H:%M:%S %z",  # RFC 2822
            "%a, %d %b %Y %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S%z",  # ISO 8601 with timezone
            "%Y-%m-%dT%H:%M:%SZ",  # ISO 8601 UTC
            "%Y-%m-%dT%H:%M:%S",  # ISO 8601 without timezone
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
            "%d %b %Y %H:%M:%S %z",
            "%d %b %Y %H:%M:%S",
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except ValueError:
                continue
        
        logger.debug(f"Failed to parse RSS date: {date_str}")
        return None
    
    def _extract_entry_content(self, entry: dict) -> tuple[str | None, str | None]:
        """Extract content from an RSS entry.
        
        Tries multiple content fields and returns both HTML and plain text
        versions if available.
        
        Args:
            entry: The feedparser entry dict
            
        Returns:
            Tuple of (html_content, text_content), either may be None
        """
        html_content: str | None = None
        text_content: str | None = None
        
        # Try 'content' field first (often contains full article)
        content_list = entry.get("content", [])
        if content_list:
            for content_item in content_list:
                content_type = content_item.get("type", "")
                value = content_item.get("value", "")
                
                if "html" in content_type.lower():
                    html_content = value
                elif "text" in content_type.lower() or not content_type:
                    if "<" in value and ">" in value:
                        html_content = value
                    else:
                        text_content = value
        
        # Try 'summary_detail' for more detailed summary
        if not html_content and not text_content:
            summary_detail = entry.get("summary_detail", {})
            if summary_detail:
                content_type = summary_detail.get("type", "")
                value = summary_detail.get("value", "")
                
                if value:
                    if "html" in content_type.lower() or ("<" in value and ">" in value):
                        html_content = value
                    else:
                        text_content = value
        
        # Fall back to 'description' field
        if not html_content and not text_content:
            description = entry.get("description", "")
            if description:
                if "<" in description and ">" in description:
                    html_content = description
                else:
                    text_content = description
        
        return html_content, text_content
    
    def _extract_author(self, entry: dict) -> str | None:
        """Extract author information from an RSS entry.
        
        Args:
            entry: The feedparser entry dict
            
        Returns:
            Author name or None if not available
        """
        # Try 'author' field first
        author = entry.get("author")
        if author:
            return author.strip()
        
        # Try 'author_detail' for more structured author info
        author_detail = entry.get("author_detail", {})
        if author_detail:
            name = author_detail.get("name")
            if name:
                return name.strip()
        
        # Try 'authors' list
        authors = entry.get("authors", [])
        if authors:
            first_author = authors[0]
            if isinstance(first_author, dict):
                name = first_author.get("name")
                if name:
                    return name.strip()
            elif isinstance(first_author, str):
                return first_author.strip()
        
        return None


class FileFetcher:
    """Fetches newsletters from local files.
    
    Reads newsletter content from local files matching a glob pattern.
    Supports both HTML and plain text files.
    
    Attributes:
        config: File source configuration
        parser: ContentParser for extracting text from HTML files
        
    Validates: Requirements 1.3
    """
    
    def __init__(self, config: FileSourceConfig) -> None:
        """Initialize the file fetcher.
        
        Args:
            config: File source configuration
        """
        self.config = config
        self.parser = ContentParser()
    
    def fetch(self, since: datetime) -> list[NewsletterItem]:
        """Fetch newsletter content from local files.
        
        Reads files matching the configured glob pattern from the configured
        directory path. Only files modified after the since date are included.
        
        Args:
            since: Only fetch files modified after this date
            
        Returns:
            List of newsletter items parsed from files. Returns empty list
            if the directory doesn't exist or no matching files are found.
            
        Validates: Requirements 1.3, 1.5
        """
        # Import here to avoid circular imports
        from newsletter_generator.models import NewsletterItem
        from pathlib import Path
        import os
        
        items: list[NewsletterItem] = []
        
        try:
            # Expand user home directory (~) in path
            base_path = Path(self.config.path).expanduser()
            
            # Check if directory exists
            if not base_path.exists():
                logger.warning(
                    f"File source directory does not exist: {self.config.path}"
                )
                return items
            
            if not base_path.is_dir():
                logger.warning(
                    f"File source path is not a directory: {self.config.path}"
                )
                return items
            
            # Find files matching the glob pattern
            matching_files = list(base_path.glob(self.config.pattern))
            
            if not matching_files:
                logger.info(
                    f"No files matching pattern '{self.config.pattern}' "
                    f"found in {self.config.path}"
                )
                return items
            
            # Process each matching file
            for file_path in matching_files:
                try:
                    # Skip directories
                    if file_path.is_dir():
                        continue
                    
                    # Get file modification time
                    mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    
                    # Filter by modification date
                    # Handle timezone-aware vs naive datetime comparison
                    since_for_comparison = since
                    mtime_for_comparison = mtime
                    
                    if mtime.tzinfo is not None and since.tzinfo is None:
                        mtime_for_comparison = mtime.replace(tzinfo=None)
                    elif mtime.tzinfo is None and since.tzinfo is not None:
                        since_for_comparison = since.replace(tzinfo=None)
                    
                    if mtime_for_comparison < since_for_comparison:
                        continue
                    
                    # Read file content
                    content, html_content = self._read_file(file_path)
                    
                    if not content and not html_content:
                        logger.warning(
                            f"Empty or unreadable file: {file_path}"
                        )
                        continue
                    
                    # Create NewsletterItem
                    item = NewsletterItem(
                        source_name=f"File: {self.config.path}",
                        source_type="file",
                        title=file_path.stem,  # Filename without extension
                        content=content,
                        published_date=mtime,
                        html_content=html_content,
                        author=None,
                        url=str(file_path.absolute()),
                    )
                    items.append(item)
                    
                except PermissionError as e:
                    logger.error(
                        f"Permission denied reading file {file_path}: {e}"
                    )
                    continue
                except OSError as e:
                    logger.warning(
                        f"Failed to read file {file_path}: {e}"
                    )
                    continue
                except Exception as e:
                    logger.warning(
                        f"Unexpected error processing file {file_path}: {e}"
                    )
                    continue
                    
        except PermissionError as e:
            logger.error(
                f"Permission denied accessing directory {self.config.path}: {e}"
            )
        except Exception as e:
            logger.error(
                f"Failed to access file source directory {self.config.path}: {e}"
            )
        
        return items
    
    def _read_file(self, file_path) -> tuple[str, str | None]:
        """Read and parse content from a file.
        
        Detects file type based on extension and parses accordingly.
        HTML files are parsed to extract text content.
        
        Args:
            file_path: Path to the file to read
            
        Returns:
            Tuple of (plain_text_content, html_content).
            html_content is None for non-HTML files.
        """
        from pathlib import Path
        
        # Determine file type from extension
        suffix = Path(file_path).suffix.lower()
        
        # Read file content
        try:
            # Try UTF-8 first, fall back to latin-1
            try:
                raw_content = Path(file_path).read_text(encoding="utf-8")
            except UnicodeDecodeError:
                raw_content = Path(file_path).read_text(encoding="latin-1")
        except Exception as e:
            logger.warning(f"Failed to read file {file_path}: {e}")
            return "", None
        
        if not raw_content.strip():
            return "", None
        
        # Parse based on file type
        if suffix in (".html", ".htm"):
            # HTML file - extract text and keep original HTML
            text_content = self.parser.extract_text(raw_content)
            text_content = self.parser.clean_content(text_content)
            return text_content, raw_content
        else:
            # Plain text file (or unknown type) - clean the content
            text_content = self.parser.clean_content(raw_content)
            return text_content, None


class NewsletterAggregator:
    """Aggregates newsletters from multiple sources.
    
    Coordinates multiple source fetchers, handles failures gracefully,
    and returns a combined list of normalized newsletter items.
    
    Attributes:
        fetchers: List of source fetchers to use
        parser: Content parser for normalizing content
        
    Validates: Requirements 1.4, 1.5, 2.1, 2.5
    """
    
    def __init__(
        self,
        fetchers: list[SourceFetcher],
        parser: ContentParser | None = None,
    ) -> None:
        """Initialize the aggregator.
        
        Args:
            fetchers: List of source fetchers
            parser: Content parser for normalizing content (optional, creates default if None)
        """
        self.fetchers = fetchers
        self.parser = parser if parser is not None else ContentParser()
    
    def aggregate(self, since: datetime) -> list[NewsletterItem]:
        """Aggregate newsletters from all configured sources.
        
        Fetches from all sources, handles failures gracefully (logging
        errors and continuing with remaining sources), and returns
        normalized items filtered by date range.
        
        Args:
            since: Only fetch items published after this date
            
        Returns:
            List of aggregated and normalized newsletter items
            
        Validates: Requirements 1.4, 1.5, 2.1, 2.5
        """
        # Import here to avoid circular imports
        from newsletter_generator.models import NewsletterItem
        
        all_items: list[NewsletterItem] = []
        
        # Iterate through all fetchers and collect items
        for fetcher in self.fetchers:
            try:
                # Fetch items from this source
                items = fetcher.fetch(since)
                
                # Filter items by date range (additional safety check)
                # Some fetchers may return items outside the date range
                filtered_items = self._filter_by_date(items, since)
                
                # Normalize content for each item
                normalized_items = [
                    self._normalize_item(item) for item in filtered_items
                ]
                
                all_items.extend(normalized_items)
                
                logger.info(
                    f"Fetched {len(normalized_items)} items from "
                    f"{self._get_fetcher_name(fetcher)}"
                )
                
            except Exception as e:
                # Log the error and continue with remaining sources
                # This ensures one failing source doesn't break the entire aggregation
                fetcher_name = self._get_fetcher_name(fetcher)
                logger.error(
                    f"Failed to fetch from {fetcher_name}: {e}"
                )
                # Continue to next fetcher - don't re-raise
                continue
        
        logger.info(f"Aggregated {len(all_items)} total items from {len(self.fetchers)} sources")
        
        return all_items
    
    def _filter_by_date(
        self,
        items: list[NewsletterItem],
        since: datetime,
    ) -> list[NewsletterItem]:
        """Filter items to only include those published after the since date.
        
        Handles timezone-aware and timezone-naive datetime comparisons.
        
        Args:
            items: List of newsletter items to filter
            since: Only include items published after this date
            
        Returns:
            Filtered list of items
            
        Validates: Requirements 2.1
        """
        filtered: list[NewsletterItem] = []
        
        for item in items:
            # Handle timezone-aware vs naive datetime comparison
            published = item.published_date
            since_cmp = since
            
            if published.tzinfo is not None and since.tzinfo is None:
                # Remove timezone info from published for comparison
                published = published.replace(tzinfo=None)
            elif published.tzinfo is None and since.tzinfo is not None:
                # Remove timezone info from since for comparison
                since_cmp = since.replace(tzinfo=None)
            
            # Include items published on or after the since date
            if published >= since_cmp:
                filtered.append(item)
        
        return filtered
    
    def _normalize_item(self, item: NewsletterItem) -> NewsletterItem:
        """Normalize a newsletter item's content.
        
        Ensures content is cleaned and normalized using the content parser.
        
        Args:
            item: The newsletter item to normalize
            
        Returns:
            A new NewsletterItem with normalized content
            
        Validates: Requirements 2.4
        """
        from newsletter_generator.models import NewsletterItem
        
        # Clean the content using the parser
        normalized_content = self.parser.clean_content(item.content)
        
        # Return a new item with normalized content
        return NewsletterItem(
            source_name=item.source_name,
            source_type=item.source_type,
            title=item.title,
            content=normalized_content,
            published_date=item.published_date,
            html_content=item.html_content,
            author=item.author,
            url=item.url,
        )
    
    def _get_fetcher_name(self, fetcher: SourceFetcher) -> str:
        """Get a human-readable name for a fetcher.
        
        Args:
            fetcher: The fetcher to get a name for
            
        Returns:
            A descriptive name for the fetcher
        """
        # Try to get a descriptive name based on fetcher type and config
        fetcher_type = type(fetcher).__name__
        
        # Try to get more specific info from config if available
        if hasattr(fetcher, 'config'):
            config = fetcher.config
            if hasattr(config, 'name'):
                return f"{fetcher_type}({config.name})"
            elif hasattr(config, 'host'):
                return f"{fetcher_type}({config.host})"
            elif hasattr(config, 'url'):
                return f"{fetcher_type}({config.url})"
            elif hasattr(config, 'path'):
                return f"{fetcher_type}({config.path})"
        
        return fetcher_type
