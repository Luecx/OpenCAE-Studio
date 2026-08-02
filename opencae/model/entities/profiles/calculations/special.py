from __future__ import annotations
import math

def general(v):
    return {"Area":float(v.get("area",0.0)),"Centroid y":0.0,"Centroid z":0.0,"Iyy":float(v.get("iyy",0.0)),
            "Izz":float(v.get("izz",0.0)),"Iyz":float(v.get("iyz",0.0)),"Torsion constant":float(v.get("torsion_constant",0.0))}

def graph(v):
    nodes=_nodes(v.get("nodes",v.get("points",""))); segments=_segments(v.get("segments",""),nodes,v.get("thickness",2.0))
    if not segments:return general({})
    area=sum(length*t for length,_,_,_,_,t in segments)
    cy=sum(length*t*y for length,y,_,_,_,t in segments)/area; cz=sum(length*t*z for length,_,z,_,_,t in segments)/area
    iyy=sum(t*length*((z-cz)**2+dz**2/12) for length,_,z,_,dz,t in segments)
    izz=sum(t*length*((y-cy)**2+dy**2/12) for length,y,_,dy,_,t in segments)
    iyz=sum(t*length*(y-cy)*(z-cz) for length,y,z,_,_,t in segments)
    jt=sum(length*t**3/3 for length,_,_,_,_,t in segments)
    return {"Area":area,"Centroid y":cy,"Centroid z":cz,"Iyy":iyy,"Izz":izz,"Iyz":iyz,"Torsion constant":jt}

def _nodes(text):
    result={}
    for line in str(text).replace(";","\n").splitlines():
        try:
            tag,y,z=(value.strip() for value in line.split(",",2)); result[int(tag)]=(float(y),float(z))
        except (ValueError,TypeError):continue
    return result

def _segments(text,nodes,default_t):
    result=[]
    if not text and len(nodes)>1:
        keys=list(nodes); text="\n".join(f"{a},{b},{default_t}" for a,b in zip(keys,keys[1:]))
    for line in str(text).replace(";","\n").splitlines():
        try:
            a,b,t=(value.strip() for value in line.split(",",2)); first,second=nodes[int(a)],nodes[int(b)]; thickness=max(float(t),0.0)
            dy,dz=second[0]-first[0],second[1]-first[1]; length=math.hypot(dy,dz)
            if length and thickness:result.append((length,(first[0]+second[0])/2,(first[1]+second[1])/2,dy,dz,thickness))
        except (ValueError,TypeError,KeyError):continue
    return result
