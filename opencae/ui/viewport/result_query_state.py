from __future__ import annotations
import numpy as np
from .result_query import element_values,node_values


class ResultQueryState:
    def __init__(self,owner):self.owner=owner; self.mode=""; self.field=None; self._marker="result-query-marker"
    def configure(self,mode,field=None):
        self.mode,self.field=mode or "",field; self._remove_marker()
        try:self.owner.plotter.disable_picking()
        except Exception:pass
        if not self.mode or self.owner.stage!="RESULTS":self.owner.query_panel.clear_query(); return
        self.owner.query_panel.show_prompt(self.mode); self.owner.canvas._position_overlays(); picker="point" if self.mode=="node" else "cell"
        try:self.owner.plotter.enable_surface_point_picking(callback=self._picked,left_clicking=True,show_message=False,show_point=False,picker=picker,pickable_window=True)
        except Exception:
            try:self.owner.plotter.enable_surface_point_picking(callback=self._picked,left_clicking=True,show_message=False,show_point=False,picker="cell")
            except Exception:pass
    def clear(self):self._remove_marker(); self.owner.query_panel.clear_query()
    def _remove_marker(self):
        try:self.owner.plotter.remove_actor(self._marker,reset_camera=False,render=False)
        except Exception:pass
    def _picked(self,point):
        grid=self.owner.scene.result_grid
        if point is None or grid is None:return
        suffix=f" — {self.field.name} / {self.field.metadata.get('component','Magnitude')}" if self.field is not None else ""
        if self.mode=="node":index,result=node_values(grid,point,self.field); marker=grid.points[index]; title="Node Query"+suffix
        else:index,result=element_values(grid,point,self.field); marker=grid.get_cell(index).center; title="Element Query"+suffix
        self.owner.plotter.add_points(np.asarray([marker]),color="#f2b84b",point_size=14,render_points_as_spheres=True,name=self._marker,pickable=False,render=False)
        self.owner.query_panel.show_result(title,result); self.owner.canvas._position_overlays(); self.owner.plotter.render()
