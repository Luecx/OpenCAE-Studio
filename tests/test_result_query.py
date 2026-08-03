import numpy as np
from opencae.model.entities.jobs import ResultField
from opencae.ui.viewport.result_query import element_values,node_values


class Cell:
    type="tetra"; point_ids=np.asarray([0,1]); center=np.asarray([0.5,0.0,0.0])
class Grid:
    n_points=2; n_cells=1; points=np.asarray([[0.,0.,0.],[1.,0.,0.]])
    point_data={"node_id":np.asarray([10,20]),"DISP:D1":np.asarray([1.,3.]),"DISP:D2":np.asarray([2.,4.]),"DISP:Magnitude":np.asarray([2.236,5.])}
    cell_data={"element_id":np.asarray([7])}
    def find_closest_point(self,_):return 0
    def find_closest_cell(self,_):return 0
    def get_cell(self,_):return Cell()

def field():return ResultField(name="DISP",location="Nodal",components=1,metadata={"block":"DISP","component":"D1","components":["D1","D2"],"derived":[]})

def test_node_query_is_component_matrix_for_current_field():
    _,result=node_values(Grid(),(0,0,0),field()); values=dict(result.summary)
    assert values["Node"]==10; assert result.columns==["Component","Value"]
    assert result.matrix==[["D1","1"],["D2","2"],["Magnitude","2.236"]]

def test_element_query_is_node_matrix_for_current_component():
    _,result=element_values(Grid(),(0,0,0),field())
    assert dict(result.summary)["Element"]==7; assert result.columns==["Node","D1"]; assert result.matrix==[[10,"1"],[20,"3"]]
