from autobahn.websocket import WebSocketServerProtocol, WebSocketServerFactory
from protocol import Protocol
from event_handler import GenericEventHandler

class WebsocketServerProtocol(WebSocketServerProtocol, Protocol):
    def connectionMade(self):
        WebSocketServerProtocol.connectionMade(self)
        Protocol.connectionMade(self)
        
    def connectionLost(self, reason):
        WebSocketServerProtocol.connectionLost(self, reason)
        Protocol.connectionLost(self, reason)
        
    def onMessage(self, msg, is_binary):
        Protocol.dataReceived(self, msg)
            
    def transport_write(self, data):
        self.sendMessage(data, False)
        
class WebsocketTransportFactory(WebSocketServerFactory):
    def __init__(self, port, is_secure=False, debug=False, signing_key=None, signing_id=None,
                 event_handler=GenericEventHandler):
        self.debug = debug
        self.signing_key = signing_key
        self.signing_id = signing_id
        self.protocol = WebsocketServerProtocol
        self.event_handler = event_handler
        
        if is_secure:
            uri = "wss://0.0.0.0:%d" % port
        else:
            uri = "ws://0.0.0.0:%d" % port
        
        WebSocketServerFactory.__init__(self, uri)

# P.S. There's not Websocket client implementation yet
# P.P.S. And it probably won't be for long time...'