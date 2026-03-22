from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QRadioButton, QButtonGroup, QLineEdit,
    QPushButton, QGroupBox, QPlainTextEdit, QWidget,
)
from PySide6.QtCore import Qt

import theme

# (operator, short label, explanation)
CHAIN_OPERATORS = [
    (
        "&&",
        "&&  (AND)",
        "Runs the new command only if the existing command succeeds "
        "(exits with code 0). Use this when the second command depends "
        "on the first completing without errors.\n"
        "Example: mkdir build && cd build",
    ),
    (
        "||",
        "||  (OR)",
        "Runs the new command only if the existing command fails "
        "(exits with a non-zero code). Useful for fallbacks.\n"
        "Example: ping -c1 server || echo 'server unreachable'",
    ),
    (
        ";",
        ";   (THEN)",
        "Runs the new command after the existing one finishes, "
        "regardless of whether it succeeded or failed. "
        "The simplest form of chaining.\n"
        "Example: echo start ; sleep 2 ; echo done",
    ),
    (
        "|",
        "|   (PIPE)",
        "Feeds the standard output of the existing command as "
        "standard input to the new command. Both commands run "
        "simultaneously.\n"
        "Example: ls -la | grep '.py'",
    ),
    (
        "&",
        "&   (BACKGROUND)",
        "Starts the existing command in the background, then "
        "immediately starts the new command. Both run in parallel.\n"
        "Example: ./server & ./client",
    ),
]


class SaveCommandDialog(QDialog):
    """Let the user pick a button slot and optionally chain with its command."""

    def __init__(self, command: str, buttons: list[dict],
                 palette: dict | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Save Command to Button")
        self.setMinimumWidth(480)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self._command = command
        self._buttons = buttons  # [{"index", "name", "command"}, ...]
        self._pal = palette or theme.DARK
        self._build_ui()
        self._on_target_changed()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(6)

        # --- command being saved ---
        layout.addWidget(QLabel("Command to save:"))
        cmd_lbl = QLabel(self._command)
        cmd_lbl.setWordWrap(True)
        cmd_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        cmd_lbl.setStyleSheet(theme.code_label(self._pal))
        layout.addWidget(cmd_lbl)

        # --- button name ---
        layout.addSpacing(4)
        layout.addWidget(QLabel("Button name:"))
        self.name_edit = QLineEdit()
        self.name_edit.setMaxLength(64)
        self.name_edit.setPlaceholderText("e.g. Update System")
        layout.addWidget(self.name_edit)

        # --- target slot ---
        layout.addWidget(QLabel("Save to:"))
        self.target_combo = QComboBox()
        for b in self._buttons:
            if b["name"]:
                label = b["name"]
                if b["command"]:
                    preview = b["command"][:40].replace("\n", " ")
                    label += f"  \u2014  {preview}"
            else:
                label = f"Slot {b['index'] + 1} (empty)"
            self.target_combo.addItem(label, b["index"])
        self.target_combo.currentIndexChanged.connect(self._on_target_changed)
        layout.addWidget(self.target_combo)

        # --- chain options (visible only when target has a command) ---
        self.chain_group = QGroupBox("Existing command detected")
        cg_layout = QVBoxLayout(self.chain_group)

        self.replace_radio = QRadioButton("Replace existing command")
        self.chain_radio = QRadioButton("Chain with existing command")
        self.replace_radio.setChecked(True)

        mode_grp = QButtonGroup(self)
        mode_grp.addButton(self.replace_radio)
        mode_grp.addButton(self.chain_radio)
        self.chain_radio.toggled.connect(self._on_chain_toggled)

        cg_layout.addWidget(self.replace_radio)
        cg_layout.addWidget(self.chain_radio)

        # operator selector (indented under chain radio)
        self.op_widget = QWidget()
        op_lay = QVBoxLayout(self.op_widget)
        op_lay.setContentsMargins(20, 4, 0, 0)

        op_lay.addWidget(QLabel("Chain operator:"))
        self.op_combo = QComboBox()
        for op, label, _desc in CHAIN_OPERATORS:
            self.op_combo.addItem(label, op)
        self.op_combo.currentIndexChanged.connect(self._on_op_changed)
        op_lay.addWidget(self.op_combo)

        self.op_desc = QLabel()
        self.op_desc.setWordWrap(True)
        self.op_desc.setStyleSheet(theme.muted_label(self._pal))
        op_lay.addWidget(self.op_desc)

        op_lay.addWidget(QLabel("Preview:"))
        self.preview = QPlainTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setMaximumHeight(56)
        self.preview.setStyleSheet(
            f"QPlainTextEdit {{ background: {self._pal['surface0']};"
            f" color: {self._pal['text']}; }}"
        )
        op_lay.addWidget(self.preview)

        cg_layout.addWidget(self.op_widget)
        self.op_widget.setVisible(False)

        layout.addWidget(self.chain_group)

        # --- buttons ---
        layout.addSpacing(6)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        ok = QPushButton("Save")
        ok.setDefault(True)
        ok.clicked.connect(self.accept)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        btn_row.addWidget(ok)
        btn_row.addWidget(cancel)
        layout.addLayout(btn_row)

    # --- slots ---

    def _on_target_changed(self):
        idx = self.target_combo.currentIndex()
        target = self._buttons[idx]
        has_cmd = bool(target["command"])
        self.chain_group.setVisible(has_cmd)
        if not has_cmd:
            self.replace_radio.setChecked(True)
        # Pre-fill name with existing name or leave blank
        self.name_edit.setText(target["name"])
        self._on_op_changed()

    def _on_chain_toggled(self, checked: bool):
        self.op_widget.setVisible(checked)
        self._on_op_changed()

    def _on_op_changed(self):
        op_idx = self.op_combo.currentIndex()
        self.op_desc.setText(CHAIN_OPERATORS[op_idx][2])
        self._update_preview()

    def _update_preview(self):
        idx = self.target_combo.currentIndex()
        existing = self._buttons[idx]["command"]
        if self.chain_radio.isChecked() and existing:
            op = self.op_combo.currentData()
            self.preview.setPlainText(f"{existing} {op} {self._command}")
        else:
            self.preview.setPlainText(self._command)

    def result_values(self) -> tuple[int, str, str]:
        """Returns (button_index, name, final_command)."""
        idx = self.target_combo.currentIndex()
        btn_index = self._buttons[idx]["index"]
        name = self.name_edit.text().strip()
        existing = self._buttons[idx]["command"]

        if self.chain_radio.isChecked() and existing:
            op = self.op_combo.currentData()
            final = f"{existing} {op} {self._command}"
        else:
            final = self._command

        return btn_index, name, final
