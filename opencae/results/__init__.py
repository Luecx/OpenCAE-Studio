from .frd_loader import FrdLoader as NativeFrdLoader
from .res_loader import ResLoader
from .result_loader import ResultLoader

# Compatibility for application code that historically imported FrdLoader from
# the package root. It is now the format-aware stored-result facade.
FrdLoader = ResultLoader

__all__ = ["ResultLoader", "FrdLoader", "NativeFrdLoader", "ResLoader"]
