"""Regression tests for main-window geometry and dock-state persistence."""

from PyQt6.QtCore import QByteArray

from opencae.app.window_state import WindowStatePersistence


class _Settings:
    def __init__(self):
        self.values = {}
        self.sync_count = 0

    def value(self, key):
        return self.values.get(key)

    def setValue(self, key, value):
        self.values[key] = value

    def sync(self):
        self.sync_count += 1


class _Window:
    def __init__(self):
        self.geometry = QByteArray(b"geometry")
        self.state = QByteArray(b"dock-state")
        self.restored_geometry = None
        self.restored_state = None
        self.restored_version = None

    def saveGeometry(self):
        return self.geometry

    def saveState(self, version):
        assert version == WindowStatePersistence.STATE_VERSION
        return self.state

    def restoreGeometry(self, value):
        self.restored_geometry = value

    def restoreState(self, value, version):
        self.restored_state = value
        self.restored_version = version


def test_window_state_round_trips_geometry_and_dock_visibility_state():
    settings = _Settings()
    source = _Window()
    persistence = WindowStatePersistence(source, settings)
    persistence.save()

    target = _Window()
    target.geometry = QByteArray()
    target.state = QByteArray()
    WindowStatePersistence(target, settings).restore()

    assert target.restored_geometry == source.geometry
    assert target.restored_state == source.state
    assert target.restored_version == WindowStatePersistence.STATE_VERSION
    assert settings.values[WindowStatePersistence.STATE_SCHEMA_KEY] == 3
    assert settings.sync_count == 1


def test_old_multi_dock_state_is_not_passed_to_qt_restore():
    settings = _Settings()
    settings.values[WindowStatePersistence.STATE_KEY] = QByteArray(b"old-dock-state")
    settings.values[WindowStatePersistence.STATE_SCHEMA_KEY] = 2

    target = _Window()
    WindowStatePersistence(target, settings).restore()

    assert WindowStatePersistence.STATE_VERSION == 3
    assert target.restored_state is None
    assert target.restored_version is None
