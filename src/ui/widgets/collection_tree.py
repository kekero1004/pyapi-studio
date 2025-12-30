"""Collection Tree Widget for PyAPI Studio"""

from typing import Optional, List
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget,
    QTreeWidgetItem, QLabel, QPushButton, QMenu,
    QInputDialog, QMessageBox
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QAction, QColor

from ...data import Collection, Request


class RequestItem(QTreeWidgetItem):
    """요청 트리 아이템"""

    METHOD_COLORS = {
        "GET": "#61affe",
        "POST": "#49cc90",
        "PUT": "#fca130",
        "PATCH": "#50e3c2",
        "DELETE": "#f93e3e",
        "HEAD": "#9012fe",
        "OPTIONS": "#0d5aa7",
    }

    def __init__(self, request: Request):
        super().__init__()
        self.request = request
        self._setup_display()

    def _setup_display(self):
        self.setText(0, f"[{self.request.method}] {self.request.name}")
        color = self.METHOD_COLORS.get(self.request.method, "#cccccc")
        self.setForeground(0, QColor(color))


class CollectionItem(QTreeWidgetItem):
    """컬렉션(폴더) 트리 아이템"""

    def __init__(self, collection: Collection):
        super().__init__()
        self.collection = collection
        self._setup_display()

    def _setup_display(self):
        self.setText(0, f"📁 {self.collection.name}")
        self.setForeground(0, QColor("#cccccc"))


class CollectionTree(QWidget):
    """컬렉션 트리"""

    request_selected = pyqtSignal(object)  # Request
    request_created = pyqtSignal(int)  # collection_id
    request_deleted = pyqtSignal(int)  # request_id
    collection_created = pyqtSignal(object)  # parent_id or None
    collection_deleted = pyqtSignal(int)  # collection_id
    collection_renamed = pyqtSignal(int, str)  # collection_id, new_name

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Header
        header_layout = QHBoxLayout()
        
        title = QLabel("Collections")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        self.add_folder_btn = QPushButton("+📁")
        self.add_folder_btn.setFixedWidth(40)
        self.add_folder_btn.setToolTip("New Collection")
        self.add_folder_btn.clicked.connect(self._on_add_collection)
        header_layout.addWidget(self.add_folder_btn)
        
        self.add_request_btn = QPushButton("+")
        self.add_request_btn.setFixedWidth(40)
        self.add_request_btn.setToolTip("New Request")
        self.add_request_btn.clicked.connect(self._on_add_request)
        header_layout.addWidget(self.add_request_btn)
        
        layout.addLayout(header_layout)

        # Tree
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_context_menu)
        self.tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.tree.setDragDropMode(QTreeWidget.DragDropMode.InternalMove)
        layout.addWidget(self.tree)

    def load_collections(self, collections: List[Collection]):
        """컬렉션 트리 로드"""
        self.tree.clear()
        
        def add_collection(parent_item, collection: Collection):
            item = CollectionItem(collection)
            
            if parent_item is None:
                self.tree.addTopLevelItem(item)
            else:
                parent_item.addChild(item)
            
            # 하위 컬렉션
            for child in collection.children:
                add_collection(item, child)
            
            # 요청들
            for request in collection.requests:
                req_item = RequestItem(request)
                item.addChild(req_item)
            
            item.setExpanded(True)
        
        for collection in collections:
            if collection.parent_id is None:
                add_collection(None, collection)

    def add_request_item(self, request: Request, collection_id: Optional[int] = None):
        """요청 아이템 추가"""
        item = RequestItem(request)
        
        # 컬렉션 찾기
        if collection_id:
            collection_item = self._find_collection_item(collection_id)
            if collection_item:
                collection_item.addChild(item)
                collection_item.setExpanded(True)
                return
        
        # 루트에 추가
        self.tree.addTopLevelItem(item)

    def _find_collection_item(self, collection_id: int) -> Optional[CollectionItem]:
        """컬렉션 아이템 찾기"""
        def search(item):
            if isinstance(item, CollectionItem) and item.collection.id == collection_id:
                return item
            for i in range(item.childCount()):
                result = search(item.child(i))
                if result:
                    return result
            return None
        
        for i in range(self.tree.topLevelItemCount()):
            result = search(self.tree.topLevelItem(i))
            if result:
                return result
        return None

    def _on_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        """아이템 더블클릭"""
        if isinstance(item, RequestItem):
            self.request_selected.emit(item.request)

    def _on_add_collection(self):
        """컬렉션 추가"""
        name, ok = QInputDialog.getText(
            self, "New Collection", "Collection name:"
        )
        if ok and name:
            self.collection_created.emit({"name": name, "parent_id": None})

    def _on_add_request(self):
        """요청 추가"""
        # 선택된 컬렉션에 추가
        current = self.tree.currentItem()
        collection_id = None
        
        if isinstance(current, CollectionItem):
            collection_id = current.collection.id
        elif isinstance(current, RequestItem):
            parent = current.parent()
            if isinstance(parent, CollectionItem):
                collection_id = parent.collection.id
        
        self.request_created.emit(collection_id)

    def _show_context_menu(self, pos):
        """컨텍스트 메뉴"""
        item = self.tree.itemAt(pos)
        menu = QMenu(self)

        if isinstance(item, CollectionItem):
            add_req_action = QAction("New Request", self)
            add_req_action.triggered.connect(
                lambda: self.request_created.emit(item.collection.id)
            )
            menu.addAction(add_req_action)

            add_folder_action = QAction("New Sub-Collection", self)
            add_folder_action.triggered.connect(
                lambda: self._create_sub_collection(item)
            )
            menu.addAction(add_folder_action)

            menu.addSeparator()

            rename_action = QAction("Rename", self)
            rename_action.triggered.connect(
                lambda: self._rename_collection(item)
            )
            menu.addAction(rename_action)

            delete_action = QAction("Delete", self)
            delete_action.triggered.connect(
                lambda: self._delete_collection(item)
            )
            menu.addAction(delete_action)

        elif isinstance(item, RequestItem):
            open_action = QAction("Open", self)
            open_action.triggered.connect(
                lambda: self.request_selected.emit(item.request)
            )
            menu.addAction(open_action)

            menu.addSeparator()

            delete_action = QAction("Delete", self)
            delete_action.triggered.connect(
                lambda: self._delete_request(item)
            )
            menu.addAction(delete_action)

        else:
            # 빈 영역
            add_collection_action = QAction("New Collection", self)
            add_collection_action.triggered.connect(self._on_add_collection)
            menu.addAction(add_collection_action)

        menu.exec(self.tree.viewport().mapToGlobal(pos))

    def _create_sub_collection(self, parent_item: CollectionItem):
        """하위 컬렉션 생성"""
        name, ok = QInputDialog.getText(
            self, "New Sub-Collection", "Collection name:"
        )
        if ok and name:
            self.collection_created.emit({
                "name": name,
                "parent_id": parent_item.collection.id
            })

    def _rename_collection(self, item: CollectionItem):
        """컬렉션 이름 변경"""
        name, ok = QInputDialog.getText(
            self, "Rename Collection", "New name:",
            text=item.collection.name
        )
        if ok and name:
            self.collection_renamed.emit(item.collection.id, name)
            item.setText(0, f"📁 {name}")

    def _delete_collection(self, item: CollectionItem):
        """컬렉션 삭제"""
        reply = QMessageBox.question(
            self, "Delete Collection",
            f"Delete '{item.collection.name}' and all its contents?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.collection_deleted.emit(item.collection.id)
            parent = item.parent()
            if parent:
                parent.removeChild(item)
            else:
                index = self.tree.indexOfTopLevelItem(item)
                self.tree.takeTopLevelItem(index)

    def _delete_request(self, item: RequestItem):
        """요청 삭제"""
        reply = QMessageBox.question(
            self, "Delete Request",
            f"Delete '{item.request.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.request_deleted.emit(item.request.id)
            parent = item.parent()
            if parent:
                parent.removeChild(item)
            else:
                index = self.tree.indexOfTopLevelItem(item)
                self.tree.takeTopLevelItem(index)
