import copy
import fcntl
import os
import pty
import re
import signal
import shutil

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QScrollArea, QGridLayout, QPushButton, QLineEdit,
    QPlainTextEdit, QSplitter, QSizePolicy, QLabel, QApplication,
    QComboBox, QMenu, QInputDialog, QMessageBox,
)
from PySide6.QtCore import Qt, QSocketNotifier
from PySide6.QtGui import QTextCursor, QFont

import config
import theme
from command_button import CommandButton
from editor_dialog import EditorDialog
from settings_dialog import SettingsDialog
from save_dialog import SaveCommandDialog

_ANSI_RE = re.compile(
    r"\x1B(?:"
    r"\[[0-?]*[ -/]*[@-~]"             # CSI sequences    (e.g. \x1B[31m)
    r"|\][^\x07\x1B]*(?:\x07|\x1B\\)"  # OSC sequences    (e.g. \x1B]0;title\x07)
    r"|P[^\x1B]*\x1B\\"                # DCS sequences    (e.g. \x1BP...\x1B\\)
    r"|\([A-Z0-9]"                      # charset select   (e.g. \x1B(B)
    r"|[@-Z\\-_]"                       # two-character sequences (e.g. \x1B7) — must be last
    r")"
)
_SUDO_RE = re.compile(r"\bsudo\b")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TerminalBoard")
        self.setMinimumSize(640, 480)
        self.cfg = config.load()
        self._buttons: list[CommandButton] = []
        self._master_fd: int | None = None
        self._child_pid: int | None = None
        self._notifier: QSocketNotifier | None = None
        self._last_command: str = ""
        self._stop_armed: bool = False
        self._pal: dict = {}

        self._build_ui()
        self._spawn_shell()
        self._refresh_profile_combo()
        self._populate_grid()
        self._apply_theme()

        # React to system theme changes while running
        hints = QApplication.instance().styleHints()
        try:
            hints.colorSchemeChanged.connect(self._on_system_theme_changed)
        except AttributeError:
            pass  # Qt < 6.5

    @property
    def _profile(self) -> dict:
        """Mutable reference to the active profile's data."""
        return config.active_profile(self.cfg)

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

        # Profile selector
        self.profile_combo = QComboBox()
        self.profile_combo.setFixedHeight(30)
        self.profile_combo.setMinimumWidth(120)
        self.profile_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.profile_combo.currentIndexChanged.connect(
            self._on_profile_changed)
        top.addWidget(self.profile_combo)

        # Profile manage button
        self.profile_menu_btn = QPushButton("\u22ee")
        self.profile_menu_btn.setFixedSize(30, 30)
        self.profile_menu_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._profile_menu = QMenu(self)
        self._profile_menu.addAction("New Profile", self._new_profile)
        self._profile_menu.addAction("Duplicate Profile",
                                     self._duplicate_profile)
        self._profile_menu.addAction("Rename Profile", self._rename_profile)
        self._profile_menu.addSeparator()
        self._profile_menu.addAction("Delete Profile", self._delete_profile)
        self.profile_menu_btn.setMenu(self._profile_menu)
        top.addWidget(self.profile_menu_btn)

        top.addSpacing(8)

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
        self.scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded)
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
        self.terminal.setPlainText("Welcome to your Terminal Board!\n\n")
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

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setEnabled(False)
        self.stop_btn.setToolTip("Ctrl+C")
        self.stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.stop_btn.clicked.connect(self._stop_process)
        input_bar.addWidget(self.stop_btn)

        self.save_btn = QPushButton("Save to Button")
        self.save_btn.setToolTip("Save last typed command to a button")
        self.save_btn.setEnabled(False)
        self.save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_btn.clicked.connect(self._save_to_button)
        input_bar.addWidget(self.save_btn)

        vbox.addLayout(input_bar)

    # ------------------------------------------------------------------
    # Profile management
    # ------------------------------------------------------------------

    def _refresh_profile_combo(self):
        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()
        for name in self.cfg.get("profiles", {}):
            self.profile_combo.addItem(name)
        idx = self.profile_combo.findText(
            self.cfg.get("active_profile", ""))
        if idx >= 0:
            self.profile_combo.setCurrentIndex(idx)
        self.profile_combo.blockSignals(False)

    def _on_profile_changed(self, index: int):
        name = self.profile_combo.itemText(index)
        if not name or name == self.cfg.get("active_profile"):
            return
        self.cfg["active_profile"] = name
        config.save(self.cfg)
        self._populate_grid()

    def _new_profile(self):
        profiles = self.cfg.get("profiles", {})
        if len(profiles) >= config.MAX_PROFILES:
            QMessageBox.warning(
                self, "Limit Reached",
                f"Maximum of {config.MAX_PROFILES} profiles allowed.")
            return
        name, ok = QInputDialog.getText(
            self, "New Profile", "Profile name:")
        if not ok or not name:
            return
        try:
            name = config.sanitize_profile_name(name)
        except ValueError as e:
            QMessageBox.warning(self, "Invalid Name", str(e))
            return
        if name in profiles:
            QMessageBox.warning(
                self, "Duplicate Name",
                f'A profile named "{name}" already exists.')
            return
        profiles[name] = {
            "grid_cols": config.PROFILE_DEFAULTS["grid_cols"],
            "grid_rows": config.PROFILE_DEFAULTS["grid_rows"],
            "buttons": {},
        }
        self.cfg["active_profile"] = name
        config.save(self.cfg)
        self._refresh_profile_combo()
        self._populate_grid()

    def _duplicate_profile(self):
        profiles = self.cfg.get("profiles", {})
        if len(profiles) >= config.MAX_PROFILES:
            QMessageBox.warning(
                self, "Limit Reached",
                f"Maximum of {config.MAX_PROFILES} profiles allowed.")
            return
        active = self.cfg.get("active_profile", "Default")
        name, ok = QInputDialog.getText(
            self, "Duplicate Profile",
            "Name for the copy:", text=f"{active} (copy)")
        if not ok or not name:
            return
        try:
            name = config.sanitize_profile_name(name)
        except ValueError as e:
            QMessageBox.warning(self, "Invalid Name", str(e))
            return
        if name in profiles:
            QMessageBox.warning(
                self, "Duplicate Name",
                f'A profile named "{name}" already exists.')
            return
        profiles[name] = copy.deepcopy(profiles[active])
        self.cfg["active_profile"] = name
        config.save(self.cfg)
        self._refresh_profile_combo()
        self._populate_grid()

    def _rename_profile(self):
        profiles = self.cfg.get("profiles", {})
        active = self.cfg.get("active_profile", "Default")
        name, ok = QInputDialog.getText(
            self, "Rename Profile", "New name:", text=active)
        if not ok or not name:
            return
        try:
            name = config.sanitize_profile_name(name)
        except ValueError as e:
            QMessageBox.warning(self, "Invalid Name", str(e))
            return
        if name == active:
            return
        if name in profiles:
            QMessageBox.warning(
                self, "Duplicate Name",
                f'A profile named "{name}" already exists.')
            return
        # Rebuild dict to preserve ordering with the new key
        rebuilt = {}
        for k, v in profiles.items():
            rebuilt[name if k == active else k] = v
        self.cfg["profiles"] = rebuilt
        self.cfg["active_profile"] = name
        config.save(self.cfg)
        self._refresh_profile_combo()

    def _delete_profile(self):
        profiles = self.cfg.get("profiles", {})
        if len(profiles) <= 1:
            QMessageBox.information(
                self, "Cannot Delete",
                "You must keep at least one profile.")
            return
        active = self.cfg.get("active_profile", "Default")
        reply = QMessageBox.question(
            self, "Delete Profile",
            f'Delete profile "{active}" and all its buttons?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        del profiles[active]
        self.cfg["active_profile"] = next(iter(profiles))
        config.save(self.cfg)
        self._refresh_profile_combo()
        self._populate_grid()

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
        if self._stop_armed:
            self.stop_btn.setStyleSheet(
                theme.action_btn(p)
                + " QPushButton { color: #ff4444; font-weight: bold; }")
        else:
            self.stop_btn.setStyleSheet(theme.action_btn(p))
        self.profile_menu_btn.setStyleSheet(
            theme.action_btn(p)
            + "QPushButton::menu-indicator { width: 0; height: 0; }")

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

        profile = self._profile
        cols = profile.get("grid_cols", 3)
        rows = profile.get("grid_rows", 3)
        btn_data: dict = profile.get("buttons", {})

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
    # PTY shell management
    # ------------------------------------------------------------------

    def _spawn_shell(self):
        """Spawn a persistent interactive bash session via PTY."""
        self._child_pid, self._master_fd = pty.fork()

        if self._child_pid == 0:
            # Child process — replace with bash
            os.execvp("/bin/bash", ["/bin/bash", "--noediting", "-i"])
            # never returns

        # Parent — make master fd non-blocking so reads don't hang the UI
        flags = fcntl.fcntl(self._master_fd, fcntl.F_GETFL)
        fcntl.fcntl(self._master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

        # Wire into Qt event loop
        self._notifier = QSocketNotifier(
            self._master_fd, QSocketNotifier.Type.Read, self)
        self._notifier.activated.connect(self._on_pty_output)

    # ------------------------------------------------------------------
    # Command execution
    # ------------------------------------------------------------------

    def _stop_process(self):
        """Send Ctrl+C on first click, SIGKILL when armed."""
        if self._master_fd is None:
            return

        if self._stop_armed:
            # Armed — force kill the foreground process, not the shell
            try:
                fg_pgrp = os.tcgetpgrp(self._master_fd)
            except OSError:
                fg_pgrp = None

            if fg_pgrp and fg_pgrp != self._child_pid:
                os.killpg(fg_pgrp, signal.SIGKILL)
            else:
                # Foreground is the shell itself — just send SIGINT again
                os.write(self._master_fd, b"\x03")
            self._reset_stop_btn()
            return

        # First click — send Ctrl+C and arm for kill
        os.write(self._master_fd, b"\x03")
        self._stop_armed = True
        self.stop_btn.setText("Kill")
        self.stop_btn.setToolTip("Ctrl+X")
        self.stop_btn.setStyleSheet(
            self.stop_btn.styleSheet()
            + " QPushButton { color: #ff4444; font-weight: bold; }")

    def _reset_stop_btn(self):
        """Reset the stop button to its default state."""
        self._stop_armed = False
        self.stop_btn.setText("Stop")
        self.stop_btn.setToolTip("Ctrl+C")
        self.stop_btn.setEnabled(False)
        if self._pal:
            self.stop_btn.setStyleSheet(theme.action_btn(self._pal))

    def _run_command(self, name: str, command: str, from_input: bool = False):
        if self._master_fd is None:
            return

        if _SUDO_RE.search(command):
            if from_input:
                self.terminal.appendPlainText("")
                self.terminal.appendHtml(
                    '<span style="color: #ff4444;">'
                    "Note: sudo passwords are visible when typed. "
                    "Use pkexec for secure password entry via system "
                    "dialog.</span>")
                self.terminal.appendPlainText("")
                self.terminal.appendPlainText("")

            
            else:
                if not shutil.which("pkexec"):
                    QMessageBox.warning(
                        self, "pkexec Not Found",
                        "This command requires elevated privileges but "
                        "pkexec is not installed.\n\n"
                        "Install policykit-1 or polkit to enable "
                        "privilege escalation.")
                    return
                command = _SUDO_RE.sub("pkexec", command)

        if not from_input:
            # For button commands, interrupt any running command first
            try:
                fg_pgrp = os.tcgetpgrp(self._master_fd)
            except OSError:
                fg_pgrp = None
            if fg_pgrp is not None and fg_pgrp != self._child_pid:
                os.write(self._master_fd, b"\x03")

        os.write(self._master_fd, (command + "\n").encode())
        self.stop_btn.setEnabled(True)

    def _on_pty_output(self):
        try:
            data = os.read(self._master_fd, 4096)
        except OSError:
            self._on_shell_exit()
            return
        if not data:
            self._on_shell_exit()
            return

        text = data.decode("utf-8", errors="replace")
        clean = _ANSI_RE.sub("", text)
        cursor = self.terminal.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.terminal.setTextCursor(cursor)
        self.terminal.insertPlainText(clean)
        self.terminal.ensureCursorVisible()

        # Reset stop button once the foreground process returns to the shell
        try:
            fg_pgrp = os.tcgetpgrp(self._master_fd)
        except OSError:
            fg_pgrp = None
        if fg_pgrp is None or fg_pgrp == self._child_pid:
            self._reset_stop_btn()

    def _on_shell_exit(self):
        """Handle unexpected shell exit."""
        if self._notifier:
            self._notifier.setEnabled(False)
        if self._master_fd is not None:
            os.close(self._master_fd)
            self._master_fd = None
        if self._child_pid:
            try:
                os.waitpid(self._child_pid, os.WNOHANG)
            except ChildProcessError:
                pass
            self._child_pid = None
        self.stop_btn.setEnabled(False)
        self.terminal.appendPlainText(
            "\n[Shell exited. Restart the application to continue.]")

    # ------------------------------------------------------------------
    # Terminal input
    # ------------------------------------------------------------------

    def _run_input_command(self):
        cmd = self.cmd_input.text().strip()
        if not cmd:
            return
        self._last_command = cmd
        self.save_btn.setEnabled(True)
        self._run_command(cmd, cmd, from_input=True)
        self.cmd_input.clear()

    def _save_to_button(self):
        if not self._last_command:
            return

        profile = self._profile
        btn_data = profile.get("buttons", {})
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
            profile.setdefault("buttons", {})[str(idx)] = {
                "name": name, "command": command, "color": existing_color,
            }
            config.save(self.cfg)
            self._buttons[idx].update_data(name, command, existing_color)

    # ------------------------------------------------------------------
    # Dialogs
    # ------------------------------------------------------------------

    def _open_editor(self, index: int):
        profile = self._profile
        slot = profile.setdefault("buttons", {}).get(str(index), {})
        dlg = EditorDialog(slot.get("name", ""), slot.get("command", ""),
                           slot.get("color", ""), self)
        if dlg.exec() == EditorDialog.DialogCode.Accepted:
            name, command, color = dlg.values()
            profile["buttons"][str(index)] = {
                "name": name, "command": command, "color": color,
            }
            config.save(self.cfg)
            self._buttons[index].update_data(name, command, color)

    def _open_settings(self):
        profile = self._profile
        dlg = SettingsDialog(
            profile.get("grid_cols", 3),
            profile.get("grid_rows", 3),
            self.cfg.get("theme", "auto"),
            self,
        )
        if dlg.exec() == SettingsDialog.DialogCode.Accepted:
            cols, rows, theme_mode = dlg.values()
            theme_changed = theme_mode != self.cfg.get("theme", "auto")
            profile["grid_cols"] = cols
            profile["grid_rows"] = rows
            self.cfg["theme"] = theme_mode
            config.save(self.cfg)
            self._populate_grid()
            if theme_changed:
                self._apply_theme()

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def closeEvent(self, event):
        if self._notifier:
            self._notifier.setEnabled(False)
        if self._master_fd is not None:
            os.close(self._master_fd)
            self._master_fd = None
        if self._child_pid:
            os.kill(self._child_pid, signal.SIGTERM)
            try:
                os.waitpid(self._child_pid, 0)
            except ChildProcessError:
                pass
            self._child_pid = None
        super().closeEvent(event)
