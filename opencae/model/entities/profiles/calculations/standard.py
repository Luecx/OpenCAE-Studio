from __future__ import annotations

import math


def rectangle(v):
    b, h = _positive(v, "width"), _positive(v, "height")
    ratio = min(b, h) / max(b, h)
    j = max(b, h) * min(b, h) ** 3 * (1 / 3 - 0.21 * ratio * (1 - ratio**4 / 12))
    return _result(b*h, b*h**3/12, h*b**3/12, 0.0, j)


def box(v):
    b, h, t = _positive(v, "width"), _positive(v, "height"), _positive(v, "thickness")
    bi, hi = max(b-2*t, 0.0), max(h-2*t, 0.0)
    area = b*h-bi*hi
    iyy = (b*h**3-bi*hi**3)/12
    izz = (h*b**3-hi*bi**3)/12
    bm, hm = max(b-t, 1e-12), max(h-t, 1e-12)
    j = 2*(bm*hm)**2*t/(bm+hm)
    return _result(area, iyy, izz, 0.0, j)


def pipe(v):
    d, t = _positive(v, "diameter"), _positive(v, "thickness")
    di = max(d-2*t, 0.0)
    area = math.pi*(d*d-di*di)/4
    inertia = math.pi*(d**4-di**4)/64
    return _result(area, inertia, inertia, 0.0, 2*inertia)


def i_profile(v):
    h, b = _positive(v, "height"), _positive(v, "flange_width")
    tw, tf = _positive(v, "web_thickness"), _positive(v, "flange_thickness")
    web_h = max(h-2*tf, 0.0)
    area = 2*b*tf+web_h*tw
    iyy = (b*h**3-(b-tw)*web_h**3)/12
    izz = 2*(tf*b**3/12)+web_h*tw**3/12
    j = (2*b*tf**3+web_h*tw**3)/3
    return _result(area, iyy, izz, 0.0, j)


def channel(v):
    h, b = _positive(v, "height"), _positive(v, "flange_width")
    tw, tf = _positive(v, "web_thickness"), _positive(v, "flange_thickness")
    web_h = max(h-2*tf, 0.0)
    parts = ((tw, web_h, tw/2, h/2), (b, tf, b/2, tf/2), (b, tf, b/2, h-tf/2))
    area = sum(w*d for w,d,_,_ in parts)
    cy = sum(w*d*y for w,d,y,_ in parts)/area
    cz = sum(w*d*z for w,d,_,z in parts)/area
    iyy = sum(w*d**3/12+w*d*(z-cz)**2 for w,d,_,z in parts)
    izz = sum(d*w**3/12+w*d*(y-cy)**2 for w,d,y,_ in parts)
    j = (web_h*tw**3+2*b*tf**3)/3
    return _result(area, iyy, izz, 0.0, j, cy, cz)


def _positive(values, key): return max(float(values.get(key, 0.0)), 0.0)
def _result(area, iyy, izz, iyz, j, cy=0.0, cz=0.0):
    return {"Area": area, "Centroid y": cy, "Centroid z": cz, "Iyy": iyy, "Izz": izz, "Iyz": iyz, "Torsion constant": j}


def circle(v):
    d=_positive(v,"diameter"); area=math.pi*d*d/4; inertia=math.pi*d**4/64
    return _result(area,inertia,inertia,0.0,2*inertia)

def u_profile(v):
    result=channel(v)
    return {**result,"Centroid y":result["Centroid z"],"Centroid z":result["Centroid y"],
            "Iyy":result["Izz"],"Izz":result["Iyy"]}
