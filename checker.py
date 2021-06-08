import python_bitbankcc
import pandas as pd
import yaml
import time
import sys

class Checker(object):
    def __init__(self, key, secret):
        self.prv = python_bitbankcc.private(key, secret)
    
    def check_order(self, order_id):
        try:
            value = self.prv.get_order("eth_jpy", order_id)
            # print(value)
        except:
            print(f"Fail to get {order_id}")
            return False
        return value['status'] == "FULLY_FILLED"
    
    def get_orders(self):
        data = self.prv.get_active_orders("eth_jpy")
        df = pd.DataFrame(data['orders'])
        df = df.sort_values(by=['price'], ascending=False)
        return df

    def get_orders_id(self):
        rst = []
        data = self.prv.get_active_orders("eth_jpy")
        for order in data['orders']:
            rst.append(order['order_id'])
        return rst


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
    checker = Checker(API_KEY, API_SECRET)
    print(checker.get_orders())

