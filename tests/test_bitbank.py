# https://realpython.com/pytest-python-testing/

import sys
sys.path.append('.')

import pytest
import time
import logging
from requests.exceptions import HTTPError
from exchanges import Bitbank
from utils import read_config, set_lvl_for_imported_lib

logger = logging.getLogger(__name__)

set_lvl_for_imported_lib()

class TestBitbank:

    def setup_method(self, method):
        config = read_config()
        api_key = config['api']['key']
        api_secret = config['api']['secret']
        pair = 'btc_jpy'
        self.bb = Bitbank(pair=pair, api_key=api_key, api_secret=api_secret)        

    def test_exceed_quota(self):
        start = time.time()
        try:
            for i in range(100):
                # info = self.bb.get_latest_prices()
                info = self.bb.get_assets()
        except HTTPError as e:
            logger.error(e)
        finally:
            end = time.time()
            elapsed = end - start
            logger.info(f"Elapsed: {elapsed:.3f} s")
        logger.info(info)

    @pytest.mark.skip
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

    @pytest.mark.skip
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

    @pytest.mark.skip
    def test_get_trade_history_btc(self):
        bb = self.bb
        pair = 'btc_jpy'
        desc_first = bb.get_trade_history(pair=pair, ascending=False, order_count=1)
        desc_20 = bb.get_trade_history(pair=pair, ascending=False, order_count=20)
        desc_200 = bb.get_trade_history(pair=pair, ascending=False, order_count=200)
        desc_all = bb.get_trade_history(pair=pair, ascending=False)

        assert desc_first.shape[0] == 1
        assert desc_first.iloc[0]['trade_id'] == 1156736034
        assert desc_20.iloc[0]['trade_id'] == 1156736034
        assert desc_20.shape[0] == 20
        assert desc_200.iloc[0]['trade_id'] == 1156736034
        assert desc_200.iloc[-1]['trade_id'] == 1136761179
        assert desc_200.shape[0] == 79
        assert desc_all.iloc[0]['trade_id'] == 1156736034
        assert desc_all.shape[0] == 79

        asc_first = bb.get_trade_history(pair=pair, ascending=True, order_count=1)
        asc_20 = bb.get_trade_history(pair=pair, ascending=True, order_count=20)
        asc_200 = bb.get_trade_history(pair=pair, ascending=True, order_count=200)
        asc_all = bb.get_trade_history(pair=pair, ascending=True)

        assert asc_first.shape[0] == 1
        assert asc_first.iloc[0]['trade_id'] == 1136761179
        assert asc_20.iloc[0]['trade_id'] == 1136761179
        assert asc_20.shape[0] == 20
        assert asc_200.iloc[0]['trade_id'] == 1136761179
        assert asc_200.iloc[-1]['trade_id'] == 1156736034
        assert asc_200.shape[0] == 79
        assert asc_all.iloc[0]['trade_id'] == 1136761179
        assert asc_all.shape[0] == 79

    def test_get_trade_history_eth(self):
        bb = self.bb
        
        pair = 'eth_jpy'
        # desc_20 = bb.get_trade_history(pair=pair, ascending=False, order_count=20)
        desc_all = bb.get_trade_history(pair=pair, ascending=False)

        # assert desc_20.iloc[0]['trade_id'] == 1156736034
        # assert desc_20.shape[0] == 20
        # assert desc_all.iloc[0]['trade_id'] == 1156736034
        assert desc_all.shape[0] >= 3238
        logger.info(desc_all.shape)
        return

        asc_20 = bb.get_trade_history(pair=pair, ascending=True, order_count=20)
        asc_all = bb.get_trade_history(pair=pair, ascending=True)

        assert asc_first.iloc[0]['trade_id'] == 1136761179
        assert asc_20.iloc[0]['trade_id'] == 1136761179
        assert asc_20.shape[0] == 20
        assert asc_all.iloc[0]['trade_id'] == 1136761179
        assert asc_all.shape[0] == 79

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
    setup_logging(log_file_path='./logs/testing/' + log_file_path, backup_count=1) # , file_level=logging.INFO
    # https://stackoverflow.com/a/41616391/1938012
    retcode = pytest.main(['-x', __file__])
