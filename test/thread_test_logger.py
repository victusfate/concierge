import logging
import threading
import time

from rsyslog_cee import log
from rsyslog_cee.logger import Logger,LoggerOptions

def reset_logger():
  oNewLogger = Logger(
        LoggerOptions(
            service='concierge.test_logger', # The App Name for Syslog
            console= True,        # we log to console here
            syslog=  False        # Output logs to syslog
        )
    )
  log.set_logger(oNewLogger)
reset_logger()



def worker(arg):
    while not arg['stop']:
        log.debug('Hi from myfunc')
        # logging.debug('Hi from myfunc')
        time.sleep(0.5)

def main():
    # logging.basicConfig(level=logging.DEBUG, format='%(relativeCreated)6d %(threadName)s %(message)s')
    info = {'stop': False}
    thread = threading.Thread(target=worker, args=(info,))
    thread.start()
    while True:
        try:
            log.debug('Hello from main')
            # logging.debug('Hello from main')
            time.sleep(0.75)
        except KeyboardInterrupt:
            info['stop'] = True
            break
    thread.join()

if __name__ == '__main__':
    main()