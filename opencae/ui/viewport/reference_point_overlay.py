import numpy as np
import pyvista as pv

from opencae.model.selection import SelectableKind, ViewportHit
from .instance_transform import transform_points
from .safe_operations import remove_actor


class ReferencePointOverlay:
    def __init__(self):
        self._names = []
        self._preview_names = []

    def clear(self, plotter):
        self.clear_preview(plotter)
        for name in self._names:
            remove_actor(plotter, name)
        self._names.clear()

    def clear_preview(self, plotter):
        for name in self._preview_names:
            remove_actor(plotter, name)
        self._preview_names.clear()

    def show_part(self, plotter, part, scene):
        self.clear(plotter)
        for index, point in enumerate(getattr(part, "reference_points", ())):
            if _visible(scene, point):
                self._draw(plotter, scene, point, f"part-{index}")

    def show_assembly(self, plotter, project, scene):
        self.clear(plotter)
        for index, point in enumerate(project.assembly.reference_points):
            if _visible(scene, point):
                self._draw(plotter, scene, point, f"assembly-{index}")
        for instance_id, instance in scene.assembly_instances.items():
            part = project.try_resolve(instance.part_ref)
            if part:
                for index, point in enumerate(part.reference_points):
                    if _visible(scene, point):
                        self._draw(plotter, scene, point, f"{instance_id}-{index}", instance, instance.name)

    def show_preview(self, plotter, name, position):
        self.clear_preview(plotter)
        point = np.asarray(position, dtype=float)
        actor_name = "reference-point-preview"
        label_name = "reference-point-preview-label"
        self._preview_names.extend((actor_name, label_name))
        actor = plotter.add_points(
            np.asarray([point]),
            color="#62d6a6",
            point_size=17,
            render_points_as_spheres=True,
            lighting=False,
            pickable=False,
            name=actor_name,
            render=False,
        )
        self._prefer_coincident_point(actor)
        plotter.add_point_labels(
            np.asarray([point]),
            [str(name)],
            name=label_name,
            show_points=False,
            point_size=0,
            font_size=10,
            text_color="#eafff6",
            shape_color="#20322d",
            shape_opacity=.88,
            always_visible=True,
            render=False,
        )

    def _draw(self, plotter, scene, point, key, instance=None, instance_name=None):
        position = np.asarray(point.position, float)
        position = transform_points([position], instance)[0] if instance else position
        name = f"rp-{key}"
        self._names.append(name)
        actor = plotter.add_points(
            np.asarray([position]),
            color="#f3b65b",
            point_size=14,
            render_points_as_spheres=True,
            lighting=False,
            pickable=True,
            name=name,
            render=False,
        )
        self._prefer_coincident_point(actor)
        label = f"{instance_name}.{point.name}" if instance_name else point.name
        scene.reference_actors[actor] = ViewportHit(
            kind=SelectableKind.REFERENCE_POINT,
            entity_id=point.id,
            instance_id=getattr(instance, "id", None),
            world_position=tuple(position),
            dimension=0,
            label=label,
        )
        text = f"{name}-label"
        self._names.append(text)
        plotter.add_point_labels(
            np.asarray([position]),
            [label],
            name=text,
            show_points=False,
            point_size=0,
            font_size=10,
            text_color="#f7f9fb",
            shape_color="#20262d",
            shape_opacity=.82,
            always_visible=True,
            render=False,
        )

    @staticmethod
    def _prefer_coincident_point(actor):
        try:
            mapper = actor.GetMapper()
            mapper.SetResolveCoincidentTopologyToPolygonOffset()
            mapper.SetRelativeCoincidentTopologyPointOffsetParameter(-2.0)
        except (AttributeError, RuntimeError, TypeError):
            pass


def _visible(scene, entity):
    visibility = getattr(getattr(scene, "owner", None), "visibility", None)
    return visibility is None or visibility.is_entity_visible(entity)
