from grid_trade.orders import OrderManager
from exchanges import Exchange


class GridBot:

    class Parameter:
        def __init__(self, unit_amount, price_interval, init_base, init_quote, init_price, support, grid_num, fee=0) -> None:
            self.unit_amount = unit_amount
            self.price_interval = price_interval
            self.init_base = init_base
            self.init_quote = init_quote
            self.init_price = init_price
            self.support = support
            self.grid_num = grid_num
            self.fee = fee
        
        @property
        def lowest_price(self):
            return self.support

        @property
        def half_grid_num(self):
            return self.grid_num // 2

        def get_highest_earn_rate_per_grid(self):
            return self.price_interval / self.lowest_price - 2 * self.fee

        def get_lowest_earn_rate_per_grid(self):
            second_highest_price = self.init_price + (self.half_grid_num-1) * self.price_interval
            return self.price_interval / second_highest_price - 2 * self.fee

        @classmethod
        def calc_grid_params(cls, init_base, init_quote, init_price, support, grid_num=100, fee=0):
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
                        init_base=init_base, init_quote=init_quote, support=support, grid_num=grid_num, fee=fee)
            return param

        def __repr__(self) -> str:
            # attrs = ['unit_amount', 'price_interval']
            paris = {
                **self.__dict__,
                "highest_grid_earn_rate": self.get_highest_earn_rate_per_grid(),
                "lowest_grid_earn_rate": self.get_lowest_earn_rate_per_grid(),
            }
            return "<Param: {}>".format(", ".join([f"{k}[{v}]" for k, v in paris.items()]))

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
