import unittest
from decimal import Decimal as D
from expenses import compensation
class PayrollTests(unittest.TestCase):
 def test_floor_negative_profit(self):self.assertEqual(compensation(-100,5),-600)
 def test_low_rate(self):self.assertEqual(compensation(10000,5),-700)
 def test_high_boundary(self):self.assertEqual(compensation(20000,5),-2000)
 def test_floor_boundary(self):
  profit=D(3000)/D('.07')/5
  self.assertAlmostEqual(compensation(profit,5),D(-600),places=20)
if __name__=='__main__':unittest.main()
