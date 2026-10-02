import unittest
from decimal import Decimal


class Quotes:
    def __init__(self, fx='5'):
        self.fx = Decimal(fx)

    def get(self, book, sheet, cell):
        return {'F1': self.fx, 'H1': Decimal('1.4'), 'I1': Decimal('1.3')}[cell]


class DirectMonthlyCostTests(unittest.TestCase):
    def row(self, **changes):
        row = {
            'kind': 'direct_monthly_cost',
            'id': 'sms-direct-2026-09-g004',
            'period': '2026-09',
            'date': '2026-09',
            'site': 'CreditoParaVeiculo',
            'manager': 'joe',
            'currency': 'BRL',
            'amount': '15972.96',
            'label': 'SMS Funnel · consumo direto G004',
            'authority': '1555422806940983327',
            'source': 'Planilhas MGS corrigidas maio–setembro 2026',
        }
        row.update(changes)
        return row

    def sites(self):
        return [{'name': 'CreditoParaVeiculo', 'status': 'ATIVO'}]

    def test_fixed_brl_cost_becomes_monthly_closing_fact(self):
        from direct_costs import direct_monthly_costs
        rows = direct_monthly_costs([self.row()], self.sites(), Quotes(), '2026-09')
        self.assertEqual(len(rows), 1)
        fact = rows[0]
        self.assertEqual(fact['manager'], 'joe')
        self.assertEqual(fact['date'], '2026-09')
        self.assertTrue(fact['monthly_closing'])
        self.assertTrue(fact['spend_only'])
        self.assertEqual(fact['cost_currency'], 'BRL')
        self.assertEqual(fact['cost_amount'], '15972.96')
        self.assertEqual(fact['spend'], Decimal('-3194.592'))
        self.assertEqual(fact['profit'], Decimal('-3194.592'))
        self.assertEqual(fact['gross'], Decimal('0'))

    def test_six_allocations_close_exactly_in_brl_and_keep_mgs_no_commission(self):
        from direct_costs import direct_monthly_costs
        amounts = [('george','12449.04'),('SEM_COMISSAO','2729.36'),('isliago','30749.04'),('joe','15972.96'),('kelly','41009.60'),('nicolas','2759.60')]
        source = [self.row(id=f'sms-direct-2026-09-{i}', manager=m, amount=a) for i,(m,a) in enumerate(amounts)]
        rows = direct_monthly_costs(source, self.sites(), Quotes('5.2'), '2026-09')
        self.assertEqual(sum((abs(x['profit'])*Decimal('5.2') for x in rows), Decimal('0')), Decimal('105669.60'))
        self.assertEqual([x['manager'] for x in rows].count('SEM_COMISSAO'), 1)

    def test_scope_and_identity_fail_closed(self):
        from direct_costs import direct_monthly_costs
        bad = [
            {'period':'2026-08'}, {'date':'2026-09-30'}, {'site':'Other'},
            {'manager':'unknown'}, {'currency':'USD'}, {'amount':'0'},
            {'amount':'-1'}, {'authority':'not-a-message'}, {'id':'bad id'},
        ]
        for change in bad:
            with self.subTest(change=change), self.assertRaises(ValueError):
                direct_monthly_costs([self.row(**change)], self.sites(), Quotes(), '2026-09')

    def test_worker_integrates_direct_cost_into_cash_and_manager_graph(self):
        from worker import run
        row = self.row(amount='100.00')
        before = run({'period': '2026-09', 'additions': []})
        after = run({'period': '2026-09', 'additions': [row]})
        fact = next(x for x in after['domain']['facts'] if x['id'] == row['id'])
        fx = Decimal(str(after['results']['principal|Agosto 2026|F1']['actual']))
        self.assertEqual((abs(fact['profit']) * fx).quantize(Decimal('0.01')), Decimal('100.00'))
        self.assertEqual(
            ((Decimal(str(before['domain']['cash']['spend'])) - Decimal(str(after['domain']['cash']['spend']))) * fx).quantize(Decimal('0.01')),
            Decimal('100.00'),
        )
        old = next(x for x in before['domain']['managers'] if x['manager'] == 'joe' and x['row'] == 12)
        new = next(x for x in after['domain']['managers'] if x['manager'] == 'joe' and x['row'] == 12)
        self.assertEqual(((Decimal(str(old['profit'])) - Decimal(str(new['profit']))) * fx).quantize(Decimal('0.01')), Decimal('100.00'))

    def test_duplicate_ids_rejected(self):
        from direct_costs import direct_monthly_costs
        row = self.row()
        with self.assertRaises(ValueError):
            direct_monthly_costs([row, dict(row)], self.sites(), Quotes(), '2026-09')


if __name__ == '__main__':
    unittest.main()
