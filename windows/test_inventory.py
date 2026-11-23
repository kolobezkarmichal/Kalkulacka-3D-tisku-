"""Testy nového skladu CSV, pevného nacenění a přepočtu zásob bez PySide6."""
import csv
import tempfile
import unittest
from pathlib import Path

from engine import Filament, PrintJob, Rates, import_filament_csv, stock_balances, save_project, open_project

SAMPLE = Path(__file__).with_name('vzorovy_sklad_test.csv')


class InventoryTests(unittest.TestCase):
    def test_import_sample_csv(self):
        items, stats = import_filament_csv(SAMPLE, [])
        self.assertEqual(stats, {'added': 5, 'updated': 0, 'overruns': 2, 'count': 5})
        self.assertAlmostEqual(sum(x.get('stock_grams',0) or 0 for x in items), 2650)
        by_id = {x['csv_id']: x for x in items}
        self.assertEqual(by_id['3']['price_kg'], 200.0)
        self.assertEqual(by_id['5']['stock_grams'], 50)
        self.assertIsNone(by_id['2']['price_kg'])
        self.assertEqual(by_id['2']['manufacturer'], 'SUNLU')
        self.assertEqual(by_id['5']['visibility'], 'Skrytý')

    def test_reimport_updates_stock_keeps_custom_prices(self):
        items, stats = import_filament_csv(SAMPLE, [])
        by_id = {x['csv_id']: x for x in items}
        by_id['2']['price_kg'] = 455.0
        by_id['2']['price_is_custom'] = True
        by_id['3']['price_kg'] = 700.0  # systémová cena musí zvítězit nad starým neuloženým číslem
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp, 'new.csv')
            text = SAMPLE.read_text(encoding='utf-8-sig')
            text = text.replace('2;Glow Zelená;PETG;SUNLU;800;', '2;Glow Zelená;PETG;SUNLU;620;')
            path.write_text(text, encoding='utf-8-sig')
            next_items, next_stats = import_filament_csv(path, items)
        by_id = {x['csv_id']: x for x in next_items}
        self.assertEqual(len(next_items), 5)
        self.assertEqual(next_stats['updated'], 5)
        self.assertEqual(by_id['2']['stock_grams'], 620)
        self.assertEqual(by_id['2']['price_kg'], 455.0)
        self.assertEqual(by_id['3']['price_kg'], 200.0)

    def test_overrun_custom_price_is_preserved(self):
        items, _ = import_filament_csv(SAMPLE, [])
        row = next(i for i in items if i['csv_id'] == '3')
        row['price_kg'] = 215
        row['price_is_custom'] = True
        again, _ = import_filament_csv(SAMPLE, items)
        self.assertEqual(next(i for i in again if i['csv_id'] == '3')['price_kg'], 215)

    def test_fixed_price_and_quantity(self):
        j = PrintJob('a','test','test.gcode',1,[],3600,
                     [Filament(1,'PETG','#AAAABB',100,price_kg=300)],quantity=3,
                     coefficient=1.5,price_mode='fixed',fixed_unit_price=145)
        total = j.totals(Rates())
        self.assertAlmostEqual(total['base'], 3 * (30 + 10 + 2))
        self.assertAlmostEqual(total['price'], 435)
        self.assertAlmostEqual(total['profit'], 435-126)
        j.fixed_unit_price = 10
        self.assertLess(j.totals(Rates())['profit'], 0)

    def test_stock_across_jobs_without_changing_inventory(self):
        items, _ = import_filament_csv(SAMPLE, [])
        j1 = PrintJob('a','test1','',1,[],3600, [Filament(1,'PLA','#FFFFFF',300,catalog_id='3')],quantity=2)
        j2 = PrintJob('b','test2','',1,[],3600, [Filament(1,'PLA','#FFFFFF',90,catalog_id='3')])
        balance = stock_balances([j1,j2],items)['3']
        self.assertEqual(balance, {'stock':600, 'used':690, 'remaining':-90})
        self.assertEqual(next(x for x in items if x['csv_id']=='3')['stock_grams'], 600)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp,'stock.3dk.json')
            save_project(path,'Proj',Rates(catalog=items),[j1,j2])
            _, loaded_rates, loaded_jobs = open_project(path)
            self.assertEqual(loaded_jobs[0].filaments[0].catalog_id,'3')
            self.assertEqual(loaded_rates.catalog[0]['csv_id'], '5')

    def test_invalid_headers_fail_without_partial_update(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp,'bad.csv')
            path.write_text('material;barva\nPLA;černá\n',encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'Chybí sloupce'):
                import_filament_csv(path, [{'name':'A','material':'PLA','price_kg':300}])

if __name__ == '__main__':
    unittest.main(verbosity=2)
