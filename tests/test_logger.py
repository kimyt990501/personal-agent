"""Tests for src/utils/logger.py"""
import logging

import pytest

from src.utils.logger import setup_logger


class TestSetupLogger:
    def test_returns_logger_instance(self):
        logger = setup_logger("test_returns")
        assert isinstance(logger, logging.Logger)

    def test_logger_name(self):
        logger = setup_logger("my_module")
        assert logger.name == "my_module"

    def test_default_name(self):
        logger = setup_logger()
        assert logger.name == "personal_agent"

    def test_has_handlers(self):
        logger = setup_logger("test_handlers")
        assert len(logger.handlers) >= 2  # console + file

    def test_debug_level_set(self):
        logger = setup_logger("test_level")
        assert logger.level == logging.DEBUG

    def test_no_duplicate_handlers(self):
        """같은 이름으로 여러 번 호출해도 핸들러 중복 방지"""
        name = "test_no_dup"
        logger1 = setup_logger(name)
        handler_count = len(logger1.handlers)

        logger2 = setup_logger(name)
        assert len(logger2.handlers) == handler_count
        assert logger1 is logger2

    def test_console_handler_exists(self):
        logger = setup_logger("test_console")
        stream_handlers = [h for h in logger.handlers if isinstance(h, logging.StreamHandler)
                          and not isinstance(h, logging.FileHandler)]
        assert len(stream_handlers) >= 1

    def test_file_handler_exists(self):
        logger = setup_logger("test_file")
        file_handlers = [h for h in logger.handlers if isinstance(h, logging.FileHandler)]
        assert len(file_handlers) >= 1
