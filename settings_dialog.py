from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QSpinBox, QComboBox, QPushButton, QLabel,
)
from PySide6.QtCore import Qt


class SettingsDialog(QDialog):
    def __init__(self, cols: int = 3, rows: int = 3,
                 theme_mode: str = "auto", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setFixedWidth(280)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self._build_ui(cols, rows, theme_mode)

    def _build_ui(self, cols: int, rows: int, theme_mode: str):
        layout = QVBoxLayout(self)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # --- grid size ---
        self.cols_spin = QSpinBox()
        self.cols_spin.setRange(1, 10)
        self.cols_spin.setValue(cols)
        form.addRow("Columns:", self.cols_spin)

        self.rows_spin = QSpinBox()
        self.rows_spin.setRange(1, 10)
        self.rows_spin.setValue(rows)
        form.addRow("Rows:", self.rows_spin)

        # --- theme ---
        self.theme_combo = QComboBox()
        self.theme_combo.addItem("Automatic", "auto")
        self.theme_combo.addItem("Dark", "dark")
        self.theme_combo.addItem("Light", "light")
        idx = self.theme_combo.findData(theme_mode)
        if idx >= 0:
            self.theme_combo.setCurrentIndex(idx)
        form.addRow("Theme:", self.theme_combo)

        layout.addLayout(form)
        layout.addSpacing(8)

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

    def values(self) -> tuple[int, int, str]:
        return (
            self.cols_spin.value(),
            self.rows_spin.value(),
            self.theme_combo.currentData(),
        )
