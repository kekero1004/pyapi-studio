"""URL Bar Widget for PyAPI Studio"""

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QComboBox,
    QLineEdit, QPushButton, QCompleter
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QKeySequence, QShortcut

from ...core import HttpMethod


class UrlBar(QWidget):
    """URL 입력 바"""

    send_requested = pyqtSignal()
    cancel_requested = pyqtSignal()
    method_changed = pyqtSignal(str)
    url_changed = pyqtSignal(str)

    METHOD_COLORS = {
        "GET": "#61affe",
        "POST": "#49cc90",
        "PUT": "#fca130",
        "PATCH": "#50e3c2",
        "DELETE": "#f93e3e",
        "HEAD": "#9012fe",
        "OPTIONS": "#0d5aa7",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_sending = False
        self._setup_ui()
        self._setup_shortcuts()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Method Dropdown
        self.method_combo = QComboBox()
        self.method_combo.setFixedWidth(110)
        for method in HttpMethod:
            self.method_combo.addItem(method.value)
        self.method_combo.currentTextChanged.connect(self._on_method_changed)
        layout.addWidget(self.method_combo)

        # URL Input
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Enter request URL (e.g., https://api.example.com/users)")
        self.url_input.textChanged.connect(self.url_changed.emit)
        self.url_input.returnPressed.connect(self._on_send_clicked)
        layout.addWidget(self.url_input, 1)

        # Send Button
        self.send_btn = QPushButton("Send")
        self.send_btn.setObjectName("sendButton")
        self.send_btn.clicked.connect(self._on_send_clicked)
        layout.addWidget(self.send_btn)

        # 초기 스타일 적용
        self._update_method_style()

    def _setup_shortcuts(self):
        shortcut = QShortcut(QKeySequence("Ctrl+Return"), self)
        shortcut.activated.connect(self._on_send_clicked)

    def _on_method_changed(self, method_text: str):
        self._update_method_style()
        self.method_changed.emit(method_text)

    def _on_send_clicked(self):
        if self._is_sending:
            self.cancel_requested.emit()
        else:
            self.send_requested.emit()

    def _update_method_style(self):
        method = self.method_combo.currentText()
        color = self.METHOD_COLORS.get(method, "#61affe")
        self.method_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {color};
                color: white;
                font-weight: bold;
                border: none;
                padding: 8px 12px;
                border-radius: 4px;
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QComboBox QAbstractItemView {{
                background-color: #252526;
                border: 1px solid #3c3c3c;
                selection-background-color: #094771;
            }}
        """)

    @property
    def method(self) -> str:
        return self.method_combo.currentText()

    @method.setter
    def method(self, value: str):
        self.method_combo.setCurrentText(value)

    @property
    def url(self) -> str:
        return self.url_input.text()

    @url.setter
    def url(self, value: str):
        self.url_input.setText(value)

    def set_sending(self, is_sending: bool):
        """전송 중 상태 설정"""
        self._is_sending = is_sending
        
        if is_sending:
            self.send_btn.setText("Cancel")
            self.send_btn.setObjectName("cancelButton")
        else:
            self.send_btn.setText("Send")
            self.send_btn.setObjectName("sendButton")
        
        # 스타일 새로고침
        self.send_btn.style().unpolish(self.send_btn)
        self.send_btn.style().polish(self.send_btn)
        
        self.method_combo.setEnabled(not is_sending)
        self.url_input.setEnabled(not is_sending)

    def set_url_history(self, urls: list[str]):
        """URL 자동완성 설정"""
        completer = QCompleter(urls)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.url_input.setCompleter(completer)
