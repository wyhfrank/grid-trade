import socketio
import yaml
from trader import Trader
from requester import Requester
from checker import Checker

with open('config.yml', 'r') as f:
    s = yaml.safe_load(f)
service = s['service']
requester = Requester(service['host'], service['token'], service['uid'], s['trade']['crypto-name'], mode=service['mode'])
webhook = s['discord']
API_KEY = s['api']['key']
API_SECRET = s['api']['secret']
checker = Checker(API_KEY, API_SECRET)
checker = Checker()
trader = Trader(s['trade']['crypto-name'], requester, webhook['info'], webhook['error'])
trader.init(s['trade']['grid-number'], s['trade']['interval'])
sio = socketio.Client()


@sio.event
def connect(trader=trader):
    print('connect')
    # trader.init(s['trade']['grid-number'], s['trade']['interval'])


@sio.event
def message(data, trader=trader):
    price = float(data['message']['data']['last'])
    if len(trader.sell_stack) > 0 and len(trader.buy_stack) > 0:
        print(f"sell: {trader.sell_stack[-1][1]}, now: {price}, buy: {trader.buy_stack[-1][1]}")
        print(f"highest: {len(trader.sell_stack)}:{trader.sell_stack[0][1]}")
        print(f"lowest: {len(trader.buy_stack)}:{trader.buy_stack[0][1]}")
        print(trader.sell_stack)
        print(trader.buy_stack)
    trader.trade(price)

@sio.event
def my_background_task(arg):
    while True:
        sio.emit('join-room', 'ticker_eth_jpy')
        sio.sleep(1)


@sio.event
def disconnect(trader=trader):
    # trader.send_msg("error", "price ticker has been disconnected")
    trader.cancel_all()


sio.connect('wss://stream.bitbank.cc', transports=['websocket'])
sio.start_background_task(my_background_task, 'ticker_eth_jpy')
