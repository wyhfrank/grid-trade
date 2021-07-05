import json
import requests


class Discord:
    def __init__(self, info_webhook, err_webhook) -> None:
        self.info_webhook = info_webhook
        self.err_webhook = err_webhook

    def info(self, message):
        self.send(message=message, info_type='info')

    def error(self, message):
        self.send(message=message, info_type='error')

    def send(self, message, info_type='info'):
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
