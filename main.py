"""
1. Decide the grid setup base on the input parameters (cell size, boundary)
2. Make limit orders and record the order ids
3. Check the orders periodically, if they are eaten, put an oppsite order on the oppsite side (make sure only one order is eaten)
  3.1 Handle situations where multiple orders were taken since last update
4. Calculate statistics and send notifications: earn rate, yearly earn rate
"""


import sys
import time
import requests
import logging
from grid_trade import GridBot
from exchanges import Bitbank
from utils import read_config, config_logging
from db.manager import FireStoreManager
from notification import Discord

logger = logging.getLogger(__name__)


def main():
    if len(sys.argv) > 1:
        config_file = sys.argv[1]
    else:
        config_file = './configs/config.yml'
    run_grid_bot(config_file)


def run_grid_bot(config_file):
    config = read_config(fn=config_file)
    config_logging(config.get('logging', None))

    fsm = setup_fsm(config=config)

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
    reset_interval_sec = bot_config['reset_interval'] * 60 * 60

    user = config['user']['name']

    discord_info_webhook = config['discord']['info']
    discord_error_webhook = config['discord']['error']
    discord = Discord(info_webhook=discord_info_webhook, err_webhook=discord_error_webhook)
    
    ex = Bitbank(pair=pair, api_key=api_key, api_secret=api_secret, max_order_count=order_limit)

    bot = None

    additional_info = {
        'pair': pair,
        'user': user,
        'exchange': ex.name,
        'db': fsm,  # Comment this line out if you don't need to store data to db
        'notifier': discord,
    }

    try:
        while True:
            init_price = ex.get_mid_price()
            assets = ex.get_assets()
            init_base = assets['base_amount'] * base_usage
            init_quote = assets['quote_amount'] * quote_usage

            bot = GridBot(exchange=ex)
            param = bot.Parameter.calc_grid_params_by_interval(init_base=init_base, init_quote=init_quote, init_price=init_price,
                                                    price_interval=price_interval, grid_num=grid_num, pair=pair, fee=ex.fee)

            bot.init_and_start(param=param, additional_info=additional_info)
            while True:
                now = time.time()

                if now - bot.started_at > reset_interval_sec:
                    # Stop this bot and restart a new bot
                    bot.cancel_and_stop()
                    time.sleep(0.5)
                    break
                
                try:
                    bot.sync_and_adjust()
                except requests.exceptions.ConnectionError as e:
                    discord.error(e)

                elapsed = time.time() - now
                to_sleep = check_interval - elapsed
                if to_sleep > 0:
                    # logger.debug(f"Sleep for: {to_sleep:.3f}s")
                    time.sleep(to_sleep)
    except KeyboardInterrupt:
        logger.info(f"On KeyboardInterrupt, cancel all orders and stop the bot...")
    except Exception as e:
        msg = f"Unknown error stopping the bot: {e}"
        discord.error(msg)
    finally:
        if bot:
            bot.cancel_and_stop()


def setup_fsm(config):
    db_config = config.get('db')
    firestore_config_file = db_config.get('db') if db_config else None
    
    fsm = None
    if firestore_config_file:
        try:
            fsm = FireStoreManager(config_file=firestore_config_file)
        except ValueError as e:
            logger.error("FireStoreManager cannot be initialized due to: ", e)
    else:
        logger.warning(f"FireStoreManager is not configured. Running without it.")
    return fsm


if __name__ == "__main__":
    main()
