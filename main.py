import socketio
import yaml
from trader import Trader
from requester import Requester

with open('config.yml', 'r') as f:
    s = yaml.safe_load(f)
service = s['service']
requester = Requester(service['host'], service['token'], service['uid'], s['trade']['crypto-name'], mock=True)
webhook = s['discord']
trader = Trader(s['trade']['crypto-name'], requester, webhook['info'], webhook['error'])
trader.init(s['trade']['grid-number'], s['trade']['interval'])
sio = socketio.Client()


@sio.event
def connect():
    print('connect')


@sio.event
def message(data, trader=trader):
    price = float(data['message']['data']['last'])
    trader.trade(price)
    trader.status()
    print(f"sell: {trader.sell_stack[-1][1]}, {price}, buy: {trader.buy_stack[-1][1]}")

@sio.event
def my_background_task(arg):
    while True:
        sio.emit('join-room', arg)
        sio.sleep(1)


@sio.event
def disconnect():
    pass


sio.connect('wss://stream.bitbank.cc', transports=['websocket'])
sio.start_background_task(my_background_task, 'ticker_eth_jpy')
