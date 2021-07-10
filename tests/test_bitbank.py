# https://realpython.com/pytest-python-testing/

import sys
sys.path.append('.')

import pytest
import logging
from exchanges import Bitbank
from utils import read_config

logger = logging.getLogger(__name__)


class TestBitbank:

    def setup_method(self, method):
        config = read_config()
        api_key = config['api']['key']
        api_secret = config['api']['secret']
        pair = 'btc_jpy'
        self.bb = Bitbank(pair=pair, api_key=api_key, api_secret=api_secret)        

    def test_get_prices(self):
        info = self.bb.get_latest_prices()

        fields_to_check = {
            'price': float,
            'best_ask': float,
            'best_bid': float,
            'spread': float,
            'mid_price': float,
        }
        for k, v in fields_to_check.items():
            assert isinstance(info[k], v)

    def test_basic_info(self):
        bb = self.bb

        to_check = {
            None: {
                'fee': -0.0002,
                'price_digits': 0,
                'amount_digits': 4,
            },
            'btc_jpy': {
                'fee': -0.0002,
                'price_digits': 0,
                'amount_digits': 4,
            },
            'eth_btc': {
                'fee': -0.0002,
                'price_digits': 8,
                'amount_digits': 4,
            },
        }

        for pair, exp_data in to_check.items():

            info = bb.get_basic_info(pair=pair)
            logger.info(f"Basic info for {pair}: {info}")
            assert info == exp_data


    @pytest.mark.skip("This happens a lot: Exception: エラーコード: 20001 内容: API認証に失敗しました")
    def test_create_and_cancel_order(self):
        import time
        from grid_trade.orders import Order, OrderSide
        
        pair = 'btc_jpy'
        data = {
            'price': 10000,
            'pair': pair,
            'amount': 0.001,
            'side': OrderSide.Buy,
        }
        o = Order.from_dict(data)
        bb = self.bb

        logger.info(f"Creating order: {o}")
        order = bb.create_order(o)
        assert order == o
        assert isinstance(o.order_id, int)

        logger.info(f"After creating order: {o}")
        time.sleep(2)

        logger.info(f"Cancelling order: {o}")
        orders_data = bb.cancel_orders(order_ids=[o.order_id])

        assert len(orders_data) == 1
        order_data = orders_data[0]
        assert order_data['order_id'] == o.order_id
        assert bb.is_order_cancelled(order_data=order_data)



if __name__ == '__main__':
    import os
    from utils import setup_logging
    log_file_path = os.path.basename(__file__) + '.log'
    setup_logging(log_file_path='./logs/testing/' + log_file_path, backup_count=1)
    # https://stackoverflow.com/a/41616391/1938012
    retcode = pytest.main(['-x', __file__])
