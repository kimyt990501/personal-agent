"""Tests for src/utils/web.py - URL extraction tests"""
import re
import pytest

from src.utils.web import extract_urls, URL_PATTERN


class TestExtractUrls:
    def test_single_http_url(self):
        text = "Visit http://example.com for more info"
        urls = extract_urls(text)
        assert urls == ["http://example.com"]

    def test_single_https_url(self):
        text = "Visit https://example.com for more info"
        urls = extract_urls(text)
        assert urls == ["https://example.com"]

    def test_url_with_path(self):
        text = "Go to https://example.com/path/to/page"
        urls = extract_urls(text)
        assert urls == ["https://example.com/path/to/page"]

    def test_url_with_query_params(self):
        text = "Search https://example.com/search?q=test&lang=ko"
        urls = extract_urls(text)
        assert len(urls) == 1
        assert "q=test" in urls[0]

    def test_multiple_urls(self):
        text = "Check https://a.com and https://b.com"
        urls = extract_urls(text)
        assert len(urls) == 2

    def test_no_urls(self):
        text = "This is just plain text without URLs"
        urls = extract_urls(text)
        assert urls == []

    def test_empty_string(self):
        urls = extract_urls("")
        assert urls == []

    def test_url_with_fragment(self):
        text = "See https://example.com/page#section"
        urls = extract_urls(text)
        assert len(urls) == 1

    def test_korean_text_with_url(self):
        text = "이 링크를 확인해봐: https://naver.com/news/12345"
        urls = extract_urls(text)
        assert len(urls) == 1
        assert "naver.com" in urls[0]


class TestUrlPattern:
    def test_matches_http(self):
        assert URL_PATTERN.search("http://example.com")

    def test_matches_https(self):
        assert URL_PATTERN.search("https://example.com")

    def test_no_match_ftp(self):
        """ftp:// 는 매칭하지 않아야 함"""
        assert URL_PATTERN.search("ftp://example.com") is None

    def test_no_match_plain_text(self):
        assert URL_PATTERN.search("just some text") is None
