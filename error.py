class IGError(Exception):
    pass

class LoginRetryError(IGError):
    pass

class APITimeoutError(IGError):
    pass

class UnkownAPIError(IGError):
    pass
