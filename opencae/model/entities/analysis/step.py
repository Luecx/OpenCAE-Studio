"""Defines reusable analysis steps and their solver-level procedure controls."""

from dataclasses import dataclass, field

from ...core import Entity, EntityRef, register_model_type
from .step_type import StepType


@register_model_type("analysis_step")
@dataclass
class AnalysisStep(Entity):
    """Store one typed analysis procedure and its referenced active entities."""

    step_type: StepType | str = StepType.LINEAR_STATIC
    load_refs: list[EntityRef] = field(default_factory=list)
    support_refs: list[EntityRef] = field(default_factory=list)
    number_of_modes: int = 10
    time_period: float = 1.0
    settings: dict[str, object] = field(default_factory=dict)

    def __setattr__(self, name, value) -> None:
        """Keep the procedure canonical across construction and later mutation."""
        if name == "step_type":
            value = StepType.coerce(value)
        super().__setattr__(name, value)

    @property
    def uses_loads(self) -> bool:
        """Return whether this procedure can consume applied loads."""
        return self.step_type is not StepType.EIGENFREQUENCY

    @property
    def uses_supports(self) -> bool:
        """Return whether this procedure can consume supports."""
        return True

    def write_abaqus(self, writer, context) -> None:
        """Write Abaqus-compatible procedure controls for the active step type."""
        if self.step_type is not StepType.NONLINEAR_STATIC:
            return

        settings = dict(self.settings or {})
        control = str(settings.get("control", "LOAD")).upper()
        if control == "ARC_LENGTH":
            control = "PATH"
        maximum_increments = max(1, int(settings.get("max_increments", 100)))
        name = (
            context.solver_name(self, self.name)
            if hasattr(context, "solver_name")
            else self.name
        )
        writer.line(
            f"*STEP, NAME={name}, NLGEOM=YES, INC={maximum_increments}"
        )

        if control == "PATH":
            solver = str(getattr(getattr(context, "analysis", None), "solver", ""))
            if solver.lower() == "calculix":
                raise ValueError(
                    "CalculiX does not provide a Riks/arc-length path-control solver; "
                    "use Load control for this nonlinear step or run it with FEMaster/Abaqus."
                )
            initial = float(
                settings.get(
                    "initial_arc_length",
                    settings.get("initial_increment", 0.05),
                )
            )
            total = float(settings.get("total_arc_length", 1.0))
            minimum = float(
                settings.get(
                    "minimum_arc_length",
                    settings.get("minimum_increment", 1.0e-5),
                )
            )
            maximum = float(
                settings.get(
                    "maximum_arc_length",
                    settings.get("maximum_increment", 0.1),
                )
            )
            writer.line("*STATIC, RIKS")
            writer.line(f"{initial:.12g}, {total:.12g}, {minimum:.12g}, {maximum:.12g}")
        else:
            adaptive = bool(settings.get("adaptive", True))
            initial = float(settings.get("initial_increment", 0.1))
            total = float(self.time_period)
            if adaptive:
                minimum = float(settings.get("minimum_increment", 1.0e-6))
                maximum = float(settings.get("maximum_increment", 0.1))
                writer.line("*STATIC")
                writer.line(
                    f"{initial:.12g}, {total:.12g}, {minimum:.12g}, {maximum:.12g}"
                )
            else:
                writer.line("*STATIC, DIRECT")
                writer.line(f"{initial:.12g}, {total:.12g}")

        writer.line("*END STEP")

    def write_femaster(self, writer, context) -> None:
        """FEMaster steps are emitted by the semantic DSL project emitter."""
        return None
