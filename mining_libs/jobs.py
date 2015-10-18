from twisted.internet import defer

from stratum import settings
import stratum.logger
log = stratum.logger.get_logger('proxy')

class Job(object):
    def __init__(self):
        self.params = ''

    @classmethod
    def build_from_pool(cls, getWorkParams):
        '''Build job object from Stratum server broadcast'''
        job = Job()
        job.params = getWorkParams
        return job

class JobRegistry(object):
    def __init__(self, f, ff):
        self.f = f
        self.ff = ff
        self.jobs = None
        # Hook for LP broadcasts
        self.on_block = defer.Deferred()

    def replace_job(self, newjob, connection_ref):
        is_main_pool = connection_ref._get_ip() == self.f.remote_ip
        if is_main_pool:
            log_text = "MAIN NEW_JOB"
        else:
            log_text = "FAILOVER NEW_JOB"

        if (self.f.is_connected and is_main_pool) or (not self.f.is_connected and self.ff and self.ff.is_connected and not is_main_pool):
            if stratum.logger.settings.DEBUG:
                log.debug("%s %s" % (log_text, newjob.params))
            else:
                log.info(log_text)
            self.jobs = newjob
            # Force miners to reload jobs
            on_block = self.on_block
            self.on_block = defer.Deferred()
            on_block.callback(True)
        elif stratum.logger.settings.DEBUG:
            log.debug("%s NOT_USED %s" % (log_text, newjob.params))

    def submit(self, method, params, worker_name):
        log_text = ""
        if settings.DEBUG:
            log_text = "%s by %s %s" % (method, worker_name, params)
        elif method=="eth_submitWork":
            log_text = "%s by %s" % (method, worker_name)
        if self.f.is_connected:
            if log_text:
                log.info( "MAIN %s" % log_text )
            self.f.rpc(method, params, worker_name)
        elif self.ff and self.ff.is_connected:
            if log_text:
                log.info( "FAILOVER %s" % log_text )
            self.ff.rpc(method, params, worker_name)
