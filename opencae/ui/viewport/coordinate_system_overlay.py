import numpy as np
import pyvista as pv
from .instance_transform import transform_points, transform_vector
from .screen_scale import world_size_for_pixels


class CoordinateSystemOverlay:
    def __init__(self):self._names=[]
    def clear(self,plotter):
        for name in self._names:
            try:plotter.remove_actor(name,reset_camera=False,render=False)
            except Exception:pass
        self._names.clear()
    def show_part(self,plotter,part):
        self.clear(plotter)
        for i,system in enumerate(getattr(part,"coordinate_systems",())):self._draw(plotter,system,f"part-{i}")
    def show_assembly(self,plotter,project,scene):
        self.clear(plotter)
        for i,system in enumerate(project.assembly.coordinate_systems):self._draw(plotter,system,f"assembly-{i}")
        for instance_name,instance in scene.assembly_instances.items():
            part=next((x for x in project.parts if x.name==instance.part_name),None)
            if part:
                for i,system in enumerate(part.coordinate_systems):self._draw(plotter,system,f"{instance_name}-{i}",instance)
    def _draw(self,plotter,system,key,instance=None):
        origin=np.asarray(system.origin,dtype=float); x,y,z=self._axes(system)
        if instance:origin=transform_points([origin],instance)[0]; x,y,z=(transform_vector(v,instance) for v in (x,y,z))
        scale=world_size_for_pixels(plotter,origin,44); cylindrical=str(system.system_type).lower().startswith("cyl")
        labels=("r","θ","z") if cylindrical else ("x","y","z")
        for suffix,vector,color,label in zip(("x","y","z"),(x,y,z),("#ef6666","#70d184","#6ca6ff"),labels):
            name=f"csys-{key}-{suffix}"; self._names.append(name); arrow=pv.Arrow(start=origin,direction=vector,scale=scale)
            plotter.add_mesh(arrow,color=color,lighting=False,pickable=False,name=name,render=False)
            tip=origin+vector*scale; lname=f"{name}-label"; self._names.append(lname)
            plotter.add_point_labels(np.asarray([tip]),[label],name=lname,point_size=0,font_size=9,text_color=color,shape_opacity=0,always_visible=False,render=False)
        if cylindrical:self._ring(plotter,origin,z,scale*.48,key)
        label=f"csys-{key}-label"; self._names.append(label)
        plotter.add_point_labels(np.asarray([origin]),[system.name],name=label,point_size=0,font_size=10,text_color="#f0f3f6",shape_color="#20262d",shape_opacity=.82,always_visible=False,render=False)
    def _ring(self,plotter,origin,normal,radius,key):
        name=f"csys-{key}-ring"; self._names.append(name); circle=pv.Circle(radius=radius,resolution=72,normal=normal)
        circle.translate(origin,inplace=True); plotter.add_mesh(circle,color="#8fd3ff",line_width=2,lighting=False,pickable=False,name=name,render=False)
    @staticmethod
    def _axes(system):
        x=CoordinateSystemOverlay._unit(system.axis_1); y0=np.asarray(system.axis_2,dtype=float); y=CoordinateSystemOverlay._unit(y0-np.dot(y0,x)*x); z=CoordinateSystemOverlay._unit(np.cross(x,y))
        if str(system.system_type).lower().startswith("cyl"):z,x=x,y; y=CoordinateSystemOverlay._unit(np.cross(z,x))
        return x,y,z
    @staticmethod
    def _unit(value):
        vector=np.asarray(value,dtype=float); norm=np.linalg.norm(vector); return vector/norm if norm>1e-14 else np.asarray((1.,0.,0.))
