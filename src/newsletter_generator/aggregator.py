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
    """
    
    def __init__(self, config: RSSSourceConfig) -> None:
        """Initialize the RSS fetcher.
        
        Args:
            config: RSS source configuration
        """
        self.config = config
    
    def fetch(self, since: datetime) -> list[NewsletterItem]:
        """Fetch RSS feed entries since the given date.
        
        Args:
            since: Only fetch entries published after this date
            
        Returns:
            List of newsletter items parsed from feed entries
        """
        raise NotImplementedError("RSSFetcher.fetch() not yet implemented")


class FileFetcher:
    """Fetches newsletters from local files.
    
    Reads newsletter content from local files matching a glob pattern.
    
    Attributes:
        config: File source configuration
    """
    
    def __init__(self, config: FileSourceConfig) -> None:
        """Initialize the file fetcher.
        
        Args:
            config: File source configuration
        """
        self.config = config
    
    def fetch(self, since: datetime) -> list[NewsletterItem]:
        """Fetch newsletter content from local files.
        
        Args:
            since: Only fetch files modified after this date
            
        Returns:
            List of newsletter items parsed from files
        """
        raise NotImplementedError("FileFetcher.fetch() not yet implemented")


class NewsletterAggregator:
    """Aggregates newsletters from multiple sources.
    
    Coordinates multiple source fetchers, handles failures gracefully,
    and returns a combined list of normalized newsletter items.
    
    Attributes:
        fetchers: List of source fetchers to use
        parser: Content parser for normalizing content
    """
    
    def __init__(
        self,
        fetchers: list[SourceFetcher],
        parser: ContentParser,
    ) -> None:
        """Initialize the aggregator.
        
        Args:
            fetchers: List of source fetchers
            parser: Content parser for normalizing content
        """
        self.fetchers = fetchers
        self.parser = parser
    
    def aggregate(self, since: datetime) -> list[NewsletterItem]:
        """Aggregate newsletters from all configured sources.
        
        Fetches from all sources, handles failures gracefully (logging
        errors and continuing with remaining sources), and returns
        normalized items.
        
        Args:
            since: Only fetch items published after this date
            
        Returns:
            List of aggregated and normalized newsletter items
        """
        raise NotImplementedError("NewsletterAggregator.aggregate() not yet implemented")
