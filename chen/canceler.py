import yaml
import python_bitbankcc
from checker import Checker
import sys

class Canceler(Checker):
    def __init__(self, key, secret):
        super().__init__(key, secret)

    def cancel_all(self, crypto_pair):
        targets = super().get_orders_id()
        prv = super().get_prv()
        prv.cancel_orders(crypto_pair, targets)


if __name__ == '__main__':
    argv = sys.argv[1:]
    try:
        path = argv[0]
    except:
        raise ValueError("NEED TO ENTER CONFIG ARGUMENT")
    with open(path, 'r') as f:
        s = yaml.safe_load(f)
    API_KEY = s['api']['key']
    API_SECRET = s['api']['secret']
    canceler = Canceler(API_KEY, API_SECRET)
    canceler.cancel_all("eth_jpy")