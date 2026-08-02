import numpy as np
import pyvista as pv
from .instance_transform import transform_points


class ReferencePointOverlay:
    def __init__(self): self._names = []
    def clear(self, plotter):
        for name in self._names:
            try: plotter.remove_actor(name, reset_camera=False, render=False)
            except Exception: pass
        self._names.clear()
    def show_part(self, plotter, part, scene):
        self.clear(plotter)
        for index, point in enumerate(getattr(part,"reference_points",())): self._draw(plotter,scene,point,f"part-{index}")
    def show_assembly(self, plotter, project, scene):
        self.clear(plotter)
        for index, point in enumerate(project.assembly.reference_points): self._draw(plotter,scene,point,f"assembly-{index}")
        for instance_name, instance in scene.assembly_instances.items():
            part = project.try_resolve(instance.part_ref)
            if part:
                for index, point in enumerate(part.reference_points): self._draw(plotter,scene,point,f"{instance_name}-{index}",instance,instance_name)
    def _draw(self, plotter, scene, point, key, instance=None, instance_name=None):
        position = np.asarray(point.position,float); position = transform_points([position],instance)[0] if instance else position
        name = f"rp-{key}"; self._names.append(name)
        actor = plotter.add_points(np.asarray([position]), color="#f3b65b", point_size=14, render_points_as_spheres=True,
                                   lighting=False, pickable=True, name=name, render=False)
        label = f"{instance_name}.{point.name}" if instance_name else point.name
        scene.reference_actors[actor] = {"name":label,"kind":"rp","dimension":0,"tag":point.id,"instance":instance_name,"instance_id":getattr(instance,"id",None),"point":tuple(position)}
        text = f"{name}-label"; self._names.append(text)
        plotter.add_point_labels(np.asarray([position]),[label],name=text,show_points=False,point_size=0,font_size=10,
                                 text_color="#f7f9fb",shape_color="#20262d",shape_opacity=.82,always_visible=True,render=False)
