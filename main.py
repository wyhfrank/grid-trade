"""
1. Decide the grid setup base on the input parameters (cell size, boundary)
2. Make limit orders and record the order ids
3. Check the orders periodically, if they are eaten, put an oppsite order on the oppsite side (make sure only one order is eaten)
  3.1 Handle situations where multiple orders were taken since last update
4. Calculate statistics and send notifications: earn rate, yearly earn rate
"""

import time
from grid_trade import GridBot
from exchanges import Bitbank
from utils import read_config
from db.manager import FireStoreManager


def run_grid_bot():
    fsm = FireStoreManager()
    config = read_config()
    api_key = config['api']['key']
    api_secret = config['api']['secret']

    bot_config = config['grid_bot']
    pair = bot_config['pair']
    grid_num = bot_config['grid_num']
    base_usage = bot_config['base_usage']
    quote_usage = bot_config['quote_usage']
    price_interval = bot_config['price_interval']
    check_interval = bot_config['check_interval']
    order_limit = bot_config['order_limit']

    user = config['user']['name']
    
    ex = Bitbank(pair=pair, api_key=api_key, api_secret=api_secret, max_order_count=order_limit)

    additional_info = {
        'pair': pair,
        'user': user,
        'exchange': ex.name,
        'db': fsm,  # Comment this line out if you don't need to store data to db
    }

    init_price = ex.get_mid_price()
    assets = ex.get_assets()
    init_base = assets['base_amount'] * base_usage
    init_quote = assets['quote_amount'] * quote_usage

    bot = GridBot(exchange=ex)
    param = bot.Parameter.calc_grid_params_by_interval(init_base=init_base, init_quote=init_quote, init_price=init_price,
                                            price_interval=price_interval, grid_num=grid_num, fee=ex.fee)

    print(f"Run with:", param)

    bot.init_and_start(param=param, additional_info=additional_info)
    try:
        while True:
            start = time.time()
            bot.sync_order_status()
            # bot.om.print_stacks()

            elapsed = time.time() - start
            to_sleep = check_interval - elapsed
            if to_sleep > 0:
                print(f"Sleep for: {to_sleep:.3f}s")
                time.sleep(to_sleep)
    except KeyboardInterrupt:
        print(f"On KeyboardInterrupt, cancel all orders and stop the bot...")
        bot.cancel_and_stop()


if __name__ == "__main__":
    run_grid_bot()
