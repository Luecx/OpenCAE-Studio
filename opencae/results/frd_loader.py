from __future__ import annotations
from pathlib import Path
import numpy as np
from opencae.model.entities.jobs import ResultField
from .frd_parser import parse_frd
from .frd_types import FRD_CELL_TYPES
from .derived_fields import attach_derived, component_values, derived_names

class FrdLoader:
    def __init__(self):self._cache={}
    def read(self,path):
        key=str(Path(path).resolve())
        if key not in self._cache:self._cache[key]=parse_frd(key)
        return self._cache[key]
    def fields(self,path):
        result=[]
        for block in self.read(path).fields:
            result.append(ResultField(name=block.name,location="Nodal",components=len(block.components),metadata={
                "components":list(block.components),"derived":derived_names(block.components),"step_id":block.step_id,
                "frame_id":block.frame_id,"frame_value":block.frame_value,"block_index":block.block_index}))
        return result

    def scalar_range(self, path, field):
        if field is None: return (0.0, 1.0)
        data = self.read(path); block_index = int(field.metadata.get("block_index", 0)); component = field.metadata.get("component", "Magnitude")
        block = next((item for item in data.fields if item.block_index == block_index), None)
        if block is None or not block.values: return (0.0, 1.0)
        width = max(len(value) for value in block.values.values()); values = np.full((len(block.values), width), np.nan)
        for row, value in enumerate(block.values.values()): values[row, :len(value)] = value
        scalar = component_values(block.components, values, component); finite = scalar[np.isfinite(scalar)]
        return (float(finite.min()), float(finite.max())) if len(finite) else (0.0, 1.0)

    def pyvista_grid(self,path,step_id=None,frame_id=None):
        import pyvista as pv
        data=self.read(path); tags=data.node_order(); lookup={tag:index for index,tag in enumerate(tags)}; cells=[]; types=[]; element_ids=[]
        for _eid,code,connectivity in data.elements:
            definition=FRD_CELL_TYPES.get(code)
            if definition is None:continue
            vtk_type,count=definition; nodes=connectivity[:count]
            if len(nodes)!=count or any(tag not in lookup for tag in nodes):continue
            cells.extend((count,*(lookup[tag] for tag in nodes))); types.append(vtk_type); element_ids.append(_eid)
        grid=pv.UnstructuredGrid(np.asarray(cells,np.int64),np.asarray(types,np.uint8),data.points()); grid.point_data["node_id"]=np.asarray(tags,np.int64); grid.cell_data["element_id"]=np.asarray(element_ids,np.int64)
        self._attach_fields(grid,data,tags,step_id,frame_id); return grid
    @staticmethod
    def _attach_fields(grid,data,tags,step_id,frame_id):
        blocks=[block for block in data.fields if (step_id is None or block.step_id==step_id) and (frame_id is None or block.frame_id==frame_id)]
        for block in blocks:
            width=max((len(value) for value in block.values.values()),default=len(block.components)); values=np.full((len(tags),width),np.nan)
            for row,tag in enumerate(tags):
                current=block.values.get(tag)
                if current is not None:values[row,:len(current)]=current
            for index,component in enumerate(block.components):
                if index<width:grid.point_data[f"{block.name}:{component}"]=values[:,index]
            physical=values[:,:max(1,min(width,len(block.components)))]; all_index=next((i for i,n in enumerate(block.components) if n.upper()=="ALL"),None)
            grid.point_data[f"{block.name}:Magnitude"]=values[:,all_index] if all_index is not None else np.linalg.norm(physical,axis=1)
            attach_derived(grid,block.name,block.components,values)
