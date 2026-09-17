import ctypes

from opencae.ui.other.viewport import spacenav_input


def test_spacenav_bridge_is_optional_when_native_library_is_missing(monkeypatch):
    monkeypatch.setattr(spacenav_input, "find_library", lambda _name: None)

    def missing(_name):
        raise OSError("not installed")

    monkeypatch.setattr(spacenav_input.ctypes, "CDLL", missing)
    assert spacenav_input._load_library() is None


def test_spacenav_motion_layout_matches_libspnav_header():
    fields = dict(spacenav_input._MotionEvent._fields_)
    assert fields["type"] is ctypes.c_int
    assert fields["period"] is ctypes.c_uint
    assert fields["data"] == ctypes.POINTER(ctypes.c_int)
