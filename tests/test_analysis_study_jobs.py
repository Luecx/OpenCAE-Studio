"""Regression tests for Steps, Analyses, Studies, Jobs and shared UI actions."""

import ast
from pathlib import Path

from opencae.model.core import EntityRef, decode_model, encode_model
from opencae.model.entities.analysis import Analysis, AnalysisStep
from opencae.model.entities.jobs import Job, ResultSet
from opencae.model.entities.optimization import TopologyOptimization
from opencae.model.entities.project import Project


ROOT = Path(__file__).resolve().parents[1]


def test_legacy_analysis_owned_steps_migrate_to_shared_project_steps():
    step = AnalysisStep(name="Static", step_type="Linear Static")
    analysis = Analysis(name="Analysis-1", steps=[step])

    project = Project(name="Migration", analyses=[analysis])

    assert project.steps == [step]
    assert analysis.steps == []
    assert [ref.entity_id for ref in analysis.step_refs] == [step.id]
    assert analysis.resolved_steps(project) == (step,)


def test_shared_steps_and_studies_survive_model_roundtrip():
    step = AnalysisStep(name="Static", step_type="Linear Static")
    analysis = Analysis(name="Analysis-1")
    analysis.bind_steps([step])
    study = TopologyOptimization(
        name="Topology-1",
        analysis_ref=EntityRef.of(analysis, "Analysis"),
    )
    project = Project(
        name="Roundtrip",
        steps=[step],
        analyses=[analysis],
        studies=[study],
    )

    restored = decode_model(encode_model(project))

    assert [value.name for value in restored.steps] == ["Static"]
    assert (
        restored.analyses[0].resolved_steps(restored)[0].id
        == restored.steps[0].id
    )
    assert restored.studies[0].name == "Topology-1"
    assert restored.optimizations is restored.studies


def test_legacy_optimizations_collection_migrates_to_studies():
    study = TopologyOptimization(name="Topology-1")

    project = Project(name="Legacy", optimizations=[study])

    assert project.studies == [study]
    assert project.optimizations is project.studies
    payload = project.to_dict()
    assert "studies" in payload
    assert "optimizations" not in payload


def test_results_are_bound_to_the_job_that_created_them():
    study = TopologyOptimization(name="Topology-1")
    job = Job(
        name="Job-1",
        source_ref=EntityRef.of(study, "TopologyOptimization"),
        source_kind="study",
        status="Completed",
    )
    result = ResultSet(
        name="Job-1",
        job_ref=EntityRef.of(job, "Job"),
        status="Available",
        metadata={
            "result_kind": "topology_density",
            "frames": [
                {
                    "number": 1,
                    "density_file": "iteration-0001/density.npz",
                },
                {
                    "number": 2,
                    "density_file": "iteration-0002/density.npz",
                },
            ],
        },
    )
    job.result_refs = [EntityRef.of(result, "ResultSet")]

    project = Project(
        name="Jobs",
        studies=[study],
        jobs=[job],
        results=[result],
    )

    assert project.resolve(result.job_ref) is job
    assert project.resolve(job.result_refs[0]) is result
    assert project.resolve(job.source_ref) is study
    assert [frame["number"] for frame in result.metadata["frames"]] == [1, 2]


def test_workflow_stages_remove_solve_and_optimization():
    source = (ROOT / "opencae/ui/ribbon/stage_bar.py").read_text(
        encoding="utf-8"
    )
    module = ast.parse(source)
    assignment = next(
        node
        for node in module.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "STAGES"
            for target in node.targets
        )
    )
    stages = tuple(ast.literal_eval(assignment.value))

    assert "STEPS" in stages
    assert "ANALYSIS" in stages
    assert "STUDIES" in stages
    assert "SOLVE" not in stages
    assert "OPTIMIZATION" not in stages


def test_tree_context_menus_reuse_ribbon_actions_and_delete():
    source = (ROOT / "opencae/ui/tree/context_menu.py").read_text(
        encoding="utf-8"
    )
    expected = (
        '"constraints": (',
        "A.CONSTRAINT_KINEMATIC",
        '"study": (',
        "A.OPT_RESPONSE",
        "A.OPT_OBJECTIVE",
        "A.OPT_CONSTRAINT",
        "A.STUDY_RUN",
        "A.DELETE_SELECTED",
        '"study_responses": (A.OPT_RESPONSE,)',
        '"study_objectives": (A.OPT_OBJECTIVE,)',
        '"study_constraints": (A.OPT_CONSTRAINT,)',
        '"study_filters": (A.OPT_FILTER,)',
        '"study_symmetries": (A.OPT_SYMMETRY,)',
        '"study_controls": (A.OPT_CONTROLS,)',
        '"study_response": (A.EDIT_SELECTED, A.DELETE_SELECTED)',
        '"study_objective": (A.EDIT_SELECTED, A.DELETE_SELECTED)',
        '"study_constraint": (A.EDIT_SELECTED, A.DELETE_SELECTED)',
        '"analysis": (',
        "A.ANALYSIS_RUN",
        '"analysis_step": (A.EDIT_SELECTED, A.DELETE_SELECTED)',
    )
    for token in expected:
        assert token in source


def test_new_workflow_modules_keep_one_class_per_file():
    files = (
        "opencae/controllers/job_manager.py",
        "opencae/jobs/analysis_job_runner.py",
        "opencae/model/entities/studies/study.py",
        "opencae/ui/core/widgets/entity_selector_bar.py",
        "opencae/ui/core/widgets/monospace_output_view.py",
        "opencae/ui/dialogs/analysis_dialog.py",
        "opencae/ui/monitors/analysis_job_monitor.py",
        "opencae/ui/monitors/topology_job_monitor.py",
        "opencae/ui/panels/jobs_panel.py",
        "opencae/ui/ribbon/analysis_page.py",
        "opencae/ui/ribbon/studies_page.py",
    )
    for relative in files:
        path = ROOT / relative
        module = ast.parse(path.read_text(encoding="utf-8"))
        assert ast.get_docstring(module), f"Missing module header: {relative}"
        classes = [node for node in module.body if isinstance(node, ast.ClassDef)]
        assert len(classes) <= 1, (
            f"Expected at most one class in {relative}, found "
            f"{[node.name for node in classes]}"
        )
