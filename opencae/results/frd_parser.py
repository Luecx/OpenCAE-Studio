from __future__ import annotations
import re
from .frd_data import FrdData, FrdFieldData

_NUMBER = re.compile(r"[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[Ee][-+]?\d+)?")


def parse_frd(path):
    data = FrdData(); mode = None; element = field = None; row_id = None; row_values = []
    step_id = frame_id = 1; frame_value = 0.0; pending_step = pending_frame = None; frame_map = {}; block_index = 0
    with open(path,"r",errors="replace") as stream:
        for line in stream:
            if line.startswith("    1PSTEP"):
                values = [int(value) for value in _NUMBER.findall(line)]
                if len(values) >= 3: pending_frame, pending_step = values[-2], values[-1]
                continue
            if line.startswith("    2C"): mode = "nodes"; continue
            if line.startswith("    3C"): mode = "elements"; continue
            if line.startswith("  100C"):
                tokens = line.split(); raw_step = _integer(tokens[1], 1) if len(tokens) > 1 else 1
                frame_value = _float(tokens[2], 0.0) if len(tokens) > 2 else 0.0
                if pending_step is not None:
                    step_id, frame_id = pending_step, pending_frame or 1
                else:
                    step_id = raw_step; key = (step_id, frame_value)
                    frame_id = frame_map.setdefault(key, 1 + sum(1 for item in frame_map if item[0] == step_id))
                mode = "results"; continue
            if line.startswith(" -4"):
                if field is not None: _finish_row(field,row_id,row_values); data.fields.append(field)
                tokens = line.split(); block_index += 1
                field = FrdFieldData(tokens[1],step_id=step_id,frame_id=frame_id,frame_value=frame_value,block_index=block_index); row_id = None; row_values = []; continue
            if line.startswith(" -5") and field is not None:
                tokens = line.split(); field.components.append(tokens[1]); continue
            if line.strip() == "-3":
                if mode == "elements" and element is not None: data.elements.append(element); element = None
                if mode == "results" and field is not None:
                    _finish_row(field,row_id,row_values); data.fields.append(field); field = None; row_id = None; row_values = []
                mode = None; continue
            if mode == "nodes" and line.startswith(" -1"):
                values = _numbers(line); data.nodes[int(values[0])] = tuple(map(float,values[1:4])); continue
            if mode == "elements":
                if line.startswith(" -1"):
                    if element is not None: data.elements.append(element)
                    values = _numbers(line); element = (int(values[0]),int(values[1]),[])
                elif line.startswith(" -2") and element is not None: element[2].extend(int(value) for value in _numbers(line))
                continue
            if mode == "results" and field is not None:
                if line.startswith(" -1"):
                    _finish_row(field,row_id,row_values); values = _numbers(line); row_id = int(values[0]); row_values = list(map(float,values[1:]))
                elif line.startswith(" -2"): row_values.extend(map(float,_numbers(line)))
    return data

def _numbers(line): return _NUMBER.findall(line[3:])
def _finish_row(field,row_id,values):
    if row_id is not None: field.values[row_id] = list(values)
def _integer(value,default):
    try: return int(value)
    except (TypeError,ValueError): return default
def _float(value,default):
    try: return float(value)
    except (TypeError,ValueError): return default
