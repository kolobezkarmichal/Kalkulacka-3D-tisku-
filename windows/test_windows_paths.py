"""Testy konfigurační složky a názvů pro Windows bez potřeby Windows OS."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import engine
from engine import Rates, default_config_path, load_rates, save_rates, suggested_project_filename


class WindowsCompatibilityTests(unittest.TestCase):
    def test_windows_appdata_settings_location_and_roundtrip(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(engine.sys, 'platform', 'win32'), patch.dict(os.environ, {'APPDATA': directory}):
                expected = Path(directory) / '3d-kalkulacka-p2s' / 'settings.json'
                self.assertEqual(default_config_path(), expected)
                self.assertFalse(expected.exists())
                save_rates(Rates(amortization_per_hour=17.5))
                self.assertTrue(expected.exists())
                self.assertAlmostEqual(load_rates().amortization_per_hour, 17.5)

    def test_windows_appdata_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            environment = dict(os.environ)
            environment.pop('APPDATA', None)
            with patch.object(engine.sys, 'platform', 'win32'), patch.dict(os.environ, environment, clear=True), \
                    patch.object(engine.Path, 'home', return_value=Path(directory)):
                self.assertEqual(default_config_path(), Path(directory) / 'AppData' / 'Roaming' /
                                 '3d-kalkulacka-p2s' / 'settings.json')

    def test_unicode_filename_windows_safe(self):
        self.assertEqual(suggested_project_filename('Dárek Aleš'), 'Dárek Aleš.3dk.json')
        self.assertEqual(suggested_project_filename('CON'), '_CON.3dk.json')
        self.assertEqual(suggested_project_filename('Cena: PLA * modrá?'),
                         'Cena_ PLA _ modrá_.3dk.json')

    def test_linux_config_location_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(engine.sys, 'platform', 'linux'), \
                    patch.object(engine.Path, 'home', return_value=Path(directory)):
                self.assertEqual(default_config_path(), Path(directory) / '.config' /
                                 '3d-kalkulacka-p2s' / 'settings.json')


if __name__ == '__main__':
    unittest.main(verbosity=2)
