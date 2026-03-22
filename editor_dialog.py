from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QTextEdit, QPushButton, QFrame, QColorDialog,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor


class EditorDialog(QDialog):
    def __init__(self, name: str = "", command: str = "",
                 color: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Button")
        self.setMinimumWidth(420)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self._color = color
        self._build_ui(name, command)

    def _build_ui(self, name: str, command: str):
        layout = QVBoxLayout(self)
        layout.setSpacing(6)

        layout.addWidget(QLabel("Button Name:"))
        self.name_edit = QLineEdit(name)
        self.name_edit.setMaxLength(64)
        self.name_edit.setPlaceholderText("e.g. Update System")
        layout.addWidget(self.name_edit)

        # Color picker row
        layout.addWidget(QLabel("Button Color:"))
        color_row = QHBoxLayout()
        color_row.setSpacing(6)

        self.color_preview = QFrame()
        self.color_preview.setFixedSize(28, 28)
        self.color_preview.setFrameShape(QFrame.Shape.Box)
        color_row.addWidget(self.color_preview)

        choose_btn = QPushButton("Choose…")
        choose_btn.clicked.connect(self._choose_color)
        color_row.addWidget(choose_btn)

        reset_btn = QPushButton("Reset")
        reset_btn.clicked.connect(self._reset_color)
        color_row.addWidget(reset_btn)

        color_row.addStretch()
        layout.addLayout(color_row)

        self._update_color_preview()

        layout.addWidget(QLabel("Command:"))
        self.cmd_edit = QTextEdit()
        self.cmd_edit.setPlainText(command)
        self.cmd_edit.setPlaceholderText("e.g. sudo apt update && sudo apt upgrade -y")
        self.cmd_edit.setMinimumHeight(130)
        self.cmd_edit.setAcceptRichText(False)
        layout.addWidget(self.cmd_edit)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        ok = QPushButton("OK")
        ok.setDefault(True)
        ok.clicked.connect(self.accept)

        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)

        btn_row.addWidget(ok)
        btn_row.addWidget(cancel)
        layout.addLayout(btn_row)

    def _choose_color(self):
        initial = QColor(self._color) if self._color else QColor("#313244")
        color = QColorDialog.getColor(initial, self, "Choose Button Color")
        if color.isValid():
            self._color = color.name()
            self._update_color_preview()

    def _reset_color(self):
        self._color = ""
        self._update_color_preview()

    def _update_color_preview(self):
        if self._color:
            self.color_preview.setStyleSheet(
                f"background: {self._color}; border: 1px solid #888; border-radius: 4px;"
            )
        else:
            self.color_preview.setStyleSheet(
                "background: transparent; border: 1px dashed #888; border-radius: 4px;"
            )

    def values(self) -> tuple[str, str, str]:
        return (
            self.name_edit.text().strip(),
            self.cmd_edit.toPlainText().strip(),
            self._color,
        )
