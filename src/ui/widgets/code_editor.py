"""Code Editor Widget for PyAPI Studio"""

from PyQt6.QtWidgets import (
    QPlainTextEdit, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTextEdit
)
from PyQt6.QtCore import pyqtSignal, Qt, QRect, QSize
from PyQt6.QtGui import (
    QColor, QPainter, QTextFormat, QFont,
    QSyntaxHighlighter, QTextCharFormat
)
import re


class JsonHighlighter(QSyntaxHighlighter):
    """JSON 구문 강조"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rules = []

        # 키 (문자열 키)
        key_format = QTextCharFormat()
        key_format.setForeground(QColor("#9cdcfe"))
        self._rules.append((r'"[^"]*"\s*:', key_format))

        # 문자열 값
        string_format = QTextCharFormat()
        string_format.setForeground(QColor("#ce9178"))
        self._rules.append((r'"[^"]*"', string_format))

        # 숫자
        number_format = QTextCharFormat()
        number_format.setForeground(QColor("#b5cea8"))
        self._rules.append((r'\b-?\d+\.?\d*\b', number_format))

        # 불리언 & null
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#569cd6"))
        self._rules.append((r'\b(true|false|null)\b', keyword_format))

    def highlightBlock(self, text):
        for pattern, fmt in self._rules:
            for match in re.finditer(pattern, text):
                self.setFormat(match.start(), match.end() - match.start(), fmt)


class LineNumberArea(QWidget):
    """라인 번호 영역"""

    def __init__(self, editor):
        super().__init__(editor)
        self._editor = editor

    def sizeHint(self):
        return QSize(self._editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self._editor.line_number_area_paint_event(event)


class CodeEditor(QPlainTextEdit):
    """코드 에디터"""

    def __init__(self, language: str = "json", parent=None):
        super().__init__(parent)
        self._language = language
        self._setup_ui()
        self._setup_highlighter()

    def _setup_ui(self):
        # 폰트 설정
        font = QFont("Consolas", 11)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(font)

        # 탭 크기
        self.setTabStopDistance(
            self.fontMetrics().horizontalAdvance(' ') * 2
        )

        # 라인 번호 영역
        self._line_number_area = LineNumberArea(self)
        
        self.blockCountChanged.connect(self._update_line_number_area_width)
        self.updateRequest.connect(self._update_line_number_area)
        self.cursorPositionChanged.connect(self._highlight_current_line)

        self._update_line_number_area_width(0)
        self._highlight_current_line()

        # 스타일
        self.setStyleSheet("""
            QPlainTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
                border-radius: 4px;
            }
        """)

    def _setup_highlighter(self):
        if self._language == "json":
            self._highlighter = JsonHighlighter(self.document())
        else:
            self._highlighter = None

    def line_number_area_width(self):
        digits = 1
        max_num = max(1, self.blockCount())
        while max_num >= 10:
            max_num //= 10
            digits += 1
        space = 3 + self.fontMetrics().horizontalAdvance('9') * digits + 10
        return space

    def _update_line_number_area_width(self, _):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def _update_line_number_area(self, rect, dy):
        if dy:
            self._line_number_area.scroll(0, dy)
        else:
            self._line_number_area.update(
                0, rect.y(),
                self._line_number_area.width(), rect.height()
            )
        if rect.contains(self.viewport().rect()):
            self._update_line_number_area_width(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self._line_number_area.setGeometry(
            QRect(cr.left(), cr.top(),
                  self.line_number_area_width(), cr.height())
        )

    def _highlight_current_line(self):
        extra_selections = []
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            line_color = QColor("#2d2d30")
            selection.format.setBackground(line_color)
            selection.format.setProperty(
                QTextFormat.Property.FullWidthSelection, True
            )
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extra_selections.append(selection)
        self.setExtraSelections(extra_selections)

    def line_number_area_paint_event(self, event):
        painter = QPainter(self._line_number_area)
        painter.fillRect(event.rect(), QColor("#1e1e1e"))

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(
            self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(QColor("#858585"))
                painter.drawText(
                    0, top,
                    self._line_number_area.width() - 5,
                    self.fontMetrics().height(),
                    Qt.AlignmentFlag.AlignRight, number
                )

            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            block_number += 1

    @property
    def text(self) -> str:
        return self.toPlainText()

    @text.setter
    def text(self, value: str):
        self.setPlainText(value)

    def format_json(self):
        """JSON 포맷팅"""
        if self._language == "json":
            try:
                import json
                parsed = json.loads(self.text)
                formatted = json.dumps(parsed, indent=2, ensure_ascii=False)
                self.text = formatted
            except:
                pass


class CodeEditorWidget(QWidget):
    """코드 에디터 + 도구 버튼"""

    text_changed = pyqtSignal()

    def __init__(self, language: str = "json", show_format_btn: bool = True, parent=None):
        super().__init__(parent)
        self._language = language
        self._show_format_btn = show_format_btn
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # 도구 버튼
        if self._show_format_btn and self._language == "json":
            btn_layout = QHBoxLayout()
            btn_layout.addStretch()
            
            self.format_btn = QPushButton("Format JSON")
            self.format_btn.setFixedWidth(100)
            self.format_btn.clicked.connect(self._format_json)
            btn_layout.addWidget(self.format_btn)
            
            layout.addLayout(btn_layout)

        # 에디터
        self.editor = CodeEditor(self._language)
        self.editor.textChanged.connect(self.text_changed.emit)
        layout.addWidget(self.editor)

    def _format_json(self):
        self.editor.format_json()

    @property
    def text(self) -> str:
        return self.editor.text

    @text.setter
    def text(self, value: str):
        self.editor.text = value

    def set_read_only(self, readonly: bool):
        self.editor.setReadOnly(readonly)

    def clear(self):
        self.editor.clear()
