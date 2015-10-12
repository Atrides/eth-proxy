'''Simple wrapper around python's logging package'''

import os
import logging
from twisted.python import log as twisted_log

import settings

'''
class Logger(object):
    def debug(self, msg):
        twisted_log.msg(msg)

    def info(self, msg):
        twisted_log.msg(msg)

    def warning(self, msg):
        twisted_log.msg(msg)
        
    def error(self, msg):
        twisted_log.msg(msg)
        
    def critical(self, msg):
        twisted_log.msg(msg)
'''

def get_logger(name):    
    logger = logging.getLogger(name)
    logger.addHandler(stream_handler)
    logger.setLevel(getattr(logging, settings.LOGLEVEL))
    
    if settings.LOGFILE != None:
        logger.addHandler(file_handler)
    
    logger.debug("Logging initialized")
    return logger
    #return Logger()

if settings.DEBUG:
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(module)s.%(funcName)s # %(message)s")
else:
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s # %(message)s")
    
if settings.LOGFILE != None:
    file_handler = logging.FileHandler(os.path.join(settings.LOGDIR, settings.LOGFILE))
    file_handler.setFormatter(fmt)

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(fmt)