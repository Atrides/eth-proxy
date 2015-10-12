from zope.interface import implements
from twisted.internet import defer
from twisted.internet import reactor
from twisted.internet.protocol import Protocol
from twisted.web.iweb import IBodyProducer
from twisted.web.client import Agent
from twisted.web.http_headers import Headers

import settings

class ResponseCruncher(Protocol):
    '''Helper for get_page()'''
    def __init__(self, finished):
        self.finished = finished
        self.response = ""
        
    def dataReceived(self, data):
        self.response += data

    def connectionLost(self, reason):
        self.finished.callback(self.response)
        
class StringProducer(object):
    '''Helper for get_page()'''
    implements(IBodyProducer)

    def __init__(self, body):
        self.body = body
        self.length = len(body)

    def startProducing(self, consumer):
        consumer.write(self.body)
        return defer.succeed(None)

    def pauseProducing(self):
        pass

    def stopProducing(self):
        pass
    
@defer.inlineCallbacks        
def get_page(url, method='GET', payload=None, headers=None):
    '''Downloads the page from given URL, using asynchronous networking'''
    agent = Agent(reactor)

    producer = None
    if payload:
        producer = StringProducer(payload)

    _headers = {'User-Agent': [settings.USER_AGENT,]}
    if headers:
        for key, value in headers.items():
            _headers[key] = [value,]
            
    response = (yield agent.request(
        method,
        str(url),
        Headers(_headers),
        producer))

    #for h in response.headers.getAllRawHeaders():
    #    print h

    try:        
        finished = defer.Deferred()
        (yield response).deliverBody(ResponseCruncher(finished))
    except:
        raise Exception("Downloading page '%s' failed" % url)

    defer.returnValue((yield finished))   
    
@defer.inlineCallbacks
def ask_old_server(method, *args):
    '''Perform request in old protocol to electrum servers.
    This is deprecated, used only for proxying some calls.'''
    import urllib
    import ast
    
    # Hack for methods without arguments
    if not len(args):
        args = ['',]
        
    res = (yield get_page('http://electrum.bitcoin.cz/electrum.php', method='POST',
                          headers={"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain"},
                          payload=urllib.urlencode({'q': repr([method,] + list(args))})))
                          
    try:
        data = ast.literal_eval(res)
    except SyntaxError:
        print "Data received from server:", res
        raise Exception("Corrupted data from old electrum server")
    defer.returnValue(data)
