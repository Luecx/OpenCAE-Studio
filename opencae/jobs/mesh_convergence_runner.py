"""Sequential mesh-refinement execution on immutable Project snapshots.

Gmsh work runs in BackgroundTask; each solver level uses the existing
AnalysisJobRunner/QProcess lifecycle. Live Part meshes are never modified.
"""
from __future__ import annotations

from copy import deepcopy
from math import ceil
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal

from opencae.controllers.background_task import BackgroundTask
from opencae.controllers.part.mesh_persistence import apply_mesh_snapshot
from opencae.geometry import GeometryService
from opencae.geometry.element_controls_apply import apply_all_controls
from opencae.jobs import AnalysisJobRunner
from opencae.model.entities.mesh import DefaultSeed
from opencae.results.mesh_convergence import evaluate_all_metrics, assess_all_metrics
from opencae.results.frd_loader import FrdLoader


def _refine_project(project, scale):
    """Remesh independent snapshot Parts; do not touch active project or Gmsh cache."""
    snapshot = deepcopy(project)
    for part in snapshot.parts:
        if not part.geometry:
            if part.mesh.element_count:
                raise ValueError(
                    f"Part {part.name} has a mesh but no editable CAD geometry; "
                    "automatic convergence cannot remesh orphan-mesh Parts"
                )
            continue
        if not part.mesh.seeds:
            raise ValueError(f"Part {part.name} has no mesh seeds")
        candidate = deepcopy(part)
        # Retain Part identity: region, edge-seed and element-control targets
        # reference the real Part ID. Opt out of live cache instead.
        for seed in candidate.mesh.seeds:
            if seed.seed_type == "Default" or seed.method.casefold() == "size":
                seed.size *= float(scale)
            elif seed.divisions:
                seed.divisions = max(1, int(ceil(seed.divisions / float(scale))))
        result = GeometryService().generate_mesh(candidate, cache=False)
        apply_mesh_snapshot(candidate, result)
        apply_all_controls(candidate)
        part.mesh = candidate.mesh
    snapshot.rebuild_index(strict=True)
    return snapshot


class MeshConvergenceRunner(QObject):
    """Emit one metric per successful level; cancellation stops between stages."""

    output = pyqtSignal(str)
    progress = pyqtSignal(float, str)
    sample_ready = pyqtSignal(object)
    finished = pyqtSignal(str, str)

    def __init__(self, project, study, analysis_id, adapter, executable,
                 arguments, directory, parent=None, *, deck_profile=None):
        super().__init__(parent)
        self.project = deepcopy(project)
        self.study = deepcopy(study)
        self.analysis_id = str(analysis_id)
        self.adapter, self.executable = adapter, str(executable)
        self.arguments = str(arguments or "")
        self.directory = Path(directory)
        self.deck_profile = deepcopy(deck_profile)
        self._level = 0
        self._samples = []
        self._mesh_task = None
        self._sample_task = None
        self._analysis = None
        self._stopping = False
        self._ended = False

    def start(self):
        self._advance()

    def stop(self):
        if self._ended:
            return
        self._stopping = True
        if self._analysis is not None:
            self._analysis.stop()
        elif self._mesh_task is None and self._sample_task is None:
            self._finish("Cancelled", "Mesh Convergence Study cancelled")

    def _advance(self):
        if self._ended:
            return
        if self._stopping:
            self._finish("Cancelled", "Mesh Convergence Study cancelled")
            return
        if self._level >= self.study.max_iterations:
            self._finish("Completed", "All mesh levels evaluated")
            return
        scale = float(self.study.mesh_scaling_factor) ** self._level
        self.progress.emit(
            self._level / self.study.max_iterations,
            f"Meshing level {self._level + 1}/{len(self.study.mesh_scales)}",
        )
        self.output.emit(
            f"Generating level {self._level + 1} with seed scale {scale:g}\n"
        )
        task = BackgroundTask(
            lambda: _refine_project(self.project, scale),
            on_result=self._meshed, on_error=self._failed, parent=self,
        )
        self._mesh_task = task
        task.start()

    def _meshed(self, snapshot):
        self._mesh_task = None
        if self._stopping:
            self._finish("Cancelled", "Cancelled after meshing")
            return
        level_directory = self.directory / f"level-{self._level + 1:02d}"
        runner = AnalysisJobRunner(
            snapshot, self.analysis_id, self.adapter,
            self.executable, self.arguments, level_directory,
            self, deck_profile=self.deck_profile,
        )
        self._analysis = runner
        runner.output.connect(self.output)
        runner.progress.connect(lambda value, label: self.progress.emit(
            (self._level + value) / self.study.max_iterations, label
        ))
        runner.finished.connect(self._solver_finished)
        runner.start()

    def _solver_finished(self, output_base, code):
        self._analysis = None
        if self._stopping or int(code) == 130:
            self._finish("Cancelled", "Solver execution cancelled")
            return
        if int(code) != 0:
            self._failed(RuntimeError(
                f"Solver failed at level {self._level + 1} (exit code {code})"
            ))
            return
        result_file = next(
            (path for path in self.adapter.result_candidates(Path(output_base))
             if path.is_file() and path.suffix.casefold() == ".frd"),
            None,
        )
        if result_file is None:
            self._failed(FileNotFoundError(
                f"No FRD result produced at level {self._level + 1}"
            ))
            return
        def measure():
            loader = FrdLoader()
            sample = evaluate_all_metrics(result_file, self.study, loader)
            # Parse field metadata off the Qt thread while the FRD is cached.
            sample["_result_fields"] = loader.fields(result_file)
            return sample

        task = BackgroundTask(
            measure, on_result=self._measured,
            on_error=self._failed, parent=self,
        )
        self._sample_task = task
        task.start()

    def _measured(self, sample):
        self._sample_task = None
        sample = dict(sample)
        sample["level"] = self._level + 1
        sample["seed_scale"] = float(self.study.mesh_scaling_factor) ** self._level
        self._samples.append(sample)
        self.sample_ready.emit(sample)
        lines = [
            f"Level {sample['level']}: {sample['elements']} elements "
            f"({sample['nodes']} nodes)"
        ]
        for result in sample.get("metrics", {}).values():
            lines.append(
                f"  {result.get('metric_name', result['metric'])}: "
                f"{result['value']:.8g}"
            )
        self.output.emit("\n".join(lines) + "\n")
        self._level += 1
        assessment = assess_all_metrics(
            self._samples, float(self.study.relative_tolerance)
        )
        if (len(self._samples) >= 3 and assessment
                and all("within tolerance" in message
                        for message in assessment.values())):
            self._finish("Completed", "All displacement metrics are within tolerance")
            return
        self._advance()

    def _failed(self, error):
        self._mesh_task = None
        self._sample_task = None
        self._finish("Failed", str(error))

    def _finish(self, status, message):
        if self._ended:
            return
        self._ended = True
        self.finished.emit(str(status), str(message))
