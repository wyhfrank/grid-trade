import yaml
import python_bitbankcc
from checker import Checker

class Canceler(Checker):
    def __init__(self, key, secret):
        super().__init__(key, secret)

    def cancel_all(self, crypto_pair):
        targets = super().get_orders_id()
        print(f"cancel orders: {len(targets)}")
        super().prv.cancel_orders(crypto_pair, targets)


if __name__ == '__main__':
    with open('config.yml', 'r') as f:
        s = yaml.safe_load(f)
    API_KEY = s['api']['key']
    API_SECRET = s['api']['secret']
    canceler = Canceler(API_KEY, API_SECRET)
    canceler.cancel_all("eth_jpy")