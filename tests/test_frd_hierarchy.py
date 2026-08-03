from pathlib import Path
from tempfile import TemporaryDirectory
from opencae.results.frd_parser import parse_frd
from opencae.results.navigation import frame_keys,step_ids


def _fields(data):
    return [type('F',(),{'metadata':{'step_id':f.step_id,'frame_id':f.frame_id,'frame_value':f.frame_value}})() for f in data.fields]

def test_frd_loadcases_and_frames_are_kept_separate_without_pstep():
    content='''    2C\n -1         1 0.0 0.0 0.0\n -3\n  100CL  101 0.0 1 0 1 1\n -4 DISP\n -5 D1\n -1 1 1.0\n -3\n  100CL  101 1.0 1 0 1 1\n -4 DISP\n -5 D1\n -1 1 2.0\n -3\n  100CL  102 1.0 1 0 1 1\n -4 STRESS\n -5 SXX\n -1 1 3.0\n -3\n'''
    with TemporaryDirectory() as directory:
        path=Path(directory)/'multi.frd'; path.write_text(content); data=parse_frd(path)
    fields=_fields(data); assert step_ids(fields)==[101,102]; assert frame_keys(fields,101)==[(1,0.0),(2,1.0)]

def test_pstep_maps_result_blocks_to_loadcase_and_frame():
    content='''    2C\n -1 1 0 0 0\n -3\n    1PSTEP 1 1 1\n  100CL 101 1.0 1 0 1 1\n -4 DISP\n -5 D1\n -1 1 1\n -3\n    1PSTEP 2 1 1\n  100CL 101 1.0 1 0 1 1\n -4 STRESS\n -5 SXX\n -1 1 2\n -3\n    1PSTEP 3 1 2\n  100CL 102 10.0 1 4 2BUCKLING 1\n -4 DISP\n -5 D1\n -1 1 3\n -3\n    1PSTEP 4 2 2\n  100CL 103 20.0 1 4 3BUCKLING 1\n -4 DISP\n -5 D1\n -1 1 4\n -3\n'''
    with TemporaryDirectory() as directory:
        path=Path(directory)/'pstep.frd'; path.write_text(content); data=parse_frd(path)
    fields=_fields(data); assert step_ids(fields)==[1,2]; assert frame_keys(fields,1)==[(1,1.0)]; assert frame_keys(fields,2)==[(1,10.0),(2,20.0)]
