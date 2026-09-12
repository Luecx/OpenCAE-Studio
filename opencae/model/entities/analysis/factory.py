"""Creates legacy concrete Analysis variants from canonical procedure kinds."""

from .analysis import Analysis
from .buckling import BucklingAnalysis
from .linear_static import LinearStaticAnalysis
from .modal import ModalAnalysis
from .nonlinear_static import NonlinearStaticAnalysis
from .transient import TransientAnalysis
from .step_type import StepType

_TYPES = {
    StepType.LINEAR_STATIC: LinearStaticAnalysis,
    StepType.NONLINEAR_STATIC: NonlinearStaticAnalysis,
    StepType.EIGENFREQUENCY: ModalAnalysis,
    StepType.LINEAR_BUCKLING: BucklingAnalysis,
    StepType.TRANSIENT: TransientAnalysis,
}


def create_analysis(analysis_type: StepType | str, **kwargs) -> Analysis:
    """Create the concrete compatibility type for a supported procedure."""
    step_type = StepType.coerce(analysis_type)
    cls = _TYPES.get(step_type, Analysis)
    if cls is Analysis:
        return cls(analysis_type=step_type.value, **kwargs)
    return cls(**kwargs)
