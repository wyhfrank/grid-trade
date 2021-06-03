import python_bitbankcc
import time, threading
import json
import requests

PUB = python_bitbankcc.public()

def init(now, unit, crypto_name):
    """
    Build grid according to price of crypto currency now
    Set grid number & interval you want
    """
    assets = {}
    assets['crypto_number'] = 0
    assets['JPY'] = 0 
    GRID_NUMBER = 200
    INTERVAL = 500
    CELL = (GRID_NUMBER / 2) * INTERVAL + now
    GROUND = now - (GRID_NUMBER / 2) * INTERVAL
    buy_stack = []
    sell_stack = []
    upper, lower = CELL, GROUND
    while upper > now and lower < now:
        if upper > now:
            sell_stack.append(("sell", upper))
            upper -= INTERVAL
            assets['crypto_number'] += unit
        if lower < now:
            buy_stack.append(("buy", lower))
            lower += INTERVAL
            assets['JPY'] += lower * unit
    assets['crypto_number'] = round(assets['crypto_number'], 3)
    assets['cost'] = assets['JPY'] + assets['crypto_number'] * now
    send_discord_msg(f"Init cost: {assets['cost']:.4f}(JPY: {assets['JPY']:.2f}, {crypto_name}: {assets['crypto_number']}), price now:{now}")
    return assets, buy_stack, sell_stack


def trade(init_cost, buy_stack, sell_stack, unit, crypto_name, count, crypto_number, JPY):
    price = float(PUB.get_ticker(f'{crypto_name}_jpy')['last'])
    flag = ""
    tmp = []
    if sell_stack and sell_stack[-1][1] <= price:
        while sell_stack and sell_stack[-1][1] < price:
            count += 1
            flag = "sell"
            crypto_number -= unit
            crypto_number = round(crypto_number, 3)
            elem = sell_stack.pop()
            JPY += (elem[1] * unit * 1.0002)
            tmp.append(("buy", elem[1])) 
            send_discord_msg(f"#{count} sell {unit} {crypto_name} on price: {elem[1]}")
        get_income(init_cost, JPY, crypto_number, price, crypto_name)

    # buy when price get low
    if buy_stack and buy_stack[-1][1] > price:
        while buy_stack and buy_stack[-1][1] > price:
            count += 1
            flag = "buy"
            crypto_number += unit
            crypto_number = round(crypto_number, 3)
            elem = buy_stack.pop()
            JPY -= (elem[1] * unit * 0.9998)
            tmp.append(("sell", elem[1]))
            send_discord_msg(f"#{count} buy {unit} {crypto_name} on price: {elem[1]}")
        get_income(init_cost, JPY, crypto_number, price, crypto_name)
    # add new order to stack
    if flag == "buy":
        while tmp:
            sell_stack.append(tmp.pop())
    elif flag == "sell":
        while tmp:
            buy_stack.append(tmp.pop())
    print(f"buy: {buy_stack[-1]}, sell: {sell_stack[-1]}, price: {price}")
    threading.Timer(1, trade, [init_cost, buy_stack, sell_stack, unit, crypto_name, count, crypto_number, JPY]).start()


def get_income(init_cost, JPY, crypto_number, price, crypto_name):
    income = JPY + crypto_number * price - init_cost
    send_discord_msg(f"JPY: {JPY:.4f}, {crypto_name}:{crypto_number}, init_cost: {init_cost:.4f}, income:{income:.4f}")


def send_discord_msg(message):
    body = {}
    url = "https://discord.com/api/webhooks/848375578906329118/wIxt-LJ2jyFpprbfQ-xjB3fjhJnTw3RpZuLes8RUKWGlrx8Q8EJjkJy4lPCgmt4NpiYA"
    body['content'] = message
    payload = json.dumps(body)
    headers = {
      'Content-Type': 'application/json',
    }
    requests.request("POST", url, headers=headers, data=payload)


if __name__ == '__main__':
    # trade(1, 2)
    crypto_name = "eth"
    unit = 0.003
    value = PUB.get_ticker(f'{crypto_name}_jpy') 
    assets, buy_stack, sell_stack = init(float(value['last']), unit, crypto_name)
    trade(assets['cost'], buy_stack, sell_stack, unit, crypto_name, 0, assets['crypto_number'], assets['JPY'])
