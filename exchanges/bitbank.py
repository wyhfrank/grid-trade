from enum import Enum
import requests
import python_bitbankcc


class ExceedOrderLimitError(Exception):
    pass


class InvalidPriceError(Exception):
    pass


class Exchange:
    name = 'AbstractExchange'
    fee = 0
    # Known exceptions that does not impact too much on the process
    KnownExceptions = () 

    def __init__(self, pair: str, max_order_count=10, api_key=None, api_secret=None) -> None:
        self.max_order_count = max_order_count
        self.pair = pair
        self.api_key = api_key
        self.api_secret = api_secret

    def get_latest_prices(self):
        raise NotImplementedError()

    def create_order(self, order):
        raise NotImplementedError()

    def cancel_orders(self, order_ids):
        raise NotImplementedError()    

    def get_orders_data(self, order_ids):
        raise NotImplementedError()

    @classmethod
    def is_order_cancelled(cls, order_data):
        raise NotImplementedError()

    @classmethod
    def is_order_fullyfilled(cls, order_data):
        raise NotImplementedError()
    
    def get_currency_name(self, part='base'):
        pos = 0 if part=='base' else 1
        return self.pair.split('_')[pos]

    @property
    def base_name(self):
        return self.get_currency_name('base')

    @property
    def quote_name(self):
        return self.get_currency_name('quote')

    def __repr__(self):
        return self.name


class BitbankPrivateExt(python_bitbankcc.private):
    
    # This endpoint is not support by the official python api
    # It is strange that this is a private api tho
    #   even the official doc says auth is not needed...
    #   https://github.com/bitbankinc/bitbank-api-docs/blob/master/rest-api.md#get-all-pairs-info
    def get_pairs(self):
        return self._get_query('/spot/pairs', {})


class Bitbank(Exchange):
    '''
    Format of order_data:
    
    "data": {
            "order_id": 15609795801,
            "pair": "btc_jpy",
            "side": "sell",
            "type": "limit",
            "start_amount": "0.0005",
            "remaining_amount": "0.0000",
            "executed_amount": "0.0005",
            "price": "3859000",
            "average_price": "3859000",
            "ordered_at": 1625324482979,
            "status": "FULLY_FILLED",
            "expire_at": 1640876482979,
            "post_only": true
        }
    '''

    name = 'bitbank'
    fee = -0.002
    # Known exceptions that does not impact too much on the process
    KnownExceptions = (requests.exceptions.SSLError, 
                    # requests.exceptions.ConnectionError
                    ) 

    class OrderStatus(Enum):
        # UNFILLED, PARTIALLY_FILLED, FULLY_FILLED, CANCELED_UNFILLED, CANCELED_PARTIALLY_FILLED
        Unfilled = "UNFILLED"
        PartiallyFilled = "PARTIALLY_FILLED"
        FullyFilled = "FULLY_FILLED"
        CancelledUnfilled = "CANCELED_UNFILLED"
        CancelledPartiallyFilled = "CANCELED_PARTIALLY_FILLED"

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.pub = python_bitbankcc.public()
        self.prv = BitbankPrivateExt(api_key=self.api_key, api_secret=self.api_secret)
    
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
    
    def get_mid_price(self):
        info = self.get_latest_prices()
        mid_price = info['mid_price'] if info else None
        return mid_price

    def parse_currency_amount(self, response, part='base'):
        for asset in response['assets']:
            if asset['asset'] == self.get_currency_name(part=part):
                return float(asset['free_amount'])
        return None
    
    def get_assets(self):
        res = self.prv.get_asset()
        base_amount = self.parse_currency_amount(response=res, part='base')
        quote_amount = self.parse_currency_amount(response=res, part='quote')
        return {'base_amount': base_amount, 'quote_amount': quote_amount}

    def get_basic_info(self, pair):
        """
        "pairs": [
            {
                "name": "btc_jpy",
                "base_asset": "btc",
                "quote_asset": "jpy",
                "maker_fee_rate_base": "0",
                "taker_fee_rate_base": "0",
                "maker_fee_rate_quote": "-0.0002",
                "taker_fee_rate_quote": "0.0012",
                "unit_amount": "0.0001",
                "limit_max_amount": "1000",
                "market_max_amount": "10",
                "market_allowance_rate": "0.2",
                "price_digits": 0,
                "amount_digits": 4,
                "is_enabled": true,
                "stop_order": false,
                "stop_order_and_cancel": false
            },
            ...
        ]        
        """
        if not pair:
            pair = self.pair
        
        if not pair:
            return {}

        res = self.prv.get_pairs()
        pair_data = {}
        for pair_data in res['pairs']:
            if pair_data['name'] == pair:
                break

        fee = float(pair_data.get('maker_fee_rate_quote', 0))
        price_digits = pair_data.get('price_digits', 0)
        amount_digits = pair_data.get('amount_digits', 4)
        return {
            'fee': fee,
            'price_digits': price_digits,
            'amount_digits': amount_digits,
        }

    def create_order(self, order):
        if not order.pair == self.pair:
            print(f"Warning: new order pair ({order.pair}) is diff than exchange default pair ({self.pair})")
        
        # TODO: find a better way to convert these enum values
        side_value = order.side.value
        order_type_value = order.order_type.value

        try:
            order_data = self.prv.order(pair=order.pair, price=order.price, amount=order.amount, 
                                side=side_value, order_type=order_type_value, post_only=order.post_only)
        except Exception as e:
            message = e.args[0] if e.args and len(e.args) > 0 else ''
             # argument of type 'MaxRetryError' is not iterable
            if isinstance(message, str):
                if '60011' in message: # エラーコード: 60011 内容: 同時発注制限件数(30件)を上回っています
                    raise ExceedOrderLimitError(message)

            raise e

        # print("Response of create order:", order_data)

        if self.is_order_cancelled(order_data=order_data):
            # It seems that the reponse data of this request always says that the order 
            #   is created successfully (UNFILLED)
            raise self.InvalidPriceError()

        fields_to_update = ['order_id', 'ordered_at']        
        for field_key in fields_to_update:
            setattr(order, field_key, order_data[field_key])
        return order

    def cancel_orders(self, order_ids):
        if not order_ids:
            return []
        res = self.prv.cancel_orders(self.pair, order_ids=order_ids)
        # print("Response of cancel order:", res)
        orders_data = res['orders']
        return orders_data

    def get_active_orders_data(self):
        res = self.prv.get_active_orders(self.pair)
        # print("Response of get_active_orders_data:", res)
        orders_data = res['orders']
        return orders_data

    def get_orders_data(self, order_ids):
        if not order_ids:
            return []
        res = self.prv.get_orders_info(self.pair, order_ids=order_ids)
        # print("Response of check_order_status:", res)
        orders_data = res['orders']
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
            return order_data['status'] in [cls.OrderStatus.FullyFilled.value]
        except KeyError:
            return False
