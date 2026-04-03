## **Terminal Board**
### Easily string commonly used sets of bash commands together with the touch of a button.
Designed, maintained, and audited by Sol87 written by Claude Opus.


* Set up complex commands to clickable buttons to be executed in order.
* Built-in terminal can append commands to buttons as you type them out.
* Customize grid size, button colors, and text.
* Multiple "scenes" of custom buttons for various workflows.
* Dark/Light theme or "Auto" to follow your system theme.
* Easily manage commands for your remote servers!

<img width="860" height="632" alt="Screenshot from 2026-03-23 18-24-49" src="https://github.com/user-attachments/assets/600cb12a-d209-44a3-aa8e-dd8808c3a291" />

PR's, bug reports, and suggestions are greatly appriciated.

#### Requirments:

* Any Modern Linux Desktop with Python 3.11+

#### Build Process:

Built with Python 3.12, PySide6, QT, and PyInstaller.

    cd /path/to/TerminalBoard
    python3 -m venv .venv
    source .venv/bin/activate
    python3 -m pip install pyside6
    python3 -m pip install pyinstaller
    pyinstaller --onefile --name Terminal-Board-amd64 --windowed main.py
