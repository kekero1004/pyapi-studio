"""Response Viewer Widget for PyAPI Studio"""

from typing import Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QLabel, QTableWidget, QTableWidgetItem, QHeaderView,
    QPushButton, QComboBox, QApplication, QFrame
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QColor

from .code_editor import CodeEditorWidget
from ...core import ResponseData


class StatusBar(QWidget):
    """응답 상태 바"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # Status Code
        self.status_label = QLabel("No Response")
        self.status_label.setStyleSheet("""
            QLabel {
                font-weight: bold;
                padding: 4px 12px;
                border-radius: 4px;
                background-color: #3c3c3c;
            }
        """)
        layout.addWidget(self.status_label)

        # Response Time
        self.time_label = QLabel("")
        self.time_label.setStyleSheet("color: #888888;")
        layout.addWidget(self.time_label)

        # Size
        self.size_label = QLabel("")
        self.size_label.setStyleSheet("color: #888888;")
        layout.addWidget(self.size_label)

        layout.addStretch()

    def set_response(self, response: Optional[ResponseData]):
        """응답 정보 설정"""
        if response is None:
            self.status_label.setText("No Response")
            self.status_label.setStyleSheet("""
                QLabel {
                    font-weight: bold;
                    padding: 4px 12px;
                    border-radius: 4px;
                    background-color: #3c3c3c;
                }
            """)
            self.time_label.setText("")
            self.size_label.setText("")
            return

        # Status Code 색상
        status = response.status_code
        if 200 <= status < 300:
            bg_color = "#4ec9b0"
            text_color = "#1e1e1e"
        elif 300 <= status < 400:
            bg_color = "#dcdcaa"
            text_color = "#1e1e1e"
        elif 400 <= status < 500:
            bg_color = "#ce9178"
            text_color = "#1e1e1e"
        else:
            bg_color = "#f14c4c"
            text_color = "white"

        status_text = self._get_status_text(status)
        self.status_label.setText(f"{status} {status_text}")
        self.status_label.setStyleSheet(f"""
            QLabel {{
                font-weight: bold;
                padding: 4px 12px;
                border-radius: 4px;
                background-color: {bg_color};
                color: {text_color};
            }}
        """)

        # Time
        time_ms = response.elapsed_ms
        if time_ms < 1000:
            self.time_label.setText(f"{time_ms:.0f} ms")
        else:
            self.time_label.setText(f"{time_ms/1000:.2f} s")

        # Size
        size = response.size_bytes
        if size < 1024:
            self.size_label.setText(f"{size} B")
        elif size < 1024 * 1024:
            self.size_label.setText(f"{size/1024:.1f} KB")
        else:
            self.size_label.setText(f"{size/(1024*1024):.1f} MB")

    def _get_status_text(self, code: int) -> str:
        texts = {
            200: "OK", 201: "Created", 204: "No Content",
            301: "Moved Permanently", 302: "Found", 304: "Not Modified",
            400: "Bad Request", 401: "Unauthorized", 403: "Forbidden",
            404: "Not Found", 405: "Method Not Allowed",
            500: "Internal Server Error", 502: "Bad Gateway",
            503: "Service Unavailable"
        }
        return texts.get(code, "")

    def set_loading(self):
        """로딩 상태"""
        self.status_label.setText("Sending...")
        self.status_label.setStyleSheet("""
            QLabel {
                font-weight: bold;
                padding: 4px 12px;
                border-radius: 4px;
                background-color: #0e639c;
                color: white;
            }
        """)
        self.time_label.setText("")
        self.size_label.setText("")

    def set_error(self, message: str):
        """에러 상태"""
        self.status_label.setText(f"Error: {message[:50]}")
        self.status_label.setStyleSheet("""
            QLabel {
                font-weight: bold;
                padding: 4px 12px;
                border-radius: 4px;
                background-color: #f14c4c;
                color: white;
            }
        """)
        self.time_label.setText("")
        self.size_label.setText("")


class ResponseViewer(QWidget):
    """응답 뷰어"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._response: Optional[ResponseData] = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Status Bar
        self.status_bar = StatusBar()
        layout.addWidget(self.status_bar)

        # Tab Widget
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Body Tab
        body_widget = QWidget()
        body_layout = QVBoxLayout(body_widget)
        body_layout.setContentsMargins(0, 8, 0, 0)

        # Format selector & copy button
        format_layout = QHBoxLayout()
        
        self.format_combo = QComboBox()
        self.format_combo.addItems(["Pretty", "Raw"])
        self.format_combo.currentTextChanged.connect(self._on_format_changed)
        format_layout.addWidget(QLabel("Format:"))
        format_layout.addWidget(self.format_combo)
        
        format_layout.addStretch()
        
        self.copy_btn = QPushButton("Copy")
        self.copy_btn.setFixedWidth(80)
        self.copy_btn.clicked.connect(self._copy_body)
        format_layout.addWidget(self.copy_btn)
        
        body_layout.addLayout(format_layout)

        self.body_editor = CodeEditorWidget("json", show_format_btn=False)
        self.body_editor.set_read_only(True)
        body_layout.addWidget(self.body_editor)
        
        self.tabs.addTab(body_widget, "Body")

        # Headers Tab
        self.headers_table = QTableWidget()
        self.headers_table.setColumnCount(2)
        self.headers_table.setHorizontalHeaderLabels(["Header", "Value"])
        self.headers_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Interactive
        )
        self.headers_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self.headers_table.setColumnWidth(0, 200)
        self.tabs.addTab(self.headers_table, "Headers")

        # Cookies Tab
        self.cookies_table = QTableWidget()
        self.cookies_table.setColumnCount(2)
        self.cookies_table.setHorizontalHeaderLabels(["Cookie", "Value"])
        self.cookies_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Interactive
        )
        self.cookies_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self.cookies_table.setColumnWidth(0, 200)
        self.tabs.addTab(self.cookies_table, "Cookies")

    def set_response(self, response: ResponseData):
        """응답 설정"""
        self._response = response
        self.status_bar.set_response(response)
        
        # Body
        self._update_body()
        
        # Headers
        self._update_headers(response.headers)
        
        # Cookies
        self._update_cookies(response.cookies)

    def _update_body(self):
        """본문 업데이트"""
        if not self._response:
            self.body_editor.text = ""
            return

        body = self._response.body_text
        format_type = self.format_combo.currentText()

        if format_type == "Pretty":
            # JSON 자동 포맷팅 시도
            content_type = self._response.headers.get("content-type", "")
            if "json" in content_type.lower():
                try:
                    import json
                    parsed = json.loads(body)
                    body = json.dumps(parsed, indent=2, ensure_ascii=False)
                except:
                    pass

        self.body_editor.text = body

    def _update_headers(self, headers: dict):
        """헤더 테이블 업데이트"""
        self.headers_table.setRowCount(len(headers))
        for row, (key, value) in enumerate(headers.items()):
            self.headers_table.setItem(row, 0, QTableWidgetItem(key))
            self.headers_table.setItem(row, 1, QTableWidgetItem(str(value)))

    def _update_cookies(self, cookies: dict):
        """쿠키 테이블 업데이트"""
        self.cookies_table.setRowCount(len(cookies))
        for row, (key, value) in enumerate(cookies.items()):
            self.cookies_table.setItem(row, 0, QTableWidgetItem(key))
            self.cookies_table.setItem(row, 1, QTableWidgetItem(str(value)))

    def _on_format_changed(self, format_type: str):
        """포맷 변경"""
        self._update_body()

    def _copy_body(self):
        """본문 복사"""
        clipboard = QApplication.clipboard()
        clipboard.setText(self.body_editor.text)

    def set_loading(self):
        """로딩 상태"""
        self.status_bar.set_loading()
        self.body_editor.text = ""
        self.headers_table.setRowCount(0)
        self.cookies_table.setRowCount(0)

    def set_error(self, message: str):
        """에러 표시"""
        self.status_bar.set_error(message)
        self.body_editor.text = f"Error: {message}"
        self.headers_table.setRowCount(0)
        self.cookies_table.setRowCount(0)

    def clear(self):
        """초기화"""
        self._response = None
        self.status_bar.set_response(None)
        self.body_editor.text = ""
        self.headers_table.setRowCount(0)
        self.cookies_table.setRowCount(0)
