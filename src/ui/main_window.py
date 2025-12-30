"""Main Window for PyAPI Studio"""

import asyncio
from typing import Optional
from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QTabWidget, QMenuBar, QMenu, QStatusBar,
    QMessageBox, QInputDialog, QFileDialog, QLabel,
    QApplication
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction, QKeySequence

from .widgets import (
    UrlBar, KeyValueTable, KeyValueItem, CodeEditorWidget,
    ResponseViewer, HistoryPanel, CollectionTree
)
from ..core import (
    HttpMethod, RequestConfig, ResponseData,
    HttpxRequestExecutor, VariableResolver
)
from ..data import (
    DatabaseManager, Collection, Request, Header, Parameter,
    Environment, EnvironmentVariable, History
)


class RequestPanel(QWidget):
    """요청 편집 패널"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # URL Bar
        self.url_bar = UrlBar()
        layout.addWidget(self.url_bar)

        # Tabs
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Params Tab
        self.params_table = KeyValueTable(
            placeholder_key="Parameter",
            placeholder_value="Value"
        )
        self.tabs.addTab(self.params_table, "Params")

        # Headers Tab
        self.headers_table = KeyValueTable(
            placeholder_key="Header",
            placeholder_value="Value"
        )
        # 기본 헤더 추가
        self.headers_table.add_row(KeyValueItem("Content-Type", "application/json", True))
        self.tabs.addTab(self.headers_table, "Headers")

        # Body Tab
        body_widget = QWidget()
        body_layout = QVBoxLayout(body_widget)
        body_layout.setContentsMargins(0, 8, 0, 0)
        
        self.body_editor = CodeEditorWidget("json")
        body_layout.addWidget(self.body_editor)
        
        self.tabs.addTab(body_widget, "Body")

        # Auth Tab
        auth_widget = QWidget()
        auth_layout = QVBoxLayout(auth_widget)
        auth_layout.setContentsMargins(8, 8, 8, 8)
        
        auth_label = QLabel("Authentication settings (coming soon)")
        auth_label.setStyleSheet("color: #888888;")
        auth_layout.addWidget(auth_label)
        auth_layout.addStretch()
        
        self.tabs.addTab(auth_widget, "Auth")

    def get_request_config(self) -> RequestConfig:
        """현재 설정에서 RequestConfig 생성"""
        method = HttpMethod(self.url_bar.method)
        url = self.url_bar.url
        
        headers = self.headers_table.get_dict()
        params = self.params_table.get_dict()
        
        body = self.body_editor.text
        body_type = "json" if body.strip() else "none"
        
        return RequestConfig(
            method=method,
            url=url,
            headers=headers,
            params=params,
            body=body if body.strip() else None,
            body_type=body_type
        )

    def load_request(self, request: Request):
        """요청 데이터 로드"""
        self.url_bar.method = request.method
        self.url_bar.url = request.url
        
        # Headers
        self.headers_table.clear()
        for h in request.headers:
            self.headers_table.add_row(KeyValueItem(h.key, h.value, h.enabled))
        
        # Params
        self.params_table.clear()
        for p in request.parameters:
            self.params_table.add_row(KeyValueItem(p.key, p.value, p.enabled))
        
        # Body
        self.body_editor.text = request.body or ""

    def clear(self):
        """초기화"""
        self.url_bar.url = ""
        self.url_bar.method = "GET"
        self.headers_table.clear()
        self.headers_table.add_row(KeyValueItem("Content-Type", "application/json", True))
        self.params_table.clear()
        self.body_editor.text = ""


class MainWindow(QMainWindow):
    """메인 윈도우"""

    def __init__(self):
        super().__init__()
        self._current_request_id: Optional[int] = None
        self._executor = HttpxRequestExecutor()
        self._resolver = VariableResolver()
        self._is_sending = False
        
        self._setup_ui()
        self._setup_menu()
        self._setup_connections()
        self._load_data()
        
        # 스타일시트 로드
        self._load_stylesheet()

    def _setup_ui(self):
        self.setWindowTitle("PyAPI Studio")
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)

        # Central Widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Main Splitter
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(self.main_splitter)

        # === Left Panel (Sidebar) ===
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(8, 8, 8, 8)
        left_layout.setSpacing(8)

        # Collection Tree
        self.collection_tree = CollectionTree()
        left_layout.addWidget(self.collection_tree, 2)

        # History Panel
        self.history_panel = HistoryPanel()
        left_layout.addWidget(self.history_panel, 1)

        self.main_splitter.addWidget(left_panel)

        # === Right Panel (Main Area) ===
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(8, 8, 8, 8)
        right_layout.setSpacing(8)

        # Request/Response Splitter
        self.req_res_splitter = QSplitter(Qt.Orientation.Vertical)
        right_layout.addWidget(self.req_res_splitter)

        # Request Panel
        self.request_panel = RequestPanel()
        self.req_res_splitter.addWidget(self.request_panel)

        # Response Viewer
        self.response_viewer = ResponseViewer()
        self.req_res_splitter.addWidget(self.response_viewer)

        # 분할 비율
        self.req_res_splitter.setSizes([400, 400])

        self.main_splitter.addWidget(right_panel)

        # 메인 분할 비율
        self.main_splitter.setSizes([280, 920])

        # Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

    def _setup_menu(self):
        menubar = self.menuBar()

        # File Menu
        file_menu = menubar.addMenu("File")

        new_action = QAction("New Request", self)
        new_action.setShortcut(QKeySequence("Ctrl+N"))
        new_action.triggered.connect(self._new_request)
        file_menu.addAction(new_action)

        save_action = QAction("Save Request", self)
        save_action.setShortcut(QKeySequence("Ctrl+S"))
        save_action.triggered.connect(self._save_request)
        file_menu.addAction(save_action)

        file_menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.setShortcut(QKeySequence("Ctrl+Q"))
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Edit Menu
        edit_menu = menubar.addMenu("Edit")

        clear_action = QAction("Clear Request", self)
        clear_action.triggered.connect(self._clear_request)
        edit_menu.addAction(clear_action)

        # View Menu
        view_menu = menubar.addMenu("View")

        toggle_sidebar = QAction("Toggle Sidebar", self)
        toggle_sidebar.setShortcut(QKeySequence("Ctrl+B"))
        toggle_sidebar.triggered.connect(self._toggle_sidebar)
        view_menu.addAction(toggle_sidebar)

        # Help Menu
        help_menu = menubar.addMenu("Help")

        about_action = QAction("About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _setup_connections(self):
        # URL Bar
        self.request_panel.url_bar.send_requested.connect(self._send_request)
        self.request_panel.url_bar.cancel_requested.connect(self._cancel_request)

        # Collection Tree
        self.collection_tree.request_selected.connect(self._on_request_selected)
        self.collection_tree.request_created.connect(self._on_request_created)
        self.collection_tree.request_deleted.connect(self._on_request_deleted)
        self.collection_tree.collection_created.connect(self._on_collection_created)
        self.collection_tree.collection_deleted.connect(self._on_collection_deleted)

        # History Panel
        self.history_panel.history_selected.connect(self._on_history_selected)

    def _load_stylesheet(self):
        """스타일시트 로드"""
        style_path = Path(__file__).parent / "styles" / "dark.qss"
        if style_path.exists():
            with open(style_path, 'r') as f:
                self.setStyleSheet(f.read())

    def _load_data(self):
        """데이터 로드"""
        db = DatabaseManager.get_instance()
        
        with db.session() as session:
            # 컬렉션 로드
            collections = session.query(Collection).filter(
                Collection.parent_id.is_(None)
            ).all()
            self.collection_tree.load_collections(collections)
            
            # 히스토리 로드
            history_list = session.query(History).order_by(
                History.created_at.desc()
            ).limit(100).all()
            self.history_panel.set_history(history_list)

    # === Request Actions ===

    def _send_request(self):
        """요청 전송"""
        if self._is_sending:
            return

        url = self.request_panel.url_bar.url.strip()
        if not url:
            QMessageBox.warning(self, "Warning", "Please enter a URL")
            return

        # URL에 프로토콜이 없으면 추가
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
            self.request_panel.url_bar.url = url

        self._is_sending = True
        self.request_panel.url_bar.set_sending(True)
        self.response_viewer.set_loading()
        self.status_bar.showMessage("Sending request...")

        # 비동기 요청 실행
        config = self.request_panel.get_request_config()
        config.url = url  # 수정된 URL 적용

        # 변수 치환
        config.url = self._resolver.resolve(config.url)
        config.headers = self._resolver.resolve_dict(config.headers)
        config.params = self._resolver.resolve_dict(config.params)
        if config.body:
            config.body = self._resolver.resolve(config.body)

        async def do_request():
            try:
                response = await self._executor.execute(config)
                self._on_response_received(response, config)
            except asyncio.CancelledError:
                self._on_request_cancelled()
            except Exception as e:
                self._on_request_error(str(e))

        asyncio.ensure_future(do_request())

    def _cancel_request(self):
        """요청 취소"""
        self._executor.cancel()

    def _on_response_received(self, response: ResponseData, config: RequestConfig):
        """응답 수신"""
        self._is_sending = False
        self.request_panel.url_bar.set_sending(False)
        self.response_viewer.set_response(response)
        self.status_bar.showMessage(
            f"Done - {response.status_code} ({response.elapsed_ms:.0f}ms)"
        )

        # 히스토리 저장
        self._save_history(config, response)

    def _on_request_error(self, error: str):
        """요청 에러"""
        self._is_sending = False
        self.request_panel.url_bar.set_sending(False)
        self.response_viewer.set_error(error)
        self.status_bar.showMessage(f"Error: {error}")

    def _on_request_cancelled(self):
        """요청 취소됨"""
        self._is_sending = False
        self.request_panel.url_bar.set_sending(False)
        self.response_viewer.clear()
        self.status_bar.showMessage("Request cancelled")

    def _save_history(self, config: RequestConfig, response: ResponseData):
        """히스토리 저장"""
        db = DatabaseManager.get_instance()
        
        with db.session() as session:
            history = History(
                method=config.method.value,
                url=config.url,
                status_code=response.status_code,
                response_time_ms=response.elapsed_ms,
                response_size=response.size_bytes,
                request_data={
                    "headers": config.headers,
                    "params": config.params,
                    "body": config.body,
                    "body_type": config.body_type
                },
                response_data=response.to_dict()
            )
            session.add(history)
            session.commit()
            
            # UI 업데이트
            self.history_panel.add_history(history)

    # === Menu Actions ===

    def _new_request(self):
        """새 요청"""
        self._current_request_id = None
        self.request_panel.clear()
        self.response_viewer.clear()
        self.status_bar.showMessage("New request")

    def _save_request(self):
        """요청 저장"""
        name, ok = QInputDialog.getText(
            self, "Save Request", "Request name:",
            text=self.request_panel.url_bar.url[:50] or "New Request"
        )
        if not ok or not name:
            return

        db = DatabaseManager.get_instance()
        
        with db.session() as session:
            # 기본 컬렉션 확인/생성
            default_collection = session.query(Collection).filter(
                Collection.name == "My Collection"
            ).first()
            
            if not default_collection:
                default_collection = Collection(name="My Collection")
                session.add(default_collection)
                session.flush()

            # 요청 저장
            request = Request(
                collection_id=default_collection.id,
                name=name,
                method=self.request_panel.url_bar.method,
                url=self.request_panel.url_bar.url,
                body=self.request_panel.body_editor.text,
                body_type="json" if self.request_panel.body_editor.text.strip() else "none"
            )
            session.add(request)
            session.flush()

            # Headers
            for item in self.request_panel.headers_table.get_data():
                if item.key:
                    header = Header(
                        request_id=request.id,
                        key=item.key,
                        value=item.value,
                        enabled=item.enabled
                    )
                    session.add(header)

            # Parameters
            for item in self.request_panel.params_table.get_data():
                if item.key:
                    param = Parameter(
                        request_id=request.id,
                        key=item.key,
                        value=item.value,
                        enabled=item.enabled
                    )
                    session.add(param)

            session.commit()
            
            # UI 업데이트
            self._load_data()
            self.status_bar.showMessage(f"Request saved: {name}")

    def _clear_request(self):
        """요청 초기화"""
        self.request_panel.clear()
        self.response_viewer.clear()

    def _toggle_sidebar(self):
        """사이드바 토글"""
        sizes = self.main_splitter.sizes()
        if sizes[0] > 0:
            self._sidebar_size = sizes[0]
            self.main_splitter.setSizes([0, sum(sizes)])
        else:
            self.main_splitter.setSizes([
                getattr(self, '_sidebar_size', 280),
                sum(sizes) - getattr(self, '_sidebar_size', 280)
            ])

    def _show_about(self):
        """About 다이얼로그"""
        QMessageBox.about(
            self, "About PyAPI Studio",
            "<h2>PyAPI Studio</h2>"
            "<p>Version 1.0.0</p>"
            "<p>A lightweight desktop API testing tool built with Python and PyQt6.</p>"
            "<p>Developed with ❤️</p>"
        )

    # === Event Handlers ===

    def _on_request_selected(self, request: Request):
        """요청 선택됨"""
        self._current_request_id = request.id
        self.request_panel.load_request(request)
        self.response_viewer.clear()
        self.status_bar.showMessage(f"Loaded: {request.name}")

    def _on_request_created(self, collection_id: Optional[int]):
        """새 요청 생성"""
        self._new_request()

    def _on_request_deleted(self, request_id: int):
        """요청 삭제됨"""
        db = DatabaseManager.get_instance()
        with db.session() as session:
            request = session.query(Request).filter(Request.id == request_id).first()
            if request:
                session.delete(request)
                session.commit()
        
        if self._current_request_id == request_id:
            self._new_request()

    def _on_collection_created(self, data: dict):
        """컬렉션 생성"""
        db = DatabaseManager.get_instance()
        with db.session() as session:
            collection = Collection(
                name=data["name"],
                parent_id=data.get("parent_id")
            )
            session.add(collection)
            session.commit()
        
        self._load_data()

    def _on_collection_deleted(self, collection_id: int):
        """컬렉션 삭제됨"""
        db = DatabaseManager.get_instance()
        with db.session() as session:
            collection = session.query(Collection).filter(
                Collection.id == collection_id
            ).first()
            if collection:
                session.delete(collection)
                session.commit()

    def _on_history_selected(self, history: History):
        """히스토리에서 요청 로드"""
        self._current_request_id = None
        
        self.request_panel.url_bar.method = history.method
        self.request_panel.url_bar.url = history.url
        
        # 요청 데이터 복원
        req_data = history.request_data or {}
        
        self.request_panel.headers_table.clear()
        for key, value in req_data.get("headers", {}).items():
            self.request_panel.headers_table.add_row(KeyValueItem(key, value, True))
        
        self.request_panel.params_table.clear()
        for key, value in req_data.get("params", {}).items():
            self.request_panel.params_table.add_row(KeyValueItem(key, value, True))
        
        self.request_panel.body_editor.text = req_data.get("body", "") or ""
        
        self.response_viewer.clear()
        self.status_bar.showMessage("Loaded from history")

    def closeEvent(self, event):
        """창 닫기 이벤트"""
        event.accept()
