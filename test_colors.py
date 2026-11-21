"""Test offline odhadu barev z názvů, bez Qt a webového připojení."""
import csv
import unittest
from pathlib import Path
from engine import approximate_filament_color, import_filament_csv

class ColorTests(unittest.TestCase):
    def test_specific_names(self):
        self.assertEqual(approximate_filament_color('Armádní zelená'), '#667453')
        self.assertEqual(approximate_filament_color('Pistáciová zelená'), '#B4D18D')
        self.assertEqual(approximate_filament_color('Glow Zelená'), '#A5E76B')
        self.assertEqual(approximate_filament_color('Stříbrná metalická'), '#A8B2BB')
        self.assertEqual(approximate_filament_color('Šedý přeběh'), '#999FA7')
        self.assertEqual(approximate_filament_color('Emerald green ŠKODA AUTO (zelená)'), '#168460')
    def test_modifiers(self):
        self.assertNotEqual(approximate_filament_color('modrá'), approximate_filament_color('světle modrá'))
        self.assertNotEqual(approximate_filament_color('modrá'), approximate_filament_color('tmavě modrá'))
        c = lambda hx: sum(int(hx[i:i+2],16) for i in (1,3,5))
        self.assertGreater(c(approximate_filament_color('světle modrá')), c(approximate_filament_color('modrá')))
        self.assertLess(c(approximate_filament_color('tmavě modrá')), c(approximate_filament_color('modrá')))
    def test_override_unknown(self):
        self.assertEqual(approximate_filament_color('armádní zelená', '#123ABC'), '#123ABC')
        self.assertEqual(approximate_filament_color('Vymyšlený odstín 2026'), '#87919D')
    def test_hex_from_new_web_export_and_price_preservation(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as temp:
            path = Path(temp, 'web.csv')
            head = 'ID;Název / barva;Materiál;Výrobce;Množství (g);Datum změny;Viditelnost;HEX barva;Zobrazení vzorku\n'
            path.write_text(head + '7;Armádní zelená;PLA;3D FOX;800;21.11.2026;Veřejný;#4F6B42;HEX\n', encoding='utf-8-sig')
            catalog, _ = import_filament_csv(path, [])
            self.assertEqual(catalog[0]['color'], '#4F6B42')
            self.assertEqual(approximate_filament_color(catalog[0]['name'],catalog[0]['color']),'#4F6B42')
            catalog[0]['price_kg'] = 359
            path.write_text(head + '7;Armádní zelená;PLA;3D FOX;500;21.11.2026;Veřejný;#516E49;HEX\n', encoding='utf-8-sig')
            catalog, stats = import_filament_csv(path, catalog)
            self.assertEqual(stats['updated'], 1)
            self.assertEqual(catalog[0]['price_kg'], 359)
            self.assertEqual(catalog[0]['stock_grams'], 500)
            self.assertEqual(catalog[0]['color'], '#516E49')
            path.write_text(head + '7;Armádní zelená;PLA;3D FOX;500;21.11.2026;Veřejný;NEPLATNÉ;HEX\n', encoding='utf-8-sig')
            with self.assertRaises(ValueError):
                import_filament_csv(path, catalog)

    def test_real_csv_and_new_import(self):
        sample = Path(__file__).with_name('prehled-filamentu-2026-11-21.csv')
        catalog, _ = import_filament_csv(sample, [])
        for entry in catalog:
            color = approximate_filament_color(entry['name'], entry.get('color',''))
            self.assertRegex(color, r'^#[0-9A-F]{6}$')
        target = next(e for e in catalog if e['name'] == 'Pistáciová zelená')
        self.assertEqual(approximate_filament_color(target['name']), '#B4D18D')
        # Nový filament v CSV automaticky dostane odhad barvy, bez zásahu do kódu.
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as temp:
            path = Path(temp, 'pridano.csv')
            path.write_text(sample.read_text(encoding='utf-8-sig') +
                '30;Tmavě modrá;PLA;3D FOX;500;21.11.2026;Veřejný\n', encoding='utf-8-sig')
            catalog, stats = import_filament_csv(path, catalog)
            self.assertEqual(stats['added'], 1)
            new = next(e for e in catalog if e['csv_id'] == '30')
            self.assertEqual(approximate_filament_color(new['name']), approximate_filament_color('Tmavě modrá'))

if __name__ == '__main__':
    unittest.main(verbosity=2)
