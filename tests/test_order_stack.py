# https://realpython.com/pytest-python-testing/

import sys
sys.path.append('.')

import pytest
from grid_trade.orders import OrderManager, OrderSide

import logging
from utils import setup_logging
# Hmmm, logging not working in tests?
setup_logging(level=logging.DEBUG)

OrderStack = OrderManager.OrderStack

class TestOrderStack:

    def setup_method(self, method):
        self.om: OrderManager = self.get_om()

    @staticmethod
    def get_om():
        pair = 'eth_jpy'

        additional_info = {
            'pair': pair,
        }
        price_interval=100
        unit_amount=0.2
        grid_num=100
        order_limit=6
        om = OrderManager(price_interval=price_interval, unit_amount=unit_amount,
                        grid_num=grid_num,order_limit=order_limit, additional_info=additional_info)        
        return om

    def test_buy(self):
        init_price = 10000

        stack = self.om.buy_stack
        stack.prepare_init(init_price=init_price)

        assert len(stack.all_orders) == 3
        assert stack.best_order.price == 9900
        assert stack.worst_order.price == 9700
        assert [o.price for o in stack.all_orders] == [9900, 9800, 9700]
        
        assert list(stack.get_price_grid(10000, direction='outer', count=3)) == [10000, 9900, 9800]
        assert list(stack.get_price_grid(10000, direction='inner', count=3)) == [10000, 10100, 10200]
        assert list(stack.get_price_grid(10002, direction='outer', count=3)) == [10000, 9900, 9800]
        assert list(stack.get_price_grid(9999, direction='inner', count=3)) == [10000, 10100, 10200]

        stack.refill_orders(direction='outer')
        assert [o.price for o in stack.all_orders] == [9900, 9800, 9700, 9600]

        stack.refill_orders(direction='inner')
        assert [o.price for o in stack.all_orders] == [10000, 9900, 9800, 9700, 9600]
        
        stack.refill_orders(direction='inner', count=2)
        assert [o.price for o in stack.all_orders] == [10200, 10100, 10000, 9900, 9800, 9700, 9600]
        
    def test_sell(self):
        init_price = 10000

        stack = self.om.sell_stack
        stack.prepare_init(init_price=init_price)

        assert len(stack.all_orders) == 3
        assert stack.best_order.price == 10100
        assert stack.worst_order.price == 10300
        assert [o.price for o in stack.all_orders] == [10100, 10200, 10300]
        
        assert list(stack.get_price_grid(10000, direction='outer', count=3)) == [10000, 10100, 10200]
        assert list(stack.get_price_grid(10000, direction='inner', count=3)) == [10000, 9900, 9800]
        assert list(stack.get_price_grid(10002, direction='outer', count=3)) == [10100, 10200, 10300]
        assert list(stack.get_price_grid(9999, direction='inner', count=3)) == [9900, 9800, 9700]

        stack.refill_orders(direction='outer')
        assert [o.price for o in stack.all_orders] == [10100, 10200, 10300, 10400]

        stack.refill_orders(direction='inner')
        assert [o.price for o in stack.all_orders] == [10000, 10100, 10200, 10300, 10400]
        
        stack.refill_orders(direction='inner', count=2)
        assert [o.price for o in stack.all_orders] == [9800, 9900, 10000, 10100, 10200, 10300, 10400]
        


if __name__ == '__main__':
    # https://stackoverflow.com/a/41616391/1938012
    retcode = pytest.main(['-x', __file__])
    # retcode = pytest.main(['-x', 'tests/test_order_stack.py'])
