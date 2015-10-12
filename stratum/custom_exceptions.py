class ProtocolException(Exception):
    pass

class TransportException(Exception):
    pass

class ServiceException(Exception):
    code = -2

class UnauthorizedException(ServiceException):
    pass

class PubsubException(ServiceException):
    pass

class AlreadySubscribedException(PubsubException):
    pass

class MissingServiceTypeException(ServiceException):
    code = -2

class MissingServiceVendorException(ServiceException):
    code = -2

class MissingServiceIsDefaultException(ServiceException):
    code = -2

class DefaultServiceAlreadyExistException(ServiceException):
    code = -2

class ServiceNotFoundException(ServiceException):
    code = -2

class MethodNotFoundException(ServiceException):
    code = -3
    
class FeeRequiredException(ServiceException):
    code = -10

class TimeoutServiceException(ServiceException):
    pass

class RemoteServiceException(Exception):
    pass