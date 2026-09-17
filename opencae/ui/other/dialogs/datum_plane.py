import numpy as np
from .datum_base import DatumDialogBase
from .datum_forms import choice, csys_choice, number, page, references


class DatumPlaneDialog(DatumDialogBase):
    METHODS = ("Point and Normal","Three Points","Offset from Face / Plane","Principal CSYS Plane","Edge and Point")
    def __init__(self, default_name, existing_names=(), coordinate_systems=(), parent=None, units=None):
        super().__init__("Create Datum Plane",self.METHODS,default_name,existing_names,parent)
        length_suffix = units.suffix("length") if units is not None else ""
        self.point = references("point"); self.normal = references("datum_vector","edge","face"); self.add_page(page((("Point",self.point),("Normal",self.normal))))
        self.points = [references("point") for _ in range(3)]; self.add_page(page(tuple((f"Point {i+1}",value) for i,value in enumerate(self.points))))
        self.reference = references("face","datum_plane"); self.offset = number(suffix=length_suffix); self.add_page(page((("Face / plane",self.reference),("Offset",self.offset))))
        self.csys = csys_choice(coordinate_systems); self.principal = choice(("XY","YZ","ZX")); self.principal_offset = number(suffix=length_suffix); self.add_page(page((("Coordinate system",self.csys),("Plane",self.principal),("Offset",self.principal_offset))))
        self.edge = references("edge"); self.edge_point = references("point"); self.add_page(page((("Edge",self.edge),("Point",self.edge_point))))
    def values(self):
        method = self.method.currentText()
        if method == "Point and Normal": parameters = {"point":self.point.reference(),"normal":self.normal.reference()}
        elif method == "Three Points": parameters = {f"point_{i+1}":value.reference() for i,value in enumerate(self.points)}
        elif method == "Offset from Face / Plane": parameters = {"reference":self.reference.reference(),"offset":self.offset.value()}
        elif method == "Principal CSYS Plane": parameters = _principal(self.csys.currentData(),self.principal.currentText(),self.principal_offset.value())
        else: parameters = {"edge":self.edge.reference(),"point":self.edge_point.reference()}
        return {"name":self.name.text().strip(),"kind":"Plane","method":method,"parameters":parameters}

def _principal(system,name,offset):
    x = np.asarray(system["axis_1"],float); x /= np.linalg.norm(x); y0 = np.asarray(system["axis_2"],float); y = y0-np.dot(y0,x)*x; y /= np.linalg.norm(y); z = np.cross(x,y)
    normal,axis = {"XY":(z,x),"YZ":(x,y),"ZX":(y,z)}[name]
    return {"origin_x":system["origin"][0],"origin_y":system["origin"][1],"origin_z":system["origin"][2],"normal":tuple(normal),"axis":tuple(axis),"offset":offset}
