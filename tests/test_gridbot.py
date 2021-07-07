# https://realpython.com/pytest-python-testing/

import sys
sys.path.append('.')

import requests
import pytest
import python_bitbankcc
from grid_trade.base import GridBot
from exchanges import Bitbank
import logging
from utils import setup_logging

# Hmmm, logging not working in tests?
setup_logging(level=logging.DEBUG)

OrderStatus = Bitbank.OrderStatus


source = {
    'prices': [
        10150,
        10250,
        10450,
    ],
    'get_orders_info':[
        {'orders': [
            {'order_id': 2, 'status': OrderStatus.FullyFilled },
            ],
        },
        {'orders': [
            {'order_id': 3, 'status': OrderStatus.FullyFilled },
            {'order_id': 4, 'status': OrderStatus.FullyFilled },
            ],
        },
        {'orders': [
            {'order_id': 5, 'status': OrderStatus.FullyFilled },
            {'order_id': 8, 'status': OrderStatus.FullyFilled },
            ],
        },
    ],
}


class BitbankPublicMock:
    def __init__(self) -> None:
        self.ticker_count = -1

    def get_ticker(self, pair):
        self.ticker_count += 1
        price = source['prices'][self.ticker_count]
        ticker_data = {
            'last': price,
            'buy': price,
            'sell': price,
        }
        return ticker_data

class BitbankPrivateMock:
    def __init__(self, *args, **kwargs) -> None:
        self.order_id = -1
        self.order_index = -1

    def order(self, pair, price, amount, side, order_type, post_only = False):
        self.order_id += 1
        order_data = {
            'order_id': self.order_id
            }
        order_data['pair'] = 'eth_jpy'
        order_data['ordered_at'] = 0
        return order_data

    def get_orders_info(self, pair, order_ids):
        self.order_index += 1
        orders_data = source['get_orders_info'][self.order_index]
        for od in orders_data['orders']:
            od['status'] = od['status'].value
        return orders_data

    def cancel_orders(self, pair, order_ids):
        return {'orders': []}


class TestGridBot:
    @pytest.fixture
    def mock_bitbank(self, monkeypatch):
        monkeypatch.setattr(requests, 'get', None)
        monkeypatch.setattr(requests, 'post', None)
        monkeypatch.setattr(python_bitbankcc, 'public', BitbankPublicMock)
        monkeypatch.setattr(python_bitbankcc, 'private', BitbankPrivateMock)

    def test_ticker(self, mock_bitbank):
        pub = python_bitbankcc.public()
        res = pub.get_ticker(pair='abc')
        print(res)

        prv = python_bitbankcc.private()
        res = prv.get_orders_info(pair='btc_jpy', order_ids=[])
        assert res['orders'][0]['order_id'] == 2

    def test_params(self, mock_bitbank):
        init_price = 100
        init_quote = 700
        init_base = 10
        support = 50
        grid_num = 10
        fee = -0.0002

        params = GridBot.Parameter.calc_grid_params_by_support(init_base, init_quote, init_price, support, grid_num=grid_num, fee=fee)
        assert params.price_interval == 10

    # @pytest.mark.skip(reason="Only works by clicking the `Run Test` button in VSCode")
    def test_bot(self, mock_bitbank):
        init_price = 10000
        init_quote = 700
        init_base = 10
        price_interval = 100
        grid_num = 10
        fee = -0.0002
        pair = 'eth_jpy'

        additional = {
            "pair": pair,
        }

        param = GridBot.Parameter.calc_grid_params_by_interval(init_base, init_quote, init_price, 
                                        price_interval=price_interval, pair=pair, grid_num=grid_num, fee=fee)
        bitbank = Bitbank(pair=pair)
        bitbank.max_order_count = 4

        bot = GridBot(bitbank)
        bot.init_and_start(param=param, additional_info=additional)

        assert len(bot.om.active_orders) == 4

        self.check_sides(bot, 2, 2)
        self.check_prices(bot, [9800, 9900, 10100, 10200])
        self.check_ids(bot, [1, 0, 2, 3])
        
        bot.om.balance_threshold = 2
        bot.sync_order_status()
        self.check_sides(bot, 2, 2)
        self.check_prices(bot, [9900, 10000, 10200, 10300])
        self.check_ids(bot, [0, 4, 3, 5])

        bot.sync_order_status()
        self.check_sides(bot, 2, 2)
        self.check_prices(bot, [10000, 10100, 10300, 10400])
        # 0 4 . 3 5
        # 0 _   _.5
        # 0 ? ? _.5
        # x ? ? _.5 ?
        #   7 6 _.5 8
        self.check_ids(bot, [7, 6, 5, 8])

        bot.sync_order_status()
        self.check_sides(bot, 3, 2)
        self.check_prices(bot, [10100, 10200, 10300, 10500, 10600])
        # 7 6 . 5 8
        # 7 6 . _ _
        # 7 6 ? ? _.?
        #   6 ? ? _.? ?
        #   6 10 9 _.11 12
        self.check_ids(bot, [6, 10, 9, 11, 12])


    @staticmethod
    def check_sides(bot, buy, sell):
        exp_sides = ['Buy'] *  buy + ['Sell'] * sell
        sides = [o.side.name for o in [*bot.om.buy_stack.active_orders, *bot.om.sell_stack.active_orders]]
        assert sides == exp_sides

    @staticmethod
    def check_prices(bot, exp_prices):
        prices = sorted([o.price for o in bot.om.active_orders])
        assert prices == exp_prices        

    @staticmethod
    def check_ids(bot, exp_ids):
        orders = sorted( bot.om.active_orders, key=lambda o: o.price)
        ids = [o.order_id for o in orders]
        assert ids == exp_ids


if __name__ == '__main__':
    # No idea why running this directly will fail the test
    #   whereas, running by click the `Run Test` button (VSCode) in source code succeeds
    retcode = pytest.main(['-x', __file__])
