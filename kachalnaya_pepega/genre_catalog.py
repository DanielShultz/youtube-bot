"""Работа с жанрами и сохранённой картой артистов."""

from __future__ import annotations

import json
import os
from pathlib import Path


def _load_genre_options() -> list[str]:
    genres_path = Path(__file__).with_name('genres.json')
    with open(genres_path, 'r', encoding='utf-8-sig') as handle:
        data = json.load(handle)
    if not isinstance(data, list):
        raise ValueError('genres.json must contain a list of genre names')
    return [str(item) for item in data if str(item).strip()]


GENRE_OPTIONS = _load_genre_options()


class GenreCatalog:
    """Хранит жанры артистов и сохраняет выборы пользователя."""

    def __init__(self, data_dir: str) -> None:
        self.data_dir = data_dir
        self.file_path = os.path.join(data_dir, 'artist_genres.json')
        self.seed_path = str(Path(__file__).with_name('artist_genres.seed.json'))
        self._ensure_catalog_file()
        self._artist_genres = self._load_json_mapping(self.file_path)
        self._artist_index = self._build_artist_index(self._artist_genres)

    @property
    def genre_options(self) -> list[str]:
        """Возвращает допустимые названия жанров."""
        return list(GENRE_OPTIONS)

    def resolve(self, artist: str) -> str | None:
        """Возвращает сохранённый жанр для артиста с учётом нормализации имени."""
        canonical = self.canonical_artist(artist)
        if canonical is None:
            return None
        return self._artist_genres.get(canonical)

    def canonical_artist(self, artist: str) -> str | None:
        """Возвращает каноническое имя артиста из каталога, если оно уже известно."""
        key = self.normalize_artist_key(artist)
        if not key:
            return None
        return self._artist_index.get(key)

    def prepare_artist(self, artist: str) -> str:
        """Возвращает имя артиста для сохранения на диск."""
        return self.canonical_artist(artist) or self.clean_artist_name(artist)

    def assign(self, artist: str, genre: str) -> str:
        """Сохраняет жанр для артиста и возвращает каноническое имя записи."""
        if genre not in GENRE_OPTIONS:
            raise ValueError(f'Unsupported genre: {genre}')
        canonical = self.prepare_artist(artist)
        self._artist_genres[canonical] = genre
        self._artist_index[self.normalize_artist_key(canonical)] = canonical
        self._save_file()
        return canonical

    def all(self) -> dict[str, str]:
        """Возвращает текущую карту жанров."""
        return dict(self._artist_genres)

    def _ensure_catalog_file(self) -> None:
        os.makedirs(self.data_dir, exist_ok=True)
        if os.path.exists(self.file_path):
            return
        seed_mapping = self._load_json_mapping(self.seed_path)
        self._write_json_mapping(self.file_path, seed_mapping)

    def _load_json_mapping(self, path: str) -> dict[str, str]:
        if not os.path.exists(path):
            return {}
        try:
            with open(path, 'r', encoding='utf-8-sig') as handle:
                data = json.load(handle)
            if isinstance(data, dict):
                return {
                    self.clean_artist_name(str(key)): str(value)
                    for key, value in data.items()
                    if str(value) in GENRE_OPTIONS and self.clean_artist_name(str(key))
                }
        except Exception:
            return {}
        return {}

    def _save_file(self) -> None:
        self._write_json_mapping(self.file_path, self._artist_genres)

    @staticmethod
    def _write_json_mapping(path: str, mapping: dict[str, str]) -> None:
        with open(path, 'w', encoding='utf-8-sig') as handle:
            json.dump(mapping, handle, ensure_ascii=False, indent=2, sort_keys=True)

    @staticmethod
    def clean_artist_name(artist: str) -> str:
        """Убирает лишние пробелы вокруг и внутри имени артиста."""
        return ' '.join((artist or '').split())

    @classmethod
    def normalize_artist_key(cls, artist: str) -> str:
        """Нормализует имя артиста для case-insensitive поиска."""
        return cls.clean_artist_name(artist).casefold()

    @classmethod
    def _build_artist_index(cls, mapping: dict[str, str]) -> dict[str, str]:
        return {
            cls.normalize_artist_key(artist): artist
            for artist in mapping
            if cls.normalize_artist_key(artist)
        }
