from .datum_base import DatumDialogBase
from .datum_forms import choice, csys_choice, number, page, references, xyz


class DatumPointDialog(DatumDialogBase):
    METHODS = ("Coordinates","Existing Point","Between Two Points","Along Edge")
    def __init__(self, default_name, existing_names=(), coordinate_systems=(), parent=None):
        super().__init__("Create Datum Point",self.METHODS,default_name,existing_names,parent)
        self.coordinate = xyz("coordinate_"); self.csys = csys_choice(coordinate_systems)
        self.add_page(page((("Coordinate system",self.csys),("X / r",self.coordinate["coordinate_x"]),("Y / θ",self.coordinate["coordinate_y"]),("Z",self.coordinate["coordinate_z"]))))
        self.source = references("point"); self.add_page(page((("Source point",self.source),)))
        self.point_1 = references("point"); self.point_2 = references("point"); self.ratio = number(.5,0,1)
        self.add_page(page((("Point 1",self.point_1),("Point 2",self.point_2),("Ratio",self.ratio))))
        self.edge = references("edge"); self.definition = choice(("Normalized parameter","Arc length from start","Arc length from end")); self.position = number(.5,0,1e15)
        self.add_page(page((("Edge",self.edge),("Definition",self.definition),("Position",self.position))))
    def values(self):
        method = self.method.currentText(); parameters = {}
        if method == "Coordinates": parameters = {**{key:control.value() for key,control in self.coordinate.items()},"coordinate_system":self.csys.currentData()}
        elif method == "Existing Point": parameters = {"source":self.source.reference()}
        elif method == "Between Two Points": parameters = {"point_1":self.point_1.reference(),"point_2":self.point_2.reference(),"ratio":self.ratio.value()}
        else: parameters = {"edge":self.edge.reference(),"definition":self.definition.currentText(),"position":self.position.value()}
        return {"name":self.name.text().strip(),"kind":"Point","method":method,"parameters":parameters}
