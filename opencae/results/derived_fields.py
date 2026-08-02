import numpy as np

_STRESS_NAMES={"SXX":"xx","SYY":"yy","SZZ":"zz","SXY":"xy","SYZ":"yz","SZX":"zx","SXZ":"zx"}


def derived_names(components):
    mapped={name.upper() for name in components}
    return ["Mises"] if {"SXX","SYY","SZZ","SXY","SYZ"}.issubset(mapped) and ({"SZX","SXZ"}&mapped) else []


def attach_derived(grid,block_name,components,values):
    if "Mises" not in derived_names(components):return
    index={name.upper():i for i,name in enumerate(components)}; zx=index.get("SZX",index.get("SXZ"))
    sxx,syy,szz=values[:,index["SXX"]],values[:,index["SYY"]],values[:,index["SZZ"]]
    sxy,syz,szx=values[:,index["SXY"]],values[:,index["SYZ"]],values[:,zx]
    mises=np.sqrt(.5*((sxx-syy)**2+(syy-szz)**2+(szz-sxx)**2)+3*(sxy**2+syz**2+szx**2))
    grid.point_data[f"{block_name}:Mises"]=mises


def component_values(components, values, component):
    names = [name.upper() for name in components]
    if component in components: return values[:, components.index(component)]
    if component == "Magnitude":
        all_index = next((i for i, name in enumerate(names) if name == "ALL"), None)
        return values[:, all_index] if all_index is not None else np.linalg.norm(values[:, :max(1, len(components))], axis=1)
    if component == "Mises" and "Mises" in derived_names(components):
        index = {name.upper(): i for i, name in enumerate(components)}; zx = index.get("SZX", index.get("SXZ"))
        sxx, syy, szz = (values[:, index[name]] for name in ("SXX", "SYY", "SZZ"))
        sxy, syz, szx = values[:, index["SXY"]], values[:, index["SYZ"]], values[:, zx]
        return np.sqrt(.5*((sxx-syy)**2+(syy-szz)**2+(szz-sxx)**2)+3*(sxy**2+syz**2+szx**2))
    return np.asarray([])
