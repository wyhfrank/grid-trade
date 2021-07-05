import sys
import json
import traceback
import requests


class Discord:
    def __init__(self, info_webhook, err_webhook, also_print=True, no_http=False) -> None:
        self.info_webhook = info_webhook
        self.err_webhook = err_webhook
        self.also_print = also_print
        self.no_http = no_http

    def info(self, message):
        self.send(message=message, info_type='info')

    def error(self, message, include_traceback=True):
        tb = ""
        if include_traceback:
            tb = self.get_traceback_message()
        self.send(message=str(message) + tb, info_type='error')

    def send(self, message, info_type='info'):
        if self.also_print:
            print(message)
        
        if self.no_http:
            return
        body = {}
        if info_type == "info":
            url = self.info_webhook
        else:
            url = self.err_webhook
        body['content'] = message
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
        lines = traceback.format_tb(tb)
        tb_str = "".join(lines).strip()
        # Code block im markdown format
        return f"\n```{tb_str}```"


##################
# Tests
def load_discord():
    import sys
    sys.path.append('.')
    from utils import read_config
    config = read_config()
    discord_info_webhook = config['discord']['test']
    discord_error_webhook = config['discord']['test']
    discord = Discord(info_webhook=discord_info_webhook, err_webhook=discord_error_webhook, no_http=True)
    return discord

def test_error():
    d = load_discord()
    d.error('Normal error.')

    try:
        raise Exception("Error with exception.")
    except Exception as e:
        d.error(e)


if __name__ == '__main__':
    test_error()
