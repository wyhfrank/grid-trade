import sys
sys.path.append('.')

import time
import logging
import uuid
from typing import Iterable
from enum import Enum
from grid_trade.mixins import FieldFormatMixin
from grid_trade.orders import Order, OrderManager, OrderSide, OrderCounter
from exchanges import Exchange
from exchanges.bitbank import ExceedOrderLimitError, InvalidPriceError
from utils import format_float, format_rate, init_formatted_properties


logger = logging.getLogger(__name__)

__version__ = '0.1.6'


class BotStatus(Enum):
    Created = 'Created'
    Running = 'Running'
    Stopped = 'Stopped'


class GridBot:

    enum_values = {
        'status': BotStatus,
    }

    class Parameter(FieldFormatMixin):
        # A new property of `NAME_s` will be added for each of the `NAME` variables
        fields_to_format = {
            'unit_amount': {'precision': 4, '_type': 'amount'},
            'init_base': {'precision': 4, '_type': 'amount'},
            'init_quote': {'precision': 0, '_type': 'price'},
            'init_price': {'precision': 0, '_type': 'price'},
            'price_interval': {'precision': 0, '_type': 'price'},
            'unused_base': {'_type': 'amount'},
            'unused_quote': {'precision': 0, '_type': 'price'},
            'lowest_price': {'precision': 0, '_type': 'price'},
            'highest_price': {'precision': 0, '_type': 'price'},
            'lowest_earn_rate_per_grid': {'precision': 4, '_type': 'rate'},
            'highest_earn_rate_per_grid': {'precision': 4, '_type': 'rate'},
        }

        def __init__(self, unit_amount, price_interval, init_base, init_quote, init_price,
                    grid_num, pair=None, fee=0, unused_base = 0, unused_quote = 0) -> None:
            self.unit_amount = unit_amount
            self.price_interval = price_interval
            self.init_base = init_base
            self.init_quote = init_quote
            self.init_price = init_price
            self.grid_num = grid_num
            self.pair = pair
            self.fee = fee
            self.unused_base = unused_base
            self.unused_quote = unused_quote
            self.round_obj(self)  # Round up the fields defined in fields_to_format
        
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

        @property
        def highest_earn_rate_per_grid(self):
            return self.price_interval / self.lowest_price - 2 * self.fee

        @property
        def lowest_earn_rate_per_grid(self):
            second_highest_price = self.init_price + (self.half_grid_num-1) * self.price_interval
            return self.price_interval / second_highest_price - 2 * self.fee

        @classmethod
        def calc_grid_params_by_support(cls, init_base, init_quote, init_price, support, grid_num=100, pair=None, fee=0):
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
        def calc_grid_params_by_interval(cls, init_base, init_quote, init_price, price_interval, grid_num=100, pair=None, fee=0):
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
                        init_base=init_base, init_quote=init_quote, grid_num=grid_num, pair=pair, fee=fee,
                        unused_base=unused_base, unused_quote=unused_quote)
            return param

        #############################
        # Serialiazation
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
                "lowest_earn_rate_per_grid": self.lowest_earn_rate_per_grid,
                "highest_earn_rate_per_grid": self.highest_earn_rate_per_grid,
            }
            variables = [f"{k}={v}" for k, v in paris.items()]
            return "{0}({1})".format(self.__class__.__name__, ", ".join(variables))

        def get_full_markdown_list(self) -> list:
            return [
                ["Grid Number" ,     f"{self.grid_num}"],
                ["Unit Amount" ,     f"{self.unit_amount_s}"],
                ["Price Interval" ,  f"{self.price_interval_s}"],
                ["Init Price" ,      f"{self.init_price_s}"],
                ["Init Currency" ,   f"[{self.init_base_s} | {self.init_quote_s}]"],
                ["Unused Currency" , f"[{self.unused_base_s} | {self.unused_quote_s}]"],
                ["Price Range" ,     f"[{self.lowest_price_s} ~ {self.highest_price_s}]"],
                ["Earn Rate" ,       f"[{self.lowest_earn_rate_per_grid_s} ~ {self.highest_earn_rate_per_grid_s}]"],
            ]
        
        @property
        def full_markdown(self) -> str:
            max_len = max(map(lambda x: len(x[0]), self.get_full_markdown_list()))
            return "\n".join(map(lambda x: "{} : {}".format(x[0].ljust(max_len), x[1]), self.get_full_markdown_list()))
        
        @property
        def short_markdown(self) -> str:
            return ", ".join(map(lambda x: "{}: {}".format(*x), self.get_full_markdown_list()[0:3]))

    class ExecutionReport:
        """ Calculate the following metrics
                Actual Earning: the earn from the matched buy/sell pairs
                Actual Earn Rate: the earn rate from the matched buy/sell pairs
                Yearly Earn Rate: the estimated yearly earn rate without considering compound interest
                Extra Hold Amount: the total amount of the unmatched orders
                Extra Hold Cost: the total value of the unmatched orders
                Avg Hold Price: the average cost/value of the extra unmatched buy/sell orders
         """

        def __init__(self, param) -> None:
            self.param: GridBot.Parameter = param

        # TODO: use the actual traded orders data
        #     self.data = defaultdict(lambda: defaultdict(list))

        # def add_order(self, order: Order):
        #     self.data[order.side][order.price].append(order)
        
        # def calc_value(self, side, amount_limit=None):
        #     pass

        @classmethod
        def _to_markdown(cls, data: dict):
            max_len = max(map(lambda x: len(x), data.keys()))
            lines = []
            for k, v in data.items():
                if isinstance(v, list):
                    value_str = "[{} ~ {}]".format(*v)
                else:
                    value_str = str(v)
                line = "{key} : {value}".format(
                    key=k.ljust(max_len),
                    value=value_str
                )
                lines.append(line)
            return "\n".join(lines)
            
        def from_order_counter(self, counter: OrderCounter, duration_hour):
            def to_yearly(earn_rate, hour):
                return earn_rate / hour * 24 * 365

            buy_count = counter.total_of(OrderSide.Buy)
            sell_count = counter.total_of(OrderSide.Sell)
            matched = min(buy_count, sell_count)
            extra_count = abs(buy_count - sell_count)
            traded_value = self.param.unit_amount * self.param.init_price * matched
            lowest_actual_earning = self.param.lowest_earn_rate_per_grid * traded_value
            highest_actual_earning = self.param.highest_earn_rate_per_grid * traded_value
            init_value = self.param.init_quote + self.param.init_base * self.param.init_price
            lowest_earn_rate = lowest_actual_earning / init_value
            highest_earn_rate = highest_actual_earning / init_value
            lowest_yearly_earn_rate = to_yearly(lowest_earn_rate, hour=duration_hour)
            highest_yearly_earn_rate = to_yearly(highest_earn_rate, hour=duration_hour)
            
            flag = 1 if sell_count > buy_count else -1
            extra_side = "equal" if sell_count == buy_count else OrderSide.Sell.value if sell_count > buy_count else OrderSide.Buy.value
            avg_hold_price = self.param.init_price + flag * (extra_count * 1) * self.param.price_interval / 2
            extra_hold_amount = self.param.unit_amount * extra_count
            extra_hold_cost = avg_hold_price * extra_hold_amount

            duration_day = duration_hour / 24
            data = {
                'Duration': "{} h ({} d)".format(format_float(duration_hour, 1), format_float(duration_day, 1)),
                'Buy-Sell Count': counter.preview,
                'Actual Earning': [format_float(lowest_actual_earning, 2), format_float(highest_actual_earning, 2)],
                'Actual Earn Rate': [format_rate(lowest_earn_rate, 4), format_rate(highest_earn_rate, 4)],
                'Yearly Earn Rate': [format_rate(lowest_yearly_earn_rate), format_rate(highest_yearly_earn_rate)],
                'Extra Side': extra_side,
                'Extra Hold Amount': format_float(extra_hold_amount, precision=4),
                'Extra Hold Cost': format_float(extra_hold_cost, precision=1),
                'Avg Hold Price': avg_hold_price,
            }
            return self._to_markdown(data)


    def __init__(self, exchange: Exchange = None, param=None, status=BotStatus.Created, 
                started_at=None, stopped_at=None, uid=None) -> None:
        if not uid:
            uid = str(uuid.uuid4())
        self.uid = uid
        self.exchange = exchange
        self.om: OrderManager = None
        self.param: GridBot.Parameter = param
        self.additional_info = None
        self.status = status
        self.started_at = started_at
        self.stopped_at = stopped_at
        self.latest_price = None
        self.traded_count = OrderCounter()
        self.execution_report = GridBot.ExecutionReport(param)   
        self._last_report_time = 0     

    #################
    # Core logic
    def init_and_start(self, param, additional_info={}):
        """ Init the order manager and start the bot """
        if self.om:
            self.notify_error("The grid trade bot is already initiated. Skip.")
            return

        self.started_at = time.time()
        self._last_report_time = self.started_at
        self.param = param
        self.execution_report = GridBot.ExecutionReport(param)
        self.additional_info = additional_info
        self.status = BotStatus.Running
        self.save_bot_info_to_db()
        self.notify_info("-" * 80 + "\n" +\
                        f"GridBot v{__version__} (`{self.uid}`) starting with param:\n```\n{self.param.full_markdown}\n```")
        self.om = OrderManager(price_interval=param.price_interval,
                                unit_amount=param.unit_amount,
                                grid_num=param.grid_num,
                                order_limit=self.exchange.max_order_count,
                                additional_info=additional_info,
                            )
        self.om.init_stacks(init_price=param.init_price)
        self._commit_create_orders()
        self.om.print_stacks()

    def cancel_and_stop(self):
        """ Cancel all orders and stop the bot. """

        if not self.om:
            logger.warning(f"Stopping a bot while it is not started yet. Skip.")
            return

        order_ids = self.om.active_order_ids
        try:
            self.exchange.cancel_orders(order_ids)
        except Exception as e:
            self.notify_error(f"Cancel orders failed for {self.exchange}. Please check manually!")
        self.om.cancel_all()
        self.stopped_at = time.time()
        self.status = BotStatus.Stopped
        self.update_bot_info_to_db()
        self.notify_info(f"GridBot v{__version__} (`{self.uid}`) stopped with param:\n```\n{self.param.full_markdown}```")
        self.notify_execution_report(force=True)

    def sync_and_adjust(self):
        """ Sync the orders status from exchange and adjust the stacks (refill new orders, balance stacks etc.) """

        orders_data = self._retrieve_orders_data()

        counter = self._sync_order_status(orders_data=orders_data)
        
        self.notify_execution_report()

        if counter.total <= 0:
            # No orders traded
            return

        if counter.total > 1:
            # logger.warning(f"Care: more than 1 orders are traded during one sync: {counter.preview}")
            if counter.both_sides:
                self.notify_error(f"Oders on both sides are traded during one sync: {counter.preview}")

        price_info = self.exchange.get_latest_prices()
        new_price = self._adjust_orders(price_info=price_info)
        if not new_price:
            return
        
        logger.info(f"Order(s) traded: {counter.preview} "
                    f"Current price [{new_price}]"
                    )
        self.om.print_stacks()

    def _retrieve_orders_data(self):
        orders_data = []
        order_ids = self.om.active_order_ids
        try:
            orders_data = self.exchange.get_orders_data(order_ids=order_ids)
        except self.exchange.KnownExceptions as e:
            logger.error(f"Known error during retrieving orders: {e}")
        except Exception as e:
            self.notify_error(f"Error during retrieving orders from {self.exchange.name}: {e}")
        return orders_data

    def _sync_order_status(self, orders_data):
        total_traded_this_sync = len(list(filter(self.exchange.is_order_fullyfilled, orders_data)))
        counter = OrderCounter()
        for order_data in orders_data:
            if self.exchange.is_order_fullyfilled(order_data=order_data):
                oid = order_data['order_id']
                # CARE: The following line needs to be executed before 
                #  `self.om.order_traded(order_id=oid)`
                #  since the order will be removed from the stack by then
                order = self.om.get_order_by_id(order_id=oid)

                # Mark the order that is traded in this sync
                self.om.mark_order_on_traded(order_id=oid)

                if order:
                    counter.increase(order.side)
                    self.traded_count.increase(order.side) # This need to be updated imediately right before the notification
                    batch_info = f" [{counter.total}/{total_traded_this_sync}]" if total_traded_this_sync > 1 else ""
                    self.notify_order_traded(order, more=batch_info)
                    # irregular_msg = self._check_irregular_price(order=order, price_info=price_info)
                    # if irregular_msg:
                        # self.notify_error(message=irregular_msg)
                else:
                    self.notify_error(f"Traded order not found during sync. Order id: `{oid}`")
            elif self.exchange.is_order_cancelled(order_data=order_data):
                oid = order_data['order_id']
                # Force cancel the order
                self.om.order_force_cancelled(order_id=oid)
                msg = f"Order possibly failed during creation or cancelled by the user: {oid}"
                # logger.warning(msg)
                # This will be spamming. Update: the order will be cancelled and removed, thus no spamming
                self.notify_error(msg)
        return counter

    def  _adjust_orders(self, price_info):
        # mid_price = self.exchange.get_mid_price()
        new_price = price_info['price']
        self.latest_price = new_price
        if new_price > self.param.highest_price or new_price < self.param.lowest_price:
            logger.warning(f"Current price (`{new_price}`) exceeds price range: " + \
                        f"[{self.param.lowest_price_s} ~ {self.param.highest_price_s}]")
            # self.notify_error(f"Current price (`{new_price}`) exceeds price range: " + \
                            #   f"[{self.param.lowest_price_s} ~ {self.param.highest_price_s}]")
            return False

        # Refill with new orders (create new orders in the opposite stack)
        # self.om.refill_orders_by_new_price(new_price=new_price)
        self.om.refill_orders_at_opposite_position()

        # Balance the stacks if necessary
        self.om.balance_stacks()

        self._commit_orders_traded()
        self._commit_cancel_orders()
        self._commit_create_orders()
        self.update_bot_info_to_db(fields=['traded_count', 'latest_price'])
        return new_price
    
    def _check_irregular_price(self, order: Order, price_info):
        """ Check whether the prcice jumpped back """
        new_price = price_info['price']
        best_bid = price_info['best_bid']
        best_ask = price_info['best_ask']
        irregular = False
        other_side_price = order.get_opponent_price(self.om.price_interval)

        if order.side == OrderSide.Buy and other_side_price <= best_bid:
            other_side = OrderSide.Sell
            other_side_marker = '---'
            irregular = True
        elif order.side == OrderSide.Sell and other_side_price >= best_ask:
            other_side = OrderSide.Buy
            other_side_marker = '+++'
            irregular = True
                
        if irregular:
            items = sorted([
                ('vvv', best_ask),
                (other_side_marker, other_side_price),
                ('@@@', new_price),
                ('^^^', best_bid),
            ], key=lambda x: x[1], reverse=True)

            msg = "\n".join(map(lambda p: "{}: {}".format(*p), items))
            return f"Opponent [{other_side.value}] order +[{other_side_price}] cannot be created.\n" +\
                f"```\n{msg}```"
        return False

    #################
    # DB related
    # TODO: add method to recover from db
    def recover_from_db(self):
        pass

    def save_bot_info_to_db(self):
        if self.db:
            self.db.create_and_use_runner(self.to_dict())

    def update_bot_info_to_db(self, fields=None):
        if self.db:
            self.db.update_runner(runner_id=self.uid, runner_data=self.to_dict(fields=fields))

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
            self.notifier.info(message, logger=logger)

    def notify_error(self, message):
        if self.notifier:
            self.notifier.error(message, logger=logger)
    
    def notify_order_traded(self, order, more=""):
        if self.notifier:
            side = 'buy' if order.side==OrderSide.Buy else 'sell'
            message = self.format_order_traded(order=order, traded_count=self.traded_count)
            self.notifier.send_trade_msg(message + more, side)

    def notify_execution_report(self, force=False):
        now = time.time()
        duration_from_last_report = now - self._last_report_time
        if force or duration_from_last_report > self.report_interval_sec:
            self._last_report_time = now
            duration_hour = (now - self.started_at) / (60 * 60)
            report = self.execution_report.from_order_counter(self.traded_count, duration_hour=duration_hour)
            self.notify_info(f"Execution Report:\n```{report}```")

    @property
    def report_interval_sec(self):
        default_interval = 99999999
        try:
            sec = self.additional_info.get('report_interval_sec', default_interval)
            return sec
        except Exception:
            return default_interval

    @property
    def notifier(self):
        try:
            notifier = self.additional_info.get('notifier', None)
            return notifier
        except Exception:
            return None

    @classmethod
    def format_order_traded(cls, order: Order, traded_count: OrderCounter):
        current_side = traded_count.total_of(order.side)
        total_count = traded_count.total
        return f"#{total_count}. {order.short_markdown}. ({order.side.value} #{current_side})"

    #################
    # Private methods
    def _commit_cancel_orders(self):
        if len(self.om.orders_to_cancel) <= 0:
            # print('Nothing to cancel')
            return
        # Create a map of order_id => order
        orders_map = {o.order_id: o for o in self.om.orders_to_cancel}
        try:
            orders_data = self.exchange.cancel_orders(list(orders_map.keys()))
            for od in orders_data:
                oid = od['order_id']
                order = orders_map.get(oid, None)
                if order:
                    if self.exchange.is_order_cancelled(order_data=od):
                        self.om.order_cancel_ok(order=order)
                    else:
                        self.notify_error(f"Requested to cancel the order but it is still active in the exchange: {od}")
                else:
                    self.notify_error(f"The exchange {self.exchange} returned an irrelevant order data during cancellation: {od}")
        except Exception as e:
            self.notify_error(f"Cancel orders failed in {self.exchange} for orders: {orders_map.keys()}")

    def _commit_create_orders(self):
        for o in self.om.orders_to_create:
            try:
                self.exchange.create_order(o)
                self.om.order_create_ok(order=o)
            except (InvalidPriceError, ExceedOrderLimitError):
                self.om.order_force_cancelled(order=o)
                self.notify_error(f"Create order failed in {self.exchange} for order: {o}")

    def _commit_orders_traded(self):
        self.om.orders_traded()

    #################
    # Serialization
    def get_dict_to_serialize(self, fields=None):
        dest = {
            'uid': self.uid,
            'name': 'grid_bot',
            'started_at': self.started_at,
            'stopped_at': self.stopped_at,
            'latest_price': self.latest_price,
            'status': self.status,
            'traded_count': self.traded_count,
            'param': self.param.to_dict(),
        }
        if fields and isinstance(fields, Iterable):
            res = {}
            for f in fields:
                res[f] = dest[f]
        else:
            res = dest
        return res

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

    def to_dict(self, fields=None):
        dest = self.get_dict_to_serialize(fields=fields)
        for key in self.enum_values.keys():
            if key in dest:
                dest[key] = dest[key].value
        return dest  


init_formatted_properties(GridBot.Parameter)


###################
# Tests
###################



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
    test_param()
    # test_serialization()
    # test_gridbot()
