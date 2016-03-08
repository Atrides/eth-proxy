from twisted.internet.protocol import ServerFactory
from twisted.internet.protocol import ReconnectingClientFactory
from twisted.internet import reactor, defer, endpoints

import socksclient
import custom_exceptions
from protocol import Protocol, ClientProtocol
from event_handler import GenericEventHandler

import logger
log = logger.get_logger('socket_transport')

def sockswrapper(proxy, dest):
    endpoint = endpoints.TCP4ClientEndpoint(reactor, dest[0], dest[1])
    return socksclient.SOCKSWrapper(reactor, proxy[0], proxy[1], endpoint)
  
class SocketTransportFactory(ServerFactory):
    def __init__(self, debug=False, signing_key=None, signing_id=None, event_handler=GenericEventHandler,
                 tcp_proxy_protocol_enable=False):
        self.debug = debug
        self.signing_key = signing_key
        self.signing_id = signing_id
        self.event_handler = event_handler
        self.protocol = Protocol
        
        # Read settings.TCP_PROXY_PROTOCOL documentation
        self.tcp_proxy_protocol_enable = tcp_proxy_protocol_enable
        
class SocketTransportClientFactory(ReconnectingClientFactory):
    def __init__(self, host, port, allow_trusted=True, allow_untrusted=False,
                 debug=False, signing_key=None, signing_id=None,
                 is_reconnecting=True, proxy=None,
                 event_handler=GenericEventHandler):
        self.debug = debug
        self.maxDelay = 60
        self.is_reconnecting = is_reconnecting
        self.signing_key = signing_key
        self.signing_id = signing_id
        self.client = None # Reference to open connection
        self.on_disconnect = defer.Deferred()
        self.on_connect = defer.Deferred()
        self.peers_trusted = {}
        self.peers_untrusted = {}
        self.main_host = (host, port)
        self.new_host = None
        self.proxy = proxy
        self.is_failover = False
        self.is_connected = False
        self.remote_ip = None
        
        self.event_handler = event_handler
        self.protocol = ClientProtocol
        self.after_connect = []
        
        self.connect()
        
    def connect(self):
        if self.proxy:
            self.timeout_handler = reactor.callLater(60, self.connection_timeout)
            sw = sockswrapper(self.proxy, self.main_host)
            sw.connect(self)
        else:
            self.timeout_handler = reactor.callLater(30, self.connection_timeout)
            reactor.connectTCP(self.main_host[0], self.main_host[1], self)
            
    '''
    This shouldn't be a part of transport layer
    def add_peers(self, peers):
        # FIXME: Use this list when current connection fails
        for peer in peers:
            hash = "%s%s%s" % (peer['hostname'], peer['ipv4'], peer['ipv6'])
            
            which = self.peers_trusted if peer['trusted'] else self.peers_untrusted
            which[hash] = peer
                 
        #print self.peers_trusted
        #print self.peers_untrusted
    '''
         
    def connection_timeout(self):
        self.timeout_handler = None
        
        if self.client:
            return
        
        e = custom_exceptions.TransportException("SocketTransportClientFactory connection timed out")
        if not self.on_connect.called:
            d = self.on_connect
            self.on_connect = defer.Deferred()
            d.errback(e)
        else:
            raise e
        
    def rpc(self, method, params, worker, *args, **kwargs):
        if not self.client:
            raise custom_exceptions.TransportException("Not connected")
        
        return self.client.rpc(method, params, worker, *args, **kwargs)
    
    def subscribe(self, method, params, *args, **kwargs):
        '''
        This is like standard RPC call, except that parameters are stored
        into after_connect list, so the same command will perform again
        on restored connection.
        '''
        if not self.client:
            raise custom_exceptions.TransportException("Not connected")
        
        self.after_connect.append((method, params))
        return self.client.rpc(method, params, worker, *args, **kwargs)
    
    def reconnect(self, host=None, port=None, wait=None):
        '''Close current connection and start new one.
        If host or port specified, it will be used for new connection.'''

        new = list(self.main_host)
        if host:
            new[0] = host
        if port:
            new[1] = port
        self.new_host = tuple(new)

        if self.client and self.client.connected:
            if wait != None:
                self.delay = wait
            self.client.transport.connector.disconnect()
        
    def retry(self, connector=None):
        if not self.is_reconnecting:
            return

        if connector is None:
            if self.connector is None:
                raise ValueError("no connector to retry")
            else:
                connector = self.connector
        
        if self.new_host:
            # Switch to new host if any
            connector.host = self.new_host[0]
            connector.port = self.new_host[1]
            self.main_host = self.new_host
            self.new_host = None
    
        return ReconnectingClientFactory.retry(self, connector)
            
    def buildProtocol(self, addr):
        self.resetDelay()
        #if not self.is_reconnecting: raise
        return ReconnectingClientFactory.buildProtocol(self, addr)
                
    def clientConnectionLost(self, connector, reason):
        if self.is_reconnecting:
            log.debug(reason)
            ReconnectingClientFactory.clientConnectionLost(self, connector, reason)
        
    def clientConnectionFailed(self, connector, reason):
        if self.is_reconnecting:
            log.debug(reason)
            ReconnectingClientFactory.clientConnectionFailed(self, connector, reason)        
        
