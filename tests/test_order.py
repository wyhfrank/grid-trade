# https://realpython.com/pytest-python-testing/

import sys
sys.path.append('.')

import pytest
from grid_trade.orders import Order, OrderSide
from utils import init_formatted_properties


class TestOrder:

    def setup_method(self, method):
        pass

    def test_precision(self):
        price_precision = 1
        amount_precision = 2

        pair = 'btc_jpy'
        data = {
            'price': 1.23456,
            'pair': pair,
            'amount': 1.23456,
            'side': OrderSide.Buy,
        }
        o = Order.from_dict(data)

        assert o.price_s == '1'
        assert o.amount_s == '1.2346'
        assert o.cost == 2
        assert "2.0" in o.short


        Order.set_precision(price_precision=price_precision, amount_precision=amount_precision)
        init_formatted_properties(Order)

        assert o.price_s == '1.2'
        assert o.amount_s == '1.23'


if __name__ == '__main__':
    import os
    from utils import setup_logging
    log_file_path = os.path.basename(__file__) + '.log'
    setup_logging(log_file_path='./logs/testing/' + log_file_path, backup_count=1)
    # https://stackoverflow.com/a/41616391/1938012
    retcode = pytest.main(['-x', __file__])
