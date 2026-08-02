from __future__ import annotations
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

@dataclass
class Change:
    path: tuple[Any, ...]
    before_exists: bool
    before: Any
    after_exists: bool
    after: Any

def changes(before: Any, after: Any, path=()) -> list[Change]:
    if type(before) is not type(after):
        return [Change(path, True, deepcopy(before), True, deepcopy(after))]
    if isinstance(before, dict):
        result=[]
        for key in before.keys() | after.keys():
            if key not in before: result.append(Change(path+(key,),False,None,True,deepcopy(after[key])))
            elif key not in after: result.append(Change(path+(key,),True,deepcopy(before[key]),False,None))
            else: result.extend(changes(before[key],after[key],path+(key,)))
        return result
    if isinstance(before, list):
        if before==after:return []
        return [Change(path,True,deepcopy(before),True,deepcopy(after))]
    if before!=after:return [Change(path,True,deepcopy(before),True,deepcopy(after))]
    return []

def apply(data: dict, patch: list[Change], forward: bool) -> dict:
    result=deepcopy(data)
    for item in patch:
        exists=item.after_exists if forward else item.before_exists
        value=item.after if forward else item.before
        _assign(result,item.path,exists,deepcopy(value))
    return result

def _assign(root, path, exists, value):
    if not path: raise ValueError("Root replacement is not supported")
    parent=root
    for key in path[:-1]:parent=parent[key]
    key=path[-1]
    if exists:parent[key]=value
    elif isinstance(parent,dict):parent.pop(key,None)
    else:del parent[key]
