import json
import time

from twisted.internet import defer, threads
from twisted.web.resource import Resource
from twisted.web.server import NOT_DONE_YET

import stratum.logger
log = stratum.logger.get_logger('proxy')

class Root(Resource):
    isLeaf = True

    def __init__(self, job_registry, enable_worker_id):
        Resource.__init__(self)
        self.job_registry = job_registry
        self.isWorkerID = enable_worker_id
        self.submitHashrates = {}
        self.getWorkCacheTimeout = {"work":"","time":0}

    def json_response(self, msg_id, result):
        resp = json.dumps({'id': msg_id, 'jsonrpc': '2.0', 'result': result})
        return resp

    def json_error(self, msg_id, message):
        resp = json.dumps({'id': msg_id, 'jsonrpc': '2.0', 'result': False, 'error': message})
        return resp

    def render_POST(self, request):
        request.setHeader('content-type', 'application/json')
        data = json.loads(request.content.read())

        if not self.job_registry.jobs:
            log.warning('Proxy is waiting for a job...')
            request.write(self.json_error(data.get('id', 0), "Proxy is waiting for a job...")+'\n')
            request.finish()
            return NOT_DONE_YET

        if not data.has_key('method'):
            response = self.json_error(data.get('id'), "Need methods")+'\n'
        elif data['method'] == 'eth_getWork':
            if self.getWorkCacheTimeout["work"]==self.job_registry.jobs.params[0] and int(time.time())-self.getWorkCacheTimeout["time"]>=self.job_registry.coinTimeout:
                log.warning('Job timeout. Proxy is waiting for an updated job. Please restart proxy!')
                response = self.json_error(data.get('id', 0), "Job timeout. Proxy is waiting for an updated job...")
            else:
                if self.getWorkCacheTimeout["work"]!=self.job_registry.jobs.params[0]:
                    self.getWorkCacheTimeout = {"work":self.job_registry.jobs.params[0],"time":int(time.time())}
                response = self.json_response(data.get('id', 0), self.job_registry.jobs.params)
        elif data['method'] == 'eth_submitWork' or data['method'] == 'eth_submitHashrate':
            if self.isWorkerID:
                worker_name = request.uri[1:15].split("/")[0]
                if not worker_name:
                    ip_temp = request.getClientIP().split('.')
                    worker_name = str( int(ip_temp[0])*16777216 + int(ip_temp[1])*65536 + int(ip_temp[2])*256 + int(ip_temp[3]) )
            else:
                worker_name = ''

            if data['method'] == 'eth_submitHashrate':
                if worker_name and (not self.submitHashrates.has_key(worker_name) or int(time.time())-self.submitHashrates[worker_name]>=60):
                    self.submitHashrates[worker_name] = int(time.time())
                    log.info('Hashrate for %s is %s MHs' % (worker_name,int(data['params'][0],16)/1000000.0 ) )
                    threads.deferToThread(self.job_registry.submit, data['method'], data['params'], worker_name)
            elif data['method'] == 'eth_submitWork':
                threads.deferToThread(self.job_registry.submit, data['method'], data['params'], worker_name)
            response = self.json_response(data.get('id', 0), True)
        else:
            response = self.json_error(data.get('id'), "Unsupported method '%s'" % data['method'])

        try:
            request.write(response+'\n')
            request.finish()
            return NOT_DONE_YET
        except Exception:
            return

    def render_GET(self, request):
        ret_text = "Ethereum stratum proxy<br>"
        if self.job_registry and self.job_registry.jobs and self.job_registry.jobs.params:
            ret_text += "DAG-file: %s<br><br>" % str(self.job_registry.jobs.params[1][2:18])
        if self.job_registry.f:
            connected = "connected" if (hasattr(self.job_registry.f, "is_connected") and self.job_registry.f.is_connected) else "disconnected"
            ret_text += "Main server %s:%s (%s) %s<br>" % (self.job_registry.f.main_host[0], self.job_registry.f.main_host[1], self.job_registry.f.remote_ip, connected)
        if self.job_registry.f1:
            connected = "connected" if (hasattr(self.job_registry.f1, "is_connected") and self.job_registry.f1.is_connected) else "disconnected"
            ret_text += "Failover server1 %s:%s (%s) %s<br>" % (self.job_registry.f1.main_host[0], self.job_registry.f1.main_host[1], self.job_registry.f1.remote_ip, connected)
        if self.job_registry.f2:
            connected = "connected" if (hasattr(self.job_registry.f2, "is_connected") and self.job_registry.f2.is_connected) else "disconnected"
            ret_text += "Failover server2 %s:%s (%s) %s<br>" % (self.job_registry.f2.main_host[0], self.job_registry.f2.main_host[1], self.job_registry.f2.remote_ip, connected)
        if self.job_registry.f3:
            connected = "connected" if (hasattr(self.job_registry.f3, "is_connected") and self.job_registry.f3.is_connected) else "disconnected"
            ret_text += "Failover server3 %s:%s (%s) %s<br>" % (self.job_registry.f3.main_host[0], self.job_registry.f3.main_host[1], self.job_registry.f3.remote_ip, connected)
        return ret_text
