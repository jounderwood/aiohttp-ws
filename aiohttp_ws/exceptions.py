from marshmallow import ValidationError as MarshmallowValidationError


class ValidationError(MarshmallowValidationError):
    pass


class ResponseValidationError(ValidationError):
    pass


class RequestValidationError(ValidationError):
    pass
