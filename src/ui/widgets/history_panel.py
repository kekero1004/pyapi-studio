"""History Panel Widget for PyAPI Studio"""

from typing import Optional, List
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget,
    QListWidgetItem, QLabel, QPushButton, QLineEdit,
    QMenu
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QColor, QAction

from ...data import History


class HistoryItem(QListWidgetItem):
    """히스토리 아이템"""

    METHOD_COLORS = {
        "GET": "#61affe",
        "POST": "#49cc90",
        "PUT": "#fca130",
        "PATCH": "#50e3c2",
        "DELETE": "#f93e3e",
        "HEAD": "#9012fe",
        "OPTIONS": "#0d5aa7",
    }

    def __init__(self, history: History):
        super().__init__()
        self.history = history
        self._setup_display()

    def _setup_display(self):
        method = self.history.method
        url = self.history.url
        status = self.history.status_code or "Error"
        time = self.history.created_at.strftime("%H:%M:%S")

        # URL 축약
        if len(url) > 50:
            url = url[:47] + "..."

        self.setText(f"[{method}] {url}")
        self.setToolTip(
            f"Method: {method}\n"
            f"URL: {self.history.url}\n"
            f"Status: {status}\n"
            f"Time: {time}"
        )

        # 상태에 따른 색상
        if self.history.status_code:
            if 200 <= self.history.status_code < 300:
                self.setForeground(QColor("#4ec9b0"))
            elif 400 <= self.history.status_code < 500:
                self.setForeground(QColor("#ce9178"))
            elif self.history.status_code >= 500:
                self.setForeground(QColor("#f14c4c"))
        else:
            self.setForeground(QColor("#888888"))


class HistoryPanel(QWidget):
    """히스토리 패널"""

    history_selected = pyqtSignal(object)  # History
    history_deleted = pyqtSignal(int)  # history_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Header
        header_layout = QHBoxLayout()
        
        title = QLabel("History")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setFixedWidth(60)
        self.clear_btn.clicked.connect(self._on_clear_clicked)
        header_layout.addWidget(self.clear_btn)
        
        layout.addLayout(header_layout)

        # Search
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search history...")
        self.search_input.textChanged.connect(self._on_search)
        layout.addWidget(self.search_input)

        # List
        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self._show_context_menu)
        layout.addWidget(self.list_widget)

    def add_history(self, history: History):
        """히스토리 추가"""
        item = HistoryItem(history)
        self.list_widget.insertItem(0, item)

        # 최대 개수 제한
        while self.list_widget.count() > 100:
            self.list_widget.takeItem(self.list_widget.count() - 1)

    def set_history(self, history_list: List[History]):
        """히스토리 목록 설정"""
        self.list_widget.clear()
        for history in history_list:
            item = HistoryItem(history)
            self.list_widget.addItem(item)

    def _on_item_double_clicked(self, item: QListWidgetItem):
        """아이템 더블클릭"""
        if isinstance(item, HistoryItem):
            self.history_selected.emit(item.history)

    def _on_search(self, text: str):
        """검색"""
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if isinstance(item, HistoryItem):
                visible = text.lower() in item.history.url.lower()
                item.setHidden(not visible)

    def _on_clear_clicked(self):
        """전체 삭제"""
        self.list_widget.clear()

    def _show_context_menu(self, pos):
        """컨텍스트 메뉴"""
        item = self.list_widget.itemAt(pos)
        if not isinstance(item, HistoryItem):
            return

        menu = QMenu(self)

        load_action = QAction("Load Request", self)
        load_action.triggered.connect(
            lambda: self.history_selected.emit(item.history)
        )
        menu.addAction(load_action)

        menu.addSeparator()

        delete_action = QAction("Delete", self)
        delete_action.triggered.connect(
            lambda: self._delete_item(item)
        )
        menu.addAction(delete_action)

        menu.exec(self.list_widget.viewport().mapToGlobal(pos))

    def _delete_item(self, item: HistoryItem):
        """아이템 삭제"""
        row = self.list_widget.row(item)
        self.list_widget.takeItem(row)
        self.history_deleted.emit(item.history.id)
