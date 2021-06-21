from enum import Enum


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

