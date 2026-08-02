from .analysis import Analysis
from .buckling import BucklingAnalysis
from .linear_static import LinearStaticAnalysis
from .modal import ModalAnalysis
from .nonlinear_static import NonlinearStaticAnalysis
from .transient import TransientAnalysis

_TYPES = {
    "Linear Static": LinearStaticAnalysis,
    "Nonlinear Static": NonlinearStaticAnalysis,
    "Eigenfrequency": ModalAnalysis,
    "Linear Buckling": BucklingAnalysis,
    "Transient": TransientAnalysis,
}


def create_analysis(analysis_type: str, **kwargs) -> Analysis:
    cls = _TYPES.get(analysis_type, Analysis)
    if cls is Analysis:
        return cls(analysis_type=analysis_type, **kwargs)
    return cls(**kwargs)
