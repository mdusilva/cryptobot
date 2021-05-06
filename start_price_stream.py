import logging
import logging.handlers
import json
import price_streamer.streamer

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
# create console handler and set level to debug
ch1 = logging.StreamHandler()
ch1.setLevel(logging.DEBUG)
#File logging
ch2 = logging.handlers.TimedRotatingFileHandler('price_stream.log', when='D', interval=1, backupCount=5, delay=False, utc=True)

# create formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# add formatter to ch
ch1.setFormatter(formatter)
ch2.setFormatter(formatter)
# add ch to logger
logger.addHandler(ch1)
logger.addHandler(ch2)

def main():
    pairs = None
    with open("configuration.json", "r") as configuration_file:
        pairs = json.loads(configuration_file).get('universe', []) + [json.loads(configuration_file).get('base_currency', 'BTC')]
    if pairs:
        logger.info("Starting price stream for %s pairs" % pairs)
        price_streamer.streamer.CBPriceServer(pairs).connect()

if __name__ == "__main__":
    main()