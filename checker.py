import python_bitbankcc
import yaml

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

if __name__ == '__main__':
    with open('config.yml', 'r') as f:
        s = yaml.safe_load(f)
    API_KEY = s['api']['key']
    API_SECRET = s['api']['secret']
    checker = Checker(API_KEY, API_SECRET)
    print(checker.check_order('14971423806'))
