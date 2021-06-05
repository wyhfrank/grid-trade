import requests
import json
import yaml


class Requester(object):
    def __init__(self, host, token, uid, crypto_name, mock=True):
        self.host = host
        self.token = token
        self.uid = uid
        self.crypto_name = crypto_name
        self.mock = mock

    def get_headers(self):
        headers = {
           'Authorization': f'Bearer {self.token}',
           'Content-Type': 'application/json'
        }
        return headers

    def get(self, path, payload):
        headers = self.get_headers()
        url = f"http://{self.host}:8080/{path}"
        return requests.get(url, headers=headers, params=payload)
    
    def post(self, path, payload):
        headers = self.get_headers()
        url = f"http://{self.host}:8080/{path}"
        data = json.dumps(payload)
        return requests.post(url, headers=headers, data=data)

    def make_order(self, amount, price, action):
        if self.mock:
            path = "api/mock/trade"
        else:
            path = "api/admin/trade"
        body = {
            "crypto_name": self.crypto_name,
            "uid": self.uid,
            "amount": amount,
            "action": action,
            "price": price,
            "type": "limit"
        }
        res = self.post(path, body)
        if res.status_code != 200:
            print(res.content)
            return 99999999
        else:
            try:
                data = res.json()['data']['order_id']
            except:
                data = 99999999
            return data

    def save_order(self, order_id):
        if self.mock:
            path = "api/mock/order"
        else:
            path = "api/admin/order"
        body = {
            "uid": self.uid,
            "order_id": order_id,
            "strategy_id": 1,
            "crypto_name": self.crypto_name
        }
        res = self.post(path, body)
        if res.status_code != 202:
            print("Fail to save order")

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



if __name__ == '__main__':
    with open('config.yml', 'r') as f:
        s = yaml.safe_load(f)
    
    service = s['service']
    requeseter = Requester(service['host'], service['token'], service['uid'], s['trade']['crypto-name'], mock=False)
    a, b = requeseter.get_wallets(1)
