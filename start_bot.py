import logging
import logging.handlers
import argparse
import bot.robot

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('env', nargs='?', default='test', type=str, help="Chose environment", choices=['production', 'test'])
    parser.add_argument('-c', '--configuration', nargs=1, default='configuration', type=str, help="Chose configration file")
    args = parser.parse_args()
    logger.info("Starting bot in %s mode using %s configuration file" % (args.env, args.configuration[0]+'.json'))
    # create console handler and set level to debug
    ch1 = logging.StreamHandler()
    ch1.setLevel(logging.DEBUG)
    #File logging
    ch2 = logging.handlers.TimedRotatingFileHandler('robot_'+args.configuration[-1].split('_')[0]+'.log', when='D', interval=1, backupCount=5, delay=False, utc=True)
    # create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    # add formatter to ch
    ch1.setFormatter(formatter)
    ch2.setFormatter(formatter)
    # add ch to logger
    logger.addHandler(ch1)
    logger.addHandler(ch2)
    bot.robot.run(args.env, configuration_file=args.configuration[0])

if __name__ == "__main__":
    main()