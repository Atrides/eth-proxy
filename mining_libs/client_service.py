from twisted.internet import reactor

from stratum.event_handler import GenericEventHandler
from jobs import Job
import version as _version

import stratum.logger
log = stratum.logger.get_logger('proxy')

class ClientMiningService(GenericEventHandler):
    job_registry = None # Reference to JobRegistry instance
    timeout = None # Reference to IReactorTime object
    
    @classmethod
    def reset_timeout(cls):
        if cls.timeout != None:
            if not cls.timeout.called:
                cls.timeout.cancel()
            cls.timeout = None
            
        cls.timeout = reactor.callLater(180, cls.on_timeout)

    @classmethod
    def on_timeout(cls):
        '''
            Try to reconnect to the pool after 3 minutes of no activity on the connection.
            It will also drop all Stratum connections to sub-miners
            to indicate connection issues.
        '''
        log.error("Connection to upstream pool timed out")
        cls.reset_timeout()
        if not cls.job_registry.f.is_connected:
            cls.job_registry.f.reconnect()
        if cls.job_registry.f1 and not cls.job_registry.f1.is_connected:
            cls.job_registry.f1.reconnect()
        if cls.job_registry.f2 and not cls.job_registry.f2.is_connected:
            cls.job_registry.f2.reconnect()
        if cls.job_registry.f3 and not cls.job_registry.f3.is_connected:
            cls.job_registry.f3.reconnect()

    def handle_event(self, method, params, connection_ref):
        '''Handle RPC calls and notifications from the pool'''
        # Yay, we received something from the pool,
        # let's restart the timeout.
        self.reset_timeout()
        
        if method == 'eth_getWork':
            '''Proxy just received information about new mining job'''
            # Broadcast to getwork clients
            job = Job.build_from_pool(params)
            self.job_registry.replace_job(job, connection_ref)
            
        else:
            '''Pool just asked us for something which we don't support...'''
            log.error("Unhandled method %s with params %s" % (method, params))
