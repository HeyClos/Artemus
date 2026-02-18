"""
Tests for newsletter aggregation components.

This module contains unit tests and property-based tests for the
ContentParser, fetchers, and NewsletterAggregator.

Property tests:
- Property 3: Date Range Filtering (Validates: Requirements 2.1)
- Property 4: Content Normalization (Validates: Requirements 2.4, 1.4)
- Property 5: Source Failure Resilience (Validates: Requirements 1.5, 2.5)
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from newsletter_generator.aggregator import ContentParser


class TestContentParser:
    """Unit tests for ContentParser.
    
    Validates: Requirements 2.2, 2.3
    """
    
    @pytest.fixture
    def parser(self) -> ContentParser:
        """Create a ContentParser instance for testing."""
        return ContentParser()
    
    # --- extract_text() tests ---
    
    def test_extract_text_simple_html(self, parser: ContentParser) -> None:
        """Test extraction from simple HTML with paragraphs."""
        html = "<html><body><p>Hello World</p><p>Second paragraph</p></body></html>"
        result = parser.extract_text(html)
        
        assert "Hello World" in result
        assert "Second paragraph" in result
    
    def test_extract_text_removes_script_tags(self, parser: ContentParser) -> None:
        """Test that script tags and their content are removed."""
        html = """
        <html>
        <body>
            <p>Visible content</p>
            <script>alert('malicious');</script>
            <p>More content</p>
        </body>
        </html>
        """
        result = parser.extract_text(html)
        
        assert "Visible content" in result
        assert "More content" in result
        assert "alert" not in result
        assert "malicious" not in result
        assert "script" not in result.lower()
    
    def test_extract_text_removes_style_tags(self, parser: ContentParser) -> None:
        """Test that style tags and their content are removed."""
        html = """
        <html>
        <head><style>.hidden { display: none; }</style></head>
        <body>
            <p>Visible content</p>
            <style>body { color: red; }</style>
        </body>
        </html>
        """
        result = parser.extract_text(html)
        
        assert "Visible content" in result
        assert "display" not in result
        assert "color" not in result
        assert ".hidden" not in result
    
    def test_extract_text_removes_nav_tags(self, parser: ContentParser) -> None:
        """Test that nav tags and their content are removed."""
        html = """
        <html>
        <body>
            <nav><a href="/">Home</a><a href="/about">About</a></nav>
            <p>Main content here</p>
        </body>
        </html>
        """
        result = parser.extract_text(html)
        
        assert "Main content here" in result
        # Nav content should be removed
        assert "Home" not in result or "About" not in result
    
    def test_extract_text_removes_footer_tags(self, parser: ContentParser) -> None:
        """Test that footer tags and their content are removed."""
        html = """
        <html>
        <body>
            <p>Main content</p>
            <footer>Copyright 2024 Company</footer>
        </body>
        </html>
        """
        result = parser.extract_text(html)
        
        assert "Main content" in result
        assert "Copyright" not in result
    
    def test_extract_text_removes_header_tags(self, parser: ContentParser) -> None:
        """Test that header tags (navigation headers) are removed."""
        html = """
        <html>
        <body>
            <header><h1>Site Title</h1><nav>Menu</nav></header>
            <article><p>Article content</p></article>
        </body>
        </html>
        """
        result = parser.extract_text(html)
        
        assert "Article content" in result
        # Header content should be removed
        assert "Site Title" not in result
    
    def test_extract_text_preserves_paragraph_structure(self, parser: ContentParser) -> None:
        """Test that paragraph structure is preserved with newlines."""
        html = """
        <html>
        <body>
            <p>First paragraph with some text.</p>
            <p>Second paragraph with more text.</p>
            <p>Third paragraph.</p>
        </body>
        </html>
        """
        result = parser.extract_text(html)
        
        # Should have newlines between paragraphs
        assert "First paragraph" in result
        assert "Second paragraph" in result
        assert "Third paragraph" in result
        # Check that there are newlines in the result
        assert "\n" in result
    
    def test_extract_text_handles_empty_html(self, parser: ContentParser) -> None:
        """Test handling of empty HTML input."""
        assert parser.extract_text("") == ""
        assert parser.extract_text("   ") == ""
    
    def test_extract_text_handles_plain_text(self, parser: ContentParser) -> None:
        """Test handling of plain text without HTML tags."""
        text = "Just plain text without any HTML"
        result = parser.extract_text(text)
        
        assert "Just plain text without any HTML" in result
    
    def test_extract_text_handles_nested_elements(self, parser: ContentParser) -> None:
        """Test extraction from nested HTML elements."""
        html = """
        <div>
            <div>
                <p><strong>Bold</strong> and <em>italic</em> text</p>
            </div>
        </div>
        """
        result = parser.extract_text(html)
        
        assert "Bold" in result
        assert "italic" in result
        assert "text" in result
    
    # --- clean_content() tests ---
    
    def test_clean_content_removes_unsubscribe_text(self, parser: ContentParser) -> None:
        """Test removal of unsubscribe-related boilerplate."""
        text = """
        Great newsletter content here.
        
        Click here to unsubscribe from this list.
        
        More content.
        """
        result = parser.clean_content(text)
        
        assert "Great newsletter content" in result
        assert "More content" in result
        assert "unsubscribe" not in result.lower()
    
    def test_clean_content_removes_view_in_browser(self, parser: ContentParser) -> None:
        """Test removal of 'view in browser' boilerplate."""
        text = """
        View this email in your browser
        
        Actual newsletter content starts here.
        """
        result = parser.clean_content(text)
        
        assert "Actual newsletter content" in result
        assert "view" not in result.lower() or "browser" not in result.lower()
    
    def test_clean_content_removes_copyright_notices(self, parser: ContentParser) -> None:
        """Test removal of copyright notices."""
        text = """
        Newsletter content.
        
        © 2024 Company Name. All rights reserved.
        """
        result = parser.clean_content(text)
        
        assert "Newsletter content" in result
        assert "©" not in result
        assert "All rights reserved" not in result
    
    def test_clean_content_removes_social_media_prompts(self, parser: ContentParser) -> None:
        """Test removal of social media follow prompts."""
        text = """
        Interesting article content.
        
        Follow us on Twitter and Facebook!
        
        More content here.
        """
        result = parser.clean_content(text)
        
        assert "Interesting article content" in result
        assert "More content here" in result
        assert "Follow us on" not in result
    
    def test_clean_content_normalizes_whitespace(self, parser: ContentParser) -> None:
        """Test normalization of excess whitespace."""
        text = "Text   with    multiple     spaces"
        result = parser.clean_content(text)
        
        # Should not have multiple consecutive spaces
        assert "   " not in result
        assert "Text with multiple spaces" in result
    
    def test_clean_content_normalizes_blank_lines(self, parser: ContentParser) -> None:
        """Test normalization of excessive blank lines."""
        text = """First paragraph.



        
        
        Second paragraph."""
        result = parser.clean_content(text)
        
        assert "First paragraph" in result
        assert "Second paragraph" in result
        # Should not have more than 2 consecutive newlines
        assert "\n\n\n" not in result
    
    def test_clean_content_normalizes_line_endings(self, parser: ContentParser) -> None:
        """Test normalization of different line ending styles."""
        text = "Line 1\r\nLine 2\rLine 3\nLine 4"
        result = parser.clean_content(text)
        
        # All line endings should be normalized to \n
        assert "\r\n" not in result
        assert "\r" not in result
        assert "Line 1" in result
        assert "Line 2" in result
        assert "Line 3" in result
        assert "Line 4" in result
    
    def test_clean_content_handles_empty_input(self, parser: ContentParser) -> None:
        """Test handling of empty input."""
        assert parser.clean_content("") == ""
        assert parser.clean_content("   ") == ""
        assert parser.clean_content("\n\n\n") == ""
    
    def test_clean_content_preserves_meaningful_content(self, parser: ContentParser) -> None:
        """Test that meaningful content is preserved."""
        text = """
        Tech News Weekly
        
        This week in technology, we saw major announcements from several companies.
        
        AI continues to dominate headlines with new breakthroughs in language models.
        
        The semiconductor industry faces new challenges amid global supply concerns.
        """
        result = parser.clean_content(text)
        
        assert "Tech News Weekly" in result
        assert "technology" in result
        assert "AI continues" in result
        assert "semiconductor" in result
    
    def test_clean_content_removes_manage_subscription(self, parser: ContentParser) -> None:
        """Test removal of subscription management text."""
        text = """
        Newsletter content.
        
        Manage your subscription preferences here.
        Update your preferences to receive fewer emails.
        """
        result = parser.clean_content(text)
        
        assert "Newsletter content" in result
        assert "Manage your subscription" not in result
        assert "Update your preferences" not in result
    
    def test_clean_content_removes_sent_to_email(self, parser: ContentParser) -> None:
        """Test removal of 'sent to' email patterns."""
        text = """
        Great content here.
        
        This email was sent to user@example.com
        You are receiving this newsletter because you subscribed.
        """
        result = parser.clean_content(text)
        
        assert "Great content here" in result
        assert "sent to" not in result.lower()
        assert "user@example.com" not in result


class TestEmailFetcher:
    """Unit tests for EmailFetcher.
    
    Validates: Requirements 1.1, 2.2
    """
    
    @pytest.fixture
    def email_config(self):
        """Create a test email configuration."""
        from newsletter_generator.config import EmailSourceConfig
        return EmailSourceConfig(
            host="imap.example.com",
            port=993,
            username="test@example.com",
            password="testpassword",
            folder="INBOX",
            use_ssl=True,
        )
    
    @pytest.fixture
    def email_fetcher(self, email_config):
        """Create an EmailFetcher instance for testing."""
        from newsletter_generator.aggregator import EmailFetcher
        return EmailFetcher(email_config)
    
    def test_init_stores_config(self, email_config):
        """Test that __init__ stores the configuration."""
        from newsletter_generator.aggregator import EmailFetcher
        fetcher = EmailFetcher(email_config)
        
        assert fetcher.config == email_config
        assert fetcher.config.host == "imap.example.com"
        assert fetcher.config.port == 993
        assert fetcher.config.use_ssl is True
    
    def test_init_creates_content_parser(self, email_config):
        """Test that __init__ creates a ContentParser instance."""
        from newsletter_generator.aggregator import EmailFetcher, ContentParser
        fetcher = EmailFetcher(email_config)
        
        assert fetcher.parser is not None
        assert isinstance(fetcher.parser, ContentParser)
    
    def test_decode_header_plain_text(self, email_fetcher):
        """Test decoding a plain text header."""
        result = email_fetcher._decode_header("Simple Subject")
        assert result == "Simple Subject"
    
    def test_decode_header_empty(self, email_fetcher):
        """Test decoding an empty header."""
        assert email_fetcher._decode_header("") == ""
        assert email_fetcher._decode_header(None) == ""
    
    def test_decode_header_utf8_encoded(self, email_fetcher):
        """Test decoding a UTF-8 encoded header."""
        # RFC 2047 encoded header
        encoded = "=?UTF-8?Q?Hello_World?="
        result = email_fetcher._decode_header(encoded)
        assert "Hello" in result
        assert "World" in result
    
    def test_parse_date_rfc2822(self, email_fetcher):
        """Test parsing RFC 2822 date format."""
        date_str = "Mon, 15 Jan 2024 10:30:00 +0000"
        result = email_fetcher._parse_date(date_str)
        
        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15
        assert result.hour == 10
        assert result.minute == 30
    
    def test_parse_date_empty(self, email_fetcher):
        """Test parsing empty date string."""
        assert email_fetcher._parse_date("") is None
        assert email_fetcher._parse_date(None) is None
    
    def test_parse_date_invalid(self, email_fetcher):
        """Test parsing invalid date string."""
        result = email_fetcher._parse_date("not a date")
        assert result is None
    
    def test_get_email_body_plain_text(self, email_fetcher):
        """Test extracting body from plain text email."""
        import email
        
        msg = email.message.EmailMessage()
        msg.set_content("This is plain text content")
        
        html, text = email_fetcher._get_email_body(msg)
        
        assert text is not None
        assert "plain text content" in text
        assert html is None
    
    def test_get_email_body_html(self, email_fetcher):
        """Test extracting body from HTML email."""
        import email
        
        msg = email.message.EmailMessage()
        msg.add_alternative("<html><body><p>HTML content</p></body></html>", subtype="html")
        
        html, text = email_fetcher._get_email_body(msg)
        
        # The message should have HTML content
        assert html is not None or text is not None
    
    def test_get_email_body_multipart(self, email_fetcher):
        """Test extracting body from multipart email."""
        import email
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        
        msg = MIMEMultipart("alternative")
        
        text_part = MIMEText("Plain text version", "plain")
        html_part = MIMEText("<html><body><p>HTML version</p></body></html>", "html")
        
        msg.attach(text_part)
        msg.attach(html_part)
        
        html, text = email_fetcher._get_email_body(msg)
        
        assert text is not None
        assert "Plain text version" in text
        assert html is not None
        assert "HTML version" in html
    
    def test_fetch_connection_error_returns_empty_list(self, email_fetcher):
        """Test that connection errors return empty list."""
        from datetime import datetime
        
        # This should fail to connect and return empty list
        result = email_fetcher.fetch(datetime.now())
        
        assert result == []
    
    def test_fetch_with_mock_imap(self, email_config, monkeypatch):
        """Test fetch with mocked IMAP connection."""
        from datetime import datetime
        from unittest.mock import MagicMock
        from newsletter_generator.aggregator import EmailFetcher
        
        # Create a mock IMAP connection
        mock_imap = MagicMock()
        mock_imap.login.return_value = ("OK", [])
        mock_imap.select.return_value = ("OK", [b"1"])
        mock_imap.search.return_value = ("OK", [b"1 2"])
        
        # Create mock email messages
        email_content_1 = b"""From: sender@example.com
To: test@example.com
Subject: Test Newsletter 1
Date: Mon, 15 Jan 2024 10:00:00 +0000
Content-Type: text/plain

This is the first newsletter content.
"""
        email_content_2 = b"""From: sender2@example.com
To: test@example.com
Subject: Test Newsletter 2
Date: Mon, 15 Jan 2024 11:00:00 +0000
Content-Type: text/html

<html><body><p>This is the second newsletter with HTML.</p></body></html>
"""
        
        mock_imap.fetch.side_effect = [
            ("OK", [(b"1", email_content_1)]),
            ("OK", [(b"2", email_content_2)]),
        ]
        mock_imap.close.return_value = ("OK", [])
        mock_imap.logout.return_value = ("OK", [])
        
        # Mock IMAP4_SSL to return our mock
        import imaplib
        monkeypatch.setattr(imaplib, "IMAP4_SSL", lambda host, port: mock_imap)
        
        fetcher = EmailFetcher(email_config)
        since = datetime(2024, 1, 1)
        result = fetcher.fetch(since)
        
        # Verify results
        assert len(result) == 2
        
        # Check first email
        assert result[0].source_type == "email"
        assert result[0].title == "Test Newsletter 1"
        assert "first newsletter content" in result[0].content
        assert result[0].author == "sender@example.com"
        
        # Check second email
        assert result[1].source_type == "email"
        assert result[1].title == "Test Newsletter 2"
        assert "second newsletter" in result[1].content
        assert result[1].html_content is not None
    
    def test_fetch_with_non_ssl_connection(self, monkeypatch):
        """Test fetch with non-SSL IMAP connection."""
        from datetime import datetime
        from unittest.mock import MagicMock
        from newsletter_generator.config import EmailSourceConfig
        from newsletter_generator.aggregator import EmailFetcher
        
        config = EmailSourceConfig(
            host="imap.example.com",
            port=143,
            username="test@example.com",
            password="testpassword",
            folder="INBOX",
            use_ssl=False,
        )
        
        # Create a mock IMAP connection
        mock_imap = MagicMock()
        mock_imap.login.return_value = ("OK", [])
        mock_imap.select.return_value = ("OK", [b"1"])
        mock_imap.search.return_value = ("OK", [b""])
        mock_imap.close.return_value = ("OK", [])
        mock_imap.logout.return_value = ("OK", [])
        
        # Track if IMAP4 was called
        imap4_called = []
        def mock_imap4(host, port):
            imap4_called.append((host, port))
            return mock_imap
        
        # Mock IMAP4 (non-SSL) to return our mock
        import imaplib
        monkeypatch.setattr(imaplib, "IMAP4", mock_imap4)
        
        fetcher = EmailFetcher(config)
        result = fetcher.fetch(datetime(2024, 1, 1))
        
        # Should have called IMAP4 (not IMAP4_SSL)
        assert len(imap4_called) == 1
        assert imap4_called[0] == ("imap.example.com", 143)
        
        assert result == []
    
    def test_fetch_handles_folder_selection_failure(self, email_config, monkeypatch):
        """Test that folder selection failure is handled gracefully."""
        from datetime import datetime
        from unittest.mock import MagicMock
        from newsletter_generator.aggregator import EmailFetcher
        
        mock_imap = MagicMock()
        mock_imap.login.return_value = ("OK", [])
        mock_imap.select.return_value = ("NO", [b"Folder not found"])
        mock_imap.close.return_value = ("OK", [])
        mock_imap.logout.return_value = ("OK", [])
        
        import imaplib
        monkeypatch.setattr(imaplib, "IMAP4_SSL", lambda host, port: mock_imap)
        
        fetcher = EmailFetcher(email_config)
        result = fetcher.fetch(datetime(2024, 1, 1))
        
        assert result == []
    
    def test_fetch_handles_search_failure(self, email_config, monkeypatch):
        """Test that search failure is handled gracefully."""
        from datetime import datetime
        from unittest.mock import MagicMock
        from newsletter_generator.aggregator import EmailFetcher
        
        mock_imap = MagicMock()
        mock_imap.login.return_value = ("OK", [])
        mock_imap.select.return_value = ("OK", [b"1"])
        mock_imap.search.return_value = ("NO", [b"Search failed"])
        mock_imap.close.return_value = ("OK", [])
        mock_imap.logout.return_value = ("OK", [])
        
        import imaplib
        monkeypatch.setattr(imaplib, "IMAP4_SSL", lambda host, port: mock_imap)
        
        fetcher = EmailFetcher(email_config)
        result = fetcher.fetch(datetime(2024, 1, 1))
        
        assert result == []
    
    def test_fetch_skips_emails_before_since_date(self, email_config, monkeypatch):
        """Test that emails before the since date are skipped."""
        from datetime import datetime
        from unittest.mock import MagicMock
        from newsletter_generator.aggregator import EmailFetcher
        
        mock_imap = MagicMock()
        mock_imap.login.return_value = ("OK", [])
        mock_imap.select.return_value = ("OK", [b"1"])
        mock_imap.search.return_value = ("OK", [b"1"])
        
        # Email from before the since date
        old_email = b"""From: sender@example.com
To: test@example.com
Subject: Old Newsletter
Date: Mon, 01 Jan 2024 10:00:00 +0000
Content-Type: text/plain

Old content.
"""
        mock_imap.fetch.return_value = ("OK", [(b"1", old_email)])
        mock_imap.close.return_value = ("OK", [])
        mock_imap.logout.return_value = ("OK", [])
        
        import imaplib
        monkeypatch.setattr(imaplib, "IMAP4_SSL", lambda host, port: mock_imap)
        
        fetcher = EmailFetcher(email_config)
        # Search for emails since Jan 15, 2024
        result = fetcher.fetch(datetime(2024, 1, 15))
        
        # The old email should be skipped
        assert result == []
    
    def test_fetch_handles_email_without_subject(self, email_config, monkeypatch):
        """Test handling of emails without a subject."""
        from datetime import datetime
        from unittest.mock import MagicMock
        from newsletter_generator.aggregator import EmailFetcher
        
        mock_imap = MagicMock()
        mock_imap.login.return_value = ("OK", [])
        mock_imap.select.return_value = ("OK", [b"1"])
        mock_imap.search.return_value = ("OK", [b"1"])
        
        # Email without subject
        email_no_subject = b"""From: sender@example.com
To: test@example.com
Date: Mon, 15 Jan 2024 10:00:00 +0000
Content-Type: text/plain

Content without subject.
"""
        mock_imap.fetch.return_value = ("OK", [(b"1", email_no_subject)])
        mock_imap.close.return_value = ("OK", [])
        mock_imap.logout.return_value = ("OK", [])
        
        import imaplib
        monkeypatch.setattr(imaplib, "IMAP4_SSL", lambda host, port: mock_imap)
        
        fetcher = EmailFetcher(email_config)
        result = fetcher.fetch(datetime(2024, 1, 1))
        
        assert len(result) == 1
        assert result[0].title == "(No Subject)"
    
    def test_fetch_handles_imap_error(self, email_config, monkeypatch):
        """Test handling of IMAP errors."""
        from datetime import datetime
        import imaplib
        from newsletter_generator.aggregator import EmailFetcher
        
        def raise_imap_error(host, port):
            raise imaplib.IMAP4.error("Authentication failed")
        
        monkeypatch.setattr(imaplib, "IMAP4_SSL", raise_imap_error)
        
        fetcher = EmailFetcher(email_config)
        result = fetcher.fetch(datetime(2024, 1, 1))
        
        # Should return empty list on error
        assert result == []


class TestRSSFetcher:
    """Unit tests for RSSFetcher.
    
    Validates: Requirements 1.2, 2.3
    """
    
    @pytest.fixture
    def rss_config(self):
        """Create a test RSS configuration."""
        from newsletter_generator.config import RSSSourceConfig
        return RSSSourceConfig(
            url="https://example.com/feed.xml",
            name="Test Feed",
        )
    
    @pytest.fixture
    def rss_fetcher(self, rss_config):
        """Create an RSSFetcher instance for testing."""
        from newsletter_generator.aggregator import RSSFetcher
        return RSSFetcher(rss_config)
    
    def test_init_stores_config(self, rss_config):
        """Test that __init__ stores the configuration."""
        from newsletter_generator.aggregator import RSSFetcher
        fetcher = RSSFetcher(rss_config)
        
        assert fetcher.config == rss_config
        assert fetcher.config.url == "https://example.com/feed.xml"
        assert fetcher.config.name == "Test Feed"
    
    def test_init_creates_content_parser(self, rss_config):
        """Test that __init__ creates a ContentParser instance."""
        from newsletter_generator.aggregator import RSSFetcher, ContentParser
        fetcher = RSSFetcher(rss_config)
        
        assert fetcher.parser is not None
        assert isinstance(fetcher.parser, ContentParser)
    
    def test_parse_entry_date_published_parsed(self, rss_fetcher):
        """Test parsing date from published_parsed field."""
        import time
        entry = {
            "published_parsed": time.strptime("2024-01-15 10:30:00", "%Y-%m-%d %H:%M:%S")
        }
        result = rss_fetcher._parse_entry_date(entry)
        
        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15
    
    def test_parse_entry_date_updated_parsed(self, rss_fetcher):
        """Test parsing date from updated_parsed field."""
        import time
        entry = {
            "updated_parsed": time.strptime("2024-02-20 14:00:00", "%Y-%m-%d %H:%M:%S")
        }
        result = rss_fetcher._parse_entry_date(entry)
        
        assert result is not None
        assert result.year == 2024
        assert result.month == 2
        assert result.day == 20
    
    def test_parse_entry_date_string_fallback(self, rss_fetcher):
        """Test parsing date from string field as fallback."""
        entry = {
            "published": "2024-03-10T12:00:00Z"
        }
        result = rss_fetcher._parse_entry_date(entry)
        
        assert result is not None
        assert result.year == 2024
        assert result.month == 3
        assert result.day == 10
    
    def test_parse_entry_date_no_date(self, rss_fetcher):
        """Test parsing when no date field is present."""
        entry = {}
        result = rss_fetcher._parse_entry_date(entry)
        
        assert result is None
    
    def test_parse_date_string_rfc2822(self, rss_fetcher):
        """Test parsing RFC 2822 date format."""
        result = rss_fetcher._parse_date_string("Mon, 15 Jan 2024 10:30:00 +0000")
        
        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15
    
    def test_parse_date_string_iso8601(self, rss_fetcher):
        """Test parsing ISO 8601 date format."""
        result = rss_fetcher._parse_date_string("2024-01-15T10:30:00Z")
        
        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15
    
    def test_parse_date_string_invalid(self, rss_fetcher):
        """Test parsing invalid date string."""
        result = rss_fetcher._parse_date_string("not a date")
        assert result is None
    
    def test_parse_date_string_empty(self, rss_fetcher):
        """Test parsing empty date string."""
        assert rss_fetcher._parse_date_string("") is None
        assert rss_fetcher._parse_date_string(None) is None
    
    def test_extract_entry_content_html(self, rss_fetcher):
        """Test extracting HTML content from entry."""
        entry = {
            "content": [
                {
                    "type": "text/html",
                    "value": "<p>HTML content here</p>"
                }
            ]
        }
        html, text = rss_fetcher._extract_entry_content(entry)
        
        assert html == "<p>HTML content here</p>"
        assert text is None
    
    def test_extract_entry_content_plain_text(self, rss_fetcher):
        """Test extracting plain text content from entry."""
        entry = {
            "content": [
                {
                    "type": "text/plain",
                    "value": "Plain text content"
                }
            ]
        }
        html, text = rss_fetcher._extract_entry_content(entry)
        
        assert html is None
        assert text == "Plain text content"
    
    def test_extract_entry_content_summary_detail(self, rss_fetcher):
        """Test extracting content from summary_detail."""
        entry = {
            "summary_detail": {
                "type": "text/html",
                "value": "<p>Summary content</p>"
            }
        }
        html, text = rss_fetcher._extract_entry_content(entry)
        
        assert html == "<p>Summary content</p>"
        assert text is None
    
    def test_extract_entry_content_description(self, rss_fetcher):
        """Test extracting content from description field."""
        entry = {
            "description": "<p>Description content</p>"
        }
        html, text = rss_fetcher._extract_entry_content(entry)
        
        assert html == "<p>Description content</p>"
        assert text is None
    
    def test_extract_entry_content_plain_description(self, rss_fetcher):
        """Test extracting plain text description."""
        entry = {
            "description": "Plain description without HTML"
        }
        html, text = rss_fetcher._extract_entry_content(entry)
        
        assert html is None
        assert text == "Plain description without HTML"
    
    def test_extract_entry_content_empty(self, rss_fetcher):
        """Test extracting content from empty entry."""
        entry = {}
        html, text = rss_fetcher._extract_entry_content(entry)
        
        assert html is None
        assert text is None
    
    def test_extract_author_simple(self, rss_fetcher):
        """Test extracting author from simple author field."""
        entry = {"author": "John Doe"}
        result = rss_fetcher._extract_author(entry)
        
        assert result == "John Doe"
    
    def test_extract_author_detail(self, rss_fetcher):
        """Test extracting author from author_detail."""
        entry = {
            "author_detail": {"name": "Jane Smith"}
        }
        result = rss_fetcher._extract_author(entry)
        
        assert result == "Jane Smith"
    
    def test_extract_author_list(self, rss_fetcher):
        """Test extracting author from authors list."""
        entry = {
            "authors": [{"name": "First Author"}, {"name": "Second Author"}]
        }
        result = rss_fetcher._extract_author(entry)
        
        assert result == "First Author"
    
    def test_extract_author_string_list(self, rss_fetcher):
        """Test extracting author from string authors list."""
        entry = {
            "authors": ["Author Name"]
        }
        result = rss_fetcher._extract_author(entry)
        
        assert result == "Author Name"
    
    def test_extract_author_none(self, rss_fetcher):
        """Test extracting author when not present."""
        entry = {}
        result = rss_fetcher._extract_author(entry)
        
        assert result is None
    
    def test_fetch_with_mock_feedparser(self, rss_config, monkeypatch):
        """Test fetch with mocked feedparser."""
        from datetime import datetime
        import time
        from newsletter_generator.aggregator import RSSFetcher
        
        # Create mock feed data
        mock_feed = {
            "bozo": False,
            "entries": [
                {
                    "title": "Test Article 1",
                    "published_parsed": time.strptime("2024-01-15 10:00:00", "%Y-%m-%d %H:%M:%S"),
                    "content": [{"type": "text/html", "value": "<p>Article 1 content</p>"}],
                    "author": "Author 1",
                    "link": "https://example.com/article1",
                },
                {
                    "title": "Test Article 2",
                    "published_parsed": time.strptime("2024-01-16 11:00:00", "%Y-%m-%d %H:%M:%S"),
                    "summary": "Article 2 summary text",
                    "author": "Author 2",
                    "link": "https://example.com/article2",
                },
            ]
        }
        
        # Mock feedparser.parse
        import feedparser
        monkeypatch.setattr(feedparser, "parse", lambda url: type('Feed', (), mock_feed)())
        
        fetcher = RSSFetcher(rss_config)
        since = datetime(2024, 1, 1)
        result = fetcher.fetch(since)
        
        assert len(result) == 2
        
        # Check first article
        assert result[0].source_type == "rss"
        assert result[0].source_name == "Test Feed"
        assert result[0].title == "Test Article 1"
        assert "Article 1 content" in result[0].content
        assert result[0].author == "Author 1"
        assert result[0].url == "https://example.com/article1"
        
        # Check second article
        assert result[1].title == "Test Article 2"
        assert result[1].author == "Author 2"
    
    def test_fetch_filters_by_date(self, rss_config, monkeypatch):
        """Test that fetch filters entries by date."""
        from datetime import datetime
        import time
        from newsletter_generator.aggregator import RSSFetcher
        
        mock_feed = {
            "bozo": False,
            "entries": [
                {
                    "title": "Old Article",
                    "published_parsed": time.strptime("2024-01-01 10:00:00", "%Y-%m-%d %H:%M:%S"),
                    "summary": "Old content",
                },
                {
                    "title": "New Article",
                    "published_parsed": time.strptime("2024-01-20 10:00:00", "%Y-%m-%d %H:%M:%S"),
                    "summary": "New content",
                },
            ]
        }
        
        import feedparser
        monkeypatch.setattr(feedparser, "parse", lambda url: type('Feed', (), mock_feed)())
        
        fetcher = RSSFetcher(rss_config)
        # Only get articles since Jan 15
        since = datetime(2024, 1, 15)
        result = fetcher.fetch(since)
        
        # Should only get the new article
        assert len(result) == 1
        assert result[0].title == "New Article"
    
    def test_fetch_handles_empty_feed(self, rss_config, monkeypatch):
        """Test handling of empty feed."""
        from datetime import datetime
        from newsletter_generator.aggregator import RSSFetcher
        
        mock_feed = {
            "bozo": False,
            "entries": []
        }
        
        import feedparser
        monkeypatch.setattr(feedparser, "parse", lambda url: type('Feed', (), mock_feed)())
        
        fetcher = RSSFetcher(rss_config)
        result = fetcher.fetch(datetime(2024, 1, 1))
        
        assert result == []
    
    def test_fetch_handles_bozo_feed(self, rss_config, monkeypatch):
        """Test handling of feed with parsing issues (bozo flag)."""
        from datetime import datetime
        import time
        from newsletter_generator.aggregator import RSSFetcher
        
        mock_feed = {
            "bozo": True,
            "bozo_exception": Exception("XML parsing error"),
            "entries": [
                {
                    "title": "Partial Article",
                    "published_parsed": time.strptime("2024-01-15 10:00:00", "%Y-%m-%d %H:%M:%S"),
                    "summary": "Partial content",
                },
            ]
        }
        
        import feedparser
        monkeypatch.setattr(feedparser, "parse", lambda url: type('Feed', (), mock_feed)())
        
        fetcher = RSSFetcher(rss_config)
        result = fetcher.fetch(datetime(2024, 1, 1))
        
        # Should still return partial data
        assert len(result) == 1
        assert result[0].title == "Partial Article"
    
    def test_fetch_handles_entry_without_title(self, rss_config, monkeypatch):
        """Test handling of entry without title."""
        from datetime import datetime
        import time
        from newsletter_generator.aggregator import RSSFetcher
        
        mock_feed = {
            "bozo": False,
            "entries": [
                {
                    "published_parsed": time.strptime("2024-01-15 10:00:00", "%Y-%m-%d %H:%M:%S"),
                    "summary": "Content without title",
                },
            ]
        }
        
        import feedparser
        monkeypatch.setattr(feedparser, "parse", lambda url: type('Feed', (), mock_feed)())
        
        fetcher = RSSFetcher(rss_config)
        result = fetcher.fetch(datetime(2024, 1, 1))
        
        assert len(result) == 1
        assert result[0].title == "(No Title)"
    
    def test_fetch_handles_entry_without_date(self, rss_config, monkeypatch):
        """Test handling of entry without date."""
        from datetime import datetime
        from newsletter_generator.aggregator import RSSFetcher
        
        mock_feed = {
            "bozo": False,
            "entries": [
                {
                    "title": "Article without date",
                    "summary": "Content",
                },
            ]
        }
        
        import feedparser
        monkeypatch.setattr(feedparser, "parse", lambda url: type('Feed', (), mock_feed)())
        
        fetcher = RSSFetcher(rss_config)
        result = fetcher.fetch(datetime(2024, 1, 1))
        
        # Should use current time for entries without date
        assert len(result) == 1
        assert result[0].title == "Article without date"
        assert result[0].published_date is not None
    
    def test_fetch_handles_parse_exception(self, rss_config, monkeypatch):
        """Test handling of feedparser exception."""
        from datetime import datetime
        from newsletter_generator.aggregator import RSSFetcher
        
        def raise_exception(url):
            raise Exception("Network error")
        
        import feedparser
        monkeypatch.setattr(feedparser, "parse", raise_exception)
        
        fetcher = RSSFetcher(rss_config)
        result = fetcher.fetch(datetime(2024, 1, 1))
        
        # Should return empty list on error
        assert result == []
    
    def test_fetch_extracts_html_content(self, rss_config, monkeypatch):
        """Test that HTML content is properly extracted and stored."""
        from datetime import datetime
        import time
        from newsletter_generator.aggregator import RSSFetcher
        
        html_content = "<html><body><p>Rich HTML content with <strong>formatting</strong></p></body></html>"
        mock_feed = {
            "bozo": False,
            "entries": [
                {
                    "title": "HTML Article",
                    "published_parsed": time.strptime("2024-01-15 10:00:00", "%Y-%m-%d %H:%M:%S"),
                    "content": [{"type": "text/html", "value": html_content}],
                },
            ]
        }
        
        import feedparser
        monkeypatch.setattr(feedparser, "parse", lambda url: type('Feed', (), mock_feed)())
        
        fetcher = RSSFetcher(rss_config)
        result = fetcher.fetch(datetime(2024, 1, 1))
        
        assert len(result) == 1
        assert result[0].html_content == html_content
        # Content should be extracted text
        assert "Rich HTML content" in result[0].content
        assert "formatting" in result[0].content
        # HTML tags should be removed from content
        assert "<p>" not in result[0].content


class TestFileFetcher:
    """Unit tests for FileFetcher.
    
    Validates: Requirements 1.3
    """
    
    @pytest.fixture
    def file_config(self):
        """Create a test file source configuration."""
        from newsletter_generator.config import FileSourceConfig
        return FileSourceConfig(
            path="/tmp/test_newsletters",
            pattern="*.html",
        )
    
    @pytest.fixture
    def file_fetcher(self, file_config):
        """Create a FileFetcher instance for testing."""
        from newsletter_generator.aggregator import FileFetcher
        return FileFetcher(file_config)
    
    @pytest.fixture
    def temp_newsletter_dir(self, tmp_path):
        """Create a temporary directory with test newsletter files."""
        # Create HTML file
        html_file = tmp_path / "newsletter1.html"
        html_file.write_text(
            "<html><body><h1>Tech News</h1><p>Latest updates in technology.</p></body></html>"
        )
        
        # Create plain text file
        txt_file = tmp_path / "newsletter2.txt"
        txt_file.write_text("Plain text newsletter content.\n\nMore content here.")
        
        # Create another HTML file
        html_file2 = tmp_path / "newsletter3.html"
        html_file2.write_text(
            "<html><body><p>Another newsletter with <strong>important</strong> news.</p></body></html>"
        )
        
        return tmp_path
    
    def test_init_stores_config(self, file_config):
        """Test that __init__ stores the configuration."""
        from newsletter_generator.aggregator import FileFetcher
        fetcher = FileFetcher(file_config)
        
        assert fetcher.config == file_config
        assert fetcher.config.path == "/tmp/test_newsletters"
        assert fetcher.config.pattern == "*.html"
    
    def test_init_creates_content_parser(self, file_config):
        """Test that __init__ creates a ContentParser instance."""
        from newsletter_generator.aggregator import FileFetcher, ContentParser
        fetcher = FileFetcher(file_config)
        
        assert fetcher.parser is not None
        assert isinstance(fetcher.parser, ContentParser)
    
    def test_fetch_html_files(self, temp_newsletter_dir):
        """Test fetching HTML files from directory."""
        from datetime import datetime, timedelta
        from newsletter_generator.config import FileSourceConfig
        from newsletter_generator.aggregator import FileFetcher
        
        config = FileSourceConfig(
            path=str(temp_newsletter_dir),
            pattern="*.html",
        )
        fetcher = FileFetcher(config)
        
        # Fetch files modified in the last day
        since = datetime.now() - timedelta(days=1)
        result = fetcher.fetch(since)
        
        # Should find 2 HTML files
        assert len(result) == 2
        
        # Check that items have correct source_type
        for item in result:
            assert item.source_type == "file"
            assert item.html_content is not None
            assert item.content  # Should have extracted text
    
    def test_fetch_text_files(self, temp_newsletter_dir):
        """Test fetching plain text files from directory."""
        from datetime import datetime, timedelta
        from newsletter_generator.config import FileSourceConfig
        from newsletter_generator.aggregator import FileFetcher
        
        config = FileSourceConfig(
            path=str(temp_newsletter_dir),
            pattern="*.txt",
        )
        fetcher = FileFetcher(config)
        
        since = datetime.now() - timedelta(days=1)
        result = fetcher.fetch(since)
        
        # Should find 1 text file
        assert len(result) == 1
        assert result[0].source_type == "file"
        assert result[0].html_content is None  # Plain text has no HTML
        assert "Plain text newsletter content" in result[0].content
    
    def test_fetch_all_files_with_wildcard(self, temp_newsletter_dir):
        """Test fetching all files with wildcard pattern."""
        from datetime import datetime, timedelta
        from newsletter_generator.config import FileSourceConfig
        from newsletter_generator.aggregator import FileFetcher
        
        config = FileSourceConfig(
            path=str(temp_newsletter_dir),
            pattern="*",
        )
        fetcher = FileFetcher(config)
        
        since = datetime.now() - timedelta(days=1)
        result = fetcher.fetch(since)
        
        # Should find all 3 files
        assert len(result) == 3
    
    def test_fetch_filters_by_date(self, tmp_path):
        """Test that files are filtered by modification date."""
        from datetime import datetime, timedelta
        from newsletter_generator.config import FileSourceConfig
        from newsletter_generator.aggregator import FileFetcher
        import os
        import time
        
        # Create a file
        test_file = tmp_path / "old_newsletter.html"
        test_file.write_text("<html><body><p>Old content</p></body></html>")
        
        # Set modification time to 10 days ago
        old_time = time.time() - (10 * 24 * 60 * 60)
        os.utime(test_file, (old_time, old_time))
        
        config = FileSourceConfig(
            path=str(tmp_path),
            pattern="*.html",
        )
        fetcher = FileFetcher(config)
        
        # Fetch files modified in the last 5 days
        since = datetime.now() - timedelta(days=5)
        result = fetcher.fetch(since)
        
        # Old file should be filtered out
        assert len(result) == 0
    
    def test_fetch_nonexistent_directory(self, file_config):
        """Test fetching from a nonexistent directory returns empty list."""
        from datetime import datetime
        from newsletter_generator.config import FileSourceConfig
        from newsletter_generator.aggregator import FileFetcher
        
        config = FileSourceConfig(
            path="/nonexistent/directory/path",
            pattern="*.html",
        )
        fetcher = FileFetcher(config)
        
        result = fetcher.fetch(datetime.now())
        
        assert result == []
    
    def test_fetch_empty_directory(self, tmp_path):
        """Test fetching from an empty directory returns empty list."""
        from datetime import datetime, timedelta
        from newsletter_generator.config import FileSourceConfig
        from newsletter_generator.aggregator import FileFetcher
        
        config = FileSourceConfig(
            path=str(tmp_path),
            pattern="*.html",
        )
        fetcher = FileFetcher(config)
        
        since = datetime.now() - timedelta(days=1)
        result = fetcher.fetch(since)
        
        assert result == []
    
    def test_fetch_no_matching_files(self, temp_newsletter_dir):
        """Test fetching with pattern that matches no files."""
        from datetime import datetime, timedelta
        from newsletter_generator.config import FileSourceConfig
        from newsletter_generator.aggregator import FileFetcher
        
        config = FileSourceConfig(
            path=str(temp_newsletter_dir),
            pattern="*.xml",  # No XML files exist
        )
        fetcher = FileFetcher(config)
        
        since = datetime.now() - timedelta(days=1)
        result = fetcher.fetch(since)
        
        assert result == []
    
    def test_fetch_uses_filename_as_title(self, temp_newsletter_dir):
        """Test that filename (without extension) is used as title."""
        from datetime import datetime, timedelta
        from newsletter_generator.config import FileSourceConfig
        from newsletter_generator.aggregator import FileFetcher
        
        config = FileSourceConfig(
            path=str(temp_newsletter_dir),
            pattern="newsletter1.html",
        )
        fetcher = FileFetcher(config)
        
        since = datetime.now() - timedelta(days=1)
        result = fetcher.fetch(since)
        
        assert len(result) == 1
        assert result[0].title == "newsletter1"
    
    def test_fetch_sets_url_to_file_path(self, temp_newsletter_dir):
        """Test that URL is set to the absolute file path."""
        from datetime import datetime, timedelta
        from newsletter_generator.config import FileSourceConfig
        from newsletter_generator.aggregator import FileFetcher
        
        config = FileSourceConfig(
            path=str(temp_newsletter_dir),
            pattern="newsletter1.html",
        )
        fetcher = FileFetcher(config)
        
        since = datetime.now() - timedelta(days=1)
        result = fetcher.fetch(since)
        
        assert len(result) == 1
        assert result[0].url is not None
        assert "newsletter1.html" in result[0].url
    
    def test_fetch_expands_home_directory(self, monkeypatch, tmp_path):
        """Test that ~ in path is expanded to home directory."""
        from datetime import datetime, timedelta
        from newsletter_generator.config import FileSourceConfig
        from newsletter_generator.aggregator import FileFetcher
        import os
        
        # Create a test file in tmp_path
        test_file = tmp_path / "test.html"
        test_file.write_text("<html><body><p>Test</p></body></html>")
        
        # Mock expanduser to return our tmp_path
        original_expanduser = os.path.expanduser
        def mock_expanduser(path):
            if path.startswith("~"):
                return str(tmp_path) + path[1:]
            return original_expanduser(path)
        
        monkeypatch.setattr(os.path, "expanduser", mock_expanduser)
        
        config = FileSourceConfig(
            path="~/",
            pattern="*.html",
        )
        fetcher = FileFetcher(config)
        
        since = datetime.now() - timedelta(days=1)
        result = fetcher.fetch(since)
        
        assert len(result) == 1
    
    def test_fetch_handles_empty_file(self, tmp_path):
        """Test handling of empty files."""
        from datetime import datetime, timedelta
        from newsletter_generator.config import FileSourceConfig
        from newsletter_generator.aggregator import FileFetcher
        
        # Create an empty file
        empty_file = tmp_path / "empty.html"
        empty_file.write_text("")
        
        config = FileSourceConfig(
            path=str(tmp_path),
            pattern="*.html",
        )
        fetcher = FileFetcher(config)
        
        since = datetime.now() - timedelta(days=1)
        result = fetcher.fetch(since)
        
        # Empty file should be skipped
        assert len(result) == 0
    
    def test_fetch_extracts_text_from_html(self, tmp_path):
        """Test that HTML content is properly parsed to extract text."""
        from datetime import datetime, timedelta
        from newsletter_generator.config import FileSourceConfig
        from newsletter_generator.aggregator import FileFetcher
        
        # Create HTML file with various elements
        html_file = tmp_path / "rich.html"
        html_file.write_text("""
        <html>
        <head><title>Newsletter</title></head>
        <body>
            <h1>Main Heading</h1>
            <p>First paragraph with <strong>bold</strong> text.</p>
            <p>Second paragraph with <em>italic</em> text.</p>
            <script>alert('should be removed');</script>
        </body>
        </html>
        """)
        
        config = FileSourceConfig(
            path=str(tmp_path),
            pattern="*.html",
        )
        fetcher = FileFetcher(config)
        
        since = datetime.now() - timedelta(days=1)
        result = fetcher.fetch(since)
        
        assert len(result) == 1
        item = result[0]
        
        # Check content extraction
        assert "Main Heading" in item.content
        assert "First paragraph" in item.content
        assert "bold" in item.content
        assert "Second paragraph" in item.content
        
        # Script content should be removed
        assert "alert" not in item.content
        
        # HTML should be preserved
        assert item.html_content is not None
        assert "<h1>" in item.html_content
    
    def test_read_file_html(self, file_fetcher, tmp_path):
        """Test _read_file method with HTML file."""
        html_file = tmp_path / "test.html"
        html_file.write_text("<html><body><p>Test content</p></body></html>")
        
        content, html_content = file_fetcher._read_file(html_file)
        
        assert "Test content" in content
        assert html_content is not None
        assert "<p>" in html_content
    
    def test_read_file_plain_text(self, file_fetcher, tmp_path):
        """Test _read_file method with plain text file."""
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("Plain text content here.")
        
        content, html_content = file_fetcher._read_file(txt_file)
        
        assert "Plain text content here" in content
        assert html_content is None
    
    def test_read_file_htm_extension(self, file_fetcher, tmp_path):
        """Test _read_file method with .htm extension."""
        htm_file = tmp_path / "test.htm"
        htm_file.write_text("<html><body><p>HTM content</p></body></html>")
        
        content, html_content = file_fetcher._read_file(htm_file)
        
        assert "HTM content" in content
        assert html_content is not None


class TestNewsletterAggregator:
    """Unit tests for NewsletterAggregator.
    
    Validates: Requirements 1.4, 1.5, 2.1, 2.5
    """
    
    @pytest.fixture
    def parser(self) -> ContentParser:
        """Create a ContentParser instance for testing."""
        return ContentParser()
    
    @pytest.fixture
    def sample_items(self):
        """Create sample NewsletterItems for testing."""
        from datetime import datetime
        from newsletter_generator.models import NewsletterItem
        
        return [
            NewsletterItem(
                source_name="Test Source 1",
                source_type="email",
                title="Test Item 1",
                content="Content from source 1",
                published_date=datetime(2024, 1, 15, 10, 0, 0),
            ),
            NewsletterItem(
                source_name="Test Source 2",
                source_type="rss",
                title="Test Item 2",
                content="Content from source 2",
                published_date=datetime(2024, 1, 16, 12, 0, 0),
            ),
        ]
    
    def test_init_stores_fetchers_and_parser(self, parser):
        """Test that __init__ stores fetchers and parser."""
        from newsletter_generator.aggregator import NewsletterAggregator
        
        fetchers = []
        aggregator = NewsletterAggregator(fetchers, parser)
        
        assert aggregator.fetchers == fetchers
        assert aggregator.parser == parser
    
    def test_init_creates_default_parser_if_none(self):
        """Test that __init__ creates a default parser if none provided."""
        from newsletter_generator.aggregator import NewsletterAggregator, ContentParser
        
        aggregator = NewsletterAggregator([])
        
        assert aggregator.parser is not None
        assert isinstance(aggregator.parser, ContentParser)
    
    def test_aggregate_with_no_fetchers_returns_empty_list(self, parser):
        """Test aggregation with no fetchers returns empty list."""
        from datetime import datetime
        from newsletter_generator.aggregator import NewsletterAggregator
        
        aggregator = NewsletterAggregator([], parser)
        result = aggregator.aggregate(datetime(2024, 1, 1))
        
        assert result == []
    
    def test_aggregate_collects_items_from_single_fetcher(self, parser, sample_items):
        """Test aggregation from a single fetcher."""
        from datetime import datetime
        from unittest.mock import MagicMock
        from newsletter_generator.aggregator import NewsletterAggregator
        
        mock_fetcher = MagicMock()
        mock_fetcher.fetch.return_value = sample_items
        
        aggregator = NewsletterAggregator([mock_fetcher], parser)
        result = aggregator.aggregate(datetime(2024, 1, 1))
        
        assert len(result) == 2
        mock_fetcher.fetch.assert_called_once_with(datetime(2024, 1, 1))
    
    def test_aggregate_collects_items_from_multiple_fetchers(self, parser):
        """Test aggregation from multiple fetchers."""
        from datetime import datetime
        from unittest.mock import MagicMock
        from newsletter_generator.aggregator import NewsletterAggregator
        from newsletter_generator.models import NewsletterItem
        
        items1 = [
            NewsletterItem(
                source_name="Source 1",
                source_type="email",
                title="Item 1",
                content="Content 1",
                published_date=datetime(2024, 1, 15),
            )
        ]
        items2 = [
            NewsletterItem(
                source_name="Source 2",
                source_type="rss",
                title="Item 2",
                content="Content 2",
                published_date=datetime(2024, 1, 16),
            ),
            NewsletterItem(
                source_name="Source 2",
                source_type="rss",
                title="Item 3",
                content="Content 3",
                published_date=datetime(2024, 1, 17),
            ),
        ]
        
        mock_fetcher1 = MagicMock()
        mock_fetcher1.fetch.return_value = items1
        
        mock_fetcher2 = MagicMock()
        mock_fetcher2.fetch.return_value = items2
        
        aggregator = NewsletterAggregator([mock_fetcher1, mock_fetcher2], parser)
        result = aggregator.aggregate(datetime(2024, 1, 1))
        
        assert len(result) == 3
        mock_fetcher1.fetch.assert_called_once()
        mock_fetcher2.fetch.assert_called_once()
    
    def test_aggregate_continues_on_fetcher_failure(self, parser):
        """Test that aggregation continues when a fetcher fails.
        
        Validates: Requirements 1.5, 2.5
        """
        from datetime import datetime
        from unittest.mock import MagicMock
        from newsletter_generator.aggregator import NewsletterAggregator
        from newsletter_generator.models import NewsletterItem
        
        items = [
            NewsletterItem(
                source_name="Working Source",
                source_type="rss",
                title="Working Item",
                content="Working content",
                published_date=datetime(2024, 1, 15),
            )
        ]
        
        # First fetcher fails
        failing_fetcher = MagicMock()
        failing_fetcher.fetch.side_effect = Exception("Connection failed")
        
        # Second fetcher succeeds
        working_fetcher = MagicMock()
        working_fetcher.fetch.return_value = items
        
        aggregator = NewsletterAggregator([failing_fetcher, working_fetcher], parser)
        result = aggregator.aggregate(datetime(2024, 1, 1))
        
        # Should still get items from the working fetcher
        assert len(result) == 1
        assert result[0].title == "Working Item"
        
        # Both fetchers should have been called
        failing_fetcher.fetch.assert_called_once()
        working_fetcher.fetch.assert_called_once()
    
    def test_aggregate_filters_items_by_date(self, parser):
        """Test that items before the since date are filtered out.
        
        Validates: Requirements 2.1
        """
        from datetime import datetime
        from unittest.mock import MagicMock
        from newsletter_generator.aggregator import NewsletterAggregator
        from newsletter_generator.models import NewsletterItem
        
        items = [
            NewsletterItem(
                source_name="Source",
                source_type="email",
                title="Old Item",
                content="Old content",
                published_date=datetime(2024, 1, 5),  # Before since date
            ),
            NewsletterItem(
                source_name="Source",
                source_type="email",
                title="New Item",
                content="New content",
                published_date=datetime(2024, 1, 15),  # After since date
            ),
        ]
        
        mock_fetcher = MagicMock()
        mock_fetcher.fetch.return_value = items
        
        aggregator = NewsletterAggregator([mock_fetcher], parser)
        result = aggregator.aggregate(datetime(2024, 1, 10))
        
        # Only the new item should be included
        assert len(result) == 1
        assert result[0].title == "New Item"
    
    def test_aggregate_includes_items_on_since_date(self, parser):
        """Test that items on the since date are included.
        
        Validates: Requirements 2.1
        """
        from datetime import datetime
        from unittest.mock import MagicMock
        from newsletter_generator.aggregator import NewsletterAggregator
        from newsletter_generator.models import NewsletterItem
        
        since_date = datetime(2024, 1, 10, 12, 0, 0)
        
        items = [
            NewsletterItem(
                source_name="Source",
                source_type="email",
                title="Exact Date Item",
                content="Content",
                published_date=since_date,  # Exactly on since date
            ),
        ]
        
        mock_fetcher = MagicMock()
        mock_fetcher.fetch.return_value = items
        
        aggregator = NewsletterAggregator([mock_fetcher], parser)
        result = aggregator.aggregate(since_date)
        
        # Item on the since date should be included
        assert len(result) == 1
        assert result[0].title == "Exact Date Item"
    
    def test_aggregate_normalizes_content(self, parser):
        """Test that content is normalized during aggregation."""
        from datetime import datetime
        from unittest.mock import MagicMock
        from newsletter_generator.aggregator import NewsletterAggregator
        from newsletter_generator.models import NewsletterItem
        
        items = [
            NewsletterItem(
                source_name="Source",
                source_type="email",
                title="Item",
                content="Content   with   extra   spaces",  # Extra whitespace
                published_date=datetime(2024, 1, 15),
            ),
        ]
        
        mock_fetcher = MagicMock()
        mock_fetcher.fetch.return_value = items
        
        aggregator = NewsletterAggregator([mock_fetcher], parser)
        result = aggregator.aggregate(datetime(2024, 1, 1))
        
        # Content should be normalized (extra spaces removed)
        assert len(result) == 1
        assert "   " not in result[0].content
    
    def test_aggregate_preserves_item_metadata(self, parser):
        """Test that item metadata is preserved during aggregation."""
        from datetime import datetime
        from unittest.mock import MagicMock
        from newsletter_generator.aggregator import NewsletterAggregator
        from newsletter_generator.models import NewsletterItem
        
        original_date = datetime(2024, 1, 15, 10, 30, 0)
        items = [
            NewsletterItem(
                source_name="Test Source",
                source_type="rss",
                title="Test Title",
                content="Test content",
                published_date=original_date,
                html_content="<p>Test content</p>",
                author="Test Author",
                url="https://example.com/article",
            ),
        ]
        
        mock_fetcher = MagicMock()
        mock_fetcher.fetch.return_value = items
        
        aggregator = NewsletterAggregator([mock_fetcher], parser)
        result = aggregator.aggregate(datetime(2024, 1, 1))
        
        assert len(result) == 1
        item = result[0]
        assert item.source_name == "Test Source"
        assert item.source_type == "rss"
        assert item.title == "Test Title"
        assert item.published_date == original_date
        assert item.html_content == "<p>Test content</p>"
        assert item.author == "Test Author"
        assert item.url == "https://example.com/article"
    
    def test_aggregate_handles_all_fetchers_failing(self, parser):
        """Test aggregation when all fetchers fail.
        
        Validates: Requirements 1.5, 2.5
        """
        from datetime import datetime
        from unittest.mock import MagicMock
        from newsletter_generator.aggregator import NewsletterAggregator
        
        failing_fetcher1 = MagicMock()
        failing_fetcher1.fetch.side_effect = Exception("Error 1")
        
        failing_fetcher2 = MagicMock()
        failing_fetcher2.fetch.side_effect = Exception("Error 2")
        
        aggregator = NewsletterAggregator([failing_fetcher1, failing_fetcher2], parser)
        result = aggregator.aggregate(datetime(2024, 1, 1))
        
        # Should return empty list, not raise exception
        assert result == []
    
    def test_filter_by_date_handles_timezone_aware_dates(self, parser):
        """Test date filtering with timezone-aware dates."""
        from datetime import datetime, timezone
        from newsletter_generator.aggregator import NewsletterAggregator
        from newsletter_generator.models import NewsletterItem
        
        aggregator = NewsletterAggregator([], parser)
        
        # Create items with timezone-aware dates
        items = [
            NewsletterItem(
                source_name="Source",
                source_type="email",
                title="TZ Aware Item",
                content="Content",
                published_date=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
            ),
        ]
        
        # Filter with timezone-naive since date
        since = datetime(2024, 1, 10)
        filtered = aggregator._filter_by_date(items, since)
        
        assert len(filtered) == 1
    
    def test_filter_by_date_handles_timezone_naive_dates(self, parser):
        """Test date filtering with timezone-naive dates."""
        from datetime import datetime, timezone
        from newsletter_generator.aggregator import NewsletterAggregator
        from newsletter_generator.models import NewsletterItem
        
        aggregator = NewsletterAggregator([], parser)
        
        # Create items with timezone-naive dates
        items = [
            NewsletterItem(
                source_name="Source",
                source_type="email",
                title="TZ Naive Item",
                content="Content",
                published_date=datetime(2024, 1, 15, 10, 0, 0),
            ),
        ]
        
        # Filter with timezone-aware since date
        since = datetime(2024, 1, 10, tzinfo=timezone.utc)
        filtered = aggregator._filter_by_date(items, since)
        
        assert len(filtered) == 1
    
    def test_get_fetcher_name_with_name_config(self, parser):
        """Test getting fetcher name when config has name attribute."""
        from unittest.mock import MagicMock
        from newsletter_generator.aggregator import NewsletterAggregator
        
        aggregator = NewsletterAggregator([], parser)
        
        mock_fetcher = MagicMock()
        mock_fetcher.config.name = "Test Feed"
        type(mock_fetcher).__name__ = "RSSFetcher"
        
        name = aggregator._get_fetcher_name(mock_fetcher)
        
        assert "RSSFetcher" in name
        assert "Test Feed" in name
    
    def test_get_fetcher_name_with_host_config(self, parser):
        """Test getting fetcher name when config has host attribute."""
        from unittest.mock import MagicMock
        from newsletter_generator.aggregator import NewsletterAggregator
        
        aggregator = NewsletterAggregator([], parser)
        
        mock_fetcher = MagicMock()
        mock_fetcher.config.host = "imap.example.com"
        del mock_fetcher.config.name  # Remove name attribute
        type(mock_fetcher).__name__ = "EmailFetcher"
        
        name = aggregator._get_fetcher_name(mock_fetcher)
        
        assert "EmailFetcher" in name
        assert "imap.example.com" in name
    
    def test_get_fetcher_name_without_config(self, parser):
        """Test getting fetcher name when fetcher has no config."""
        from unittest.mock import MagicMock
        from newsletter_generator.aggregator import NewsletterAggregator
        
        aggregator = NewsletterAggregator([], parser)
        
        mock_fetcher = MagicMock(spec=[])  # No attributes
        type(mock_fetcher).__name__ = "CustomFetcher"
        
        name = aggregator._get_fetcher_name(mock_fetcher)
        
        assert name == "CustomFetcher"


class TestAggregatorProperties:
    """Property-based tests for aggregation.
    
    Property tests:
    - Property 4: Content Normalization (Validates: Requirements 2.4, 1.4)
    - Property 3: Date Range Filtering (Validates: Requirements 2.1) - to be implemented
    - Property 5: Source Failure Resilience (Validates: Requirements 1.5, 2.5) - to be implemented
    """
    
    @pytest.mark.property
    @given(
        raw_content=st.one_of(
            # HTML content with various structures
            st.builds(
                lambda tag, text: f"<{tag}>{text}</{tag}>",
                tag=st.sampled_from(['p', 'div', 'span', 'article', 'section']),
                text=st.text(min_size=1, max_size=200, alphabet=st.characters(
                    whitelist_categories=('L', 'N', 'P', 'Z'),
                    whitelist_characters=' '
                )).filter(lambda x: x.strip())
            ),
            # Nested HTML structures
            st.builds(
                lambda outer, inner, text: f"<{outer}><{inner}>{text}</{inner}></{outer}>",
                outer=st.sampled_from(['div', 'article', 'section']),
                inner=st.sampled_from(['p', 'span', 'h1', 'h2']),
                text=st.text(min_size=1, max_size=200, alphabet=st.characters(
                    whitelist_categories=('L', 'N', 'P', 'Z'),
                    whitelist_characters=' '
                )).filter(lambda x: x.strip())
            ),
            # HTML with multiple elements
            st.builds(
                lambda texts: ''.join(f"<p>{t}</p>" for t in texts),
                texts=st.lists(
                    st.text(min_size=1, max_size=100, alphabet=st.characters(
                        whitelist_categories=('L', 'N', 'P', 'Z'),
                        whitelist_characters=' '
                    )).filter(lambda x: x.strip()),
                    min_size=1,
                    max_size=5
                )
            ),
            # Plain text content
            st.text(min_size=1, max_size=500, alphabet=st.characters(
                whitelist_categories=('L', 'N', 'P', 'Z'),
                whitelist_characters=' \n'
            )).filter(lambda x: x.strip())
        ),
        source_type=st.sampled_from(["email", "rss", "file"]),
        source_name=st.text(min_size=1, max_size=50, alphabet=st.characters(
            whitelist_categories=('L', 'N'),
            whitelist_characters=' -_'
        )).filter(lambda x: x.strip()),
        title=st.text(min_size=1, max_size=100, alphabet=st.characters(
            whitelist_categories=('L', 'N', 'P', 'Z'),
            whitelist_characters=' '
        )).filter(lambda x: x.strip()),
    )
    def test_content_normalization_produces_valid_newsletter_item(
        self,
        raw_content: str,
        source_type: str,
        source_name: str,
        title: str,
    ) -> None:
        """Property 4: Content Normalization.
        
        **Validates: Requirements 2.4, 1.4**
        
        For any raw content from any source type (email, RSS, file), the parser
        should produce a valid NewsletterItem with all required fields populated
        (source_name, source_type, title, content, published_date).
        
        This test verifies that:
        1. ContentParser can extract text from any HTML or plain text input
        2. The extracted content can be used to create a valid NewsletterItem
        3. All required fields are populated and valid
        """
        from datetime import datetime
        from newsletter_generator.aggregator import ContentParser
        from newsletter_generator.models import NewsletterItem
        
        # Create parser and extract text
        parser = ContentParser()
        
        # Extract text from raw content (could be HTML or plain text)
        extracted_text = parser.extract_text(raw_content)
        
        # Clean the extracted content
        cleaned_content = parser.clean_content(extracted_text)
        
        # For meaningful input, we should get meaningful output
        # If the raw content has actual text, the cleaned content should be non-empty
        # Note: Some HTML structures might result in empty content after cleaning
        # (e.g., if all content is in removed tags like nav/footer)
        
        # Create a NewsletterItem with the parsed content
        published_date = datetime.now()
        
        newsletter_item = NewsletterItem(
            source_name=source_name.strip(),
            source_type=source_type,
            title=title.strip(),
            content=cleaned_content if cleaned_content else extracted_text,
            published_date=published_date,
            html_content=raw_content if '<' in raw_content else None,
        )
        
        # Assert all required fields are populated
        assert newsletter_item.source_name, "source_name must be non-empty"
        assert len(newsletter_item.source_name) > 0, "source_name must have length > 0"
        
        assert newsletter_item.source_type in ["email", "rss", "file"], \
            f"source_type must be one of email, rss, file, got: {newsletter_item.source_type}"
        
        assert newsletter_item.title, "title must be non-empty"
        assert len(newsletter_item.title) > 0, "title must have length > 0"
        
        # Content should be populated (either cleaned or extracted)
        assert newsletter_item.content is not None, "content must not be None"
        
        assert newsletter_item.published_date is not None, "published_date must not be None"
        assert isinstance(newsletter_item.published_date, datetime), \
            "published_date must be a datetime instance"
        
        # Verify the source_type is valid
        assert newsletter_item.source_type == source_type, \
            "source_type should match the input source_type"
        
        # Verify html_content is set correctly for HTML input
        if '<' in raw_content and '>' in raw_content:
            assert newsletter_item.html_content is not None, \
                "html_content should be set for HTML input"
    
    @pytest.mark.property
    @given(
        html_content=st.one_of(
            # Simple HTML with text
            st.builds(
                lambda text: f"<html><body><p>{text}</p></body></html>",
                text=st.text(min_size=5, max_size=200, alphabet=st.characters(
                    whitelist_categories=('L', 'N', 'P', 'Z'),
                    whitelist_characters=' '
                )).filter(lambda x: len(x.strip()) >= 5)
            ),
            # HTML with multiple paragraphs
            st.builds(
                lambda texts: f"<html><body>{''.join(f'<p>{t}</p>' for t in texts)}</body></html>",
                texts=st.lists(
                    st.text(min_size=5, max_size=100, alphabet=st.characters(
                        whitelist_categories=('L', 'N', 'P', 'Z'),
                        whitelist_characters=' '
                    )).filter(lambda x: len(x.strip()) >= 5),
                    min_size=1,
                    max_size=3
                )
            ),
            # HTML with nested divs
            st.builds(
                lambda text: f"<div><div><p>{text}</p></div></div>",
                text=st.text(min_size=5, max_size=200, alphabet=st.characters(
                    whitelist_categories=('L', 'N', 'P', 'Z'),
                    whitelist_characters=' '
                )).filter(lambda x: len(x.strip()) >= 5)
            ),
        ),
        source_type=st.sampled_from(["email", "rss", "file"]),
    )
    def test_html_content_extraction_preserves_meaningful_text(
        self,
        html_content: str,
        source_type: str,
    ) -> None:
        """Property 4 (supplementary): HTML content extraction preserves text.
        
        **Validates: Requirements 2.4, 1.4**
        
        For any HTML content with meaningful text, the parser should extract
        non-empty content that preserves the original text.
        """
        from datetime import datetime
        from newsletter_generator.aggregator import ContentParser
        from newsletter_generator.models import NewsletterItem
        
        parser = ContentParser()
        
        # Extract text from HTML
        extracted_text = parser.extract_text(html_content)
        cleaned_content = parser.clean_content(extracted_text)
        
        # For HTML with meaningful content, extraction should produce non-empty result
        assert extracted_text.strip(), \
            f"Extracted text should be non-empty for HTML with content: {html_content[:100]}"
        
        # Create NewsletterItem
        newsletter_item = NewsletterItem(
            source_name="Test Source",
            source_type=source_type,
            title="Test Title",
            content=cleaned_content if cleaned_content else extracted_text,
            published_date=datetime.now(),
            html_content=html_content,
        )
        
        # Verify all required fields
        assert newsletter_item.source_name == "Test Source"
        assert newsletter_item.source_type == source_type
        assert newsletter_item.title == "Test Title"
        assert newsletter_item.content, "content should be non-empty for meaningful HTML"
        assert newsletter_item.published_date is not None
        assert newsletter_item.html_content == html_content


    @pytest.mark.property
    @settings(max_examples=20)
    @given(
        # Generate a list of newsletter items with various dates
        items_data=st.lists(
            st.tuples(
                # Days offset from a base date (can be negative for past, positive for future)
                st.integers(min_value=-365, max_value=365),
                # Hours offset within the day
                st.integers(min_value=0, max_value=23),
                # Source type
                st.sampled_from(["email", "rss", "file"]),
                # Title
                st.text(min_size=1, max_size=50, alphabet=st.characters(
                    whitelist_categories=('L', 'N'),
                    whitelist_characters=' '
                )).filter(lambda x: x.strip()),
            ),
            min_size=0,
            max_size=20,
        ),
        # Generate a date range (days offset from base date)
        since_offset=st.integers(min_value=-365, max_value=365),
    )
    def test_date_range_filtering_only_includes_items_in_range(
        self,
        items_data: list[tuple[int, int, str, str]],
        since_offset: int,
    ) -> None:
        """Property 3: Date Range Filtering.
        
        **Validates: Requirements 2.1**
        
        For any set of NewsletterItems with various dates and any date range,
        the filtered result should contain only items whose published_date
        falls within the specified range (on or after the since date).
        
        This test verifies that:
        1. Items with published_date >= since are included
        2. Items with published_date < since are excluded
        3. The total count of filtered items equals the count of items in range
        """
        from datetime import datetime, timedelta
        from newsletter_generator.aggregator import NewsletterAggregator, ContentParser
        from newsletter_generator.models import NewsletterItem
        
        # Use a fixed base date for reproducibility
        base_date = datetime(2024, 6, 15, 12, 0, 0)
        
        # Calculate the since date
        since_date = base_date + timedelta(days=since_offset)
        
        # Create NewsletterItems from the generated data
        items: list[NewsletterItem] = []
        for day_offset, hour_offset, source_type, title in items_data:
            published_date = base_date + timedelta(days=day_offset, hours=hour_offset)
            item = NewsletterItem(
                source_name=f"Test Source {source_type}",
                source_type=source_type,
                title=title.strip() if title.strip() else "Default Title",
                content=f"Content for item published on {published_date}",
                published_date=published_date,
            )
            items.append(item)
        
        # Create aggregator with a mock fetcher that returns our items
        parser = ContentParser()
        aggregator = NewsletterAggregator([], parser)
        
        # Use the internal _filter_by_date method directly
        filtered_items = aggregator._filter_by_date(items, since_date)
        
        # Calculate expected items (those with published_date >= since_date)
        expected_items = [
            item for item in items
            if item.published_date >= since_date
        ]
        
        # Verify the filtered count matches expected
        assert len(filtered_items) == len(expected_items), \
            f"Expected {len(expected_items)} items, got {len(filtered_items)}"
        
        # Verify all filtered items have published_date >= since_date
        for item in filtered_items:
            assert item.published_date >= since_date, \
                f"Item with date {item.published_date} should not be included " \
                f"(since_date: {since_date})"
        
        # Verify no items before since_date are included
        filtered_dates = {item.published_date for item in filtered_items}
        for item in items:
            if item.published_date < since_date:
                assert item.published_date not in filtered_dates, \
                    f"Item with date {item.published_date} should be excluded " \
                    f"(since_date: {since_date})"

    @pytest.mark.property
    @settings(max_examples=20)
    @given(
        # Generate items with timezone-aware and timezone-naive dates
        use_timezone=st.booleans(),
        items_count=st.integers(min_value=1, max_value=10),
        since_offset_days=st.integers(min_value=-30, max_value=30),
    )
    def test_date_range_filtering_handles_timezone_comparison(
        self,
        use_timezone: bool,
        items_count: int,
        since_offset_days: int,
    ) -> None:
        """Property 3 (supplementary): Date range filtering handles timezones.
        
        **Validates: Requirements 2.1**
        
        The date range filtering should correctly handle comparisons between
        timezone-aware and timezone-naive datetime objects.
        """
        from datetime import datetime, timedelta, timezone
        from newsletter_generator.aggregator import NewsletterAggregator, ContentParser
        from newsletter_generator.models import NewsletterItem
        
        # Base date
        base_date = datetime(2024, 6, 15, 12, 0, 0)
        
        # Create since date (timezone-naive)
        since_date = base_date + timedelta(days=since_offset_days)
        
        # Create items with dates spread around the since date
        items: list[NewsletterItem] = []
        for i in range(items_count):
            # Spread items from -5 to +5 days relative to since_date
            offset = i - (items_count // 2)
            published_date = since_date + timedelta(days=offset)
            
            # Optionally add timezone info
            if use_timezone:
                published_date = published_date.replace(tzinfo=timezone.utc)
            
            item = NewsletterItem(
                source_name=f"Source {i}",
                source_type="rss",
                title=f"Item {i}",
                content=f"Content {i}",
                published_date=published_date,
            )
            items.append(item)
        
        # Create aggregator
        parser = ContentParser()
        aggregator = NewsletterAggregator([], parser)
        
        # Filter should not raise an exception regardless of timezone mix
        filtered_items = aggregator._filter_by_date(items, since_date)
        
        # Verify filtering logic is correct
        for item in filtered_items:
            # Normalize for comparison
            item_date = item.published_date
            cmp_since = since_date
            
            if item_date.tzinfo is not None and cmp_since.tzinfo is None:
                item_date = item_date.replace(tzinfo=None)
            elif item_date.tzinfo is None and cmp_since.tzinfo is not None:
                cmp_since = cmp_since.replace(tzinfo=None)
            
            assert item_date >= cmp_since, \
                f"Filtered item date {item.published_date} should be >= since {since_date}"


    @pytest.mark.property
    @settings(max_examples=20)
    @given(
        # Generate configuration for multiple sources
        # Each source is a tuple of (should_fail: bool, items_count: int)
        sources_config=st.lists(
            st.tuples(
                st.booleans(),  # should_fail
                st.integers(min_value=0, max_value=5),  # items_count
            ),
            min_size=1,
            max_size=6,
        ),
    )
    def test_source_failure_resilience_returns_items_from_successful_sources(
        self,
        sources_config: list[tuple[bool, int]],
    ) -> None:
        """Property 5: Source Failure Resilience.
        
        **Validates: Requirements 1.5, 2.5**
        
        For any set of configured sources where one or more sources fail,
        the aggregator should still return items from all successful sources
        and the total item count should equal the sum of items from non-failing sources.
        
        This test verifies that:
        1. Failing sources do not prevent successful sources from being processed
        2. The total item count equals the sum of items from non-failing sources
        3. All items from successful sources are present in the result
        4. The aggregator continues processing after encountering failures
        """
        from datetime import datetime, timedelta
        from unittest.mock import MagicMock
        from newsletter_generator.aggregator import NewsletterAggregator, ContentParser
        from newsletter_generator.models import NewsletterItem
        
        # Base date for items
        base_date = datetime(2024, 6, 15, 12, 0, 0)
        since_date = base_date - timedelta(days=7)
        
        # Create mock fetchers based on configuration
        fetchers = []
        expected_items: list[NewsletterItem] = []
        
        for source_idx, (should_fail, items_count) in enumerate(sources_config):
            mock_fetcher = MagicMock()
            mock_fetcher.config = MagicMock()
            mock_fetcher.config.name = f"Source_{source_idx}"
            
            if should_fail:
                # Configure fetcher to raise an exception
                mock_fetcher.fetch.side_effect = Exception(f"Source {source_idx} failed")
            else:
                # Configure fetcher to return items
                source_items = []
                for item_idx in range(items_count):
                    item = NewsletterItem(
                        source_name=f"Source_{source_idx}",
                        source_type="rss",
                        title=f"Item {item_idx} from Source {source_idx}",
                        content=f"Content for item {item_idx} from source {source_idx}",
                        published_date=base_date + timedelta(hours=item_idx),
                    )
                    source_items.append(item)
                    expected_items.append(item)
                
                mock_fetcher.fetch.return_value = source_items
            
            fetchers.append(mock_fetcher)
        
        # Create aggregator with the mock fetchers
        parser = ContentParser()
        aggregator = NewsletterAggregator(fetchers, parser)
        
        # Run aggregation - should not raise even if some sources fail
        result = aggregator.aggregate(since_date)
        
        # Verify the total item count equals the sum from non-failing sources
        assert len(result) == len(expected_items), \
            f"Expected {len(expected_items)} items from successful sources, got {len(result)}"
        
        # Verify all expected items are present (by checking titles)
        result_titles = {item.title for item in result}
        expected_titles = {item.title for item in expected_items}
        
        assert result_titles == expected_titles, \
            f"Missing items: {expected_titles - result_titles}, " \
            f"Extra items: {result_titles - expected_titles}"
        
        # Verify all fetchers were called
        for fetcher in fetchers:
            fetcher.fetch.assert_called_once()

    @pytest.mark.property
    @settings(max_examples=20)
    @given(
        # Number of successful sources
        successful_count=st.integers(min_value=0, max_value=5),
        # Number of failing sources
        failing_count=st.integers(min_value=1, max_value=5),
        # Items per successful source
        items_per_source=st.integers(min_value=1, max_value=5),
    )
    def test_source_failure_resilience_with_mixed_success_and_failure(
        self,
        successful_count: int,
        failing_count: int,
        items_per_source: int,
    ) -> None:
        """Property 5 (supplementary): Mixed success and failure sources.
        
        **Validates: Requirements 1.5, 2.5**
        
        When some sources succeed and some fail, the aggregator should:
        1. Return all items from successful sources
        2. Not include any items from failed sources
        3. Continue processing all sources regardless of failures
        """
        from datetime import datetime, timedelta
        from unittest.mock import MagicMock
        from newsletter_generator.aggregator import NewsletterAggregator, ContentParser
        from newsletter_generator.models import NewsletterItem
        
        base_date = datetime(2024, 6, 15, 12, 0, 0)
        since_date = base_date - timedelta(days=7)
        
        fetchers = []
        expected_total_items = 0
        
        # Create successful fetchers
        for i in range(successful_count):
            mock_fetcher = MagicMock()
            mock_fetcher.config = MagicMock()
            mock_fetcher.config.name = f"SuccessSource_{i}"
            
            items = [
                NewsletterItem(
                    source_name=f"SuccessSource_{i}",
                    source_type="email",
                    title=f"Success Item {j} from Source {i}",
                    content=f"Content {j}",
                    published_date=base_date,
                )
                for j in range(items_per_source)
            ]
            mock_fetcher.fetch.return_value = items
            expected_total_items += items_per_source
            fetchers.append(mock_fetcher)
        
        # Create failing fetchers
        for i in range(failing_count):
            mock_fetcher = MagicMock()
            mock_fetcher.config = MagicMock()
            mock_fetcher.config.name = f"FailSource_{i}"
            mock_fetcher.fetch.side_effect = ConnectionError(f"Failed to connect to source {i}")
            fetchers.append(mock_fetcher)
        
        # Create aggregator and run
        parser = ContentParser()
        aggregator = NewsletterAggregator(fetchers, parser)
        
        result = aggregator.aggregate(since_date)
        
        # Verify correct number of items returned
        assert len(result) == expected_total_items, \
            f"Expected {expected_total_items} items, got {len(result)}"
        
        # Verify all items are from successful sources
        for item in result:
            assert "SuccessSource" in item.source_name, \
                f"Item from failed source found: {item.source_name}"

    @pytest.mark.property
    @settings(max_examples=20)
    @given(
        # Different types of exceptions to test
        exception_type=st.sampled_from([
            Exception,
            ConnectionError,
            TimeoutError,
            ValueError,
            RuntimeError,
        ]),
        # Number of items from successful source
        items_count=st.integers(min_value=1, max_value=10),
    )
    def test_source_failure_resilience_handles_various_exception_types(
        self,
        exception_type: type,
        items_count: int,
    ) -> None:
        """Property 5 (supplementary): Various exception types are handled.
        
        **Validates: Requirements 1.5, 2.5**
        
        The aggregator should gracefully handle various types of exceptions
        from failing sources without affecting successful sources.
        """
        from datetime import datetime, timedelta
        from unittest.mock import MagicMock
        from newsletter_generator.aggregator import NewsletterAggregator, ContentParser
        from newsletter_generator.models import NewsletterItem
        
        base_date = datetime(2024, 6, 15, 12, 0, 0)
        since_date = base_date - timedelta(days=7)
        
        # Create a failing fetcher with the specified exception type
        failing_fetcher = MagicMock()
        failing_fetcher.config = MagicMock()
        failing_fetcher.config.name = "FailingSource"
        failing_fetcher.fetch.side_effect = exception_type("Test failure")
        
        # Create a successful fetcher
        successful_fetcher = MagicMock()
        successful_fetcher.config = MagicMock()
        successful_fetcher.config.name = "SuccessfulSource"
        
        items = [
            NewsletterItem(
                source_name="SuccessfulSource",
                source_type="file",
                title=f"Item {i}",
                content=f"Content {i}",
                published_date=base_date,
            )
            for i in range(items_count)
        ]
        successful_fetcher.fetch.return_value = items
        
        # Test with failing source first, then successful
        parser = ContentParser()
        aggregator = NewsletterAggregator([failing_fetcher, successful_fetcher], parser)
        
        result = aggregator.aggregate(since_date)
        
        # Should still get all items from successful source
        assert len(result) == items_count, \
            f"Expected {items_count} items, got {len(result)}"
        
        # Both fetchers should have been called
        failing_fetcher.fetch.assert_called_once()
        successful_fetcher.fetch.assert_called_once()
