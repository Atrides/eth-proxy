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
        if data['method'] == 'eth_getWork':
            response = self.json_response(data.get('id', 0), self.job_registry.jobs.params)
        elif data['method'] == 'eth_submitWork' or data['method'] == 'eth_submitHashrate':
            if self.isWorkerID:
                worker_name = request.uri[1:15]
                if not worker_name:
                    ip_temp = request.getClientIP().split('.')
                    worker_name = str( int(ip_temp[0])*16777216 + int(ip_temp[1])*65536 + int(ip_temp[2])*256 + int(ip_temp[3]) )
            else:
                worker_name = ''

            if data['method'] == 'eth_submitWork': # ToFix!!!!
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
        return "Ethereum startum proxy"
