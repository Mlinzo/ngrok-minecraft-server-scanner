import logging
import sys

logging.basicConfig(level=logging.INFO, format='')

def gen_logger(loggername: str):
    logger =logging.getLogger(loggername)
    syslog = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(f'[{loggername}] %(message)s')
    syslog.setFormatter(formatter)
    logger.addHandler(syslog)
    logger.propagate = False
    return logger

db_logger = gen_logger('db')
scanner_logger = gen_logger('scanner')
threads_logger = gen_logger('threads')
main_logger = gen_logger('main')

THREADS=2048
THREADS_NOTIFY_PERIOD=15
DB_POOL_RELEASE_PERIOD=60
SOCKET_RESPONSE_TIMEOUT=10
DB_PATH='mservers.db'
