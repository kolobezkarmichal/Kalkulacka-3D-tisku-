"""Regresní test: česká diakritika v názvu ukládané zakázky."""
import tempfile
import unittest
from pathlib import Path

from engine import Rates, open_project, save_project, suggested_project_filename


class FilenameTests(unittest.TestCase):
    def test_czech_diacritics_and_spaces_remain(self):
        self.assertEqual(suggested_project_filename('Dárek Aleš'), 'Dárek Aleš.3dk.json')
        self.assertEqual(suggested_project_filename('Žluťoučký kůň – č. 2'),
                         'Žluťoučký kůň – č. 2.3dk.json')

    def test_combining_accents_are_normalized(self):
        self.assertEqual(suggested_project_filename('Da\u0301rek Ales\u030c'), 'Dárek Aleš.3dk.json')

    def test_only_invalid_filename_characters_are_replaced(self):
        self.assertEqual(suggested_project_filename('Dárek: Aleš / 2026'),
                         'Dárek_ Aleš _ 2026.3dk.json')
        self.assertEqual(suggested_project_filename('  '), 'zakázka.3dk.json')
        self.assertEqual(suggested_project_filename('CON'), '_CON.3dk.json')

    def test_save_and_open_unicode_and_old_filename(self):
        with tempfile.TemporaryDirectory() as tmp:
            for filename in ('Dárek Aleš.3dk.json', 'D_rek_Ale_.3dk.json'):
                with self.subTest(filename=filename):
                    path = Path(tmp, filename)
                    save_project(path, 'Dárek Aleš', Rates(), [])
                    self.assertTrue(path.is_file())
                    title, _rates, jobs = open_project(path)
                    self.assertEqual(title, 'Dárek Aleš')
                    self.assertEqual(jobs, [])


if __name__ == '__main__':
    unittest.main(verbosity=2)
