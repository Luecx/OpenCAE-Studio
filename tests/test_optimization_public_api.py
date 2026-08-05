"""Regression coverage for the topology runner package boundary."""


def test_topology_runner_is_exported_for_job_manager():
    from opencae.optimization import TopologyOptimizationRunner

    assert TopologyOptimizationRunner.__name__ == "TopologyOptimizationRunner"
    assert TopologyOptimizationRunner.__module__ == "opencae.optimization.job_runner"
