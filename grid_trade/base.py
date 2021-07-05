import sys
sys.path.append('.')

import time
import uuid
from enum import Enum
from collections import defaultdict
from grid_trade.orders import Order, OrderManager, OrderSide
from exchanges import Exchange
from exchanges.bitbank import ExceedOrderLimitError, InvalidPriceError


class BotStatus(Enum):
    Created = 'Created'
    Running = 'Running'
    Stopped = 'Stopped'


class GridBot:

    enum_values = {
        'status': BotStatus,
    }

    class Parameter:
        def __init__(self, unit_amount, price_interval, init_base, init_quote, init_price,
                    grid_num, fee=0, unused_base = 0, unused_quote = 0) -> None:
            self.unit_amount = unit_amount
            self.price_interval = price_interval
            self.init_base = init_base
            self.init_quote = init_quote
            self.init_price = init_price
            self.grid_num = grid_num
            self.fee = fee
            self.unused_base = unused_base
            self.unused_quote = unused_quote
        
        @property
        def lowest_price(self):
            half_price_height = self.half_grid_num * self.price_interval
            return self.init_price - half_price_height

        @property
        def highest_price(self):
            half_price_height = self.half_grid_num * self.price_interval
            return self.init_price + half_price_height

        @property
        def half_grid_num(self):
            return self.grid_num // 2

        def get_highest_earn_rate_per_grid(self):
            return self.price_interval / self.lowest_price - 2 * self.fee

        def get_lowest_earn_rate_per_grid(self):
            second_highest_price = self.init_price + (self.half_grid_num-1) * self.price_interval
            return self.price_interval / second_highest_price - 2 * self.fee

        @classmethod
        def calc_grid_params_by_support(cls, init_base, init_quote, init_price, support, grid_num=100, fee=0):
            """ Calculate the grid setup parameters by fixing the support line

                init_base: initial amount of base currency (e.g., BTC): 0.01
                init_quote: initial amount of quote currency (e.g., JPY): 50000
                init_price: currenty price (exchange rate) of the base currency: 4000000
                support: the support line, or the estimated potential lowest price, or the bottom line of the grid
                grid_num: the number of grids in total (it will be divided into two equal parts)
                fee: the fee rate for makers
            """
            half_grid_num = grid_num // 2
            price_interval = (init_price - support) / half_grid_num

            return cls.calc_grid_params_by_interval(init_base=init_base, init_quote=init_quote, init_price=init_price,
                                            price_interval=price_interval, grid_num=grid_num, fee=fee)

        @classmethod
        def calc_grid_params_by_interval(cls, init_base, init_quote, init_price, price_interval, grid_num=100, fee=0):
            """ Calculate the grid setup parameters by fixing the price_interval

                init_base: initial amount of base currency (e.g., BTC): 0.01
                init_quote: initial amount of quote currency (e.g., JPY): 50000
                init_price: currenty price (exchange rate) of the base currency: 4000000
                price_interval: interval price between two grid lines (the height of the cell in quote)
                grid_num: the number of grids in total (it will be divided into two equal parts)
                fee: the fee rate for makers
            """
            unused_base = 0
            unused_quote = 0
            half_grid_num = grid_num // 2
            ideal_unit_amount = init_base / half_grid_num
            total_buy_price = half_grid_num * (init_price - (1+half_grid_num)*price_interval/2)
            quote_needed = total_buy_price * ideal_unit_amount
            if quote_needed > init_quote:
                # Not enough quote
                # Decrease the unit amount of base currency in each trade
                unit_amount = init_quote / total_buy_price
                # Calculate how much amount of base currency will be unused
                unused_base = init_base - unit_amount * half_grid_num
            else:
                unit_amount = ideal_unit_amount
                unused_quote = init_quote - quote_needed
            
            param = cls(unit_amount=unit_amount, price_interval=price_interval, init_price=init_price,
                        init_base=init_base, init_quote=init_quote, grid_num=grid_num, fee=fee,
                        unused_base=unused_base, unused_quote=unused_quote)
            return param   
            
        def get_dict_to_serialize(self):
            dest = vars(self).copy()
            return dest

        @classmethod
        def from_dict(cls, source):
            return cls(**source)

        def to_dict(self):
            dest = self.get_dict_to_serialize()
            return dest

        def __repr__(self) -> str:
            # attrs = ['unit_amount', 'price_interval']
            paris = {
                **self.__dict__,
                "lowest_price": self.lowest_price,
                "highest_price": self.highest_price,
                "lowest_grid_earn_rate": self.get_lowest_earn_rate_per_grid(),
                "highest_grid_earn_rate": self.get_highest_earn_rate_per_grid(),
            }
            variables = [f"{k}={v}" for k, v in paris.items()]
            return "{0}({1})".format(self.__class__.__name__, ", ".join(variables))

    def __init__(self, exchange: Exchange = None, param=None, status=BotStatus.Created, 
                started_at=None, stopped_at=None, uid=None) -> None:
        if not uid:
            uid = str(uuid.uuid4())
        self.uid = uid
        self.exchange = exchange
        self.om = None
        self.param: GridBot.Parameter = param
        self.additional_info = None
        self.status = status
        self.started_at = started_at
        self.stopped_at = stopped_at
        self.traded_count = defaultdict(int)
        self.notifier = None

    #################
    # Core logic
    def init_and_start(self, param, additional_info):
        """ Init the order manager and start the bot """
        if self.om:
            self.notify_error("The grid trade bot is already initiated. Skip.")
            return

        self.started_at = time.time()
        self.param = param
        self.additional_info = additional_info
        self.status = BotStatus.Running
        self.save_bot_info_to_db()
        self.om = OrderManager(price_interval=param.price_interval,
                                unit_amount=param.unit_amount,
                                grid_num=param.grid_num,
                                order_limit=self.exchange.max_order_count,
                                additional_info=additional_info,
                            )
        self.om.init_stacks(init_price=param.init_price)
        self._commit_create_orders()

    def cancel_and_stop(self):
        """ Cancel all orders and stop the bot. """
        order_ids = self.om.active_order_ids
        try:
            self.exchange.cancel_orders(order_ids)
        except Exception as e:
            self.notify_error(f"Cancel orders failed for {self.exchange}. Plesase check manually!")
        self.om.cancel_all()
        self.stopped_at = time.time()        
        self.status = BotStatus.Stopped
        self.update_bot_info_to_db()
    
    def sync_order_status(self):
        order_ids = self.om.active_order_ids
        try:
            orders_data = self.exchange.get_orders_data(order_ids=order_ids)
        except Exception as e:
            self.notify_error(f"Error during retrieving orders from {self.exchange.name}: {e}")
            return
        # print(f"orders_data: {orders_data}")
        traded_count = 0
        for order_data in orders_data:
            if self.exchange.is_order_fullyfilled(order_data=order_data):
                oid = order_data['order_id']
                # Notify the order manager that the order is traded
                self.om.order_traded(order_id=oid)
                traded_count += 1
                order = self.om.get_order_by_id(order_id=oid)
                self.traded_count[order.side.value] += 1
                self.notify_order_traded(order)
            elif self.exchange.is_order_cancelled(order_data=order_data):
                self.notify_error(f"Order is possibly cancelled by the uesr: {order_data['order_id']}")

        if traded_count <= 0:
            return
        if traded_count > 1:
            self.notify_error(f"More than 1 orders are traded: [{traded_count}] orders")
        mid_price = self.exchange.get_mid_price()
        if mid_price > self.param.highest_price or mid_price < self.param.lowest_price:
            # TODO: notify user
            return False

        # Refill with new orders (create new orders in the opposite stack)
        self.om.refill_orders(mid_price)
        self.om.blance_stacks()
        self._commit_cancel_orders()
        self._commit_create_orders()
        # self.om.print_stacks()
        self.update_bot_info_to_db()

    #################
    # DB related
    # TODO: add method to recover from db
    def recover_from_db(self):
        pass

    def save_bot_info_to_db(self):
        if self.db:
            self.db.create_and_use_runner(self.to_dict())

    def update_bot_info_to_db(self):
        if self.db:
            self.db.update_runner(runner_id=self.uid, runner_data=self.to_dict())

    @property
    def db(self):
        try:
            db = self.additional_info.get('db', None)
            return db
        except Exception:
            return None

    #################
    # Notification / Message related
    def notify_info(self, message):
        if self.notifier:
            self.notifier.info(message)

    def notify_error(self, message):
        if self.notifier:
            self.notifier.error(message)
    
    def notify_order_traded(self, order):
        if self.notifier:
            side = 'buy' if order.side==OrderSide.Buy else 'sell'
            message = self.format_order_traded(order=order, traded_count=self.traded_count)
            self.notifier.send_trade_msg(message, side)

    @property
    def notifier(self):
        try:
            notifier = self.additional_info.get('notifier', None)
            return notifier
        except Exception:
            return None

    @classmethod
    def format_order_traded(cls, order: Order, traded_count: dict):
        current_side = 0
        total_count = 0
        for k, v in traded_count.items():
            if k == order.side.value:
                current_side = v
            total_count += v
        return f"#{total_count}. {order.short_markdown}. ({order.side.value} #{current_side})"

    #################
    # Private methods
    def _commit_cancel_orders(self):
        if len(self.om.orders_to_cancel) <= 0:
            print('Nothing to cancel')
            return
        order_ids = [o.order_id for o in self.om.orders_to_cancel]
        try:
            self.exchange.cancel_orders(order_ids)
        except Exception as e:
            self.notify_error(f"Cancel orders failed in {self.exchange} for orders: {order_ids}")
        for o in self.om.orders_to_cancel:
            self.om.order_cancel_ok(order=o)

    def _commit_create_orders(self):
        for o in self.om.orders_to_create:
            try:
                self.exchange.create_order(o)
                self.om.order_create_ok(order=o)
            except (InvalidPriceError, ExceedOrderLimitError):
                self.om.order_create_fail(order=o)
                self.notify_error(f"Create order failed in {self.exchange} for order: {o}")
    
    #################
    # Serialization
    def get_dict_to_serialize(self):
        dest = {
            'uid': self.uid,
            'name': 'grid_bot',
            'started_at': self.started_at,
            'stopped_at': self.stopped_at,
            'status': self.status,
            'traded_count': self.traded_count,
            'param': self.param.to_dict(),
        }
        return dest

    @classmethod
    def from_dict(cls, source):
        raise NotImplementedError('Not tested yet.')
        param = cls.Parameter.from_dict(source['param'])
        data = {
            'uid': source['uid'],
            'started_at': source['started_at'],
            'stopped_at': source['stopped_at'],
            'status': source['status'],
            'traded_count': source['traded_count']
        }
        for key, enum_type in cls.enum_values.items():
            if key in data and not isinstance(data[key], enum_type):
                data[key] = enum_type(data[key])
        return cls(param=param, **data)

    def to_dict(self):
        dest = self.get_dict_to_serialize()
        for key in self.enum_values.keys():
            # dest[key] = getattr(self, key).value
            dest[key] = dest[key].value
        return dest  


###################
# Tests
def test_gridbot():
    import sys
    sys.path.append('.')
    import time
    from db.manager import FireStoreManager
    from exchanges import Bitbank
    from utils import read_config


    fsm = FireStoreManager()
    config = read_config()
    api_key = config['api']['key']
    api_secret = config['api']['secret']

    pair = 'eth_jpy'
    order_limit=6
    ex = Bitbank(pair=pair, api_key=api_key, api_secret=api_secret, max_order_count=order_limit)

    additional_info = {
        'pair': pair,
        'user': 'user1',
        'exchange': ex.name,
        'db': fsm,
    }
    price_interval=5000
    grid_num=100
    init_base = 0.1915
    init_quote = 90000
    init_price = 257000
    fee = -0.002

    init_price = ex.get_mid_price()
    bot = GridBot(exchange=ex)
    param = bot.Parameter.calc_grid_params_by_interval(init_base=init_base, init_quote=init_quote, init_price=init_price,
                                            price_interval=price_interval, grid_num=grid_num, fee=fee)

    print(param)

    bot.init_and_start(param=param, additional_info=additional_info)

    time.sleep(10)

    bot.cancel_and_stop()
    return

    MIN_SLEEP_TIME = 1
    for i in range(30):
        start = time.time()
        bot.sync_order_status()
        # bot.om.print_stacks()

        elapsed = time.time() - start
        print(elapsed)
        to_sleep = MIN_SLEEP_TIME - elapsed
        if to_sleep > 0:
            time.sleep(to_sleep)


def test_serialization():
    p = GridBot.Parameter(1,2,3,4,5,6)
    res = p.to_dict()
    print(res)
    
    p1 = GridBot.Parameter.from_dict(res)
    print(p1)

    bot = GridBot(param=p1)
    data = bot.to_dict()
    print(data)

    bot.save_bot_info_to_db()

    # bot1 = GridBot.from_dict(data)
    # print(bot1.to_dict())

if __name__ == '__main__':
    test_serialization()
    # test_gridbot()
