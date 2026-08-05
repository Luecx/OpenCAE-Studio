"""Regression coverage for the Steps, Analyses, Studies and Jobs architecture."""

import ast
from pathlib import Path

from opencae.model.core import EntityRef
from opencae.model.entities.analysis import Analysis, AnalysisStep
from opencae.model.entities.jobs import Job, ResultSet
from opencae.model.entities.optimization import TopologyOptimization
from opencae.model.entities.project import Project
from opencae.model.validation import validate_project


ROOT = Path(__file__).resolve().parents[1]


def test_legacy_analysis_steps_migrate_to_shared_project_steps():
    first = AnalysisStep(name="Load", step_type="Linear Static")
    second = AnalysisStep(name="Modes", step_type="Eigenfrequency")
    analysis = Analysis(name="Analysis", steps=[first, second])

    project = Project(name="Migration", analyses=[analysis])

    assert [step.id for step in project.steps] == [first.id, second.id]
    assert [step.id for step in analysis.resolved_steps(project)] == [
        first.id,
        second.id,
    ]
    assert analysis.steps == []
    assert [ref.entity_id for ref in analysis.step_refs] == [
        first.id,
        second.id,
    ]


def test_legacy_optimizations_migrate_to_studies_without_serialized_alias():
    study = TopologyOptimization(name="Topology")
    project = Project(name="Migration", optimizations=[study])

    assert project.studies == [study]
    assert project.optimizations is project.studies
    payload = project.to_dict()
    assert "studies" in payload
    assert "optimizations" not in payload


def test_analysis_resolves_only_its_explicit_step_order():
    first = AnalysisStep(name="First", step_type="Linear Static")
    second = AnalysisStep(name="Second", step_type="Eigenfrequency")
    analysis = Analysis(
        name="Selected",
        step_refs=[
            EntityRef.of(second, "AnalysisStep"),
            EntityRef.of(first, "AnalysisStep"),
        ],
    )
    project = Project(
        name="Ordering",
        steps=[first, second],
        analyses=[analysis],
    )

    assert [step.name for step in analysis.resolved_steps(project)] == [
        "Second",
        "First",
    ]


def test_results_are_unambiguously_linked_to_the_generating_job():
    step = AnalysisStep(name="Step", step_type="Linear Static")
    analysis = Analysis(
        name="Analysis",
        step_refs=[EntityRef.of(step, "AnalysisStep")],
    )
    job = Job(
        name="Job-1",
        source_ref=EntityRef.of(analysis, "Analysis"),
        source_kind="analysis",
        status="Completed",
    )
    result = ResultSet(
        name="Job-1",
        job_ref=EntityRef.of(job, "Job"),
        status="Available",
    )
    job.result_refs = [EntityRef.of(result, "ResultSet")]
    project = Project(
        name="Jobs",
        steps=[step],
        analyses=[analysis],
        jobs=[job],
        results=[result],
    )

    assert project.resolve(result.job_ref) is job
    assert project.resolve(job.result_refs[0]) is result
    assert not [
        error
        for error in validate_project(project)
        if "Job" in error or "job" in error or "result" in error.lower()
    ]


def test_topology_result_persists_all_iteration_frames_on_one_job_result():
    study = TopologyOptimization(name="Topology")
    job = Job(
        name="Job-1",
        source_ref=EntityRef.of(study, "Study"),
        source_kind="study",
        status="Completed",
    )
    result = ResultSet(
        name=job.name,
        job_ref=EntityRef.of(job, "Job"),
        status="Available",
        metadata={
            "result_kind": "topology_density",
            "frames": [
                {"number": 1, "density_file": "iteration-0001/density.npz"},
                {"number": 2, "density_file": "iteration-0002/density.npz"},
            ],
        },
    )
    project = Project(name="Topology Results", studies=[study], jobs=[job], results=[result])

    assert project.resolve(result.job_ref) is job
    assert [frame["number"] for frame in result.metadata["frames"]] == [1, 2]


def test_stage_bar_contains_steps_analysis_studies_but_no_solve_or_optimization():
    source = (ROOT / "opencae/ui/ribbon/stage_bar.py").read_text(encoding="utf-8")
    module = ast.parse(source)
    assignment = next(
        node
        for node in module.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "STAGES" for target in node.targets)
    )
    stages = tuple(ast.literal_eval(assignment.value))

    assert "STEPS" in stages
    assert "ANALYSIS" in stages
    assert "STUDIES" in stages
    assert "SOLVE" not in stages
    assert "OPTIMIZATION" not in stages


def test_tree_context_menus_use_central_actions_for_study_subsections_and_delete():
    source = (ROOT / "opencae/ui/tree/context_menu.py").read_text(encoding="utf-8")

    for token in (
        '"study_responses": (A.OPT_RESPONSE,)',
        '"study_objectives": (A.OPT_OBJECTIVE,)',
        '"study_constraints": (A.OPT_CONSTRAINT,)',
        '"study_filters": (A.OPT_FILTER,)',
        '"study_symmetries": (A.OPT_SYMMETRY,)',
        '"study_controls": (A.OPT_CONTROLS,)',
        '"study_response": (A.EDIT_SELECTED, A.DELETE_SELECTED)',
        '"study_objective": (A.EDIT_SELECTED, A.DELETE_SELECTED)',
        '"study_constraint": (A.EDIT_SELECTED, A.DELETE_SELECTED)',
    ):
        assert token in source


def test_new_ui_and_runtime_modules_define_at_most_one_top_level_class():
    paths = [
        ROOT / "opencae/controllers/job_manager.py",
        ROOT / "opencae/jobs/analysis_job_runner.py",
        ROOT / "opencae/model/entities/studies/study.py",
        ROOT / "opencae/ui/core/widgets/entity_selector_bar.py",
        ROOT / "opencae/ui/core/widgets/monospace_output_view.py",
        ROOT / "opencae/ui/monitors/analysis_job_monitor.py",
        ROOT / "opencae/ui/monitors/topology_job_monitor.py",
        ROOT / "opencae/ui/panels/jobs_panel.py",
        ROOT / "opencae/ui/ribbon/analysis_page.py",
        ROOT / "opencae/ui/ribbon/studies_page.py",
    ]
    for path in paths:
        module = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        classes = [node for node in module.body if isinstance(node, ast.ClassDef)]
        assert len(classes) <= 1, f"{path} defines {[node.name for node in classes]}"
