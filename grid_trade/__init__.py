from grid_trade.orders import Order
from grid_trade.base import GridBot
from utils import init_formatted_properties


def set_precision(price_precision, amount_precision):
    GridBot.Parameter.set_precision(price_precision=price_precision, amount_precision=amount_precision)
    init_formatted_properties(GridBot.Parameter)

    Order.set_precision(price_precision=price_precision, amount_precision=amount_precision)
    init_formatted_properties(Order)
