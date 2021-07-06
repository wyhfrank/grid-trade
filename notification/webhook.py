import sys
import json
import traceback
import requests


class Discord:
    # https://www.spycolor.com/f2003c#
    color_buy = 43127
    color_sell = 15859772

    def __init__(self, info_webhook, err_webhook, also_print=True, no_http=False) -> None:
        self.info_webhook = info_webhook
        self.err_webhook = err_webhook
        self.also_print = also_print
        self.no_http = no_http

    def info(self, message, logger=None):
        self.send(message=message, info_type='info', logger=logger)

    def error(self, message, logger=None, include_traceback=True):
        tb = ""
        if include_traceback:
            tb = self.get_traceback_message()
        self.send(message=str(message) + tb, info_type='error', logger=logger)

    def send(self, message, info_type='info', logger=None):
        if self.also_print:
            if logger:
                func = logger.info if info_type=='info' else logger.error
                func(message)
            else:
                print(message)
        body = {}
        body['content'] = message
        self._send_post(body=body, info_type=info_type)
    
    def send_buy_msg(self, message):
        self.send_trade_msg(message=message, side='buy')

    def send_sell_msg(self, message):
        self.send_trade_msg(message=message, side='sell')

    def send_trade_msg(self, message, side='buy'):
        # https://discord.com/developers/docs/resources/channel#embed-object
        color = self.color_buy if side == 'buy' else self.color_sell
        embed = {
            "description": message,
            "color": color,
        }
        body = {
            "embeds": [embed], # Care: this should be an array
        }
        self._send_post(body=body, info_type='info')

    def _send_post(self, body, info_type='info'):
        if self.no_http:
            return
        if info_type == "info":
            url = self.info_webhook
        else:
            url = self.err_webhook
        payload = json.dumps(body)
        headers = {
            'Content-Type': 'application/json',
        }
        requests.request("POST", url, headers=headers, data=payload)

    @staticmethod
    def get_traceback_message():
        _, _, tb = sys.exc_info()
        if not tb:
            return ""
        # https://docs.python.org/3/library/traceback.html#traceback.format_tb
        lines = traceback.format_tb(tb)
        tb_str = "".join(lines).strip()
        # Code block im markdown format
        return f"\n```{tb_str}```"


##################
# Tests
def load_discord(no_http=False):
    import sys
    sys.path.append('.')
    from utils import read_config
    config = read_config()
    discord_info_webhook = config['discord']['test']
    discord_error_webhook = config['discord']['test']
    discord = Discord(info_webhook=discord_info_webhook, err_webhook=discord_error_webhook, no_http=no_http)
    return discord

def test_error():
    d = load_discord()
    d.error('Normal error.')

    try:
        raise Exception("Error with exception.")
    except Exception as e:
        d.error(e)

def test_trade_msg():
    d = load_discord()
    d.send_buy_msg('#16. Micy buy 0.2 ETH @ **24000**. (buy #6)')
    d.send_sell_msg('#17. Micy sell 0.2 ETH @ **24000**. (sell #4)')


def test_logger():
    import sys
    sys.path.append('.')
    import logging
    from utils import setup_logging
    setup_logging(level=logging.DEBUG)
    logger = logging.getLogger(__name__)

    d = load_discord(no_http=True)
    d.info('info', logger=logger)
    d.error('error', logger=logger)
    d.error('error, no logger')
    

if __name__ == '__main__':
    # test_error()
    # test_trade_msg()
    test_logger()
