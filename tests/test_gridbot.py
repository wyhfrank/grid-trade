# https://realpython.com/pytest-python-testing/

import requests
import pytest
import python_bitbankcc
from grid_trade.base import GridBot
from exchanges import Bitbank

source = {
    'ticker': [
        {
        'last': 115,
        'sell': 116,
        'buy': 114,
        },
    ],
    'get_orders_info':[
        {'orders': [
            {'order_id':1002, 'status': 'FULLY_FILLED' },
            # {'order_id':1001, 'status': 'UNFILLED' },
            ],
        },
    ],
}


class BitbankPublicMock:
    def __init__(self) -> None:
        self.ticker_count = -1

    def get_ticker(self, pair):
        self.ticker_count += 1
        return source['ticker'][self.ticker_count]

class BitbankPrivateMock:
    def __init__(self) -> None:
        self.order_id = 999
        self.order_index = -1

    def order(self, pair, price, amount, side, order_type, post_only = False):
        self.order_id += 1
        return {
            'order_id': self.order_id
            }

    def get_orders_info(self, pair, order_ids):
        self.order_index += 1
        # TODO
        self.order_index = 0
        return source['get_orders_info'][self.order_index]

    def cancel_orders(self, pair, order_ids):
        pass


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
        assert res['orders'][0]['order_id'] == 1002

    def test_params(self, mock_bitbank):
        init_price = 100
        init_quote = 700
        init_base = 10
        support = 50
        grid_num = 10
        fee = -0.0002

        params = GridBot.Parameter.calc_grid_params_by_support(init_base, init_quote, init_price, support, grid_num=grid_num, fee=fee)
        assert params.price_interval == 10

    @staticmethod
    def check_prices(bot, exp_prices):
        prices = sorted([o.price for o in bot.om.active_orders])
        assert prices == exp_prices        

    @staticmethod
    def check_sides(bot, exp_sides):
        sides = [o.side.name for o in [*bot.om.buy_stack.active_orders, *bot.om.sell_stack.active_orders]]
        assert sides == exp_sides
    
    def test_bot(self, mock_bitbank):
        init_price = 100
        init_quote = 700
        init_base = 10
        support = 50
        grid_num = 10
        fee = -0.0002
        pair = 'eth_jpy'

        param = GridBot.Parameter.calc_grid_params_by_support(init_base, init_quote, init_price, support, grid_num=grid_num, fee=fee)
        bitbank = Bitbank(pair=pair)
        bitbank.max_order_count = 4

        bot = GridBot(bitbank)
        bot.init_and_start(param=param)

        assert len(bot.om.active_orders) == 4

        self.check_sides(bot, ['Buy'] * 2 + ['Sell'] * 2)
        self.check_prices(bot, [80, 90, 110, 120])
        
        bot.om.balance_threshold = 0
        bot.sync_order_status()

        self.check_sides(bot, ['Buy'] * 2 + ['Sell'] * 2)
        self.check_prices(bot, [90, 100, 120, 130])

        



    # def test_bot(self):
    #     pair = 'eth_jpy'

    #     init_price = 35393
    #     init_quote = 50000
    #     init_base = init_quote / init_price
    #     support = 24756
    #     fee = -0.0002
    #     grid_num = 100

    #     init_price = 100
    #     init_quote = 700
    #     init_base = 10
    #     support = 50
    #     grid_num = 10    

    #     param = GridBot.Parameter.calc_grid_params_by_support(init_base, init_quote, init_price, support, grid_num=grid_num, fee=fee)

    #     bitbank = Bitbank(pair=pair)
    #     bot = GridBot(bitbank)
    #     bot.init_and_start(param=param)

    #     # print(bot.om.active_orders)
    #     bot.om.print_stacks()

    #     bot.sync_order_status()
    #     bot.om.print_stacks()        
        

        