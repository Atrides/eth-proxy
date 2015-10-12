import time
import logger
log = logger.get_logger('stats')

class PeerStats(object):
    '''Stub for server statistics'''
    counter = 0
    changes = 0
    
    @classmethod
    def client_connected(cls, ip):
        cls.counter += 1
        cls.changes += 1
        
        cls.print_stats()
        
    @classmethod
    def client_disconnected(cls, ip):
        cls.counter -= 1
        cls.changes += 1
        
        cls.print_stats()
        
    @classmethod
    def print_stats(cls):
        if cls.counter and float(cls.changes) / cls.counter < 0.05:
            # Print connection stats only when more than
            # 5% connections change to avoid log spam
            return
        
        log.info("%d peers connected, state changed %d times" % (cls.counter, cls.changes))
        cls.changes = 0
        
    @classmethod
    def get_connected_clients(cls):
        return cls.counter

'''    
class CpuStats(object):
    start_time = time.time()
            
    @classmethod
    def get_time(cls):
        diff = time.time() - cls.start_time
        return resource.getrusage(resource.RUSAGE_SELF)[0] / diff
'''