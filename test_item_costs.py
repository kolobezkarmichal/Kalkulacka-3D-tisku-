"""Regrese: každá položka má vlastní náklady, cenu a rozdíl i při pevné ceně."""
import unittest
from engine import Filament, PrintJob, Rates, project_totals


class ItemCostsTests(unittest.TestCase):
    @staticmethod
    def job(item_id: str, qty: int, mode: str = 'coefficient', fixed: float = 0):
        return PrintJob(
            id=item_id, name='Model ' + item_id, path=item_id + '.gcode.3mf',
            plate=1, objects=[item_id], time_seconds=3600,
            filaments=[Filament(1, 'PLA', '#FFFFFF', 100, price_kg=300)],
            quantity=qty, coefficient=1.5, price_mode=mode, fixed_unit_price=fixed,
        )

    def test_three_individual_jobs_equal_project_totals(self):
        rates = Rates(amortization_per_hour=10, energy_per_hour=2)
        jobs = [self.job('a', 1), self.job('b', 2), self.job('c', 3)]
        for job in jobs:
            t = job.totals(rates)
            self.assertAlmostEqual(t['price'] - t['base'], t['profit'])
            self.assertAlmostEqual(t['base'], 42 * job.quantity)
        overall = project_totals(jobs, rates)
        self.assertAlmostEqual(overall['base'], 42 * 6)
        self.assertAlmostEqual(overall['price'], 63 * 6)
        self.assertAlmostEqual(overall['profit'], 21 * 6)

    def test_fixed_price_can_mean_loss(self):
        rates = Rates(amortization_per_hour=10, energy_per_hour=2)
        job = self.job('fixed', 4, mode='fixed', fixed=30)
        t = job.totals(rates)
        self.assertAlmostEqual(t['base'], 168)
        self.assertAlmostEqual(t['price'], 120)
        self.assertAlmostEqual(t['profit'], -48)


if __name__ == '__main__':
    unittest.main(verbosity=2)
