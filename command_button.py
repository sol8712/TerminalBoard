from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QMenu, QSizePolicy
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QAction, QCursor

import theme


class CommandButton(QWidget):
    command_clicked = Signal(str, str)   # (name, command)
    edit_requested = Signal(int)          # button index

    def __init__(self, index: int, name: str = "", command: str = "",
                 color: str = "", palette: dict | None = None, parent=None):
        super().__init__(parent)
        self.index = index
        self.name = name
        self.command = command
        self.color = color
        self._pal = palette or theme.DARK
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.btn = QPushButton()
        self.btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn.clicked.connect(self._on_click)
        layout.addWidget(self.btn)

        # Overlay menu button — manually positioned, not in layout
        self.menu_btn = QPushButton("⋮", self)
        self.menu_btn.setFixedSize(22, 22)
        self.menu_btn.setCursor(Qt.CursorShape.ArrowCursor)
        self.menu_btn.setToolTip("Options")
        self.menu_btn.setVisible(False)
        self.menu_btn.clicked.connect(self._show_menu)

        self._apply_styles()

    def _apply_styles(self):
        p = self._pal
        label = self.name if self.name else f"Slot {self.index + 1}"
        self.btn.setText(label)
        if self.color and self.command:
            self.btn.setStyleSheet(theme.btn_custom(self.color, p))
        elif self.command:
            self.btn.setStyleSheet(theme.btn_filled(p))
        else:
            self.btn.setStyleSheet(theme.btn_empty(p))
        self.menu_btn.setStyleSheet(theme.btn_menu(p))

    def update_data(self, name: str, command: str, color: str = ""):
        self.name = name
        self.command = command
        self.color = color
        self._apply_styles()

    def apply_theme(self, palette: dict):
        self._pal = palette
        self._apply_styles()

    # --- hover show/hide ---

    def enterEvent(self, event):
        self.menu_btn.setVisible(True)
        self.menu_btn.raise_()
        super().enterEvent(event)

    def leaveEvent(self, event):
        if not self.rect().contains(self.mapFromGlobal(QCursor.pos())):
            self.menu_btn.setVisible(False)
        super().leaveEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.menu_btn.move(self.width() - self.menu_btn.width() - 4, 4)
        self.menu_btn.raise_()

    # --- actions ---

    def _on_click(self):
        if self.command:
            self.command_clicked.emit(self.name, self.command)

    def _show_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet(theme.context_menu(self._pal))
        edit_act = QAction("Edit", self)
        edit_act.triggered.connect(lambda: self.edit_requested.emit(self.index))
        menu.addAction(edit_act)
        menu.exec(self.menu_btn.mapToGlobal(self.menu_btn.rect().bottomLeft()))

    def sizeHint(self):
        return QSize(110, 110)
