import logging
from datetime import datetime

from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QSizePolicy


class LogWidget(QtWidgets.QGroupBox):
    def __init__(self, parent):
        super().__init__(parent)
        self.setTitle("Log")

        layout = QtWidgets.QHBoxLayout()
        self.content = QtWidgets.QTextEdit(self)
        self.content.setReadOnly(True)
        self.content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.content.setText('--')

        self.btn_clear = QtWidgets.QPushButton("Clear", self)
        self.btn_clear.clicked.connect(self.clear_log)

        layout.addWidget(self.content)
        layout.addWidget(self.btn_clear, alignment=Qt.AlignmentFlag.AlignRight)
        self.setLayout(layout)

    def set_log(self, text: str):
        lines = self.content.toPlainText().split('\n')
        lines.append(text)
        lines = lines[-50:]
        self.content.setPlainText('\n'.join(lines))
        self.content.verticalScrollBar().setValue(self.content.verticalScrollBar().maximum())

    def clear_log(self):
        self.content.setText("--")


class LogHandler(logging.Handler):
    def __init__(self, log_widget):
        super().__init__()
        self.log_widget = log_widget

    def emit(self, record):
        log_entry = self.format(record)
        self.log_widget.set_log(log_entry)
