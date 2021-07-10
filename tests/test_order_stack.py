# https://realpython.com/pytest-python-testing/

import sys
sys.path.append('.')

import pytest
from grid_trade.orders import OrderManager, OrderSide, OrderStatus

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

    def test_refill_orders_on_buy_stack(self):
        init_price = 10000

        stack = self.om.buy_stack
        stack.prepare_init(init_price=init_price)

        assert len(stack.all_orders) == 3
        assert stack.best_order_of_all.price == 9900
        assert stack.worst_order_of_all.price == 9700
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
        
    def test_refill_orders_on_sell_stack(self):
        init_price = 10000

        stack = self.om.sell_stack
        stack.prepare_init(init_price=init_price)

        assert len(stack.all_orders) == 3
        assert stack.best_order_of_all.price == 10100
        assert stack.worst_order_of_all.price == 10300
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
        

    def test_refill_stack_by_paring_on_sell_stack(self):
        init_price = 10000

        stack = self.om.sell_stack
        stack.prepare_init(init_price=init_price)

        buy_stack = self.om.buy_stack
        buy_stack.prepare_init(init_price=init_price)

        # stack.refill_stack_by_pairing(traded_orders=[buy_stack.best_order])
        # assert [o.price for o in stack.all_orders] == [10000, 10100, 10200, 10300]
        # assert stack.best_order.status == OrderStatus.ToCreate

        filled_count = stack.refill_stack_by_pairing(traded_orders=buy_stack.all_orders)
        assert [o.price for o in stack.all_orders] == [9800, 9900, 10000, 10100, 10200, 10300]
        assert filled_count == 3


if __name__ == '__main__':
    import os
    from utils import setup_logging
    log_file_path = os.path.basename(__file__) + '.log'
    setup_logging(log_file_path='./logs/testing/' + log_file_path, backup_count=1)
    # https://stackoverflow.com/a/41616391/1938012
    retcode = pytest.main(['-x', __file__])
