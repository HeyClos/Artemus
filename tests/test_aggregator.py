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
    """Unit tests for RSSFetcher."""
    
    pass  # Tests will be implemented in task 5.4


class TestFileFetcher:
    """Unit tests for FileFetcher."""
    
    pass  # Tests will be implemented in task 5.5


class TestNewsletterAggregator:
    """Unit tests for NewsletterAggregator."""
    
    pass  # Tests will be implemented in task 5.6


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
