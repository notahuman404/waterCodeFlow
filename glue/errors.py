class GlueError(Exception):
    """Generic glue-layer error."""


class NotFoundError(GlueError):
    """Raised when an expected resource is missing."""
    pass
