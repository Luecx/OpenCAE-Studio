"""Defines parsing failures raised for malformed FEMaster native result files."""


class ResFormatError(ValueError):
    """Raised when a `.res` file violates the expected FEMaster field format."""
