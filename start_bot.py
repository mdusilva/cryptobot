import logging
import logging.handlers
import argparse
import bot.robot

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
# create console handler and set level to debug
ch1 = logging.StreamHandler()
ch1.setLevel(logging.DEBUG)
#File logging
ch2 = logging.handlers.TimedRotatingFileHandler('robot.log', when='D', interval=1, backupCount=5, delay=False, utc=True)

# create formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# add formatter to ch
ch1.setFormatter(formatter)
ch2.setFormatter(formatter)
# add ch to logger
logger.addHandler(ch1)
logger.addHandler(ch2)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('env', nargs='?', default='test', type=str, help="Chose environment", choices=['production', 'test'])
    args = parser.parse_args()
    logger.info("Starting bot in %s mode" % args.env)
    bot.robot.run(args.env)

if __name__ == "__main__":
    main()