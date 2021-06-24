from enum import Enum
import python_bitbankcc

class ExceedOrderLimitError(Exception):
    pass


class InvalidPriceError(Exception):
    pass


class Exchange:
    def __init__(self, pair, max_order_count=10) -> None:
        self.max_order_count = max_order_count
        self.pair = pair


class Bitbank(Exchange):
    class OrderStatus(Enum):
        # UNFILLED, PARTIALLY_FILLED, FULLY_FILLED, CANCELED_UNFILLED, CANCELED_PARTIALLY_FILLED
        Unfilled = "UNFILLED"
        PartiallyFilled = "PARTIALLY_FILLED"
        FullyFilled = "FULLY_FILLED"
        CancelledUnfilled = "CANCELED_UNFILLED"
        CancelledPartiallyFilled = "CANCELED_PARTIALLY_FILLED"

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

        # TODO: DEBUG PURPOSE
        self.order_id = 1000
        self.pub = python_bitbankcc.public()
    
    def get_latest_prices(self):
        """Get the latest price, best_ask, best_bid"""
        info = {}
        res = self.pub.get_ticker(self.pair)
        
        info['price'] = float(res['last'])
        info['best_ask'] = float(res['sell'])
        info['best_bid'] = float(res['buy'])
        info['spread'] = info['best_ask'] - info['best_bid']
        info['mid_price'] = (info['best_ask'] + info['best_bid']) / 2
        
        return info
    
    def get_my_orders():
        orders = []
        return orders
    
    def check_order_status(self, order_ids):
        orders_data = []
        # TODO: make request here
        
        orders_data = [
            {
                'order_id': 1005,
                'status': self.OrderStatus.FullyFilled,
            },
            {
                'order_id': 1000,
                'status': self.OrderStatus.FullyFilled,
            },
        ]

        return orders_data
    
    @classmethod
    def is_order_cancelled(cls, order_data):
        try:
            return order_data['status'] in [cls.OrderStatus.CancelledPartiallyFilled.value, 
                                            cls.OrderStatus.CancelledUnfilled.value]
        except KeyError:
            return False

    @classmethod
    def is_order_fullyfilled(cls, order_data):
        try:
            return order_data['status'] in [cls.OrderStatus.FullyFilled]
        except KeyError:
            return False

    def create_order(self, order):
        order_data = {}
        # TODO: make request here

        order_data = {
            'order_id': self.order_id,
        }
        self.order_id += 1

        print(f"Request to create order: {order}")
        
        if self.is_order_cancelled(order_data=order_data):
            raise self.InvalidPriceError()
        order.id = order_data['order_id']
        return order

    def cancel_order(self, order):
        order_data = {}
        # TODO: make request here

        order_data = {
            'order_id': 0,
        }
        
        # order.id = order_data['order_id']
        print(f"Request to cancel order: {order}")

        return order


def test_bitbank():
    bb = Bitbank(pair='btc_jpy')
    info = bb.get_latest_prices()
    print(info)


if __name__ == "__main__":
    test_bitbank()
