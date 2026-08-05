"""Regression tests for Steps, Analyses, Studies, Jobs and shared UI actions."""

import ast
from pathlib import Path

from opencae.model.core import EntityRef, decode_model, encode_model
from opencae.model.entities.analysis import Analysis, AnalysisStep
from opencae.model.entities.jobs import Job, ResultSet
from opencae.model.entities.optimization import TopologyOptimization
from opencae.model.entities.project import Project
from opencae.ui.actions.ids import A
from opencae.ui.ribbon.stage_bar import STAGES
from opencae.ui.tree.context_menu import MAP


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
    assert restored.analyses[0].resolved_steps(restored)[0].id == restored.steps[0].id
    assert restored.studies[0].name == "Topology-1"
    assert restored.optimizations is restored.studies


def test_legacy_optimizations_collection_migrates_to_studies():
    study = TopologyOptimization(name="Topology-1")

    project = Project(name="Legacy", optimizations=[study])

    assert project.studies == [study]
    assert project.optimizations is project.studies


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
        metadata={"result_kind": "topology_density", "frames": []},
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


def test_workflow_stages_remove_solve_and_optimization():
    assert "STEPS" in STAGES
    assert "ANALYSIS" in STAGES
    assert "STUDIES" in STAGES
    assert "SOLVE" not in STAGES
    assert "OPTIMIZATION" not in STAGES


def test_tree_context_menus_reuse_ribbon_actions_and_delete():
    assert A.CONSTRAINT_KINEMATIC in MAP["constraints"]
    assert A.OPT_RESPONSE in MAP["study"]
    assert A.OPT_OBJECTIVE in MAP["study"]
    assert A.OPT_CONSTRAINT in MAP["study"]
    assert A.STUDY_RUN in MAP["study"]
    assert A.DELETE_SELECTED in MAP["study"]
    assert MAP["study_constraints"] == (A.OPT_CONSTRAINT,)
    assert A.DELETE_SELECTED in MAP["study_constraint"]
    assert A.ANALYSIS_RUN in MAP["analysis"]
    assert A.DELETE_SELECTED in MAP["analysis"]
    assert A.DELETE_SELECTED in MAP["analysis_step"]


def test_new_workflow_modules_keep_one_class_per_file():
    repository = Path(__file__).resolve().parents[1]
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
        path = repository / relative
        module = ast.parse(path.read_text(encoding="utf-8"))
        assert ast.get_docstring(module), f"Missing module header: {relative}"
        classes = [node for node in module.body if isinstance(node, ast.ClassDef)]
        assert len(classes) <= 1, (
            f"Expected at most one class in {relative}, found "
            f"{[node.name for node in classes]}"
        )
