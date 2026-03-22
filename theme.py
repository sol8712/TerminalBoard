"""Colour palettes, system-theme detection, and stylesheet generators."""

from PySide6.QtCore import Qt

# ── Catppuccin Mocha (dark) ──────────────────────────────────────────
DARK = {
    "base":     "#181825",
    "surface":  "#1e1e2e",
    "surface0": "#313244",
    "surface1": "#45475a",
    "surface2": "#585b70",
    "text":     "#cdd6f4",
    "subtext":  "#a6adc8",
    "muted":    "#6c7086",
    "accent":   "#89b4fa",
    "green":    "#a6e3a1",
}

# ── Catppuccin Latte (light) ─────────────────────────────────────────
LIGHT = {
    "base":     "#eff1f5",
    "surface":  "#e6e9ef",
    "surface0": "#ccd0da",
    "surface1": "#bcc0cc",
    "surface2": "#acb0be",
    "text":     "#1e1e2e",
    "subtext":  "#363659",
    "muted":    "#5c5f77",
    "accent":   "#1e66f5",
    "green":    "#40a02b",
}


# ── helpers ──────────────────────────────────────────────────────────

def _rgb(hex_color: str) -> str:
    """'#aabbcc' → '170, 187, 204'  (for rgba())."""
    h = hex_color.lstrip("#")
    return f"{int(h[0:2], 16)}, {int(h[2:4], 16)}, {int(h[4:6], 16)}"


def _luminance(hex_color: str) -> float:
    """Perceived brightness 0.0–1.0."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return (0.299 * r + 0.587 * g + 0.114 * b) / 255


def _lighten(hex_color: str, amount: float = 0.15) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    r = min(255, int(r + (255 - r) * amount))
    g = min(255, int(g + (255 - g) * amount))
    b = min(255, int(b + (255 - b) * amount))
    return f"#{r:02x}{g:02x}{b:02x}"


def _darken(hex_color: str, amount: float = 0.15) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    r = max(0, int(r * (1 - amount)))
    g = max(0, int(g * (1 - amount)))
    b = max(0, int(b * (1 - amount)))
    return f"#{r:02x}{g:02x}{b:02x}"


def detect_system() -> str:
    """Return 'dark' or 'light' based on the desktop environment."""
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        return "dark"
    try:
        scheme = app.styleHints().colorScheme()
        if scheme == Qt.ColorScheme.Light:
            return "light"
        if scheme == Qt.ColorScheme.Dark:
            return "dark"
    except AttributeError:
        pass
    # Fallback: check the default window‐text luminance
    try:
        pal = app.palette()
        lum = pal.color(pal.ColorRole.WindowText).lightnessF()
        return "dark" if lum > 0.5 else "light"
    except Exception:
        return "dark"


def resolve(mode: str) -> dict:
    """Return the palette dict for a given mode ('dark', 'light', 'auto')."""
    if mode == "auto":
        mode = detect_system()
    return DARK if mode == "dark" else LIGHT


# ── application‑wide stylesheet ──────────────────────────────────────

def app_stylesheet(p: dict) -> str:
    return f"""
/* ── base ─────────────────────────────────── */
QMainWindow, QDialog {{ background: {p["base"]}; color: {p["text"]}; }}
QWidget {{ color: {p["text"]}; }}
QLabel  {{ background: transparent; }}

/* ── menus ────────────────────────────────── */
QMenu {{
    background: {p["surface0"]}; color: {p["text"]};
    border: 1px solid {p["surface1"]}; padding: 4px;
}}
QMenu::item {{ padding: 4px 20px; border-radius: 3px; }}
QMenu::item:selected {{ background: {p["surface1"]}; }}

/* ── combo / spin ─────────────────────────── */
QComboBox {{
    background: {p["surface0"]}; color: {p["text"]};
    border: 1px solid {p["surface1"]}; border-radius: 4px;
    padding: 4px 8px;
}}
QComboBox:hover {{ border-color: {p["accent"]}; }}
QComboBox::drop-down {{ border: none; }}
QComboBox QAbstractItemView {{
    background: {p["surface0"]}; color: {p["text"]};
    selection-background-color: {p["surface1"]};
    border: 1px solid {p["surface1"]};
}}
QSpinBox {{
    background: {p["surface0"]}; color: {p["text"]};
    border: 1px solid {p["surface1"]}; border-radius: 4px;
    padding: 2px 6px;
}}
QSpinBox:hover {{ border-color: {p["accent"]}; }}

/* ── group box / radio ────────────────────── */
QGroupBox {{
    color: {p["subtext"]}; border: 1px solid {p["surface1"]};
    border-radius: 6px; margin-top: 8px; padding-top: 14px;
}}
QGroupBox::title {{ subcontrol-origin: margin; padding: 0 6px; }}
QRadioButton {{ color: {p["text"]}; spacing: 6px; }}

/* ── line / text edits (dialog fallback) ──── */
QLineEdit, QTextEdit, QPlainTextEdit {{
    background: {p["surface"]}; color: {p["text"]};
    border: 1px solid {p["surface0"]}; border-radius: 4px;
    padding: 4px;
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border-color: {p["accent"]};
}}

/* ── push buttons (dialog fallback) ──────── */
QPushButton {{
    background: {p["surface0"]}; color: {p["text"]};
    border: 1px solid {p["surface1"]}; border-radius: 6px;
    padding: 5px 16px;
}}
QPushButton:hover {{ background: {p["surface1"]}; border-color: {p["accent"]}; }}
QPushButton:pressed {{ background: {p["surface2"]}; }}
QPushButton:disabled {{
    background: {p["surface"]}; color: {p["muted"]};
    border-color: {p["surface0"]};
}}

/* ── scroll bars ──────────────────────────── */
QScrollBar:vertical {{
    background: {p["surface"]}; width: 8px; border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background: {p["surface1"]}; border-radius: 4px; min-height: 20px;
}}
QScrollBar::handle:vertical:hover {{ background: {p["surface2"]}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}
QScrollBar:horizontal {{
    background: {p["surface"]}; height: 8px; border-radius: 4px;
}}
QScrollBar::handle:horizontal {{
    background: {p["surface1"]}; border-radius: 4px; min-width: 20px;
}}
QScrollBar::handle:horizontal:hover {{ background: {p["surface2"]}; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: none; }}

/* ── splitter ─────────────────────────────── */
QSplitter::handle {{ background: {p["surface0"]}; }}
QSplitter::handle:hover {{ background: {p["surface1"]}; }}

/* ── tooltips ─────────────────────────────── */
QToolTip {{
    background: {p["surface0"]}; color: {p["text"]};
    border: 1px solid {p["surface1"]}; padding: 4px;
}}
"""


# ── widget‑specific stylesheets ──────────────────────────────────────

def btn_filled(p: dict) -> str:
    return f"""
QPushButton {{
    background: {p["surface0"]}; color: {p["text"]};
    border: 1px solid {p["surface1"]}; border-radius: 10px;
    font-size: 13px; font-weight: 500; padding: 8px;
}}
QPushButton:hover  {{ background: {p["surface1"]}; border-color: {p["accent"]}; }}
QPushButton:pressed {{ background: {p["surface2"]}; }}
"""


def btn_custom(bg: str, p: dict) -> str:
    text = "#ffffff" if _luminance(bg) < 0.5 else "#1e1e2e"
    hover = _lighten(bg, 0.15)
    pressed = _darken(bg, 0.15)
    border = _darken(bg, 0.25)
    return f"""
QPushButton {{
    background: {bg}; color: {text};
    border: 1px solid {border}; border-radius: 10px;
    font-size: 13px; font-weight: 500; padding: 8px;
}}
QPushButton:hover  {{ background: {hover}; border-color: {p["accent"]}; }}
QPushButton:pressed {{ background: {pressed}; }}
"""


def btn_empty(p: dict) -> str:
    return f"""
QPushButton {{
    background: transparent; color: {p["muted"]};
    border: 1px dashed {p["surface1"]}; border-radius: 10px;
    font-size: 13px; padding: 8px;
}}
QPushButton:hover {{
    background: rgba({_rgb(p["surface0"])}, 0.5);
    border-color: {p["surface2"]}; color: {p["subtext"]};
}}
"""


def btn_menu(p: dict) -> str:
    return (
        f"QPushButton {{ background: rgba({_rgb(p['surface1'])}, 0.4); color: {p['text']};"
        f" border: none; border-radius: 3px;"
        f" font-size: 16px; font-weight: bold; padding: 0px; }}"
        f"QPushButton:hover {{ background: rgba({_rgb(p['accent'])}, 0.5); }}"
    )


def context_menu(p: dict) -> str:
    return (
        f"QMenu {{ background: {p['surface0']}; color: {p['text']};"
        f" border: 1px solid {p['surface1']}; padding: 4px; }}"
        f"QMenu::item {{ padding: 4px 20px; border-radius: 3px; }}"
        f"QMenu::item:selected {{ background: {p['surface1']}; }}"
    )


def scroll_area(p: dict) -> str:
    return (
        f"QScrollArea {{ background: {p['surface']};"
        f" border: 1px solid {p['surface0']}; border-radius: 8px; }}"
    )


def terminal(p: dict) -> str:
    return (
        f"QPlainTextEdit {{ background: {p['surface']}; color: {p['text']};"
        f" border: 1px solid {p['surface0']}; border-radius: 8px; padding: 6px; }}"
    )


def input_field(p: dict) -> str:
    return (
        f"QLineEdit {{ background: {p['surface']}; color: {p['text']};"
        f" border: 1px solid {p['surface0']}; border-radius: 6px; padding: 4px 8px; }}"
        f"QLineEdit:focus {{ border-color: {p['accent']}; }}"
    )


def action_btn(p: dict, hover_accent: str | None = None) -> str:
    hc = hover_accent or p["accent"]
    return (
        f"QPushButton {{ background: {p['surface0']}; color: {p['text']};"
        f" border: 1px solid {p['surface1']}; border-radius: 6px;"
        f" padding: 4px 14px; font-size: 12px; }}"
        f"QPushButton:hover {{ background: {p['surface1']}; border-color: {hc}; }}"
        f"QPushButton:pressed {{ background: {p['surface2']}; }}"
        f"QPushButton:disabled {{ background: {p['surface']}; color: {p['muted']};"
        f" border-color: {p['surface0']}; }}"
    )


def code_label(p: dict) -> str:
    return (
        f"QLabel {{ background: {p['surface0']}; color: {p['text']};"
        f" padding: 6px; border-radius: 4px; }}"
    )


def muted_label(p: dict) -> str:
    return f"QLabel {{ color: {p['muted']}; font-size: 11px; padding: 2px 0; }}"


def prompt_label(p: dict) -> str:
    return f"QLabel {{ color: {p['green']}; font-weight: bold; }}"
