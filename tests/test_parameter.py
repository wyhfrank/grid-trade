# https://realpython.com/pytest-python-testing/

import sys
sys.path.append('.')

import pytest
import logging
from grid_trade import GridBot, set_precision

logger = logging.getLogger(__name__)


class TestParameter:

    def setup_method(self, method):
        pass

    def test_calculation(self):
        set_precision(price_precision=0, amount_precision=2)

        price_interval=5000.123456
        grid_num=100
        init_base = 0.123456
        init_quote = 90000.123456
        init_price = 257000.123456
        fee = -0.002
        pair = None
        param = GridBot.Parameter.calc_grid_params_by_interval(init_base=init_base, init_quote=init_quote, init_price=init_price,
                                                price_interval=price_interval, grid_num=grid_num, pair=pair, fee=fee)

        logger.info(param)

        assert param.init_base == 0.12
        assert param.init_quote == 90000
        assert param.price_interval == 5000
        assert param.init_quote_s == '90000'



if __name__ == '__main__':
    import os
    from utils import setup_logging
    log_file_path = os.path.basename(__file__) + '.log'
    setup_logging(log_file_path='./logs/testing/' + log_file_path, backup_count=1)
    # https://stackoverflow.com/a/41616391/1938012
    retcode = pytest.main(['-x', __file__])
