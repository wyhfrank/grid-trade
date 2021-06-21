"""
1. Decide the grid setup base on the input parameters (cell size, boundary)
2. Make limit orders and record the order ids
3. Check the orders periodically, if they are eaten, put an oppsite order on the oppsite side (make sure only one order is eaten)
  3.1 Handle situations where multiple orders were taken since last update
4. Calculate statistics and send notifications: earn rate, yearly earn rate
"""

from grid_trade import GridBot
from exchanges import Bitbank


def test_params():
    init_price = 35393
    init_quote = 50000
    init_base = init_quote / init_price
    support = 24756
    grid_num = 100

    # init_price = 100
    # init_quote = 700
    # init_base = 10
    # support = 50
    # grid_num = 10

    for gn in [10, 20, 30, 50, 80 , 100]:
        grid_num = gn
        params = GridBot.Parameter.calc_grid_params(init_base, init_quote, init_price, support, grid_num=grid_num, fee=0.0008)
        print(params)

def test_bot():
    pair = 'eth_jpy'

    init_price = 35393
    init_quote = 50000
    init_base = init_quote / init_price
    support = 24756
    fee = -0.0002
    grid_num = 100

    init_price = 100
    init_quote = 700
    init_base = 10
    support = 50
    grid_num = 10    

    param = GridBot.Parameter.calc_grid_params(init_base, init_quote, init_price, support, grid_num=grid_num, fee=fee)

    bitbank = Bitbank(pair=pair)
    bot = GridBot(bitbank)
    bot.init_grid(param=param)

    # print(bot.om.active_orders)
    bot.om.print_stacks()

    bot.sync_order_status()
    bot.om.print_stacks()


if __name__ == "__main__":
    # test_params()
    test_bot()
