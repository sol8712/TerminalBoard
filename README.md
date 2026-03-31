Terminal Board - Easily string commonly used sets of commands together with the touch of a button.

Designed, maintained, and audited by Sol87 written by Claude Opus.

Set up complex commands to clickable buttons to be executed in order.
Built-in terminal can append commands to buttons as you type them out.
Customize grid size, button colors, and text.
Dark/Light theme or "Auto" to follow your system theme.


PR's, bug reports, and suggestions are greatly appriciated.

Requirments:
Python 3.11+
Polkit(required for sudo use)

Most modern linux desktops will have these preinstalled.

Build Process:
Built with Python 3.12, PySide6, QT, and PyInstaller.

cd /path/to/TerminalBoard
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install pyside6
python3 -m pip install pyinstaller
pyinstaller --onefile --name Terminal-Board-amd64 --windowed main.p
