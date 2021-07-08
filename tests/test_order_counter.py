# https://realpython.com/pytest-python-testing/

import sys
sys.path.append('.')

import pytest
from grid_trade.orders import OrderCounter, OrderSide


class TestOrderCounter:

    def setup_method(self, method):
        pass

    def test_buy(self):
        c = OrderCounter()
        assert isinstance(c, dict)

        assert c.total_of(OrderSide.Buy) == 0

        c.increase(side=OrderSide.Buy)
        assert c.total == 1
        assert c.total_of(OrderSide.Buy) == 1

        c.increase(side=OrderSide.Sell)
        c.increase(side=OrderSide.Sell)
        assert c.total == 3

        assert "+1" in c.preview and "-2" in c.preview

        total = OrderCounter()

        total.increase(side=OrderSide.Buy)
        # total.increase(side="buy")

        assert total.total == 1
        total.merge(c)
        assert "+2" in total.preview and "-2" in total.preview



if __name__ == '__main__':
    # https://stackoverflow.com/a/41616391/1938012
    retcode = pytest.main(['-x', __file__])
    # retcode = pytest.main(['-x', 'tests/test_order_stack.py'])
