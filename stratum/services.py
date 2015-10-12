from twisted.internet import defer, threads
from twisted.python import log
import hashlib
import weakref
import re

import custom_exceptions

VENDOR_RE = re.compile(r'\[(.*)\]')

class ServiceEventHandler(object): # reimplements event_handler.GenericEventHandler
    def _handle_event(self, msg_method, msg_params, connection_ref):
        return ServiceFactory.call(msg_method, msg_params, connection_ref=connection_ref)
        
class ResultObject(object):
    def __init__(self, result=None, sign=False, sign_algo=None, sign_id=None):
        self.result = result
        self.sign = sign
        self.sign_algo = sign_algo
        self.sign_id = sign_id     
            
def wrap_result_object(obj):
    def _wrap(o):
        if isinstance(o, ResultObject):
            return o
        return ResultObject(result=o)
        
    if isinstance(obj, defer.Deferred):
        # We don't have result yet, just wait for it and wrap it later
        obj.addCallback(_wrap)
        return obj
    
    return _wrap(obj)

class ServiceFactory(object):
    registry = {} # Mapping service_type -> vendor -> cls
    
    @classmethod
    def _split_method(cls, method):
        '''Parses "some.service[vendor].method" string
        and returns 3-tuple with (service_type, vendor, rpc_method)'''
        
        # Splits the service type and method name
        (service_type, method_name) = method.rsplit('.', 1)
        vendor = None
        
        if '[' in service_type:
            # Use regular expression only when brackets found
            try:
                vendor = VENDOR_RE.search(service_type).group(1)
                service_type = service_type.replace('[%s]' % vendor, '')
            except:
                raise
                #raise custom_exceptions.ServiceNotFoundException("Invalid syntax in service name '%s'" % type_name[0])
            
        return (service_type, vendor, method_name)
    
    @classmethod
    def call(cls, method, params, connection_ref=None):
        if method in ['submit','login']:
            method = 'mining.%s' % method
            params = [params,]
        try:
            (service_type, vendor, func_name) = cls._split_method(method)
        except ValueError:
            raise custom_exceptions.MethodNotFoundException("Method name parsing failed. You *must* use format <service name>.<method name>, e.g. 'example.ping'")

        try:
            if func_name.startswith('_'):
                raise        
        
            _inst = cls.lookup(service_type, vendor=vendor)()
            _inst.connection_ref = weakref.ref(connection_ref)
            func = _inst.__getattribute__(func_name)
            if not callable(func):
                raise
        except:
            raise custom_exceptions.MethodNotFoundException("Method '%s' not found for service '%s'" % (func_name, service_type))
        
        def _run(func, *params):
            return wrap_result_object(func(*params))
        
        # Returns Defer which will lead to ResultObject sometimes
        return defer.maybeDeferred(_run, func, *params)
        
    @classmethod
    def lookup(cls, service_type, vendor=None):
        # Lookup for service type provided by specific vendor
        if vendor:
            try:
                return cls.registry[service_type][vendor]
            except KeyError:
                raise custom_exceptions.ServiceNotFoundException("Class for given service type and vendor isn't registered")
        
        # Lookup for any vendor, prefer default one
        try:
            vendors = cls.registry[service_type]        
        except KeyError:
            raise custom_exceptions.ServiceNotFoundException("Class for given service type isn't registered")

        last_found = None        
        for _, _cls in vendors.items():
            last_found = _cls
            if last_found.is_default:
                return last_found
            
        if not last_found:
            raise custom_exceptions.ServiceNotFoundException("Class for given service type isn't registered")
        
        return last_found

    @classmethod
    def register_service(cls, _cls, meta):
        # Register service class to ServiceFactory
        service_type = meta.get('service_type')
        service_vendor = meta.get('service_vendor')
        is_default = meta.get('is_default')
           
        if str(_cls.__name__) in ('GenericService',):
            # str() is ugly hack, but it is avoiding circular references
            return
        
        if not service_type:
            raise custom_exceptions.MissingServiceTypeException("Service class '%s' is missing 'service_type' property." % _cls)

        if not service_vendor:
            raise custom_exceptions.MissingServiceVendorException("Service class '%s' is missing 'service_vendor' property." % _cls)

        if is_default == None:
            raise custom_exceptions.MissingServiceIsDefaultException("Service class '%s' is missing 'is_default' property." % _cls)
        
        if is_default:
            # Check if there's not any other default service
            
            try:
                current = cls.lookup(service_type)
                if current.is_default:
                    raise custom_exceptions.DefaultServiceAlreadyExistException("Default service already exists for type '%s'" % service_type)
            except custom_exceptions.ServiceNotFoundException:
                pass
        
        setup_func = meta.get('_setup', None)
        if setup_func != None:
            _cls()._setup()

        ServiceFactory.registry.setdefault(service_type, {})
        ServiceFactory.registry[service_type][service_vendor] = _cls
        
        log.msg("Registered %s for service '%s', vendor '%s' (default: %s)" % (_cls, service_type, service_vendor, is_default))

def synchronous(func):
    '''Run given method synchronously in separate thread and return the result.'''
    def inner(*args, **kwargs):
        return threads.deferToThread(func, *args, **kwargs)
    return inner

def admin(func):
    '''Requires an extra first parameter with superadministrator password'''
    import settings
    def inner(*args, **kwargs):
        if not len(args):
            raise custom_exceptions.UnauthorizedException("Missing password")

        if settings.ADMIN_RESTRICT_INTERFACE != None:
            ip = args[0].connection_ref()._get_ip()
            if settings.ADMIN_RESTRICT_INTERFACE != ip:
                raise custom_exceptions.UnauthorizedException("RPC call not allowed from your IP")
            
        if not settings.ADMIN_PASSWORD_SHA256:
            raise custom_exceptions.UnauthorizedException("Admin password not set, RPC call disabled")

        (password, args) = (args[1], [args[0],] + list(args[2:]))

        if hashlib.sha256(password).hexdigest() != settings.ADMIN_PASSWORD_SHA256:
            raise custom_exceptions.UnauthorizedException("Wrong password")

        return func(*args, **kwargs)
    return inner

class ServiceMetaclass(type):
    def __init__(cls, name, bases, _dict):
        super(ServiceMetaclass, cls).__init__(name, bases, _dict)
        ServiceFactory.register_service(cls, _dict)
        
class GenericService(object):
    __metaclass__ = ServiceMetaclass
    service_type = None
    service_vendor = None
    is_default = None
    
    # Keep weak reference to connection which asked for current
    # RPC call. Useful for pubsub mechanism, but use it with care.
    # It does not need to point to actual and valid data, so
    # you have to check if connection still exists every time.  
    connection_ref = None
    
class ServiceDiscovery(GenericService):
    service_type = 'discovery'
    service_vendor = 'Stratum'
    is_default = True
    
    def list_services(self):
        return ServiceFactory.registry.keys()
    
    def list_vendors(self, service_type):
        return ServiceFactory.registry[service_type].keys()
    
    def list_methods(self, service_name):
        # Accepts also vendors in square brackets: firstbits[firstbits.com]
        
        # Parse service type and vendor. We don't care about the method name,
        # but _split_method needs full path to some RPC method.
        (service_type, vendor, _) = ServiceFactory._split_method("%s.foo" % service_name)
        service = ServiceFactory.lookup(service_type, vendor)
        out = []
        
        for name, obj in service.__dict__.items():
            
            if name.startswith('_'):
                continue
            
            if not callable(obj):
                continue

            out.append(name)
        
        return out
    
    def list_params(self, method):
        (service_type, vendor, meth) = ServiceFactory._split_method(method)
        service = ServiceFactory.lookup(service_type, vendor)
            
        # Load params and helper text from method attributes
        func = service.__dict__[meth]
        params = getattr(func, 'params', None)
        help_text = getattr(func, 'help_text', None)
       
        return (help_text, params)     
    list_params.help_text = "Accepts name of method and returns its description and available parameters. Example: 'firstbits.resolve'"
    list_params.params = [('method', 'string', 'Method to lookup for description and parameters.'),]