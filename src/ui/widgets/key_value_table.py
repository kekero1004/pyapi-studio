"""Key-Value Table Widget for PyAPI Studio"""

from typing import List, Optional
from dataclasses import dataclass
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QCheckBox, QPushButton, QHeaderView,
    QMenu, QAbstractItemView
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QAction


@dataclass
class KeyValueItem:
    """키-값 아이템"""
    key: str = ""
    value: str = ""
    enabled: bool = True
    description: str = ""


class KeyValueTable(QWidget):
    """키-값 편집 테이블"""

    data_changed = pyqtSignal()

    def __init__(
        self,
        show_description: bool = False,
        placeholder_key: str = "Key",
        placeholder_value: str = "Value",
        parent=None
    ):
        super().__init__(parent)
        self._show_description = show_description
        self._placeholder_key = placeholder_key
        self._placeholder_value = placeholder_value
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(4 if self._show_description else 3)

        headers = ["", self._placeholder_key, self._placeholder_value]
        if self._show_description:
            headers.append("Description")
        self.table.setHorizontalHeaderLabels(headers)

        # Column sizing
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        if self._show_description:
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        
        self.table.setColumnWidth(0, 30)
        self.table.setColumnWidth(1, 150)

        # 선택 모드
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

        # Context menu
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)

        # 셀 변경 감지
        self.table.cellChanged.connect(self._on_cell_changed)

        layout.addWidget(self.table)

        # Add button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.add_btn = QPushButton("+ Add")
        self.add_btn.setFixedWidth(80)
        self.add_btn.clicked.connect(lambda: self.add_row())
        btn_layout.addWidget(self.add_btn)

        layout.addLayout(btn_layout)

    def add_row(self, item: Optional[KeyValueItem] = None):
        """행 추가"""
        if item is None:
            item = KeyValueItem()

        # 셀 변경 시그널 일시 차단
        self.table.blockSignals(True)

        row = self.table.rowCount()
        self.table.insertRow(row)

        # Checkbox
        checkbox_widget = QWidget()
        checkbox_layout = QHBoxLayout(checkbox_widget)
        checkbox_layout.setContentsMargins(0, 0, 0, 0)
        checkbox_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        checkbox = QCheckBox()
        checkbox.setChecked(item.enabled)
        checkbox.stateChanged.connect(self._on_checkbox_changed)
        checkbox_layout.addWidget(checkbox)
        
        self.table.setCellWidget(row, 0, checkbox_widget)

        # Key
        key_item = QTableWidgetItem(item.key)
        self.table.setItem(row, 1, key_item)

        # Value
        value_item = QTableWidgetItem(item.value)
        self.table.setItem(row, 2, value_item)

        # Description
        if self._show_description:
            desc_item = QTableWidgetItem(item.description)
            self.table.setItem(row, 3, desc_item)

        self.table.blockSignals(False)
        self.data_changed.emit()

    def remove_row(self, row: int):
        """행 제거"""
        if 0 <= row < self.table.rowCount():
            self.table.removeRow(row)
            self.data_changed.emit()

    def get_data(self) -> List[KeyValueItem]:
        """전체 데이터 반환"""
        items = []
        for row in range(self.table.rowCount()):
            checkbox_widget = self.table.cellWidget(row, 0)
            checkbox = checkbox_widget.findChild(QCheckBox) if checkbox_widget else None
            
            key_item = self.table.item(row, 1)
            value_item = self.table.item(row, 2)

            item = KeyValueItem(
                key=key_item.text() if key_item else "",
                value=value_item.text() if value_item else "",
                enabled=checkbox.isChecked() if checkbox else True
            )

            if self._show_description:
                desc_item = self.table.item(row, 3)
                item.description = desc_item.text() if desc_item else ""

            items.append(item)

        return items

    def set_data(self, items: List[KeyValueItem]):
        """데이터 설정"""
        self.table.setRowCount(0)

        for item in items:
            self.add_row(item)

    def get_dict(self) -> dict:
        """활성화된 항목만 딕셔너리로 반환"""
        return {
            item.key: item.value
            for item in self.get_data()
            if item.enabled and item.key
        }

    def _on_cell_changed(self, row: int, column: int):
        """셀 변경 처리"""
        self.data_changed.emit()

    def _on_checkbox_changed(self, state: int):
        """체크박스 상태 변경"""
        self.data_changed.emit()

    def _show_context_menu(self, pos):
        row = self.table.rowAt(pos.y())
        if row < 0:
            return

        menu = QMenu(self)

        delete_action = QAction("Delete", self)
        delete_action.triggered.connect(lambda: self.remove_row(row))
        menu.addAction(delete_action)

        duplicate_action = QAction("Duplicate", self)
        duplicate_action.triggered.connect(
            lambda: self.add_row(self.get_data()[row])
        )
        menu.addAction(duplicate_action)

        menu.exec(self.table.viewport().mapToGlobal(pos))

    def clear(self):
        """모든 행 제거"""
        self.table.setRowCount(0)
        self.data_changed.emit()
