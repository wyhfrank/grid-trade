from enum import Enum

class OrderSide(Enum):
    Buy = 'buy'
    Sell = 'sell'


class OrderType(Enum):
    Limit = 'limit'
    Market = 'market'


class OrderStatus(Enum):
    ToCreate = 'ToCreate'
    Created = 'Created'
    Traded = 'Traded'
    Paired = 'Paired'
    ToCancel = 'ToCancel'
    Cancelled = 'Cancelled'


class Order:
    # Exclude these fields from serializing
    _to_exclude = ['db']
    enum_values = {
        'side': OrderSide,
        'status': OrderStatus,
        'order_type': OrderType,
    }

    def __init__(self, price, amount, pair, order_type=OrderType.Limit, order_id=None, couple_id=None, 
                side=OrderSide.Buy, average_price=0, status=OrderStatus.ToCreate, 
                executed_at=None, ordered_at=None, post_only=True, user='', exchange='',
                db=None):
        self.order_id = order_id
        self.couple_id = couple_id
        self.pair = pair
        self.side = side
        self.order_type = order_type
        self.amount = amount
        self.price = price
        self.average_price = average_price
        self.ordered_at = ordered_at
        self.executed_at = executed_at
        self.post_only = post_only
        self.status = status
        self.user = user
        self.exchange = exchange
        self.db = db
        
    def mark_cancel(self):
        if self.status == OrderStatus.Created:
            self.status = OrderStatus.ToCancel
        elif self.status == OrderStatus.ToCreate:
            print(f"This order is not created yet when being cancelled: {self}")
            self.status = OrderStatus.Cancelled
    
    def create_ok(self):
        if self.status == OrderStatus.ToCreate:
            self.status = OrderStatus.Created
            if self.db:
                self.db.create_order(self.to_dict())
        else:
            print(f"Warning: order was not at status ToCreate. {self}")
    
    def create_fail(self):
        if self.status == OrderStatus.ToCreate:
            self.status = OrderStatus.Cancelled
            if self.db:
                self.db.delete_order(self.order_id)

    def cancel_ok(self, force=False):
        if self.status == OrderStatus.ToCancel or force:
            self.status = OrderStatus.Cancelled
            self.save_status_to_db()
        else:
            print(f"Warning: order was not at status ToCancel. {self}")  

    def trade_ok(self):
        if self.status == OrderStatus.Created:
            self.status = OrderStatus.Traded
            self.save_status_to_db()
        else:
            print(f"Warning: order was not at status Created when being Traded. {self}") 
    
    def save_status_to_db(self):
        if self.db:
            self.db.update_order(self.order_id, {'status': self.status.value})
    
    @property
    def is_active(self):
        return self.status == OrderStatus.Created

    def copy(self, price_interval, direction='inner', status=OrderStatus.ToCreate):
        flag = self.get_direction_flag(self.side, direction=direction)
        new_price = self.price + flag * price_interval
        dest = vars(self).copy()
        dest['price'] = new_price
        dest['status'] = status
        obj = self.__class__(**dest)
        return obj
    
    @classmethod
    def get_direction_flag(cls, side, direction):
        flag = 1
        if ((side == OrderSide.Buy and direction == 'outer') 
            or (side == OrderSide.Sell and direction == 'inner')):
            flag = -1
        return flag
    
    def get_dict_to_serialize(self):
        dest = vars(self).copy()
        for k in self._to_exclude:
            del dest[k]
        return dest

    @classmethod
    def from_dict(cls, source):
        for key, enum_type in cls.enum_values.items():
            if key in source and not isinstance(source[key], enum_type):
                source[key] = enum_type(source[key])
        return cls(**source)

    def to_dict(self):
        dest = self.get_dict_to_serialize()
        for key in self.enum_values.keys():
            dest[key] = dest[key].value
        return dest
    
    def __repr__(self) -> str:
        dest = self.get_dict_to_serialize()
        variables = [f"{k}={v.value if isinstance(v, Enum) else v}" for k,v in dest.items()]
        return "{0}({1})".format(self.__class__.__name__, ", ".join(variables))


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
            return [o.order_id for o in self._orders]
        
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
        
        @property
        def all_orders(self):
            return self._orders

        def get_orders_by_status(self, status_list):
            return list(filter(lambda o: o.status in status_list, self._orders))

        def sort(self):
            desc = self.side == OrderSide.Buy
            self._orders.sort(key=lambda x: x.price, reverse=desc)
        
        def get_order(self, order_id):
            for o in self._orders:
                if order_id == o.order_id:
                    return o
            return None
        
        def prepare_init(self, init_price):
            """ Init stack with limited numbers of orders, based on init_price """

            for i in range(self.active_limit):
                flag = Order.get_direction_flag(self.side, direction="outer")
                price = init_price + flag * self.price_interval * (i+1)
                o = Order(price=price, amount=self.unit_amount, side=self.side, 
                        pair=self.om.pair, user=self.om.user, exchange=self.om.exchange, db=self.om.db)
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

        def order_create_fail(self, order):
            if order in self.to_create:
                order.create_fail()
                self._orders.remove(order)
        
        def order_cancel_ok(self, order):
            if order in self.to_cancel:
                order.cancel_ok()
                self._orders.remove(order)
            else:
                print(f"Order not found in to_cancel: {order}")
        
        def order_traded(self, order):
            if order in self.active_orders:
                order.trade_ok()
                self._orders.remove(order)
            else:
                print(f"Order not found in active orders in {self.side} stack: {order}")
        
        def cancel_all(self):
            for order in self.active_orders:
                order.cancel_ok(force=True)
            self._orders.clear()
        
        @property
        def expected_size(self):
            return len(self.get_orders_by_status(status_list=[OrderStatus.ToCreate, OrderStatus.Created])) 
            
    def __init__(self, price_interval, unit_amount, grid_num, order_limit, balance_threshold=1, additional_info=None) -> None:
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
        self.additional_info = additional_info
    
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
        return [o.order_id for o in self.active_orders]
    
    # Additional information
    def get_additional(self, key):
        if self.additional_info and key in self.additional_info:
            return self.additional_info[key]
        return None

    @property
    def pair(self):
        return self.get_additional('pair')

    @property
    def user(self):
        return self.get_additional('user')
    
    @property
    def exchange(self):
        return self.get_additional('exchange')
    
    @property
    def db(self):
        return self.get_additional('db')
    
    def print_stacks(self):
        for o in [*reversed(self.sell_stack.all_orders), *self.buy_stack.all_orders]:
            print(f"OID<{o.order_id}> {o.side.name} @[{o.price}] - {o.status.value}")
    
    def cancel_all(self):
        for stack in [self.buy_stack, self.sell_stack]:
            stack.cancel_all()
    
    def get_order_by_id(self, order_id):
        """ Find the order and the corresponding stack if exists """
        order, _ = self.get_order_and_stack_by_order_id(order_id=order_id)
        return order

    def get_order_and_stack_by_order_id(self, order_id):
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
        order, stack = self.get_order_and_stack_by_order_id(order_id=order_id)
        stack.order_traded(order)

    def refill_orders(self, mid_price):
        def refill_stack(price_diff, stack: self.OrderStack):
            count = int(price_diff // self.price_interval) - 1
            if count > 0:
                print(f"Filling {count} order(s) in [{stack.side.value}] stack")
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
        
        if exp_buy_size + exp_sell_size > self.order_limit:
            pass

        if exp_buy_size <= self.balance_threshold:
            stack_to_expand = self.buy_stack
            stack_to_shrink = self.sell_stack
            size_diff = exp_sell_size - exp_buy_size
        elif exp_sell_size <= self.balance_threshold:
            stack_to_expand = self.sell_stack
            stack_to_shrink = self.buy_stack
            size_diff = exp_buy_size - exp_sell_size
        
        if stack_to_expand and stack_to_shrink:
            delta = int(size_diff // 2)
            print(f"delta: {delta}")
            stack_to_expand.refill_orders(delta, direction="outer")
            stack_to_shrink.shrink_outer(delta)


def test_order():
    data = {
        'price': 10000,
        'pair': 'btc_jpy',
        'amount': 0.001,
        'side': OrderSide.Sell,
    }
    o1 = Order(**data)
    data['side'] = 'sell'
    o2 = Order.from_dict(source=data)
    print(o1==o2)
    print(o1)
    print(o2)



def test_om():
    import sys
    sys.path.append('.')
    from db.manager import FireStoreManager
    from exchanges import Bitbank
    from utils import read_config


    fsm = FireStoreManager()
    config = read_config()
    api_key = config['api']['key']
    api_secret = config['api']['secret']

    pair = 'eth_jpy'
    ex = Bitbank(pair=pair, api_key=api_key, api_secret=api_secret)

    additional_info = {
        'pair': pair,
        'user': 'user1',
        'exchange': ex.name,
        'db': fsm,
    }
    price_interval=500
    unit_amount=0.2
    grid_num=100
    order_limit=6
    om = OrderManager(price_interval=price_interval, unit_amount=unit_amount,
                    grid_num=grid_num,order_limit=order_limit, additional_info=additional_info)
    om.init_stacks(init_price=3000)
    
    for o in om.orders_to_create:
        om.order_create_ok(o)

    om.print_stacks()

    o = om.buy_stack.active_orders[0]
    om.order_traded(order_id=o.order_id)
    o = om.buy_stack.active_orders[0]
    om.order_traded(order_id=o.order_id)

    om.print_stacks()

    mid_price = 1800
    om.refill_orders(mid_price=mid_price)

    om.blance_stacks()
    for o in om.orders_to_cancel:
        om.order_cancel_ok(o)
    for o in om.orders_to_create:
        om.order_create_ok(order=o)

    om.print_stacks()


if __name__ == '__main__':
    test_order()
    # test_om()
