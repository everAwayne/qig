
__all__ = ['LoginRetryError', 'APITimeoutError', 'UnkownAPIError']

class IGError(Exception):
    pass

class LoginRetryError(IGError):
    pass

class APITimeoutError(IGError):
    pass

class UnkownAPIError(IGError):
    pass
