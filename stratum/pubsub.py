import weakref
from connection_registry import ConnectionRegistry
import custom_exceptions
import hashlib

def subscribe(func):
    '''Decorator detect Subscription object in result and subscribe connection'''
    def inner(self, *args, **kwargs):
        subs = func(self, *args, **kwargs)
        return Pubsub.subscribe(self.connection_ref(), subs)
    return inner

def unsubscribe(func):
    '''Decorator detect Subscription object in result and unsubscribe connection'''
    def inner(self, *args, **kwargs):
        subs = func(self, *args, **kwargs)
        if isinstance(subs, Subscription):
            return Pubsub.unsubscribe(self.connection_ref(), subscription=subs)
        else:
            return Pubsub.unsubscribe(self.connection_ref(), key=subs)
    return inner

class Subscription(object):
    def __init__(self, event=None, **params):
        if hasattr(self, 'event'):
            if event:
                raise Exception("Event name already defined in Subscription object")
        else:
            if not event:
                raise Exception("Please define event name in constructor")
            else:
                self.event = event
        
        self.params = params # Internal parameters for subscription object
        self.connection_ref = None
            
    def process(self, *args, **kwargs):
        return args
            
    def get_key(self):
        '''This is an identifier for current subscription. It is sent to the client,
        so result should not contain any sensitive information.'''
        #return hashlib.md5(str((self.event, self.params))).hexdigest()
        return "%s" % int(hashlib.md5( str((self.event, self.params)) ).hexdigest()[:12], 16)
    
    def get_session(self):
        '''Connection session may be useful in filter or process functions'''
        return self.connection_ref().get_session()
        
    @classmethod
    def emit(cls, *args, **kwargs):
        '''Shortcut for emiting this event to all subscribers.'''
        if not hasattr(cls, 'event'):
            raise Exception("Subscription.emit() can be used only for subclasses with filled 'event' class variable.")
        return Pubsub.emit(cls.event, *args, **kwargs)
        
    def emit_single(self, *args, **kwargs):
        '''Perform emit of this event just for current subscription.'''
        conn = self.connection_ref()
        if conn == None:
            # Connection is closed
            return

        payload = self.process(*args, **kwargs)
        if payload != None:
            if isinstance(payload, (tuple, list)):
                if len(payload)==1 and isinstance(payload[0], dict):
                    payload = payload[0]
                conn.writeJsonRequest(self.event, payload, '', is_notification=True)
                self.after_emit(*args, **kwargs)
            else:
                raise Exception("Return object from process() method must be list or None")

    def after_emit(self, *args, **kwargs):
        pass
    
    # Once function is defined, it will be called every time
    #def after_subscribe(self, _):
    #    pass
    
    def __eq__(self, other):
        return (isinstance(other, Subscription) and other.get_key() == self.get_key())
    
    def __ne__(self, other):
        return not self.__eq__(other)
    
class Pubsub(object):
    __subscriptions = {}
    
    @classmethod
    def subscribe(cls, connection, subscription):
        if connection == None:
            raise custom_exceptions.PubsubException("Subscriber not connected")
        
        key = subscription.get_key()
        session = ConnectionRegistry.get_session(connection)
        if session == None:
            raise custom_exceptions.PubsubException("No session found")
        
        subscription.connection_ref = weakref.ref(connection)
        session.setdefault('subscriptions', {})
        
        if key in session['subscriptions']:
            raise custom_exceptions.AlreadySubscribedException("This connection is already subscribed for such event.")
        
        session['subscriptions'][key] = subscription
                    
        cls.__subscriptions.setdefault(subscription.event, weakref.WeakKeyDictionary())
        cls.__subscriptions[subscription.event][subscription] = None
        
        if hasattr(subscription, 'after_subscribe'):
            if connection.on_finish != None:
                # If subscription is processed during the request, wait to
                # finish and then process the callback
                connection.on_finish.addCallback(subscription.after_subscribe)
            else:
                # If subscription is NOT processed during the request (any real use case?),
                # process callback instantly (better now than never).
                subscription.after_subscribe(True)
        
        # List of 2-tuples is prepared for future multi-subscriptions
        return ((subscription.event, key, subscription),)
    
    @classmethod
    def unsubscribe(cls, connection, subscription=None, key=None):
        if connection == None:
            raise custom_exceptions.PubsubException("Subscriber not connected")
        
        session = ConnectionRegistry.get_session(connection)
        if session == None:
            raise custom_exceptions.PubsubException("No session found")
        
        if subscription:
            key = subscription.get_key()

        try:
            # Subscription don't need to be removed from cls.__subscriptions,
            # because it uses weak reference there.
            del session['subscriptions'][key]
        except KeyError:
            print "Warning: Cannot remove subscription from connection session"
            return False
            
        return True
        
    @classmethod
    def get_subscription_count(cls, event):
        return len(cls.__subscriptions.get(event, {}))

    @classmethod
    def get_subscription(cls, connection, event, key=None):
        '''Return subscription object for given connection and event'''
        session = ConnectionRegistry.get_session(connection)
        if session == None:
            raise custom_exceptions.PubsubException("No session found")

        if key == None:    
            sub = [ sub for sub in session.get('subscriptions', {}).values() if sub.event == event ]
            try:
                return sub[0]
            except IndexError:
                raise custom_exceptions.PubsubException("Not subscribed for event %s" % event)

        else:
            raise Exception("Searching subscriptions by key is not implemented yet")
              
    @classmethod
    def iterate_subscribers(cls, event):
        for subscription in cls.__subscriptions.get(event, weakref.WeakKeyDictionary()).iterkeyrefs():
            subscription = subscription()
            if subscription == None:
                # Subscriber is no more connected
                continue
            
            yield subscription
            
    @classmethod
    def emit(cls, event, *args, **kwargs):
        for subscription in cls.iterate_subscribers(event):                        
            subscription.emit_single(*args, **kwargs)