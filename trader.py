import python_bitbankcc
from requester import Requester
import yaml
import time
import requests
import json


class Trader(object):
    def __init__(self, crypto_name, requester, d_info, d_err):
        self.crypto_name = crypto_name
        self.PUB = python_bitbankcc.public()
        self.infoWebhook = d_info
        self.errWebhook = d_err
        self.buy_stack = []
        self.sell_stack = []
        self.now = self.get_price()
        self.unit = 0
        self.requester = requester
        self.lock = False
        self.count = 0
        self.crypto_amount = 0
        self.JPY = 0
        self.init_cost = 0

    def get_price(self):
        return float(self.PUB.get_ticker(f'{self.crypto_name}_jpy')['last'])
    
    def cal_cost(self, crypto_amount, JPY, price_now, grid_number, interval):
        if grid_number % 2 != 0:
            raise ValueError("Wrong format on grid number")
        half_grid_count = grid_number // 2
        crypto_each_grid = crypto_amount / half_grid_count
        tmp = half_grid_count * price_now - ((1 + half_grid_count) * half_grid_count / 2 * interval)
        JPY_need = tmp * crypto_each_grid
        if JPY_need > JPY:
            crypto_each_grid = JPY / tmp
            return normalizeFloat(crypto_each_grid) * 100, JPY
        return normalizeFloat(crypto_amount), normalizeFloat(JPY_need)

    def init(self, grid_number, interval):
        """
        Build grid according to price of crypto currency now
        Set grid number & interval you want
        """
        crypto_amount, JPY = self.requester.get_wallets(1)
        price_now = self.get_price()
        crypto_amount, JPY = self.cal_cost(crypto_amount, JPY, price_now, grid_number, interval)
        self.unit = normalizeFloat(crypto_amount / grid_number * 2)
        for i in range(1, grid_number // 2 + 1):
            buy_order_id = self.requester.make_order(self.unit, price_now - i * interval, "buy")
            self.buy_stack.insert(0, ("buy", price_now - i * interval, buy_order_id))
            sell_order_id = self.requester.make_order(self.unit, price_now + i * interval, "sell")
            self.sell_stack.insert(0, ("sell", price_now + i * interval, sell_order_id))
            time.sleep(0.1)
        self.JPY, self.crypto_amount, self.now = JPY, crypto_amount, price_now
        self.init_cost = normalizeFloat(self.JPY + self.crypto_amount * price_now)
        print(f"inital cost: {self.init_cost} with JPY: {self.JPY} & {self.crypto_name}: {self.crypto_amount}")

    def trade(self, price):
        if self.lock is True:
            return
        self.lock = True
        if self.sell_stack and self.sell_stack[-1][1] < price:
            while self.sell_stack and self.sell_stack[-1][1] < price:
                self.count += 1
                self.crypto_amount = normalizeFloat(self.crypto_amount - self.unit)
                elem = self.sell_stack.pop()
                self.requester.save_order(elem[2])
                buy_order_id = self.requester.make_order(self.unit, self.now, "buy")
                self.buy_stack.append(("buy", self.now, buy_order_id))
                self.JPY = normalizeFloat(self.JPY + (elem[1] * self.unit * 1.0002))
                self.now = elem[1]
                self.send_msg("info", f"#{self.count} sell {self.unit} {self.crypto_name} on price: {elem[1]}")
            if self.sell_stack:
                self.get_income(self.init_cost, price)

        # buy when price get low
        if self.buy_stack and self.buy_stack[-1][1] > price:
            while self.buy_stack and self.buy_stack[-1][1] > price:
                self.count += 1
                self.crypto_amount = normalizeFloat(self.unit + self.crypto_amount)
                elem = self.buy_stack.pop()
                self.requester.save_order(elem[2])
                sell_order_id = self.requester.make_order(self.unit, self.now, "sell")
                self.sell_stack.append(("sell", self.now, sell_order_id))
                self.JPY = normalizeFloat(self.JPY - (elem[1] * self.unit * 0.9998))
                self.now = elem[1]
                self.send_msg("info", f"#{self.count} buy {self.unit} {self.crypto_name} on price: {elem[1]}")
            if self.buy_stack:
                self.get_income(self.init_cost, price)
        self.lock = False
        
    def get_income(self, init_cost, price):
        income = self.JPY + self.crypto_amount * price - init_cost
        self.send_msg("info", f"JPY: {self.JPY:.4f}, {self.crypto_name}:{self.crypto_amount}, init_cost: {init_cost:.4f}, income:{income:.4f}")

    def status(self):
        print(f"{len(self.buy_stack)} : {self.buy_stack}")
        print(f"{len(self.sell_stack)} : {self.sell_stack}")

    def send_msg(self, info_type, message):
        body = {}
        if info_type == "info":
            url = self.infoWebhook
        else:
            url = self.errWebhook
        body['content'] = message
        payload = json.dumps(body)
        headers = {
            'Content-Type': 'application/json',
        }
        requests.request("POST", url, headers=headers, data=payload) 


def normalizeFloat(data):
    return round(data, 4)


if __name__ == '__main__':
    with open('config.yml', 'r') as f:
        s = yaml.safe_load(f)
    
    service = s['service']
    requester = Requester(service['host'], service['token'], service['uid'], s['trade']['crypto-name'], mock=True)
    trader = Trader(s['trade']['crypto-name'], requester, "", "")
    trader.init(s['trade']['grid-number'], s['trade']['interval'])
    # trader.status()
