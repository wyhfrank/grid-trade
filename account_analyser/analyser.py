import sys
sys.path.append('.')
import datetime
import pandas as pd
import python_bitbankcc
from utils import create_pine_script, read_config


MAX_ORDER_HISTORY_COUNT = 99999999

def check_avg(df, side):
    start = df['executed_at_date'].min()
    end = df['executed_at_date'].max()
    count = df.shape[0]

    df_side = df[df['side']==side]
    df_cost = df_side.price * df_side.amount
    total_cost = df_cost.sum()
    total_amount = df_side.amount.sum()
    avg_cost = total_cost / total_amount
    
    avg = {
        'total_cost': total_cost,
        'total_amount': total_amount,
        'avg_cost': avg_cost,
        'start': start,
        'end': end,
        'count': count,
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


def analyze_earn_rate(df, latest_price):
    df = df[df['cost'] > 5000]
    res = {}
    for side in ['buy', 'sell']:
        res[side] = check_avg(df, side)
    
    buy_cost = res['buy']['total_cost']
    sell_cost = res['sell']['total_cost']
    current_amount = res['buy']['total_amount'] - res['sell']['total_amount']
    pivot_price = (buy_cost - sell_cost) / current_amount
    res['pivot_price'] = pivot_price

    res['earn_rate'] = (sell_cost + current_amount * latest_price - buy_cost) / buy_cost

    return res


def get_pine_script(df, symbol):
    code = create_pine_script(df)
    with open(f"data/{symbol}.script.txt", 'w') as f:
        f.write(code)


def get_trade_history(exchange, symbols):
    dfs = pd.DataFrame()
    for symbol in symbols:
        pub = python_bitbankcc.public()
        resp = pub.get_ticker(pair=symbol)
        latest_price = float(resp['last'])

        resp = exchange.get_trade_history(pair=symbol, order_count=MAX_ORDER_HISTORY_COUNT)
        data = resp['trades']
        
        df = pd.DataFrame(data)
        convert_float(df)
        df['cost'] = df['amount'] * df['price']
        convert_date(df)

        res = analyze_earn_rate(df, latest_price)

        get_pine_script(df[df['cost']>2000], symbol=symbol)
        print(symbol, res)
        # print(res)
        # print(df.head())

        dfs = dfs.append(df)
    return dfs


def get_candlesticks(exchange, symbols, window='1min', date=datetime.datetime.now()-datetime.timedelta(days=1)):
    date_str = date.strftime('%Y%m%d')
    date_str
    dfs = {}
    for symbol in symbols:
        resp = exchange.get_candlestick(pair=symbol, candle_type=window, yyyymmdd=date_str)
        data = resp['candlestick'][0]['ohlcv']
        df = pd.DataFrame(data)
        df.columns = ['open', 'high', 'low', 'close', 'volume', 'timestamp']
        convert_float(df, cols=['open', 'high', 'low', 'close', 'volume',])
        convert_date(df, cols=['timestamp'])
        df['height'] = df['high'] - df['low']
        print(df.head())

        print(df['height'].describe())

        dfs[symbol] = df
    return dfs


def analyze_trade_history():
    config = read_config()
    API_KEY = config['api']['key']
    API_SECRET = config['api']['secret']
    symbols = ['btc_jpy', 'eth_jpy']

    exchange = python_bitbankcc.private(api_key=API_KEY, api_secret=API_SECRET)
    df_trades = get_trade_history(exchange=exchange, symbols=symbols)
    df_trades.to_csv('data/trades.csv')


def analyze_candle_height():
    symbols = ['eth_jpy']
    window = '5min'
    exchange = python_bitbankcc.public()

    df_candlesticks = get_candlesticks(exchange=exchange, symbols=symbols, window=window)


if __name__ == "__main__":
    analyze_trade_history()
    # analyze_candle_height()

