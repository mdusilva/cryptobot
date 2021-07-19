import websocket
import hmac
import hashlib
import time
import base64
import json
import logging

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

def get_auth_headers(timestamp, message, api_key, secret_key, passphrase):
    message = message.encode('ascii')
    hmac_key = base64.b64decode(secret_key)
    signature = hmac.new(hmac_key, message, hashlib.sha256)
    signature_b64 = base64.b64encode(signature.digest()).decode('utf-8')
    return {
        'Content-Type': 'Application/JSON',
        'CB-ACCESS-SIGN': signature_b64,
        'CB-ACCESS-TIMESTAMP': timestamp,
        'CB-ACCESS-KEY': api_key,
        'CB-ACCESS-PASSPHRASE': passphrase
    }

class CBChannelServer(object):

    host = "wss://ws-feed.pro.coinbase.com"
    wsc = None

    def __init__(self, pairs, channel, host="wss://ws-feed.pro.coinbase.com", 
                auth=False, api_key="", api_secret="", api_passphrase="", reconnect_interval=30,  ping=30, ping_timeout=15):
        self.pairs = pairs
        self.channels = [channel]
        self.host = host
        self.auth = auth
        self.api_key = api_key
        self.api_secret = api_secret
        self.api_passphrase = api_passphrase
        self._need_reconnection = False
        self._ping_interval=ping
        self._ping_timeout = ping_timeout
        self._reconnect_interval = reconnect_interval

    def _build_subscribe_msg(self):
        subscribe_msg = {
            "type": "subscribe",
            "product_ids": self.pairs,
            "channels": self.channels
        }
        if self.auth:
            timestamp = str(time.time())
            message = timestamp + 'GET' + '/users/self/verify'
            auth_headers = get_auth_headers(timestamp, message, self.api_key, self.api_secret, self.api_passphrase)
            subscribe_msg['signature'] = auth_headers['CB-ACCESS-SIGN']
            subscribe_msg['key'] = auth_headers['CB-ACCESS-KEY']
            subscribe_msg['passphrase'] = auth_headers['CB-ACCESS-PASSPHRASE']
            subscribe_msg['timestamp'] = auth_headers['CB-ACCESS-TIMESTAMP']
        return subscribe_msg

    def _on_open(self, ws):
        subscribe_msg = self._build_subscribe_msg()
        logger.debug("Connecting and sending subscribe message: %s" % subscribe_msg)
        self._need_reconnection = True
        try:
            ws.send(json.dumps(subscribe_msg))
        except Exception as e:
            logger.error("Unable to send subscribe message, connection will probably be closed by server")
        try:
            self.on_open()
        except Exception as e:
            logger.error("Unable to run on open function: %s" % e)

    def _on_message(self, ws, msg):
        logger.debug("Received message: %s" % msg)
        try:
            self.on_message(msg)
        except Exception as e:
            logger.error("Unable to run on message function: %s" % e)

    def _on_error(self, ws, msg):
        logger.debug("Received error: %s" % msg)
        try:
            self.on_error(msg)
        except Exception as e:
            logger.error("Unable to run on error function: %s" % e)

    def _on_close(self, ws):
        logger.debug("Connection closed")
        try:
            self.on_close()
        except Exception as e:
            logger.error("Unable to run on close function: %s" % e)

    def _on_ping(self, ws, msg):
        logger.debug("Received PING: %s" % msg)

    def _on_pong(self, ws, msg):
        logger.debug("Received PONG: %s" % msg)

    def connect(self):
        websocket.enableTrace(True)
        self.wsc = websocket.WebSocketApp(
            self.host, 
            on_open=self._on_open, 
            on_message=self._on_message, 
            on_error=self._on_error, 
            on_close=self._on_close,
            on_ping=self._on_ping, 
            on_pong=self._on_pong)

        logger.debug("Connecting to server with ping interval %s and ping timeout %s" % (self._ping_interval, self._ping_timeout))
        self.wsc.run_forever(ping_interval=self._ping_interval, ping_timeout=self._ping_timeout)
        while self._need_reconnection:
            logger.debug("Attempting to reconnect...")
            self.wsc.run_forever(ping_interval=self._ping_interval, ping_timeout=self._ping_timeout)
            time.sleep(self._reconnect_interval)

    def close(self):
        logger.debug("Closing connection...")
        self._need_reconnection = False
        if self.wsc is not None:
            self.wsc.close()

    def on_message(self, msg):
        #Overide to perform desired action on message arrival
        pass

    def on_open(self):
        #Overide to perform desired action on open
        pass

    def on_error(self, msg):
        #Overide to perform desired action on error arrival
        pass

    def on_close(self):
        #Overide to perform desired action on error arrival
        pass

if __name__ == "__main__":
    pass