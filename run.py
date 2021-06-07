import asyncio
import yaml
from trader import Trader
from requester import Requester
from checker import Checker


async def async_main():
    """Entry point for the script."""
    timer = asyncio.get_event_loop().time
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

    interval = 1 # seconds
    while True:
        await asyncio.sleep(interval - timer() % interval)
        try:
            price = trader.get_price()
        except e:
            trader.send_msg("Error", "Grid trade fail to get price")
            continue
        # if len(trader.sell_stack) > 0 and len(trader.buy_stack) > 0:
        #     print(f"sell: {trader.sell_stack[-1][1]}, now: {price}, buy: {trader.buy_stack[-1][1]}")
        #     print(f"highest: {len(trader.sell_stack)}:{trader.sell_stack[0][1]}")
        #     print(f"lowest: {len(trader.buy_stack)}:{trader.buy_stack[0][1]}")
        #     print(trader.sell_stack)
        #     print(trader.buy_stack)
        trader.trade(price)


if __name__ == "__main__":
    asyncio.run(async_main())
    