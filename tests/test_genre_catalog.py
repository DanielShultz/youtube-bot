import json
import shutil
import tempfile
import unittest
from pathlib import Path

from kachalnaya_pepega.genre_catalog import GENRE_OPTIONS, GenreCatalog


class GenreCatalogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp(prefix='genre-catalog-')

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_creates_runtime_json_from_seed(self) -> None:
        catalog = GenreCatalog(self.temp_dir)
        runtime_file = Path(self.temp_dir) / 'artist_genres.json'
        self.assertTrue(runtime_file.exists())
        self.assertEqual(catalog.resolve('ATEEZ'), 'K-Pop - Idol')
        self.assertEqual(catalog.genre_options, GENRE_OPTIONS)

    def test_assign_persists_new_artist(self) -> None:
        catalog = GenreCatalog(self.temp_dir)
        canonical = catalog.assign('New Artist', GENRE_OPTIONS[2])
        self.assertEqual(canonical, 'New Artist')
        runtime_file = Path(self.temp_dir) / 'artist_genres.json'
        data = json.loads(runtime_file.read_text(encoding='utf-8-sig'))
        self.assertEqual(data['New Artist'], GENRE_OPTIONS[2])
        reloaded = GenreCatalog(self.temp_dir)
        self.assertEqual(reloaded.resolve('New Artist'), GENRE_OPTIONS[2])

    def test_assign_reuses_existing_canonical_artist_name(self) -> None:
        catalog = GenreCatalog(self.temp_dir)
        self.assertEqual(catalog.canonical_artist('ateez'), 'ATEEZ')
        self.assertEqual(catalog.prepare_artist('  ateez '), 'ATEEZ')
        canonical = catalog.assign('ateez', GENRE_OPTIONS[0])
        self.assertEqual(canonical, 'ATEEZ')
        data = json.loads((Path(self.temp_dir) / 'artist_genres.json').read_text(encoding='utf-8-sig'))
        self.assertIn('ATEEZ', data)
        self.assertNotIn('ateez', data)

    def test_assign_rejects_unknown_genre(self) -> None:
        catalog = GenreCatalog(self.temp_dir)
        with self.assertRaises(ValueError):
            catalog.assign('New Artist', 'Unknown Genre')
