import requests
import json
import yaml
import datetime


class Requester(object):
    def __init__(self, host, token, uid, crypto_name, mode="local"):
        self.host = host
        self.token = token
        self.uid = uid
        self.crypto_name = crypto_name
        self.mode = mode

    def get_headers(self):
        headers = {
           'Authorization': f'Bearer {self.token}',
           'Content-Type': 'application/json'
        }
        return headers

    def get(self, path, payload):
        headers = self.get_headers()
        url = f"http://{self.host}:8080/{path}"
        print(url)
        return requests.get(url, headers=headers, params=payload)
    
    def post(self, path, payload):
        headers = self.get_headers()
        url = f"http://{self.host}:8080/{path}"
        data = json.dumps(payload)
        return requests.post(url, headers=headers, data=data)

    def make_order(self, amount, price, action):
        if self.mode == "local":
            print(f"make order action: {action} {amount} on {price} - order_id")
            return
        elif self.mode == "mock":
            path = "api/mock/trade"
        elif self.mode == "prod":
            path = "api/admin/trade"
        else:
            raise ValueError("Wrong no mode")
        body = {
            "crypto_name": self.crypto_name,
            "uid": self.uid,
            "amount": amount,
            "action": action,
            "price": price,
            "type": "limit"
        }
        res = self.post(path, body)
        now = self.get_now()
        if res.status_code != 200:
            print(f"{now},make_{action},{price},99999999,false")
            return 99999999
        else:
            try:
                order_id = res.json()['data']['order_id']
            except:
                order_id = 99999999
                print(f"{now},make_{action},{price},{order_id},false", flush=True)
                return order_id
            print(f"{now},make_{action},{price},{order_id},true", flush=True)
            return order_id

    def save_order(self, action, price, order_id):
        # print(f"save order {order_id}")
        if self.mode == "local":
            return
        elif self.mode == "mock":
            path = "api/mock/order"
        elif self.mode == "prod":
            path = "api/admin/order"
        else:
            raise ValueError("Wrong no mode")
        body = {
            "uid": self.uid,
            "order_id": order_id,
            "strategy_id": 1,
            "crypto_name": self.crypto_name
        }
        res = self.post(path, body)
        now = self.get_now()
        if res.status_code != 202:
            print(f"{now},save_{action},{price},{order_id},false", flush=True)
            return
        print(f"{now},save_{action},{price},{order_id},true", flush=True)

    def get_wallets(self, strategy):
        path = "api/admin/auto_trade"
        payload = {
            "crypto_name": self.crypto_name,
            "strategy_id": strategy
        }
        res = self.get(path, payload)
        if res.status_code != 200:
            return 0, 0
        else:
            data = res.json()['data'][0]
            return data['amount'], data['JPY']

    def cancel_order(self, action, price, order_id):
        if self.mode == "local":
            return
        elif self.mode != "prod" and self.mode != "mock":
            return
        path = "api/admin/cancel"
        body = {
            "uid": self.uid,
            "crypto_name": self.crypto_name,
            "order_id": f"{order_id}",
        }
        res = self.post(path, body)
        now = self.get_now()
        if res.status_code != 200:
            print(f"{now},cancel_{action},{price},{order_id},false", flush=True)
            return
        print(f"{now},cancel_{action},{price},{order_id},true", flush=True)

    def get_now(self):
        now = datetime.datetime.utcnow() + datetime.timedelta(hours=9)
        return now.strftime('%Y-%m-%d %H:%M:%S')
    

if __name__ == '__main__':
    with open('config.yml', 'r') as f:
        s = yaml.safe_load(f)
    service = s['service']
    requeseter = Requester(service['host'], service['token'], service['uid'], s['trade']['crypto-name'])
    a, b = requeseter.get_wallets(1)
    print(a, b)
