from .standard import box, channel, circle, i_profile, pipe, rectangle, u_profile
from .special import general, graph

_COMMON_OPEN=(
    ("height","Overall height",80.0),("flange_width","Flange width",40.0),
    ("web_thickness","Web thickness",4.0),("flange_thickness","Flange thickness",6.0),
)
_PARAMETERS={
    "Rectangle":(("width","Width",40.0),("height","Height",20.0)),
    "Box":(("width","Outer width",40.0),("height","Outer height",20.0),("thickness","Wall thickness",2.0)),
    "Pipe":(("diameter","Outer diameter",30.0),("thickness","Wall thickness",2.0)),
    "Circle":(("diameter","Diameter",30.0),),
    "I-profile":_COMMON_OPEN,"H-profile":_COMMON_OPEN,"C-profile":_COMMON_OPEN,"Channel":_COMMON_OPEN,"U-profile":_COMMON_OPEN,
    "General":(("area","Area",100.0),("iyy","Iyy",1000.0),("izz","Izz",1000.0),("iyz","Iyz",0.0),("torsion_constant","Torsion constant",100.0)),
    "Graph profile":(("nodes","Local nodes: id, y, z","1,-20,0\n2,20,0"),("segments","Segments: n1, n2, thickness","1,2,2.0")),
}
_CALCULATORS={"Rectangle":rectangle,"Box":box,"Pipe":pipe,"Circle":circle,"I-profile":i_profile,"H-profile":i_profile,
              "C-profile":channel,"Channel":channel,"U-profile":u_profile,"General":general,"Graph profile":graph}

def profile_parameters(profile_type): return _PARAMETERS.get(profile_type,_PARAMETERS["General"])
def profile_properties(profile_type,values): return _CALCULATORS.get(profile_type,general)(values)
