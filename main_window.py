import re

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QScrollArea, QGridLayout, QPushButton, QLineEdit,
    QPlainTextEdit, QSplitter, QSizePolicy, QLabel, QApplication,
)
from PySide6.QtCore import Qt, QProcess, QProcessEnvironment
from PySide6.QtGui import QTextCursor, QFont

import config
import theme
from command_button import CommandButton
from editor_dialog import EditorDialog
from settings_dialog import SettingsDialog
from save_dialog import SaveCommandDialog

_ANSI_RE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TerminalBoard")
        self.setMinimumSize(640, 480)
        self.cfg = config.load()
        self._buttons: list[CommandButton] = []
        self._process: QProcess | None = None
        self._last_command: str = ""
        self._pal: dict = {}

        self._build_ui()
        self._populate_grid()
        self._apply_theme()

        # React to system theme changes while running
        hints = QApplication.instance().styleHints()
        try:
            hints.colorSchemeChanged.connect(self._on_system_theme_changed)
        except AttributeError:
            pass  # Qt < 6.5

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        vbox = QVBoxLayout(root)
        vbox.setContentsMargins(10, 10, 10, 10)
        vbox.setSpacing(8)

        # Top bar
        top = QHBoxLayout()
        top.addStretch()
        self.settings_btn = QPushButton("\u2699  Settings")
        self.settings_btn.setFixedHeight(30)
        self.settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.settings_btn.clicked.connect(self._open_settings)
        top.addWidget(self.settings_btn)
        vbox.addLayout(top)

        # Splitter: grid (top) / terminal (bottom)
        splitter = QSplitter(Qt.Orientation.Vertical)

        # Scrollable button grid
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.grid_widget = QWidget()
        self.grid_widget.setStyleSheet("background: transparent;")
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setSpacing(10)
        self.grid_layout.setContentsMargins(10, 10, 10, 10)
        self.scroll.setWidget(self.grid_widget)
        splitter.addWidget(self.scroll)

        # Terminal output pane
        self.terminal = QPlainTextEdit()
        self.terminal.setReadOnly(True)
        self.terminal.setMaximumBlockCount(5000)
        self._mono = QFont("Monospace", 10)
        self._mono.setStyleHint(QFont.StyleHint.TypeWriter)
        self.terminal.setFont(self._mono)
        splitter.addWidget(self.terminal)

        splitter.setSizes([300, 200])
        vbox.addWidget(splitter)

        # Command input bar
        input_bar = QHBoxLayout()
        input_bar.setSpacing(4)

        self.prompt_lbl = QLabel("$")
        self.prompt_lbl.setFont(self._mono)
        input_bar.addWidget(self.prompt_lbl)

        self.cmd_input = QLineEdit()
        self.cmd_input.setFont(self._mono)
        self.cmd_input.setPlaceholderText("Type a command and press Enter\u2026")
        self.cmd_input.returnPressed.connect(self._run_input_command)
        input_bar.addWidget(self.cmd_input)

        self.save_btn = QPushButton("Save to Button")
        self.save_btn.setEnabled(False)
        self.save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_btn.clicked.connect(self._save_to_button)
        input_bar.addWidget(self.save_btn)

        vbox.addLayout(input_bar)

    # ------------------------------------------------------------------
    # Theming
    # ------------------------------------------------------------------

    def _apply_theme(self):
        mode = self.cfg.get("theme", "auto")
        self._pal = theme.resolve(mode)
        p = self._pal

        QApplication.instance().setStyleSheet(theme.app_stylesheet(p))

        self.scroll.setStyleSheet(theme.scroll_area(p))
        self.terminal.setStyleSheet(theme.terminal(p))
        self.prompt_lbl.setStyleSheet(theme.prompt_label(p))
        self.cmd_input.setStyleSheet(theme.input_field(p))
        self.settings_btn.setStyleSheet(theme.action_btn(p))
        self.save_btn.setStyleSheet(theme.action_btn(p, hover_accent=p["green"]))

        for btn in self._buttons:
            btn.apply_theme(p)

    def _on_system_theme_changed(self):
        if self.cfg.get("theme", "auto") == "auto":
            self._apply_theme()

    # ------------------------------------------------------------------
    # Grid management
    # ------------------------------------------------------------------

    def _populate_grid(self):
        # Discard the existing layout and create a fresh one
        QWidget().setLayout(self.grid_widget.layout())
        self._buttons.clear()

        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setSpacing(10)
        self.grid_layout.setContentsMargins(10, 10, 10, 10)

        cols = self.cfg.get("grid_cols", 3)
        rows = self.cfg.get("grid_rows", 3)
        btn_data: dict = self.cfg.get("buttons", {})

        for c in range(cols):
            self.grid_layout.setColumnStretch(c, 1)
        for r in range(rows):
            self.grid_layout.setRowStretch(r, 1)
            for c in range(cols):
                idx = r * cols + c
                slot = btn_data.get(str(idx), {})
                btn = CommandButton(
                    idx, slot.get("name", ""), slot.get("command", ""),
                    color=slot.get("color", ""), palette=self._pal,
                )
                btn.command_clicked.connect(self._run_command)
                btn.edit_requested.connect(self._open_editor)
                self.grid_layout.addWidget(btn, r, c)
                self._buttons.append(btn)

    # ------------------------------------------------------------------
    # Command execution
    # ------------------------------------------------------------------

    def _run_command(self, name: str, command: str):
        if self._process and self._process.state() != QProcess.ProcessState.NotRunning:
            self._process.kill()
            self._process.waitForFinished(2000)

        self.terminal.appendPlainText(f"\n$ {name}\n{'─' * 44}")

        self._process = QProcess(self)
        self._process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self._process.readyReadStandardOutput.connect(self._on_output)
        self._process.finished.connect(self._on_finished)
        self._process.setProcessEnvironment(QProcessEnvironment.systemEnvironment())
        self._process.start("/bin/bash", ["-c", command])

    def _on_output(self):
        raw = self._process.readAllStandardOutput().data().decode("utf-8", errors="replace")
        clean = _ANSI_RE.sub("", raw)
        cursor = self.terminal.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.terminal.setTextCursor(cursor)
        self.terminal.insertPlainText(clean)
        self.terminal.ensureCursorVisible()

    def _on_finished(self, exit_code: int, _exit_status):
        self.terminal.appendPlainText(f"\n[exited with code {exit_code}]")

    # ------------------------------------------------------------------
    # Terminal input
    # ------------------------------------------------------------------

    def _run_input_command(self):
        cmd = self.cmd_input.text().strip()
        if not cmd:
            return
        self._last_command = cmd
        self.save_btn.setEnabled(True)
        self._run_command(cmd, cmd)
        self.cmd_input.clear()

    def _save_to_button(self):
        if not self._last_command:
            return

        btn_data = self.cfg.get("buttons", {})
        info = []
        for btn in self._buttons:
            slot = btn_data.get(str(btn.index), {})
            info.append({
                "index": btn.index,
                "name": slot.get("name", ""),
                "command": slot.get("command", ""),
            })

        dlg = SaveCommandDialog(self._last_command, info,
                                palette=self._pal, parent=self)
        if dlg.exec() == SaveCommandDialog.DialogCode.Accepted:
            idx, name, command = dlg.result_values()
            existing_color = btn_data.get(str(idx), {}).get("color", "")
            self.cfg.setdefault("buttons", {})[str(idx)] = {
                "name": name, "command": command, "color": existing_color,
            }
            config.save(self.cfg)
            self._buttons[idx].update_data(name, command, existing_color)

    # ------------------------------------------------------------------
    # Dialogs
    # ------------------------------------------------------------------

    def _open_editor(self, index: int):
        slot = self.cfg.setdefault("buttons", {}).get(str(index), {})
        dlg = EditorDialog(slot.get("name", ""), slot.get("command", ""),
                           slot.get("color", ""), self)
        if dlg.exec() == EditorDialog.DialogCode.Accepted:
            name, command, color = dlg.values()
            self.cfg["buttons"][str(index)] = {
                "name": name, "command": command, "color": color,
            }
            config.save(self.cfg)
            self._buttons[index].update_data(name, command, color)

    def _open_settings(self):
        dlg = SettingsDialog(
            self.cfg.get("grid_cols", 3),
            self.cfg.get("grid_rows", 3),
            self.cfg.get("theme", "auto"),
            self,
        )
        if dlg.exec() == SettingsDialog.DialogCode.Accepted:
            cols, rows, theme_mode = dlg.values()
            theme_changed = theme_mode != self.cfg.get("theme", "auto")
            self.cfg["grid_cols"] = cols
            self.cfg["grid_rows"] = rows
            self.cfg["theme"] = theme_mode
            config.save(self.cfg)
            self._populate_grid()
            if theme_changed:
                self._apply_theme()

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def closeEvent(self, event):
        if self._process and self._process.state() != QProcess.ProcessState.NotRunning:
            self._process.kill()
            self._process.waitForFinished(2000)
        super().closeEvent(event)
