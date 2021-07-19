import cbpro, time
class myWebsocketClient(cbpro.WebsocketClient):
    def on_open(self):
        self.url = "wss://ws-feed.pro.coinbase.com/"
        self.products = ["LTC-USD"]
        self.message_count = 0
        self.channels = ['ticker']
        print("Lets count the messages!")

    def on_message(self, msg):
        self.message_count += 1
        print("MESSAGE COUNT=%s" % self.message_count)
        print(msg)
        # if 'price' in msg and 'type' in msg:
        #     print ("Message type:", msg["type"],
        #            "\t@ {:.3f}".format(float(msg["price"])))

    def on_close(self):
        print("-- Goodbye! --")

wsClient = myWebsocketClient()
wsClient.start()
print(wsClient.url, wsClient.products)
while (wsClient.message_count < 9):
    print ("\nmessage_count =", "{} \n".format(wsClient.message_count))
    time.sleep(1)
    if wsClient.ws is not None:
        wsClient.ws.ping("keepalive")
        print ("PING SENT")
wsClient.close()