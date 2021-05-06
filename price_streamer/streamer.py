import websocket
import time
import json
import logging

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

class CBPriceServer(object):

    host = "wss://ws-feed.pro.coinbase.com"
    wsc = None

    def __init__(self, pairs, reconnect_interval=30,  ping=30, ping_timeout=15):
        self.pairs = pairs
        self.channels = ['ticker']
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
        return subscribe_msg

    def _on_open(self, ws):
        logger.debug("Connecting and sending subscribe message: %s" % self.subscribe_msg)
        self._need_reconnection = True
        try:
            ws.send(json.dumps(self._build_subscribe_msg()))
        except Exception as e:
            logger.error("Unable to send subscribe message, connection will probably be closed by server")

    def _on_message(self, ws, msg):
        logger.debug("Received message: %s" % msg)

    def _on_error(self, ws, msg):
        logger.debug("Received error: %s" % msg)

    def _on_close(self, ws):
        logger.debug("Connection closed")

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

if __name__ == "__main__":
    pass