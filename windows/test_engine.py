"""Testy běžící pouze se standardním Pythonem: python3 test_engine.py"""
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from engine import Filament, PrintJob, Rates, open_project, parse_file, project_totals, save_project


class EngineTests(unittest.TestCase):
    def test_price_calculation_and_multiple_quantity(self):
        rates = Rates()
        job = PrintJob('a', 'Oci', 'a.gcode.3mf', 1, ['Oko 1', 'Oko 2'], 3899,
                       [Filament(1, 'PLA', '#161616', 4.87),
                        Filament(2, 'PLA', '#FFF144', 8.95),
                        Filament(3, 'PLA', '#FFFFFF', 5.44)])
        self.assertAlmostEqual(job.totals(rates)['material'], 3.852)
        self.assertAlmostEqual(job.totals(rates)['base'], 16.84866666667)
        self.assertAlmostEqual(job.totals(rates)['price'], 25.273)
        job.quantity = 3
        self.assertAlmostEqual(job.totals(rates)['price'], 75.819)
        self.assertAlmostEqual(project_totals([job], rates)['grams'], 57.78)

    def test_energy_kwh(self):
        r = Rates(energy_mode='power', power_watt=100, price_kwh=6)
        self.assertAlmostEqual(r.hourly_energy_cost(), 0.60)

    def test_color_price_catalog_and_fallback(self):
        r = Rates(catalog=[{'material':'PLA', 'color':'', 'price_kg':250},
                                 {'material':'PLA', 'color':'#FFFFFF', 'price_kg':320}])
        self.assertEqual(r.lookup_price('PLA', '#FFFFFF'), 320)
        self.assertEqual(r.lookup_price('pla', '#F5F5F5'), 250)
        self.assertEqual(r.lookup_price('PETG', '#161616'), 200)

    def test_save_reopen(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp, 'test.3dk.json')
            r = Rates()
            j = PrintJob('id', 'Tisk A', '/tmp/g.gcode.3mf', 1, [], 3600,
                         [Filament(1,'TPU','#ABCDEF', 11.5, price_kg=400)])
            save_project(path, 'Zakázka ABC', r, [j])
            title, stored, jobs = open_project(path)
            self.assertEqual(title, 'Zakázka ABC')
            self.assertEqual(jobs[0].filaments[0].material, 'TPU')
            self.assertEqual(stored.amortization_per_hour, 10)

    def test_parse_minimal_3mf(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp, 'Test.gcode.3mf')
            xml = '''<config><plate><metadata key="index" value="1"/>
              <metadata key="prediction" value="7200"/><metadata key="weight" value="8"/>
              <object name="A"/><filament id="1" type="PETG" color="#FF0011" used_g="8" used_m="2.7"/>
              <filament id="2" type="PLA" color="#FFFFFF" used_g="0" used_m="0"/></plate></config>'''
            with zipfile.ZipFile(path, 'w') as z:
                z.writestr('Metadata/slice_info.config', xml)
                z.writestr('Metadata/plate_1.gcode', '; model printing time: 1h 55m 0s; total estimated time: 2h 0m 0s\n')
            jobs = parse_file(path, Rates())
            self.assertEqual(len(jobs), 1)
            self.assertEqual(jobs[0].objects, ['A'])
            self.assertEqual(jobs[0].time_seconds, 7200)
            self.assertEqual(len(jobs[0].filaments), 1)
            self.assertEqual(jobs[0].filaments[0].material, 'PETG')

    def test_plain_gcode_missing_metadata_is_editable(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp, 'empty.gcode')
            path.write_text('G28\nG1 X20 Y30 E5\n')
            j = parse_file(path, Rates())[0]
            self.assertEqual(j.time_seconds, 0)
            self.assertFalse(j.filaments)
            self.assertTrue(j.warnings)


    def test_v02_backward_compatibility_and_named_catalog(self):
        # Starší ceníky/zakázky z v0.1 nemají „name“ ani „theme“.
        legacy = Rates(catalog=[
            {'material': 'PLA', 'color': '#000000', 'price_kg': 250},
            {'material': 'PLA', 'color': '#000000', 'price_kg': 350},
        ], dark_mode=False)
        self.assertEqual(legacy.theme_name(), 'light')
        self.assertNotEqual(legacy.catalog[0]['name'], legacy.catalog[1]['name'])
        legacy.theme = 'hybrid'
        job = PrintJob('catalog', 'Více cen PLA', 'Oci.gcode.3mf', 1, [], 3900,
                       [Filament(1, 'PLA', '#000000', 12, price_kg=350,
                                 catalog_name=legacy.catalog[1]['name'])])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp, 'ulozeni.3dk.json')
            save_project(path, 'Více barev', legacy, [job])
            title, restored_rates, restored = open_project(path)
            self.assertEqual(restored_rates.theme_name(), 'hybrid')
            self.assertEqual(restored[0].filaments[0].catalog_name, legacy.catalog[1]['name'])
            self.assertEqual(restored[0].filaments[0].price_kg, 350)
            self.assertEqual(len(restored_rates.catalog), 2)



if __name__ == '__main__':
    unittest.main(verbosity=2)
