import custom_exceptions
from twisted.internet import defer
from services import wrap_result_object

class GenericEventHandler(object):
    def _handle_event(self, msg_method, msg_result, connection_ref):
        return defer.maybeDeferred(wrap_result_object, self.handle_event(msg_method, msg_result, connection_ref))
    
    def handle_event(self, msg_method, msg_params, connection_ref):
        '''In most cases you'll only need to overload this method.'''
        print "Other side called method", msg_method, "with params", msg_params
        raise custom_exceptions.MethodNotFoundException("Method '%s' not implemented" % msg_method)