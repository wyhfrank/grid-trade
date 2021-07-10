# https://realpython.com/pytest-python-testing/

import sys
sys.path.append('.')

import requests
import pytest
import python_bitbankcc
from grid_trade.base import GridBot
from grid_trade.orders import Order, OrderSide
from exchanges import Bitbank
import logging
from utils import setup_logging

logger = logging.getLogger(__name__)

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
            {'order_id': 6, 'status': OrderStatus.FullyFilled },
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
        orders = [{'order_id': oid, 'status': OrderStatus.CancelledUnfilled.value} for oid in order_ids]
        return {'orders': orders}


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
    
    def test_irregular_price(self, mock_bitbank):
        bot, param, additional = self.create_bot(max_order_count = 4)
        
        bot.init_and_start(param=param, additional_info=additional)

        amount = 0.1
        order_price = 10000
        price_info = {'price': 9900}

        side = OrderSide.Buy
        o = Order(price=order_price, amount=amount, side=side, pair='')

        price_info['best_bid'] = 8900
        price_info['best_ask'] = 9100
        res = bot._check_irregular_price(order=o, price_info=price_info)
        assert not res

        price_info['best_bid'] = 10100
        price_info['best_ask'] = 10200
        res = bot._check_irregular_price(order=o, price_info=price_info)
        assert 'sell' in res and '---: 10100' in res
        logger.warning(res)

        side = OrderSide.Sell
        o = Order(price=order_price, amount=amount, side=side, pair='')

        price_info['best_bid'] = 10100
        price_info['best_ask'] = 10200
        res = bot._check_irregular_price(order=o, price_info=price_info)
        assert not res

        price_info['best_bid'] = 8900
        price_info['best_ask'] = 9100
        res = bot._check_irregular_price(order=o, price_info=price_info)
        assert 'buy' in res and '+++: 9900' in res
        logger.warning(res)


    @classmethod
    def create_bot(cls, max_order_count=4):
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
        bitbank.max_order_count = max_order_count
        bot = GridBot(bitbank)
        return bot, param, additional


    @pytest.mark.skip(reason="Only works by clicking the `Run Test` button in VSCode")
    def test_bot(self, mock_bitbank):
        bot, param, additional = self.create_bot(max_order_count = 4)
        
        bot.init_and_start(param=param, additional_info=additional)

        assert len(bot.om.active_orders) == 4

        self.check_sides(bot, 2, 2)
        self.check_prices(bot, [9800, 9900, 10100, 10200])
        self.check_ids(bot, [1, 0, 2, 3])
        
        bot.om.balance_threshold = 2
        bot.sync_and_adjust()
        self.check_sides(bot, 2, 2)
        self.check_prices(bot, [9900, 10000, 10200, 10300])
        self.check_ids(bot, [0, 4, 3, 5])

        bot.sync_and_adjust()
        # self.check_sides(bot, 2, 2)
        # self.check_prices(bot, [10000, 10100, 10300, 10400])
        # 0 4 . 3 5
        # 0 _   _.5
        # 0 ? ? _.5
        # x ? ? _.5 ?
        #   7 6 _.5 8

        self.check_sides(bot, 1, 2)
        self.check_prices(bot, [9900, 10100, 10300])
        # 0 4 . 3 5
        # 0   - _.5
        # 0   6  .5
        self.check_ids(bot, [0, 6, 5])

        bot.sync_and_adjust()
        self.check_sides(bot, 2, 1)
        self.check_prices(bot, [10000, 10200, 10400])
        # 0   6   5 .
        # 0   _   _ .
        # 0 ?   ?   .
        # x ?   ?    ?
        #   8   7    9
        self.check_ids(bot, [8, 7, 9])


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
    import os
    from utils import setup_logging
    log_file_path = os.path.basename(__file__) + '.log'
    setup_logging(log_file_path='./logs/testing/' + log_file_path, backup_count=1)
    # https://stackoverflow.com/a/41616391/1938012
    retcode = pytest.main(['-x', __file__])
