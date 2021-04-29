import dashboard.app as dashboard
import logging
import logging.handlers

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
# create console handler and set level to debug
ch1 = logging.StreamHandler()
ch1.setLevel(logging.DEBUG)
#File logging
ch2 = logging.handlers.TimedRotatingFileHandler('dashboard_server.log', when='D', interval=1, backupCount=5, delay=False, utc=True)

# create formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# add formatter to ch
ch1.setFormatter(formatter)
ch2.setFormatter(formatter)
# add ch to logger
logger.addHandler(ch1)
logger.addHandler(ch2)

if __name__ == "__main__":
    dashboard.server.run()