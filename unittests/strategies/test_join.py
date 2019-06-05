import unittest
from testing.strategies.generic import Strategy, CompoundStrategy


class JoinStrategies(unittest.TestCase):

    def test_strategy_plus_strategy(self):
        a = Strategy()
        b = Strategy()
        c = a + b
        self.assertTrue(isinstance(c, CompoundStrategy))  # check correct object
        self.assertEqual(c.strategies[0], a)  # check order
        self.assertEqual(c.strategies[1], b)  # check order

    def test_compound_plus_strategy(self):
        cs1 = CompoundStrategy()
        a = Strategy()
        cs2 = CompoundStrategy(a)
        b = Strategy()

        cs3 = cs1 + a

        self.assertNotEqual(cs3, cs1)
        self.assertEqual(cs3.strategies[0], a)

        self.assertEqual(len(cs2.strategies), 1)
        cs2 += b
        self.assertEqual(len(cs2.strategies), 2)

    def test_compound_plus_compund(self):
        a = Strategy()
        b = Strategy()
        cs1 = CompoundStrategy(a)
        cs2 = CompoundStrategy(b)
        cs3 = CompoundStrategy(a)

        cs3 += cs2 + cs1
        cs4 = cs1 + cs2

        self.assertEqual(cs3.strategies[0], a)
        self.assertEqual(cs3.strategies[1], b)
        self.assertEqual(cs3.strategies[2], a)

        self.assertNotEqual(cs3, cs2)
        self.assertNotEqual(cs4, cs1)
        self.assertNotEqual(cs4, cs2)

        self.assertEqual(cs4.strategies[0], a)
        self.assertEqual(cs4.strategies[1], b)



