import pytest
from backend.app.providers.news import parse_rss_feed


def test_rss_parser_cleans_html_and_normalizes_publication_time():
    rss = b'''<rss><channel><item>
      <title>Bitcoin &amp;amp; Markets</title>
      <link>https://example.com/story</link>
      <pubDate>Sun, 11 Oct 2026 10:00:00 GMT</pubDate>
      <description><![CDATA[<p>Market <b>moves</b> &amp; context.</p>]]></description>
    </item></channel></rss>'''
    result = parse_rss_feed("Example", rss)
    assert len(result) == 1
    assert result[0]["url"] == "https://example.com/story"
    assert "<p>" not in result[0]["summary"]
    assert "Market moves" in result[0]["summary"]
    assert result[0]["published_at"].startswith("2026-10-11T10:00:00")


def test_rss_parser_rejects_non_http_links():
    rss = b'''<rss><channel><item><title>Story</title><link>javascript:alert(1)</link></item></channel></rss>'''
    assert parse_rss_feed("Example", rss) == []


def test_rss_parser_rejects_invalid_xml():
    with pytest.raises(Exception):
        parse_rss_feed("Example", "<rss>")
