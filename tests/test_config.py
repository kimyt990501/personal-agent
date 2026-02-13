"""Tests for src/config.py"""
from pathlib import Path

import pytest

from src.config import BASE_DIR, DATA_DIR, DB_PATH, MAX_HISTORY_LENGTH


class TestConfig:
    def test_base_dir_is_project_root(self):
        """BASE_DIR이 프로젝트 루트(src의 부모)를 가리키는지"""
        assert BASE_DIR.exists()
        assert (BASE_DIR / "src").is_dir()

    def test_data_dir_path(self):
        assert DATA_DIR == BASE_DIR / "data"

    def test_db_path(self):
        assert DB_PATH == DATA_DIR / "conversations.db"
        assert str(DB_PATH).endswith(".db")

    def test_max_history_length_is_positive_int(self):
        assert isinstance(MAX_HISTORY_LENGTH, int)
        assert MAX_HISTORY_LENGTH > 0

    def test_paths_are_path_objects(self):
        assert isinstance(BASE_DIR, Path)
        assert isinstance(DATA_DIR, Path)
        assert isinstance(DB_PATH, Path)
