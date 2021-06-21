"""
1. Decide the grid setup base on the input parameters (cell size, boundary)
2. Make limit orders and record the order ids
3. Check the orders periodically, if they are eaten, put an oppsite order on the oppsite side (make sure only one order is eaten)
  3.1 Handle situations where multiple orders were taken since last update
4. Calculate statistics and send notifications: earn rate, yearly earn rate
"""
from enum import Enum


class Exchange:
    class OrderStatus(Enum):
        # UNFILLED, PARTIALLY_FILLED, FULLY_FILLED, CANCELED_UNFILLED, CANCELED_PARTIALLY_FILLED
        Unfilled = "UNFILLED"
        PartiallyFilled = "PARTIALLY_FILLED"
        FullyFilled = "FULLY_FILLED"
        CancelledUnfilled = "CANCELED_UNFILLED"
        CancelledPartiallyFilled = "CANCELED_PARTIALLY_FILLED"

    class ExceedOrderLimitError(Exception):
        pass

    class InvalidPriceError(Exception):
        pass

    def __init__(self, pair, max_order_count=10) -> None:
        self.max_order_count = max_order_count
        self.pair = pair

        # TODO: DEBUG PURPOSE
        self.order_id = 1000
    
    def get_latest_prices(self):
        """Get the latest price, best_ask, best_bid"""
        info = {
            "price": 0,
            "best_ask": 0,
            "best_bid": 0,
            "spread": 0,
            "mid_price": 115,
        }
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



class OrderSide(Enum):
    Buy = 'buy'
    Sell = 'sell'


class OrderStatus(Enum):
    # Init = 0
    ToCreate = 0
    Created = 1
    Traded = 2
    Paired = 3
    ToCancel = 4
    Cancelled = 5
    

class Order:
    def __init__(self, price, amount, id=None, couple_id=None, side=OrderSide.Buy, status=OrderStatus.ToCreate) -> None:
        self.id = id
        self.couple_id = couple_id
        self.side = side
        self.price = price
        self.amount = amount
        self.status = status
    
    def mark_cancel(self):
        if self.status == OrderStatus.Created:
            self.status = OrderStatus.ToCancel
        elif self.status == OrderStatus.ToCreate:
            print(f"This order is not created yet when being cancelled: {self}")
            self.status = OrderStatus.Cancelled
    
    def create_ok(self):
        if self.status == OrderStatus.ToCreate:
            self.status = OrderStatus.Created
        else:
            print(f"Warning: order was not at status ToCreate. {self}")

    def cancel_ok(self):
        if self.status == OrderStatus.ToCancel:
            self.status = OrderStatus.Cancelled
        else:
            print(f"Warning: order was not at status ToCancel. {self}")  

    def trade_ok(self):
        if self.status == OrderStatus.Created:
            self.status = OrderStatus.Traded
        else:
            print(f"Warning: order was not at status Created when being Traded. {self}")   

    def copy(self, price_interval, direction='inner', status=OrderStatus.ToCreate):
        flag = self.get_direction_flag(self.side, direction=direction)
        new_price = self.price + flag * price_interval
        obj = self.__class__(price=new_price, amount=self.amount, side=self.side, status=status)
        return obj
    
    @classmethod
    def get_direction_flag(cls, side, direction):
        flag = 1
        if ((side == OrderSide.Buy and direction == 'outer') 
            or (side == OrderSide.Sell and direction == 'inner')):
            flag = -1
        return flag
    
    def __repr__(self) -> str:
        return f"<Order id[{self.id}], s[{self.side.name}], p[{self.price}], a[{self.amount}], st[{self.status.name}]>"


class OrderManager:
    # TODO: handel special case where orders were cancel mannually during synchronizing
    class OrderStack:
        def __init__(self, om, side: OrderSide) -> None:
            self.om = om
            self.side = side
            self._orders = []
        
        @property
        def price_interval(self):
            return self.om.price_interval

        @property
        def unit_amount(self):
            return self.om.unit_amount

        @property
        def capacity(self):
            return self.om.grid_num // 2 # should equal to half_grid_num

        @property
        def active_limit(self):
            return self.om.order_limit // 2 # should equal to half of the pre-defined exchange limit of active orders (e.g., 30 for bitbank)
        
        @property
        def order_ids(self):
            return [o.id for o in self._orders]
        
        @property
        def best_order(self):
            self.sort()
            return self._orders[0] if len(self._orders) > 0 else None

        @property
        def to_create(self):
            return self.get_orders_by_status(status_list=[OrderStatus.ToCreate])

        @property
        def to_cancel(self):
            return self.get_orders_by_status(status_list=[OrderStatus.ToCancel])

        @property
        def active_orders(self):
            return self.get_orders_by_status(status_list=[OrderStatus.Created])

        def get_orders_by_status(self, status_list):
            return list(filter(lambda o: o.status in status_list, self._orders))

        def sort(self):
            desc = self.side == OrderSide.Buy
            self._orders.sort(key=lambda x: x.price, reverse=desc)
        
        def get_order(self, order_id):
            for o in self._orders:
                if order_id == o.id:
                    return o
            return None
        
        def prepare_init(self, init_price):
            """ Init stack with limited numbers of orders, based on init_price """

            for i in range(self.active_limit):
                flag = Order.get_direction_flag(self.side, direction="outer")
                price = init_price + flag * self.price_interval * (i+1)
                o = Order(price=price, amount=self.unit_amount, side=self.side)
                self._orders.append(o)

        def refill_orders(self, count=1, direction="inner"):
            """ Refill the stack with certain numbers of orders with direction
                    direction: `inner`  means towards the center of current price
                                `outer` means creating more backup orders
            """
            if self.best_order and count > 0:
                for i in range(count):
                    o = self.best_order.copy(self.price_interval * (i+1), direction=direction)
                    self._orders.append(o)
                self.sort()

        def shrink_outer(self, count=1):
            """ Prepare to remove `count` of the orders from the outer """
            if count <= 0:
                return 
            for o in self._orders[-count:]:
                o.mark_cancel()
        
        def order_create_ok(self, order):
            if order in self.to_create:
                order.create_ok()
            else:
                print(f"Order not found in to_create: {order}")
        
        def order_cancel_ok(self, order):
            if order in self.to_cancel:
                order.cancel_ok()
            else:
                print(f"Order not found in to_cancel: {order}")
        
        def order_traded(self, order):
            if order in self.active_orders:
                order.trade_ok()
                # TODO: update db records of this order
                self._orders.remove(order)
            else:
                print(f"Order not found in active orders in {self.side} stack: {order}")
        
        def remove_all(self):
            self._orders.clear()
        
        @property
        def expected_size(self):
            return len(self.get_orders_by_status(status_list=[OrderStatus.ToCreate, OrderStatus.Created])) 
            
    def __init__(self, price_interval, unit_amount, grid_num, order_limit, balance_threshold=1) -> None:
        """ 
            balance_threshold: balance the size of two stacks when the size of either stack is <= this threshold
        """
        self.price_interval = price_interval
        self.unit_amount = unit_amount
        self.grid_num = grid_num
        self.order_limit = order_limit
        self.buy_stack = self.OrderStack(om=self, side = OrderSide.Buy)
        self.sell_stack = self.OrderStack(om=self, side = OrderSide.Sell)
        self.balance_threshold = balance_threshold
    
    def init_stacks(self, init_price):
        self.buy_stack.prepare_init(init_price=init_price)
        self.sell_stack.prepare_init(init_price=init_price)
    
    @property
    def orders_to_create(self):
        return [*self.buy_stack.to_create, *self.sell_stack.to_create]
    
    def order_create_ok(self, order):
        """ Set the status of the order to Created """
        stack = self.buy_stack if order.side==OrderSide.Buy else self.sell_stack
        stack.order_create_ok(order)

    def order_cancel_ok(self, order):
        """ Set the status of the order to Canceld """
        stack = self.buy_stack if order.side==OrderSide.Buy else self.sell_stack
        stack.order_cancel_ok(order)

    @property
    def orders_to_cancel(self):
        return [*self.buy_stack.to_cancel, *self.sell_stack.to_cancel]
    
    @property
    def active_orders(self):
        return [*self.buy_stack.active_orders, *self.sell_stack.active_orders]
    
    @property
    def active_order_ids(self):
        return [o.id for o in self.active_orders]
    
    def print_stacks(self):
        for o in [*reversed(self.sell_stack.active_orders), *self.buy_stack.active_orders]:
            print(f"OID<{o.id}> {o.side.name} @[{o.price}]")
    
    def remove_all(self):
        print("TODO: save all orders into db")
        for stack in [self.buy_stack, self.sell_stack]:
            stack.remove_all()
    
    def get_order_by_id(self, order_id):
        """ Find the order and the corresponding stack if exists """
        order = self.buy_stack.get_order(order_id=order_id)
        if order:
            return order, self.buy_stack
        else:
            order = self.sell_stack.get_order(order_id=order_id)
            if order:
                return order, self.sell_stack
        return None, None
            
    def order_traded(self, order_id):
        """ Set the status of the order to Traded """
        order, stack = self.get_order_by_id(order_id=order_id)
        stack.order_traded(order)

    def refill_orders(self, mid_price):

        def refill_stack(price_diff, stack: self.OrderStack):
            count = int(price_diff // self.price_interval) - 1
            if count > 0:
                stack.refill_orders(count=count, direction="inner")

        diff_buy = mid_price - self.buy_stack.best_order.price
        refill_stack(diff_buy, self.buy_stack)
        
        diff_sell =  self.sell_stack.best_order.price - mid_price
        refill_stack(diff_sell, self.sell_stack)

    def blance_stacks(self):
        exp_buy_size = self.buy_stack.expected_size
        exp_sell_size = self.sell_stack.expected_size
        stack_to_expand = stack_to_shrink = None

        print(f"ESS: {exp_sell_size}, EBS: {exp_buy_size}")
        
        if exp_buy_size <= self.balance_threshold:
            stack_to_expand = self.buy_stack
            stack_to_shrink = self.sell_stack
            size_diff =  exp_sell_size - exp_buy_size
        elif exp_sell_size <= self.balance_threshold:
            stack_to_expand = self.sell_stack
            stack_to_shrink = self.buy_stack
            size_diff = exp_buy_size - exp_sell_size
        
        if stack_to_expand and stack_to_shrink:
            delta = int(size_diff // 2)
            print(f"delta: {delta}")
            stack_to_expand.refill_orders(delta, direction="outer")
            stack_to_shrink.shrink_outer(delta)


class GridBot:

    class Parameter:
        def __init__(self, unit_amount, price_interval, init_base, init_quote, init_price, support, grid_num) -> None:
            self.unit_amount = unit_amount
            self.price_interval = price_interval
            self.init_base = init_base
            self.init_quote = init_quote
            self.init_price = init_price
            self.support = support
            self.grid_num = grid_num
        
        @property
        def lowest_price(self):
            return self.support

        @property
        def half_grid_num(self):
            return self.grid_num // 2

        def get_highest_earn_rate_per_grid(self, fee):
            return self.price_interval / self.lowest_price - 2 * fee

        def get_lowest_earn_rate_per_grid(self, fee):
            second_highest_price = self.init_price + (self.half_grid_num-1) * self.price_interval
            return self.price_interval / second_highest_price - 2 * fee

        @classmethod
        def calc_grid_params(cls, init_base, init_quote, init_price, support, grid_num=100, fee=-0.0002):
            """ Calculate the grid setup parameters

                init_base: initial amount of base currency (e.g., BTC): 0.01
                init_quote: initial amount of quote currency (e.g., JPY): 50000
                init_price: currenty price (exchange rate) of the base currency: 4000000
                support: the support line, or the estimated potential lowest price, or the bottom line of the grid
                grid_num: the number of grids in total (it will be divided into two equal parts)
                fee: the fee rate for makers
            """
            unused_base = 0
            unused_quote = 0
            half_grid_num = grid_num // 2
            ideal_unit_amount = init_base / half_grid_num
            price_interval = (init_price - support) / half_grid_num
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
                        init_base=init_base, init_quote=init_quote, support=support, grid_num=grid_num)
            return param

        def __repr__(self) -> str:
            # attrs = ['unit_amount', 'price_interval']
            return "<Param: {}>".format(", ".join([f"{k}[{v}]" for k, v in self.__dict__.items()]))

    def __init__(self, exchange: Exchange) -> None:
        self.exchange = exchange
        self.om = None
        self.param = None

    def init_grid(self, param):

        self.param = param
        if self.om:
            print("The grid trade bot is already initiated. Abort...")
            return
        self.om = OrderManager(price_interval=param.price_interval,
                                unit_amount=param.unit_amount,
                                grid_num=param.grid_num,
                                order_limit=self.exchange.max_order_count,
                            )
        self.om.init_stacks(init_price=param.init_price)
        self.commit_create_orders()

    def commit_cancel_orders(self):
        for o in self.om.orders_to_cancel:
            self.exchange.cancel_order(o)
            self.om.order_cancel_ok(order=o)

    def commit_create_orders(self):
        for o in self.om.orders_to_create:
            self.exchange.create_order(o)
            self.om.order_create_ok(order=o)
            # except Exchange.ExceedOrderLimitError:

    def cancel_all_orders(self):
        order_ids = self.om.active_order_ids
        self.exchange.cancel_all_orders(order_ids)
        self.om.remove_all()
    
    def sync_order_status(self):
        order_ids = self.om.active_order_ids
        orders_data = self.exchange.check_order_status(order_ids=order_ids)
        traded_count = 0
        for order_data in orders_data:
            if self.exchange.is_order_fullyfilled(order_data=order_data):
                # Notify the order manager that the order is traded
                self.om.order_traded(order_id=order_data['order_id'])
                traded_count += 1
            elif self.exchange.is_order_cancelled(order_data=order_data):
                print(f"Order is possibly cancelled by the uesr: {order_data['order_id']}")

        self.om.print_stacks()

        if traded_count > 1:
            print(f"More than 1 orders are traded: [{traded_count}] orders")
        # Refill with new orders (create new orders in the opposite stack)
        data = self.exchange.get_latest_prices()
        mid_price = data['mid_price']
        self.om.refill_orders(mid_price)
        self.om.blance_stacks()
        self.commit_cancel_orders()
        self.commit_create_orders()


def test_params():
    init_price = 35393
    init_quote = 50000
    init_base = init_quote / init_price
    support = 24756
    grid_num = 100

    # init_price = 100
    # init_quote = 700
    # init_base = 10
    # support = 50
    # grid_num = 10

    for gn in [10, 20, 30, 50, 80 , 100]:
        grid_num = gn
        params = GridBot.Parameter.calc_grid_params(init_base, init_quote, init_price, support, grid_num=grid_num, fee=0.0008)
        print(params)

def test_bot():
    pair = 'eth_jpy'

    init_price = 35393
    init_quote = 50000
    init_base = init_quote / init_price
    support = 24756
    fee = -0.0002
    grid_num = 100

    init_price = 100
    init_quote = 700
    init_base = 10
    support = 50
    grid_num = 10    

    param = GridBot.Parameter.calc_grid_params(init_base, init_quote, init_price, support, grid_num=grid_num, fee=fee)

    bitbank = Exchange(pair=pair)
    bot = GridBot(bitbank)
    bot.init_grid(param=param)

    # print(bot.om.active_orders)
    bot.om.print_stacks()

    bot.sync_order_status()
    bot.om.print_stacks()


if __name__ == "__main__":
    # test_params()
    test_bot()
