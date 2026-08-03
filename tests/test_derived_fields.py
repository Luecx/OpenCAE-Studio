import numpy as np
from opencae.results.derived_fields import attach_derived, derived_names


class Grid:
    def __init__(self): self.point_data={}


def test_mises_is_derived_for_stress_components():
    components=["SXX","SYY","SZZ","SXY","SYZ","SZX"]
    assert derived_names(components)==["Mises"]
    grid=Grid(); values=np.asarray([[100.0,0.0,0.0,0.0,0.0,0.0]])
    attach_derived(grid,"STRESS",components,values)
    assert np.isclose(grid.point_data["STRESS:Mises"][0],100.0)
