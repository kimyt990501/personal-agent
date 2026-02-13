"""Tests for format_search_results() in src/utils/web.py"""
import pytest

from src.utils.web import format_search_results


class TestFormatSearchResults:
    def test_single_result(self):
        results = [
            {"title": "Python 3.13", "body": "New features in Python 3.13", "href": "https://python.org"}
        ]
        output = format_search_results(results)
        assert "1." in output
        assert "Python 3.13" in output
        assert "New features" in output
        assert "https://python.org" in output

    def test_multiple_results(self):
        results = [
            {"title": "Result 1", "body": "Body 1", "href": "https://a.com"},
            {"title": "Result 2", "body": "Body 2", "href": "https://b.com"},
            {"title": "Result 3", "body": "Body 3", "href": "https://c.com"},
        ]
        output = format_search_results(results)
        assert "1." in output
        assert "2." in output
        assert "3." in output

    def test_empty_results(self):
        output = format_search_results([])
        assert "없습니다" in output

    def test_missing_fields_fallback(self):
        """필드가 누락된 경우 빈 문자열로 처리"""
        results = [{"title": "Only Title"}]
        output = format_search_results(results)
        assert "Only Title" in output
        # body, href가 없어도 에러 없이 처리
        assert "링크:" in output

    def test_korean_content(self):
        results = [
            {"title": "비트코인 시세", "body": "현재 비트코인 가격은...", "href": "https://example.com"}
        ]
        output = format_search_results(results)
        assert "비트코인 시세" in output
        assert "현재 비트코인 가격" in output
