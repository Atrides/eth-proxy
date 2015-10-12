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
    def __init__(self, f):
        self.f = f
        self.jobs = None
        # Hook for LP broadcasts
        self.on_block = defer.Deferred()

    def replace_job(self, newjob):
        self.jobs = newjob
        # Force miners to reload jobs
        on_block = self.on_block
        self.on_block = defer.Deferred()
        on_block.callback(True)

    def submit(self, method, params, worker_name):
        if settings.DEBUG:
            log.info("%s by %s %s" % (method, worker_name, params))
        else:
            log.info("%s by %s" % (method, worker_name) )
        self.f.rpc(method, params, worker_name)
