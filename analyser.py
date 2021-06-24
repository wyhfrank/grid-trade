import pandas as pd
import python_bitbankcc
from utils import read_config


MAX_ORDER_HISTORY_COUNT = 99999999

def check_avg(df, side):
    df_side = df[df['side']==side]
    df_cost = df_side.price * df_side.amount
    total_cost = df_cost.sum()
    total_amount = df_side.amount.sum()
    avg_cost = total_cost / total_amount
    
    avg = {
        'total_cost': total_cost,
        'total_amount': total_amount,
        'avg_cost': avg_cost,
    }
    return avg


def calc_stats(df):
    for side in ['buy', 'sell']:
        avg = check_avg(df, side)
        print(side, avg)


def convert_float(df, cols=['amount', 'price', 'fee_amount_base', 'fee_amount_quote']):
    for col in cols:
        df[col] = df[col].astype(float)


def convert_date(df, cols=['executed_at']):
    for col in cols:
        df[col] = df[col].astype(float)
        # https://stackoverflow.com/a/54488698/1938012
        df[f"{col}_date"] = pd.to_datetime(df[col], unit='ms', utc=True).dt.tz_convert('Asia/Tokyo')


def get_trade_history(exchange, symbols):
    dfs = []
    for symbol in symbols:
        resp = exchange.get_trade_history(pair=symbol, order_count=MAX_ORDER_HISTORY_COUNT)
        data = resp['trades']
        df = pd.DataFrame(data)
        convert_float(df)
        convert_date(df)
        print(df.head())
        dfs.append(df)
    return dfs


def main():
    config = read_config()
    API_KEY = config['api']['key']
    API_SECRET = config['api']['secret']
    symbols = ['btc_jpy']

    exchange = python_bitbankcc.private(api_key=API_KEY, api_secret=API_SECRET)
    df_trades = get_trade_history(exchange=exchange, symbols=symbols)
    


if __name__ == "__main__":
    main()
