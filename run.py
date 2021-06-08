import asyncio
import yaml
from trader import Trader
from requester import Requester
from checker import Checker
import time


async def async_main():
    timer = asyncio.get_event_loop().time
    # need to change the path to absolute path
    with open('config.yml', 'r') as f:
        s = yaml.safe_load(f)
    service = s['service']
    requester = Requester(service['host'], service['token'], service['uid'], s['trade']['crypto-name'], mode=service['mode'])
    webhook = s['discord']
    API_KEY = s['api']['key']
    API_SECRET = s['api']['secret']
    checker = Checker(API_KEY, API_SECRET)
    trader = Trader(s['trade']['crypto-name'], requester, checker, webhook['info'], webhook['error'])
    trader.init(s['trade']['grid-number'], s['trade']['interval'])

    interval = 1  # seconds
    while True:
        await asyncio.sleep(interval - timer() % interval)
        try:
            price = trader.get_price()
        except:
            trader.send_msg("Error", "Grid trade fail to get price")
            continue
        trader.trade(price)


if __name__ == "__main__":
    asyncio.run(async_main())
    