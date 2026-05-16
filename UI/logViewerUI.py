#logViewerUI.py
#Github\NTE_boheAI\UI\logViewerUI.py

import os
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPlainTextEdit
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QIcon, QTextCursor
import config

class LogViewer(QWidget):
    def __init__(self, log_file="MintNTE.log", parent=None):
        super().__init__(parent)
        self.log_file = log_file
        self._last_pos = 0
        self._user_scrolled = False
        self.setWindowTitle("运行日志")
        self.resize(600, 400)
        try:
            if hasattr(config, 'TITLE_LOGO_PATH') and os.path.exists(str(config.TITLE_LOGO_PATH)):
                self.setWindowIcon(QIcon(str(config.TITLE_LOGO_PATH)))
        except: pass

        self.setStyleSheet("""
            QWidget {
                background-color: #1e1e2f;
                border: 2px solid #0ff;
                border-radius: 8px;
            }
            QPlainTextEdit {
                background-color: #0a0a15;
                color: #0ff;
                font-family: 'Courier New', monospace;
                font-size: 12px;
                border: none;
                margin: 4px;
                padding: 4px;
            }
            QPlainTextEdit:focus {
                outline: none;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)

        self.text_edit = QPlainTextEdit()
        self.text_edit.setReadOnly(True)
        layout.addWidget(self.text_edit)

        self.text_edit.verticalScrollBar().valueChanged.connect(self._on_scroll)

        self._last_pos = 0
        self.refresh_log()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_log)
        self.timer.start(1000)

    def _on_scroll(self):
        scrollbar = self.text_edit.verticalScrollBar()
        self._user_scrolled = scrollbar.value() < scrollbar.maximum() - 2

    def refresh_log(self):
        if not os.path.exists(self.log_file):
            return
        try:
            file_size = os.path.getsize(self.log_file)
            if file_size < self._last_pos:
                self._last_pos = 0
                self.text_edit.clear()

            with open(self.log_file, "r", encoding="utf-8") as f:
                f.seek(self._last_pos)
                new_data = f.read()
                self._last_pos = f.tell()

            if not new_data:
                return

            at_bottom = not self._user_scrolled

            self.text_edit.appendPlainText(new_data.rstrip("\n"))

            line_count = self.text_edit.document().blockCount()
            if line_count > 1000:
                cursor = self.text_edit.textCursor()
                cursor.movePosition(cursor.Start)
                cursor.movePosition(cursor.Down, cursor.KeepAnchor, line_count - 1000)
                cursor.removeSelectedText()

            if at_bottom:
                sb = self.text_edit.verticalScrollBar()
                QTimer.singleShot(0, lambda: sb.setValue(sb.maximum()))
        except Exception:
            pass
