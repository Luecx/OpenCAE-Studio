from __future__ import annotations

from copy import deepcopy

from PyQt6.QtGui import QColor, QPalette

from .styles import STYLE_MODULES

DEFAULT_COLOR_SCHEME = "dark"

_COLOR_SCHEMES = {
    "dark": {
        "window": "#171a1f",
        "panel": "#1d2127",
        "panel_alt": "#22272e",
        "panel_active": "#252b32",
        "panel_hover": "#29313a",
        "input": "#171a1f",
        "search": "#252b32",
        "border": "#303741",
        "border_light": "#3a424d",
        "border_hover": "#53606d",
        "ribbon_separator": "#46515c",
        "text": "#e5e9ef",
        "muted": "#98a2ad",
        "disabled": "#66717c",
        "accent": "#3296e6",
        "accent_hover": "#43a6f5",
        "accent_dim": "#173d5b",
        "selection": "#173d5b",
        "selection_text": "#f7fbff",
        "success": "#49b675",
        "success_dim": "#173526",
        "success_border": "#254d38",
        "warning": "#d5a442",
        "warning_dim": "#4b3b19",
        "danger": "#df6262",
        "danger_dim": "#4b2327",
        "viewport": "#232a32",
        "viewport_text": "#dce3e8",
        "overlay_bg": "#20262d",
        "overlay_text": "#f0f3f6",
        "overlay_border": "#46515c",
        "cad_face": "#7f8d99",
        "cad_edge": "#1b232b",
        "cad_vertex": "#d7dde3",
        "meshability_regular": "#72a86a",
        "meshability_irregular": "#9a789f",
        "selection_3d": "#3296e6",
        "mesh_surface": "#89939d",
        "mesh_lines": "#6d7884",
        "result_edge": "#10161c",
        "seed": "#f2b84b",
        "datum": "#ffd166",
        "datum_vector": "#63c7d8",
        "datum_plane": "#8f78d8",
        "datum_plane_edge": "#b7a7ef",
        "reference_point": "#62d6a6",
        "query_marker": "#f2b84b",
        "design_domain": "#4fa3d9",
        "axes": "#dce3e8",
        "axis_x": "#de6a62",
        "axis_y": "#66b56f",
        "axis_z": "#5c91db",
    },
    "light": {
        # Deliberately neutral rather than paper-white. The UI should read as a
        # light engineering workstation surface, not a web page.
        "window": "#e7eaed",
        "panel": "#eef1f3",
        "panel_alt": "#e1e5e8",
        "panel_active": "#d7dde2",
        "panel_hover": "#dce1e5",
        "input": "#f2f4f5",
        "search": "#f5f6f7",
        "border": "#c8ced4",
        "border_light": "#b7c0c8",
        "border_hover": "#87939e",
        "ribbon_separator": "#aeb8c1",
        "text": "#20242a",
        "muted": "#66717d",
        "disabled": "#969fa8",
        "accent": "#1976c9",
        "accent_hover": "#0d84e5",
        "accent_dim": "#d0e5f7",
        "selection": "#d0e5f7",
        "selection_text": "#10263a",
        "success": "#2d8a57",
        "success_dim": "#dceee3",
        "success_border": "#a6cfb5",
        "warning": "#91620a",
        "warning_dim": "#efe2bf",
        "danger": "#bd3b3b",
        "danger_dim": "#efd9d9",
        "viewport": "#cbd1d6",
        "viewport_text": "#26313b",
        "overlay_bg": "#e8ecef",
        "overlay_text": "#20262d",
        "overlay_border": "#aeb8c2",
        "cad_face": "#a8b2bc",
        "cad_edge": "#4f5963",
        "cad_vertex": "#34404a",
        "meshability_regular": "#4f8f4a",
        "meshability_irregular": "#865c8d",
        "selection_3d": "#1976c9",
        "mesh_surface": "#b5bdc5",
        "mesh_lines": "#3d4751",
        "result_edge": "#39434c",
        "seed": "#a97205",
        "datum": "#a97800",
        "datum_vector": "#16879a",
        "datum_plane": "#755ac7",
        "datum_plane_edge": "#6047ad",
        "reference_point": "#20845e",
        "query_marker": "#a97205",
        "design_domain": "#1976c9",
        "axes": "#34404a",
        "axis_x": "#c94d46",
        "axis_y": "#348a47",
        "axis_z": "#3978c4",
    },
    "gray": {
        "window": "#2b2d30",
        "panel": "#313337",
        "panel_alt": "#383a3e",
        "panel_active": "#3f4248",
        "panel_hover": "#45484f",
        "input": "#2b2d30",
        "search": "#3a3c40",
        "border": "#45484e",
        "border_light": "#56595f",
        "border_hover": "#6b7078",
        "ribbon_separator": "#62666d",
        "text": "#dfe1e5",
        "muted": "#a8adb5",
        "disabled": "#777c84",
        "accent": "#4a9bd8",
        "accent_hover": "#5aa9e6",
        "accent_dim": "#2d4b60",
        "selection": "#2d4b60",
        "selection_text": "#edf6ff",
        "success": "#56a869",
        "success_dim": "#2f4535",
        "success_border": "#426148",
        "warning": "#c9a26d",
        "warning_dim": "#51432f",
        "danger": "#d96c75",
        "danger_dim": "#512f34",
        "viewport": "#3c3f44",
        "viewport_text": "#e0e4e8",
        "overlay_bg": "#313337",
        "overlay_text": "#edf0f3",
        "overlay_border": "#5b6067",
        "cad_face": "#9a9fa8",
        "cad_edge": "#25272a",
        "cad_vertex": "#d4d7dc",
        "meshability_regular": "#78a970",
        "meshability_irregular": "#a383a8",
        "selection_3d": "#4a9bd8",
        "mesh_surface": "#888d96",
        "mesh_lines": "#25282d",
        "result_edge": "#1f2226",
        "seed": "#d6a84b",
        "datum": "#e2bd68",
        "datum_vector": "#6ebccc",
        "datum_plane": "#9a86dd",
        "datum_plane_edge": "#c0b2ee",
        "reference_point": "#63c59d",
        "query_marker": "#d6a84b",
        "design_domain": "#4a9bd8",
        "axes": "#e0e4e8",
        "axis_x": "#d36b65",
        "axis_y": "#69b875",
        "axis_z": "#6f9ddd",
    },
}

COLOR_SCHEME_LABELS = {
    "dark": "OpenCAE Dark",
    "light": "OpenCAE Light",
    "gray": "Gray",
}

_ALIASES = {
    "grey": "gray",
    "pycharm": "gray",
    "pycharm-gray": "gray",
    "pycharm grey": "gray",
    "pycharm gray": "gray",
}

_ACTIVE_COLOR_SCHEME = DEFAULT_COLOR_SCHEME
PALETTE = deepcopy(_COLOR_SCHEMES[DEFAULT_COLOR_SCHEME])


def color_scheme_names() -> tuple[str, ...]:
    """Return stable persisted identifiers for all built-in color schemes."""
    return tuple(_COLOR_SCHEMES)


def color_scheme_label(name: str) -> str:
    """Return the user-facing label for one scheme identifier."""
    normalized = normalize_color_scheme(name)
    return COLOR_SCHEME_LABELS[normalized]


def normalize_color_scheme(name: str | None) -> str:
    """Normalize persisted/user aliases and fall back to the default scheme."""
    value = str(name or "").strip().lower()
    value = _ALIASES.get(value, value)
    return value if value in _COLOR_SCHEMES else DEFAULT_COLOR_SCHEME


def current_color_scheme() -> str:
    """Return the identifier whose values currently populate ``PALETTE``."""
    return _ACTIVE_COLOR_SCHEME


def palette_for(name: str | None = None) -> dict[str, str]:
    """Return a detached palette for the requested or currently active scheme."""
    scheme = normalize_color_scheme(name or _ACTIVE_COLOR_SCHEME)
    return deepcopy(_COLOR_SCHEMES[scheme])


def set_color_scheme(name: str | None) -> str:
    """Switch the process-wide palette in-place and return its canonical id.

    ``PALETTE`` is intentionally mutated instead of rebound. A large part of the
    UI imports that dictionary once at module import time; preserving its object
    identity makes those consumers observe the newly selected colors immediately.
    """
    global _ACTIVE_COLOR_SCHEME
    scheme = normalize_color_scheme(name)
    PALETTE.clear()
    PALETTE.update(_COLOR_SCHEMES[scheme])
    _ACTIVE_COLOR_SCHEME = scheme
    return scheme


def stylesheet(name: str | None = None) -> str:
    """Build the global QSS from semantic tokens of one color scheme."""
    palette = PALETTE if name is None else _COLOR_SCHEMES[normalize_color_scheme(name)]
    return "\n".join(module.css(palette) for module in STYLE_MODULES)


def qt_palette(name: str | None = None) -> QPalette:
    """Build a Fusion QPalette for native/un-styled Qt controls."""
    p = PALETTE if name is None else _COLOR_SCHEMES[normalize_color_scheme(name)]
    result = QPalette()
    roles = {
        QPalette.ColorRole.Window: p["window"],
        QPalette.ColorRole.WindowText: p["text"],
        QPalette.ColorRole.Base: p["input"],
        QPalette.ColorRole.AlternateBase: p["panel_alt"],
        QPalette.ColorRole.ToolTipBase: p["panel_alt"],
        QPalette.ColorRole.ToolTipText: p["text"],
        QPalette.ColorRole.Text: p["text"],
        QPalette.ColorRole.Button: p["panel"],
        QPalette.ColorRole.ButtonText: p["text"],
        QPalette.ColorRole.BrightText: p["selection_text"],
        QPalette.ColorRole.Link: p["accent"],
        QPalette.ColorRole.Highlight: p["selection"],
        QPalette.ColorRole.HighlightedText: p["selection_text"],
        QPalette.ColorRole.PlaceholderText: p["muted"],
    }
    for role, value in roles.items():
        result.setColor(role, QColor(value))
    for role in (
        QPalette.ColorRole.WindowText,
        QPalette.ColorRole.Text,
        QPalette.ColorRole.ButtonText,
        QPalette.ColorRole.PlaceholderText,
    ):
        result.setColor(QPalette.ColorGroup.Disabled, role, QColor(p["disabled"]))
    return result


def apply_color_scheme(application, name: str | None) -> str:
    """Apply one scheme to Qt and update the shared palette in-place."""
    scheme = set_color_scheme(name)
    application.setPalette(qt_palette())
    application.setStyleSheet(stylesheet())
    return scheme
