import sys
sys.path.append('.')
import pprint
import datetime
import pandas as pd
import python_bitbankcc
from utils import create_pine_script, read_config
from exchanges import Bitbank


MAX_ORDER_HISTORY_COUNT = 99999999

def check_avg(df, side):
    start = df['executed_at_date'].min()
    end = df['executed_at_date'].max()
    count = df.shape[0]

    df_side = df[df['side']==side]
    count_side = df_side.shape[0]
    df_cost = df_side.price * df_side.amount
    total_cost = df_cost.sum()
    total_amount = df_side.amount.sum()
    avg_price = total_cost / total_amount
    
    avg = {
        'total_cost': total_cost,
        'total_amount': total_amount,
        'avg_price': avg_price,
        'start': start,
        'end': end,
        'count_side': count_side,
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
    df = df[df['cost'] < 5000]
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


def get_trade_history(exchange, symbols, since=None):
    dfs = pd.DataFrame()
    for symbol in symbols:
        pub = python_bitbankcc.public()
        resp = pub.get_ticker(pair=symbol)
        latest_price = float(resp['last'])

        df = exchange.get_trade_history(pair=symbol, since=since)

        res = analyze_earn_rate(df, latest_price)

        get_pine_script(df[df['cost']>2000], symbol=symbol)
        print(symbol)
        pprint.pprint(res)
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
    symbols = ['eth_jpy']

    api_key = config['api']['key']
    api_secret = config['api']['secret']

    # This is the date  I (Micy) started grid trade
    since = datetime.datetime(2021, 7, 5).timestamp()
    # since = 1625496416000

    bb = Bitbank(pair=None, api_key=api_key, api_secret=api_secret)   
    # exchange = python_bitbankcc.private(api_key=api_key, api_secret=api_secret)
    df_trades = get_trade_history(exchange=bb, symbols=symbols, since=since)
    now = datetime.datetime.now()
    filename = 'data/{}-trades.csv'.format(now.strftime("%Y-%m-%d-%H-%M-%S"))
    df_trades.to_csv(filename)


def analyze_candle_height():
    symbols = ['eth_jpy']
    window = '5min'
    exchange = python_bitbankcc.public()

    df_candlesticks = get_candlesticks(exchange=exchange, symbols=symbols, window=window)


if __name__ == "__main__":
    analyze_trade_history()
    # analyze_candle_height()

