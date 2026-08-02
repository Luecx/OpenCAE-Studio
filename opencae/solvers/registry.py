from .abaqus import AbaqusAdapter
from .calculix import CalculiXAdapter
from .femaster import FEMasterAdapter


def available_solvers():
    adapters = [FEMasterAdapter(), AbaqusAdapter(), CalculiXAdapter()]
    return {adapter.name: adapter for adapter in adapters}
