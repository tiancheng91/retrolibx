"""Public exception hierarchy."""


class RetroLibXError(Exception):
    """Base class for expected RetroLibX failures."""


class DetectionError(RetroLibXError):
    pass


class ParseError(RetroLibXError):
    pass


class ValidationError(RetroLibXError):
    pass


class MappingError(RetroLibXError):
    pass


class ConflictError(RetroLibXError):
    pass


class ExportError(RetroLibXError):
    pass


class FileOperationError(RetroLibXError):
    pass
