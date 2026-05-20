"""
=================================================================================
ASCET Code Chat Panel
=================================================================================

Use-case: Generate / modify ASCET ESDL code via conversational AI.

Workflow:
    1. User selects an ASCET class in the tree.
    2. The class path is pushed into CodeChatPanel via set_class().
    3. User clicks "Load ESDL Code" → EsdlLoaderWorker reads the calc method
       code from the live ASCET OM interface (same as the existing extractor).
    4. The loaded code is shown as context inside the chat panel.
    5. User types a requirement (e.g. "Add a switch-case for gear selection")
       and hits Send.
    6. ChatWorker calls the configured LLM (streaming), passing:
         - System prompt describing ASCET ESDL syntax rules
         - The current ESDL source as context
         - The full conversation history
    7. The streaming reply is rendered in the chat history area.
    8. Code blocks inside the reply are shown with a "Copy" button so the
       user can paste them directly into ASCET.
=================================================================================
"""

from __future__ import annotations

import json
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple

from PySide6.QtGui import (
    QFont, QKeySequence, QShortcut,
    QSyntaxHighlighter, QTextCharFormat, QColor # Thêm 3 class này
)
from PySide6.QtCore import (
    Qt, QThread, Signal, QTimer, QSettings,
    QRegularExpression # Thêm class này
)

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QLineEdit, QGroupBox, QSplitter, QScrollArea,
    QFrame, QSizePolicy, QApplication, QToolButton, QComboBox,
    QMessageBox, QDialog, QTreeWidget, QTreeWidgetItem, QFormLayout
)

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

try:
    import win32com.client
    import pythoncom
    WIN32COM_AVAILABLE = True
except ImportError:
    WIN32COM_AVAILABLE = False

try:
    from src.ai_core.model_config import ModelConfig
    MODEL_CONFIG_AVAILABLE = True
except ImportError:
    MODEL_CONFIG_AVAILABLE = False

# ---------------------------------------------------------------------------
# ESDL system prompt used for all code-generation requests
# ---------------------------------------------------------------------------
_ESDL_SYSTEM_PROMPT = """You are an expert ASCET ESDL (Embedded Software Description Language) code assistant.
You help developers write, modify, and extend ASCET calc methods (C-like procedural language used inside ASCET diagrams).

Rules for ASCET ESDL code:
- Variables are declared at the top of the method body (ASCET uses implicit declaration via assignment).
- Use standard C operators (+, -, *, /, %, ==, !=, <, >, <=, >=, &&, ||, !).
- If/else blocks use the keywords: if (...) { ... } else if (...) { ... } else { ... }
- Switch/case uses: switch (expr) { case VALUE: ...; break; default: ...; }
- Loop keywords: while (...) { ... } and for (init; cond; incr) { ... }
- Output variables are assigned by value: outVar = expression;
- Do NOT add includes, headers, or extern declarations – only the method body.
- When the user asks for modifications, show the COMPLETE updated method body.
- Wrap all generated code in a fenced code block: ```esdl ... ```

When the user sends a requirement, analyse the existing calc method code, then produce
the updated (or new) code that satisfies the requirement.
"""

# ---------------------------------------------------------------------------
# Worker: Load ESDL code from live ASCET via COM
# ---------------------------------------------------------------------------

class EsdlLoaderWorker(QThread):
    """Reads the Main.calc source from ASCET COM in a background thread."""

    code_loaded = Signal(str)          # emits cleaned code string on success
    error_occurred = Signal(str)       # emits error message on failure

    def __init__(self, class_path: str, ascet_version: str = "6.1.4"):
        super().__init__()
        self.class_path = class_path
        self.ascet_version = ascet_version

    def run(self):
        if not WIN32COM_AVAILABLE:
            self.error_occurred.emit(
                "win32com is not available – cannot connect to ASCET.\n"
                "Please install pywin32 and make sure ASCET is running."
            )
            return

        try:
            pythoncom.CoInitialize()
            code = self._extract_code()
            if code:
                self.code_loaded.emit(code)
            else:
                self.error_occurred.emit(
                    f"Could not read Main.calc from '{self.class_path}'.\n"
                    "Make sure ASCET is running and the class has a Main diagram with a calc method."
                )
        except Exception as exc:
            self.error_occurred.emit(f"ASCET COM error: {exc}")
        finally:
            try:
                pythoncom.CoUninitialize()
            except Exception:
                pass

    def _extract_code(self) -> Optional[str]:
        """Core extraction via ASCET COM interface.

        Uses Dispatch() (same as ASCETStructureScannerAPI) instead of
        GetActiveObject() – ASCET does not register itself in the Windows
        Running Object Table, so GetActiveObject always fails.
        """
        from win32com.client import Dispatch as ComDispatch

        ascet_obj = None
        last_err = ""
        for ver in [self.ascet_version, "6.1.5", "6.1.4", "6.1.3", "6.2.0", "6.0.0"]:
            try:
                obj = ComDispatch(f"Ascet.Ascet.{ver}")
                # Verify we actually got a working DB connection
                if obj is not None and obj.GetCurrentDataBase() is not None:
                    ascet_obj = obj
                    break
            except Exception as exc:
                last_err = str(exc)

        if ascet_obj is None:
            raise RuntimeError(
                f"Could not connect to ASCET (tried versions: {self.ascet_version}, "
                f"6.1.5, 6.1.4, 6.1.3, 6.2.0).\n"
                f"Last error: {last_err}\n"
                "Make sure ASCET is open and its COM server is registered."
            )

        db = ascet_obj.GetCurrentDataBase()
        if db is None:
            raise RuntimeError("Cannot access ASCET database.")

        # Normalise path
        class_path = self.class_path.lstrip("\\")
        parts = class_path.split("\\")
        class_name = parts[-1]
        folder_path = "\\".join(parts[:-1])

        class_item = db.GetItemInFolder(class_name, folder_path)
        if class_item is None:
            raise RuntimeError(f"Class '{class_path}' not found in ASCET database.")

        diagram = class_item.GetDiagramWithName("Main")
        if diagram is None:
            raise RuntimeError(f"No 'Main' diagram found in class '{class_name}'.")

        method = diagram.GetMethod("calc")
        if method is None:
            raise RuntimeError(f"No 'calc' method found in diagram 'Main' of '{class_name}'.")

        code = method.GetCode()
        return code.strip() if code and code.strip() else None


# ---------------------------------------------------------------------------
# Worker: Stream AI chat completions
# ---------------------------------------------------------------------------

class ChatWorker(QThread):
    """Calls the LLM API (streaming) and emits each chunk as it arrives."""

    chunk_received = Signal(str)    # partial text chunk
    finished = Signal()             # stream complete
    error_occurred = Signal(str)    # error message

    def __init__(
        self,
        api_url: str,
        api_key: str,
        model: str,
        messages: List[Dict],
        proxies: Optional[Dict] = None,
    ):
        super().__init__()
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.messages = messages
        self.proxies = proxies or {"http": None, "https": None}
        self._stop_flag = False

    def stop(self):
        self._stop_flag = True

    def run(self):
        if not REQUESTS_AVAILABLE:
            self.error_occurred.emit(
                "'requests' library is not installed. Run: pip install requests"
            )
            return

        # Resolve the real API model name via ModelConfig (e.g. "gpt5-mini" → "gpt-5-mini")
        # This mirrors how diagram_ai_review.py uses model_config.get_request_params().
        actual_model = self.model
        if MODEL_CONFIG_AVAILABLE:
            try:
                actual_model = ModelConfig(self.model).get_model_name()
            except Exception:
                pass  # Unknown key – send as-is and let the API return the error

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        payload = {
            "model": actual_model,
            "messages": self.messages,
            "stream": True,
            "max_completion_tokens": 4096,
        }

        try:
            with requests.post(
                url=f"{self.api_url}/chat/completions",
                json=payload,
                headers=headers,
                proxies=self.proxies,
                timeout=120,
                stream=True,
            ) as resp:
                if resp.status_code != 200:
                    body = resp.text[:500]
                    self.error_occurred.emit(
                        f"API error {resp.status_code}: {body}"
                    )
                    return

                for line in resp.iter_lines():
                    if self._stop_flag:
                        break
                    if not line:
                        continue
                    line_str = line.decode("utf-8") if isinstance(line, bytes) else line
                    if line_str.startswith("data: "):
                        data_str = line_str[6:]
                        if data_str.strip() == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            delta = (
                                data.get("choices", [{}])[0]
                                .get("delta", {})
                                .get("content", "")
                            )
                            if delta:
                                self.chunk_received.emit(delta)
                        except json.JSONDecodeError:
                            pass
        except requests.exceptions.ConnectionError as exc:
            self.error_occurred.emit(f"Connection failed: {exc}")
        except requests.exceptions.Timeout:
            self.error_occurred.emit("Request timed out (>120 s).")
        except Exception as exc:
            self.error_occurred.emit(f"Unexpected error: {exc}")
        finally:
            self.finished.emit()


# ---------------------------------------------------------------------------
# Chat bubble widget
# ---------------------------------------------------------------------------

class ChatBubble(QFrame):
    """Single message bubble (user or assistant)."""

    def __init__(self, text: str, role: str, parent=None):
        super().__init__(parent)
        self.role = role
        self._full_text = text

        self.setFrameShape(QFrame.NoFrame)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(4, 2, 4, 2)
        outer.setSpacing(2)

        # Role header
        role_label = QLabel("You" if role == "user" else "AI Assistant")
        role_label.setStyleSheet(
            "font-weight: 700; font-size: 8pt; color: #495057;"
        )
        outer.addWidget(role_label)

        # Message content (read-only text edit for easy copy)
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setFrameShape(QFrame.NoFrame)
        self.text_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.text_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        font = QFont("Segoe UI", 9)
        self.text_edit.setFont(font)

        if role == "user":
            self.text_edit.setStyleSheet(
                "background-color: #e3f2fd; border-radius: 8px; padding: 6px;"
            )
        else:
            self.text_edit.setStyleSheet(
                "background-color: #f1f8e9; border-radius: 8px; padding: 6px;"
            )

        self.set_text(text)
        outer.addWidget(self.text_edit)

        # Copy buttons below code blocks
        self._add_copy_buttons(outer, text)

    def set_text(self, text: str):
        """Update visible text (called during streaming)."""
        self._full_text = text
        self.text_edit.setPlainText(text)
        # Auto-resize height
        doc = self.text_edit.document()
        doc.setTextWidth(self.text_edit.viewport().width())
        height = int(doc.size().height()) + 16
        self.text_edit.setFixedHeight(max(height, 40))

    def append_text(self, chunk: str):
        """Append chunk during streaming."""
        self._full_text += chunk
        self.text_edit.setPlainText(self._full_text)
        doc = self.text_edit.document()
        doc.setTextWidth(self.text_edit.viewport().width())
        height = int(doc.size().height()) + 16
        self.text_edit.setFixedHeight(max(height, 40))

    def finalise(self):
        """Called after streaming ends to add copy buttons for code blocks."""
        # Remove old copy buttons if any, then rebuild
        layout = self.layout()
        # Clear widgets after the text_edit
        while layout.count() > 2:
            item = layout.takeAt(2)
            if item and item.widget():
                item.widget().deleteLater()
        self._add_copy_buttons(layout, self._full_text)

    def _add_copy_buttons(self, layout, text: str):
        """Parse text for code blocks and add individual copy buttons."""
        code_blocks = re.findall(r"```(?:\w+)?\n?(.*?)```", text, re.DOTALL)
        for i, block in enumerate(code_blocks):
            block = block.strip()
            if not block:
                continue
            btn_row = QHBoxLayout()
            lbl = QLabel(f"Code block {i + 1}:")
            lbl.setStyleSheet("font-size: 8pt; color: #6c757d;")
            btn_row.addWidget(lbl)

            copy_btn = QPushButton("📋 Copy Code")
            copy_btn.setMaximumWidth(110)
            copy_btn.setMaximumHeight(24)
            copy_btn.setStyleSheet(
                "QPushButton { background:#4dabf7; color:white; border:none;"
                " border-radius:4px; padding:3px 8px; font-size:8pt; font-weight:600; }"
                "QPushButton:hover { background:#339af0; }"
            )
            captured_block = block
            copy_btn.clicked.connect(
                lambda checked=False, b=captured_block: QApplication.clipboard().setText(b)
            )
            btn_row.addWidget(copy_btn)
            btn_row.addStretch()
            layout.addLayout(btn_row)

class EsdlHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self.highlighting_rules = []

        # 1. Từ khóa (Keywords) - Màu xanh da trời
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#569CD6"))
        keyword_format.setFontWeight(QFont.Bold)
        keywords = [
            r"\bif\b", r"\belse\b", r"\bswitch\b", r"\bcase\b",
            r"\bdefault\b", r"\bbreak\b", r"\bwhile\b", r"\bfor\b",
            r"\breturn\b", r"\btrue\b", r"\bfalse\b"
        ]
        for word in keywords:
            pattern = QRegularExpression(word)
            self.highlighting_rules.append((pattern, keyword_format))

        # 2. Số (Numbers) - Màu xanh lá nhạt
        number_format = QTextCharFormat()
        number_format.setForeground(QColor("#B5CEA8"))
        self.highlighting_rules.append((QRegularExpression(r"\b[0-9]+(\.[0-9]+)?\b"), number_format))

        # 3. Chuỗi (Strings) - Màu cam đất
        string_format = QTextCharFormat()
        string_format.setForeground(QColor("#CE9178"))
        self.highlighting_rules.append((QRegularExpression("\".*\""), string_format))

        # 4. Single-line Comment (//) - Màu xanh lá đậm
        self.comment_format = QTextCharFormat()
        self.comment_format.setForeground(QColor("#6A9955"))
        self.highlighting_rules.append((QRegularExpression(r"//[^\n]*"), self.comment_format))

        # Khai báo regex cho Multi-line Comment (/* ... */)
        self.comment_start_expression = QRegularExpression(r"/\*")
        self.comment_end_expression = QRegularExpression(r"\*/")

    def highlightBlock(self, text):
        # Apply simple rules
        for pattern, format in self.highlighting_rules:
            iterator = pattern.globalMatch(text)
            while iterator.hasNext():
                match = iterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), format)

        # Apply multi-line comment logic
        self.setCurrentBlockState(0)
        start_index = 0
        if self.previousBlockState() != 1:
            start_index = text.find("/*")

        while start_index >= 0:
            match = self.comment_end_expression.match(text, start_index)
            end_index = match.capturedStart()
            comment_length = 0

            if end_index == -1:
                self.setCurrentBlockState(1)
                comment_length = len(text) - start_index
            else:
                comment_length = end_index - start_index + match.capturedLength()

            self.setFormat(start_index, comment_length, self.comment_format)
            start_index = text.find("/*", start_index + comment_length)


# ---------------------------------------------------------------------------
# Chat History Manager
# ---------------------------------------------------------------------------

class ChatHistoryManager:
    """Persists chat sessions as JSON files under a configurable directory."""

    def __init__(self, history_dir: str = "chat_history"):
        self.history_dir = Path(history_dir)
        self.history_dir.mkdir(parents=True, exist_ok=True)

    def save_session(self, session_data: dict) -> str:
        """Write a new session file and return its absolute path."""
        class_name = session_data.get("class_name", "unknown")
        safe_name  = re.sub(r"[^\w\-_.]", "_", class_name)[:40]
        created    = session_data.get("created_at", datetime.now().isoformat())
        try:
            prefix = datetime.fromisoformat(created).strftime("%Y-%m-%d_%H-%M-%S")
        except Exception:
            prefix = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        filepath = self.history_dir / f"{prefix}_{safe_name}.json"
        counter  = 1
        while filepath.exists():
            filepath = self.history_dir / f"{prefix}_{safe_name}_{counter}.json"
            counter += 1

        with open(filepath, "w", encoding="utf-8") as fh:
            json.dump(session_data, fh, ensure_ascii=False, indent=2)
        return str(filepath)

    def update_session(self, filepath: str, session_data: dict) -> bool:
        """Overwrite an existing session file in-place."""
        try:
            with open(filepath, "w", encoding="utf-8") as fh:
                json.dump(session_data, fh, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False

    def load_all_sessions(self) -> List[Tuple[str, dict]]:
        """Return list of (filepath, data) sorted newest-first."""
        result: List[Tuple[str, dict]] = []
        for jf in sorted(self.history_dir.glob("*.json"), reverse=True):
            try:
                with open(jf, "r", encoding="utf-8") as fh:
                    result.append((str(jf), json.load(fh)))
            except Exception:
                pass
        return result

    def delete_session(self, filepath: str) -> bool:
        try:
            Path(filepath).unlink()
            return True
        except Exception:
            return False


# ---------------------------------------------------------------------------
# Chat History Dialog
# ---------------------------------------------------------------------------

class ChatHistoryDialog(QDialog):
    """Browse, preview, load and delete saved chat sessions."""

    session_load_requested = Signal(dict)

    _S_GREEN = (
        "QPushButton { background:#27ae60; color:white; border:none; border-radius:5px;"
        " padding:6px 16px; font-weight:700; font-size:9pt; }"
        "QPushButton:hover { background:#229954; }"
        "QPushButton:disabled { background:#ced4da; color:#6c757d; }"
    )
    _S_RED = (
        "QPushButton { background:#e74c3c; color:white; border:none; border-radius:5px;"
        " padding:6px 14px; font-weight:700; font-size:9pt; }"
        "QPushButton:hover { background:#c0392b; }"
        "QPushButton:disabled { background:#ced4da; color:#6c757d; }"
    )
    _S_GRAY = (
        "QPushButton { background:#6c757d; color:white; border:none; border-radius:5px;"
        " padding:6px 14px; font-size:9pt; }"
        "QPushButton:hover { background:#495057; }"
    )
    _S_GROUP = (
        "QGroupBox { font-weight:600; font-size:9pt; color:#495057;"
        " border:1px solid #dee2e6; border-radius:6px; margin-top:6px; padding-top:10px; }"
        "QGroupBox::title { subcontrol-origin:margin; left:10px; padding:0 4px; }"
    )

    def __init__(self, history_manager: ChatHistoryManager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Chat History")
        self.setMinimumSize(940, 640)
        self._hm            = history_manager
        self._sessions: List[Tuple[str, dict]] = []
        self._selected_fp: Optional[str]       = None
        self._setup_ui()
        self._load_all()

    # ── UI construction ────────────────────────────────────────────────

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 10)
        root.setSpacing(10)

        title = QLabel("📚  Chat History")
        title.setStyleSheet(
            "font-size: 13pt; font-weight: 700; color: #2c3e50; padding: 2px 0;"
        )
        root.addWidget(title)

        splitter = QSplitter(Qt.Horizontal)

        # ── Left: session tree ─────────────────────────────────────────
        left = QWidget()
        ll   = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 6, 0)
        ll.setSpacing(6)

        self._search = QLineEdit()
        self._search.setPlaceholderText("🔍  Filter by class or content…")
        self._search.setMinimumHeight(28)
        self._search.textChanged.connect(self._filter_sessions)
        ll.addWidget(self._search)

        self._tree = QTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.itemClicked.connect(self._on_item_clicked)
        self._tree.itemDoubleClicked.connect(lambda *_: self._on_load())
        self._tree.setStyleSheet("""
            QTreeWidget {
                border: 1px solid #dee2e6; border-radius: 6px;
                background: #ffffff; font-size: 9pt;
            }
            QTreeWidget::item { padding: 5px 4px; }
            QTreeWidget::item:selected  { background: #e3f2fd; color: #1565c0; }
            QTreeWidget::item:hover:!selected { background: #f5f5f5; }
        """)
        ll.addWidget(self._tree, stretch=1)
        left.setMinimumWidth(240)
        left.setMaximumWidth(340)
        splitter.addWidget(left)

        # ── Right: details + preview ───────────────────────────────────
        right = QWidget()
        rl    = QVBoxLayout(right)
        rl.setContentsMargins(6, 0, 0, 0)
        rl.setSpacing(8)

        info_grp = QGroupBox("Session Details")
        info_grp.setStyleSheet(self._S_GROUP)
        info_form = QFormLayout(info_grp)
        info_form.setContentsMargins(10, 14, 10, 10)
        info_form.setSpacing(6)

        lbl_st = "font-size: 9pt; color: #2c3e50;"
        self._lbl_class   = QLabel("-"); self._lbl_class.setStyleSheet(lbl_st)
        self._lbl_created = QLabel("-"); self._lbl_created.setStyleSheet(lbl_st)
        self._lbl_model   = QLabel("-"); self._lbl_model.setStyleSheet(lbl_st)
        self._lbl_turns   = QLabel("-"); self._lbl_turns.setStyleSheet(lbl_st)
        self._lbl_esdl    = QLabel("-"); self._lbl_esdl.setStyleSheet(lbl_st)
        self._lbl_api     = QLabel("-"); self._lbl_api.setStyleSheet(lbl_st)
        info_form.addRow("Class:",      self._lbl_class)
        info_form.addRow("Created:",    self._lbl_created)
        info_form.addRow("Model:",      self._lbl_model)
        info_form.addRow("Turns:",      self._lbl_turns)
        info_form.addRow("ESDL lines:", self._lbl_esdl)
        info_form.addRow("API:",        self._lbl_api)
        rl.addWidget(info_grp)

        prev_grp = QGroupBox("Message Preview  (double-click a session to load it)")
        prev_grp.setStyleSheet(self._S_GROUP)
        prev_lay = QVBoxLayout(prev_grp)
        prev_lay.setContentsMargins(6, 14, 6, 6)
        self._preview = QTextEdit()
        self._preview.setReadOnly(True)
        self._preview.setFont(QFont("Segoe UI", 9))
        self._preview.setStyleSheet(
            "QTextEdit { border:none; background:#fafafa; font-size:9pt; }"
        )
        prev_lay.addWidget(self._preview)
        rl.addWidget(prev_grp, stretch=1)

        splitter.addWidget(right)
        splitter.setSizes([280, 620])
        root.addWidget(splitter, stretch=1)

        # ── Bottom buttons ─────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self._load_btn = QPushButton("🔄  Load Session")
        self._load_btn.setEnabled(False)
        self._load_btn.setMinimumHeight(32)
        self._load_btn.setStyleSheet(self._S_GREEN)
        self._load_btn.clicked.connect(self._on_load)

        self._del_btn = QPushButton("🗑  Delete")
        self._del_btn.setEnabled(False)
        self._del_btn.setMinimumHeight(32)
        self._del_btn.setStyleSheet(self._S_RED)
        self._del_btn.clicked.connect(self._on_delete)

        close_btn = QPushButton("Close")
        close_btn.setMinimumHeight(32)
        close_btn.setStyleSheet(self._S_GRAY)
        close_btn.clicked.connect(self.accept)

        self._count_lbl = QLabel("")
        self._count_lbl.setStyleSheet("color:#6c757d; font-size:8pt;")

        btn_row.addWidget(self._load_btn)
        btn_row.addWidget(self._del_btn)
        btn_row.addStretch()
        btn_row.addWidget(self._count_lbl)
        btn_row.addWidget(close_btn)
        root.addLayout(btn_row)

    # ── Data loading ───────────────────────────────────────────────────

    def _load_all(self):
        self._sessions = self._hm.load_all_sessions()
        self._populate_tree(self._sessions)
        n = len(self._sessions)
        self._count_lbl.setText(f"{n} session{'s' if n != 1 else ''}")

    def _populate_tree(self, sessions: List[Tuple[str, dict]]):
        self._tree.clear()
        if not sessions:
            placeholder = QTreeWidgetItem(["  No saved sessions"])
            placeholder.setDisabled(True)
            self._tree.addTopLevelItem(placeholder)
            return

        today     = datetime.now().date()
        yesterday = today - timedelta(days=1)
        week_ago  = today - timedelta(days=7)

        groups: dict = {}
        for fp, data in sessions:
            try:
                d = datetime.fromisoformat(data.get("created_at", "")).date()
            except Exception:
                d = today
            if d == today:
                key = "📅  Today"
            elif d == yesterday:
                key = "📅  Yesterday"
            elif d >= week_ago:
                key = "📅  This Week"
            else:
                key = f"📅  {d.strftime('%B %Y')}"
            groups.setdefault(key, []).append((fp, data))

        for group_label, items in groups.items():
            grp_item = QTreeWidgetItem([group_label])
            grp_font = QFont("Segoe UI", 9)
            grp_font.setBold(True)
            grp_item.setFont(0, grp_font)
            grp_item.setForeground(0, QColor("#495057"))

            for fp, data in items:
                cls   = data.get("class_name", "Unknown")
                turns = data.get("stats", {}).get("total_turns", 0)
                try:
                    ts = datetime.fromisoformat(data.get("created_at", "")).strftime("%H:%M")
                except Exception:
                    ts = ""

                label = f"  💬  {cls}  —  {ts}  ({turns} turn{'s' if turns != 1 else ''})"
                child = QTreeWidgetItem([label])
                child.setData(0, Qt.UserRole, fp)
                child.setToolTip(0, fp)
                if turns == 0:
                    child.setForeground(0, QColor("#adb5bd"))
                grp_item.addChild(child)

            self._tree.addTopLevelItem(grp_item)
            grp_item.setExpanded(True)

    def _filter_sessions(self, text: str):
        if not text.strip():
            self._populate_tree(self._sessions)
            return
        lo = text.lower()
        filtered = [
            (fp, d) for fp, d in self._sessions
            if (
                lo in d.get("class_name", "").lower()
                or lo in d.get("class_path", "").lower()
                or any(lo in m.get("content", "").lower() for m in d.get("messages", []))
            )
        ]
        self._populate_tree(filtered)

    # ── Event handlers ─────────────────────────────────────────────────

    def _on_item_clicked(self, item: QTreeWidgetItem, _col: int):
        fp = item.data(0, Qt.UserRole)
        if not fp:
            self._selected_fp = None
            self._load_btn.setEnabled(False)
            self._del_btn.setEnabled(False)
            return
        self._selected_fp = fp
        self._load_btn.setEnabled(True)
        self._del_btn.setEnabled(True)
        data = next((d for f, d in self._sessions if f == fp), None)
        if data:
            self._show_details(data)

    def _show_details(self, data: dict):
        self._lbl_class.setText(data.get("class_name", "-"))
        try:
            dt = datetime.fromisoformat(data.get("created_at", ""))
            self._lbl_created.setText(dt.strftime("%Y-%m-%d  %H:%M:%S"))
        except Exception:
            self._lbl_created.setText(data.get("created_at", "-"))

        cfg = data.get("config", {})
        mk  = cfg.get("model_key", "-")
        mn  = cfg.get("model_name", "")
        self._lbl_model.setText(f"{mk}  →  {mn}" if mn and mn != mk else mk)

        stats = data.get("stats", {})
        turns = stats.get("total_turns", 0)
        self._lbl_turns.setText(
            f"{turns} turn{'s' if turns != 1 else ''}  "
            f"({stats.get('user_messages', 0)} user / {stats.get('assistant_messages', 0)} AI)"
        )

        esdl = data.get("esdl_snapshot", "")
        self._lbl_esdl.setText(
            f"{esdl.count(chr(10)) + 1} lines" if esdl else "—  no snapshot"
        )
        self._lbl_api.setText(cfg.get("api_url", "-"))

        # Build message preview
        parts = []
        for msg in data.get("messages", []):
            role    = msg.get("role", "")
            content = msg.get("content", "")
            try:
                ts = datetime.fromisoformat(msg.get("timestamp", "")).strftime("%H:%M")
            except Exception:
                ts = ""
            if role == "user":
                snippet = content[:400] + ("…" if len(content) > 400 else "")
                parts.append(f"{'─'*55}\n▶  You  {ts}\n{snippet}")
            elif role == "assistant":
                snippet = content[:600] + ("…" if len(content) > 600 else "")
                parts.append(f"◀  AI Assistant  {ts}\n{snippet}")
        self._preview.setPlainText("\n\n".join(parts) if parts else "No messages to preview.")

    def _on_load(self):
        if not self._selected_fp:
            return
        data = next((d for f, d in self._sessions if f == self._selected_fp), None)
        if data:
            self.session_load_requested.emit(data)
            self.accept()

    def _on_delete(self):
        if not self._selected_fp:
            return
        reply = QMessageBox.question(
            self, "Delete Session",
            "Permanently delete this chat session?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self._hm.delete_session(self._selected_fp)
            self._sessions = [(f, d) for f, d in self._sessions if f != self._selected_fp]
            self._selected_fp = None
            self._load_btn.setEnabled(False)
            self._del_btn.setEnabled(False)
            self._preview.clear()
            for lbl in (self._lbl_class, self._lbl_created, self._lbl_model,
                        self._lbl_turns, self._lbl_esdl, self._lbl_api):
                lbl.setText("-")
            self._populate_tree(self._sessions)
            n = len(self._sessions)
            self._count_lbl.setText(f"{n} session{'s' if n != 1 else ''}")


# ---------------------------------------------------------------------------
# Main Chat Panel Widget
# ---------------------------------------------------------------------------

class CodeChatPanel(QWidget):
    """
    ASCET Code Generation Chat Panel.

    Public API (called from AscetAgentMainWindow):
        set_class(class_path, available_classes=None)  – set selected class
        set_api_config(api_url, api_key, model)        – update API settings
    """

    def __init__(self, settings: QSettings, parent=None):
        super().__init__(parent)
        self.settings = settings

        self._class_path: Optional[str] = None
        self._esdl_code: Optional[str] = None
        self._chat_history: List[Dict] = []   # OpenAI message format
        self._loader_worker: Optional[EsdlLoaderWorker] = None
        self._chat_worker: Optional[ChatWorker] = None
        self._current_assistant_bubble: Optional[ChatBubble] = None
        self._bubble_widgets: List[ChatBubble] = []
        self._manual_load: bool = False

        # History persistence
        history_dir = settings.value("paths/chat_history_dir", "chat_history")
        self._history_manager  = ChatHistoryManager(history_dir)
        self._active_session_path: Optional[str] = None
        self._session_start_time: Optional[str]  = None
        self._session_messages: List[Dict]        = []  # user + assistant only, with timestamps

        self._init_ui()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_class(self, class_path: str, available_classes: Optional[dict] = None):
        """Called when user selects a class in the database tree.

        Auto-triggers an ESDL load so the user does not need to press
        the button manually after every class selection.
        """
        if class_path == self._class_path:
            return
        # Auto-save any ongoing session before switching to a new class
        if self._session_messages:
            self._save_session()
        self._session_messages        = []
        self._active_session_path     = None
        self._session_start_time      = None
        self._class_path = class_path
        self._esdl_code  = None

        class_name = class_path.split("\\")[-1] if class_path else "None"
        self._selected_class_label.setText(f"Selected: {class_name}")
        self._selected_class_label.setToolTip(class_path)
        self._load_btn.setEnabled(bool(class_path))

        # Reset ESDL display
        self._esdl_display.setPlainText("")
        self._esdl_status_lbl.setText("Reading ESDL code…")
        self._esdl_status_lbl.setStyleSheet("color: #f39c12; font-size: 8pt;")

        # Auto-load after a short delay so the UI can render first
        QTimer.singleShot(150, self._on_load_esdl)

    def set_api_config(self, api_url: str, api_key: str, model: str):
        """Update the API endpoint used for chat completions."""
        self._api_url = api_url
        self._api_key = api_key
        self._model_combo.setCurrentText(model)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(6)

        # ── Class selector bar ─────────────────────────────────────────
        class_bar = QHBoxLayout()
        self._selected_class_label = QLabel("No class selected")
        self._selected_class_label.setStyleSheet(
            "font-weight: 600; font-size: 9pt; color: #2c3e50;"
        )
        self._selected_class_label.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed
        )

        self._load_btn = QPushButton("Load ESDL Code")
        self._load_btn.setEnabled(False)
        self._load_btn.setMaximumWidth(140)
        self._load_btn.setMinimumHeight(28)
        self._load_btn.setStyleSheet(
            "QPushButton { background:#4dabf7; color:white; border:none;"
            " border-radius:5px; padding:4px 10px; font-weight:600; font-size:9pt; }"
            "QPushButton:hover { background:#339af0; }"
            "QPushButton:disabled { background:#ced4da; color:#6c757d; }"
        )
        self._load_btn.clicked.connect(lambda: self._on_load_esdl(manual=True))

        class_bar.addWidget(QLabel("Class:"))
        class_bar.addWidget(self._selected_class_label)
        class_bar.addWidget(self._load_btn)
        root.addLayout(class_bar)

        # ── Main splitter: ESDL preview (top) + Chat (bottom) ──────────
        splitter = QSplitter(Qt.Vertical)
        splitter.setChildrenCollapsible(True)

        # ── ESDL code panel ────────────────────────────────────────────
        esdl_group = QGroupBox("Current ESDL Code (Main.calc)")
        esdl_layout = QVBoxLayout(esdl_group)
        esdl_layout.setContentsMargins(6, 10, 6, 6)
        esdl_layout.setSpacing(4)

        self._esdl_status_lbl = QLabel("ESDL code not loaded")
        self._esdl_status_lbl.setStyleSheet("color: #6c757d; font-size: 8pt;")
        esdl_layout.addWidget(self._esdl_status_lbl)

        self._esdl_display = QTextEdit()
        self._esdl_display.setReadOnly(True)
        self._esdl_display.setPlaceholderText(
            "Load a class to see its ESDL code here…"
        )
        self._esdl_display.setFont(QFont("Consolas", 8))
        self._esdl_display.setStyleSheet(
            "background:#1e1e1e; color:#d4d4d4; border-radius:6px; padding:6px;"
        )
        self._esdl_display.setMinimumHeight(80)
        esdl_layout.addWidget(self._esdl_display)

        self._esdl_highlighter = EsdlHighlighter(self._esdl_display.document())

        esdl_copy_bar = QHBoxLayout()
        esdl_copy_btn = QPushButton("📋 Copy ESDL")
        esdl_copy_btn.setMaximumWidth(110)
        esdl_copy_btn.setMaximumHeight(24)
        esdl_copy_btn.setStyleSheet(
            "QPushButton { background:#6c757d; color:white; border:none;"
            " border-radius:4px; padding:3px 8px; font-size:8pt; }"
            "QPushButton:hover { background:#495057; }"
        )
        esdl_copy_btn.clicked.connect(
            lambda: QApplication.clipboard().setText(self._esdl_display.toPlainText())
        )
        esdl_copy_bar.addStretch()
        esdl_copy_bar.addWidget(esdl_copy_btn)
        esdl_layout.addLayout(esdl_copy_bar)

        splitter.addWidget(esdl_group)

        # ── Chat panel ─────────────────────────────────────────────────
        chat_group = QGroupBox("Chat – Code Generation / Modification")
        chat_layout = QVBoxLayout(chat_group)
        chat_layout.setContentsMargins(6, 10, 6, 6)
        chat_layout.setSpacing(4)

        # Scrollable history area
        self._history_scroll = QScrollArea()
        self._history_scroll.setWidgetResizable(True)
        self._history_scroll.setFrameShape(QFrame.NoFrame)
        self._history_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._history_scroll.setMinimumHeight(120)

        self._history_container = QWidget()
        self._history_layout = QVBoxLayout(self._history_container)
        self._history_layout.setContentsMargins(4, 4, 4, 4)
        self._history_layout.setSpacing(8)
        self._history_layout.addStretch()

        self._history_scroll.setWidget(self._history_container)
        chat_layout.addWidget(self._history_scroll, stretch=1)

        # Input area
        input_group = QGroupBox("Your Request")
        input_layout = QVBoxLayout(input_group)
        input_layout.setContentsMargins(6, 8, 6, 6)
        input_layout.setSpacing(4)

        self._input_edit = QTextEdit()
        self._input_edit.setPlaceholderText(
            "Describe what you want to add or change…\n"
            "Example: 'Add a switch-case for gear values 1-6'\n"
            "Example: 'Add an if/else to clamp output between 0 and 100'"
        )
        self._input_edit.setFont(QFont("Segoe UI", 9))
        self._input_edit.setMaximumHeight(90)
        self._input_edit.setMinimumHeight(60)
        self._input_edit.setStyleSheet(
            "border: 1px solid #ced4da; border-radius:6px; padding:6px;"
        )
        input_layout.addWidget(self._input_edit)

        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(8)

        # Model selector
        self._model_combo = QComboBox()
        self._model_combo.addItems(["gpt5-mini", "gpt-oss-120b", "DeepSeek-r1-0528-fp16-671b"])
        self._model_combo.setMaximumWidth(210)
        self._model_combo.setMaximumHeight(28)
        self._model_combo.setStyleSheet(
            "QComboBox { border:1px solid #ced4da; border-radius:4px; padding:3px 8px;"
            " font-size:8pt; background:#ffffff; }"
            "QComboBox:focus { border-color:#4dabf7; }"
        )
        # Pre-select model from settings
        saved_model = self.settings.value("api/model_type", "gpt5-mini")
        idx = self._model_combo.findText(saved_model)
        if idx >= 0:
            self._model_combo.setCurrentIndex(idx)

        self._send_btn = QPushButton("Send ➤")
        self._send_btn.setMinimumHeight(28)
        self._send_btn.setMinimumWidth(80)
        self._send_btn.setStyleSheet(
            "QPushButton { background:#27ae60; color:white; border:none;"
            " border-radius:5px; padding:4px 14px; font-weight:700; font-size:9pt; }"
            "QPushButton:hover { background:#229954; }"
            "QPushButton:disabled { background:#ced4da; color:#6c757d; }"
        )
        self._send_btn.clicked.connect(self._on_send)

        self._stop_btn = QPushButton("Stop ■")
        self._stop_btn.setMinimumHeight(28)
        self._stop_btn.setMinimumWidth(70)
        self._stop_btn.setEnabled(False)
        self._stop_btn.setStyleSheet(
            "QPushButton { background:#e74c3c; color:white; border:none;"
            " border-radius:5px; padding:4px 10px; font-weight:700; font-size:9pt; }"
            "QPushButton:hover { background:#c0392b; }"
            "QPushButton:disabled { background:#ced4da; color:#6c757d; }"
        )
        self._stop_btn.clicked.connect(self._on_stop)

        clear_btn = QPushButton("Clear Chat")
        clear_btn.setMinimumHeight(28)
        clear_btn.setStyleSheet(
            "QPushButton { background:#f8f9fa; border:1px solid #ced4da;"
            " border-radius:5px; padding:4px 10px; font-size:8pt; }"
            "QPushButton:hover { background:#e9ecef; }"
        )
        clear_btn.clicked.connect(self._on_clear_chat)

        history_btn = QPushButton("📂 History")
        history_btn.setMinimumHeight(28)
        history_btn.setStyleSheet(
            "QPushButton { background:#f8f9fa; border:1px solid #ced4da;"
            " border-radius:5px; padding:4px 10px; font-size:8pt; }"
            "QPushButton:hover { background:#e9ecef; }"
        )
        history_btn.clicked.connect(self._open_history_dialog)

        btn_bar.addWidget(QLabel("Model:"))
        btn_bar.addWidget(self._model_combo)
        btn_bar.addStretch()
        btn_bar.addWidget(history_btn)
        btn_bar.addWidget(clear_btn)
        btn_bar.addWidget(self._stop_btn)
        btn_bar.addWidget(self._send_btn)

        input_layout.addLayout(btn_bar)
        chat_layout.addWidget(input_group)

        splitter.addWidget(chat_group)
        splitter.setSizes([200, 420])

        root.addWidget(splitter, stretch=1)

        # Keyboard shortcut: Ctrl+Enter to send
        shortcut = QShortcut(QKeySequence("Ctrl+Return"), self._input_edit)
        shortcut.activated.connect(self._on_send)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_load_esdl(self, manual: bool = False):
        """Start loading ESDL code from ASCET.

        Called automatically when a class is selected (manual=False), or
        when the user explicitly clicks the Reload button (manual=True).
        """
        if not self._class_path:
            return
        # Don't start a second load if one is already running
        if self._loader_worker and self._loader_worker.isRunning():
            return

        self._load_btn.setEnabled(False)
        self._load_btn.setText("Loading…")
        self._esdl_status_lbl.setText("Connecting to ASCET…")
        self._esdl_status_lbl.setStyleSheet("color: #f39c12; font-size: 8pt;")
        self._manual_load = manual

        # Use detected version from settings; fall back to "6.1.4"
        ascet_version = self.settings.value("ascet/version",
                            self.settings.value("ascet/detected_version", "6.1.4"))

        self._loader_worker = EsdlLoaderWorker(self._class_path, ascet_version)
        self._loader_worker.code_loaded.connect(self._on_esdl_loaded)
        self._loader_worker.error_occurred.connect(self._on_esdl_error)
        self._loader_worker.finished.connect(self._on_loader_finished)
        self._loader_worker.start()

    def _on_loader_finished(self):
        """Re-enable the button after load attempt."""
        self._load_btn.setEnabled(True)
        if self._esdl_code:
            self._load_btn.setText("↺ Reload")
        else:
            self._load_btn.setText("Load ESDL Code")

    def _on_esdl_loaded(self, code: str):
        """Display loaded ESDL code."""
        self._esdl_code = code
        self._esdl_display.setPlainText(code)
        lines = code.count("\n") + 1
        self._esdl_status_lbl.setText(f"Loaded  ({lines} lines)")
        self._esdl_status_lbl.setStyleSheet(
            "color: #27ae60; font-size: 8pt; font-weight: 600;"
        )
        # Reset chat so the new code is picked up in subsequent sends
        self._chat_history.clear()
        self._append_system_message()

    def _on_esdl_error(self, msg: str):
        """Show ESDL load error.

        Always shows inline. Only shows a popup when the user explicitly
        clicked the button (manual=True) to avoid annoying auto-load popups.
        """
        self._esdl_status_lbl.setText("❌ Load failed – click Reload to retry")
        self._esdl_status_lbl.setStyleSheet("color: #e74c3c; font-size: 8pt;")
        self._esdl_status_lbl.setToolTip(msg)
        if getattr(self, "_manual_load", True):
            QMessageBox.warning(self, "ESDL Load Error", msg)

    def _on_send(self):
        """Send user message to the AI."""
        user_text = self._input_edit.toPlainText().strip()
        if not user_text:
            return

        if self._chat_worker and self._chat_worker.isRunning():
            return

        # Build history if not yet started
        if not self._chat_history:
            self._append_system_message()

        # Add user message
        self._chat_history.append({"role": "user", "content": user_text})
        self._add_bubble(user_text, "user")
        self._input_edit.clear()

        # Track for history persistence
        if not self._session_start_time:
            self._session_start_time = datetime.now().isoformat()
        self._session_messages.append({
            "role":      "user",
            "content":   user_text,
            "timestamp": datetime.now().isoformat(),
        })

        # Get API settings
        api_url = self.settings.value("api/deepseek_api_url", "http://10.161.112.104:3000/v1")
        api_key = self.settings.value("api/deepseek_api_key", "")
        model = self._model_combo.currentText()

        if not api_key:
            QMessageBox.warning(
                self,
                "API Key Missing",
                "No API key configured.\nPlease go to Settings → API Configuration.",
            )
            return

        # Create placeholder assistant bubble
        self._current_assistant_bubble = self._add_bubble("", "assistant")

        self._send_btn.setEnabled(False)
        self._stop_btn.setEnabled(True)

        self._chat_worker = ChatWorker(
            api_url=api_url,
            api_key=api_key,
            model=model,
            messages=self._chat_history,
        )
        self._chat_worker.chunk_received.connect(self._on_chunk)
        self._chat_worker.finished.connect(self._on_chat_finished)
        self._chat_worker.error_occurred.connect(self._on_chat_error)
        self._chat_worker.start()

    def _on_stop(self):
        if self._chat_worker and self._chat_worker.isRunning():
            self._chat_worker.stop()

    def _on_chunk(self, chunk: str):
        if self._current_assistant_bubble:
            self._current_assistant_bubble.append_text(chunk)
            # Auto-scroll to bottom
            vsb = self._history_scroll.verticalScrollBar()
            vsb.setValue(vsb.maximum())

    def _on_chat_finished(self):
        self._send_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)

        if self._current_assistant_bubble:
            full_reply = self._current_assistant_bubble._full_text
            self._current_assistant_bubble.finalise()
            self._current_assistant_bubble = None
            # Save assistant turn to history
            self._chat_history.append({"role": "assistant", "content": full_reply})
            # Track for history persistence and auto-save
            self._session_messages.append({
                "role":      "assistant",
                "content":   full_reply,
                "timestamp": datetime.now().isoformat(),
            })
            self._save_session()  # auto-save after each complete exchange

        # Scroll to bottom
        QTimer.singleShot(50, self._scroll_to_bottom)

    def _on_chat_error(self, msg: str):
        self._send_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._current_assistant_bubble = None
        self._add_bubble(f"[Error] {msg}", "assistant")

    def _on_clear_chat(self):
        # Save current session before wiping
        if self._session_messages:
            self._save_session()
        # Remove all bubble widgets
        for bubble in self._bubble_widgets:
            self._history_layout.removeWidget(bubble)
            bubble.deleteLater()
        self._bubble_widgets.clear()
        self._chat_history.clear()
        self._session_messages.clear()
        self._active_session_path = None
        self._session_start_time  = None

    # ------------------------------------------------------------------
    # History persistence
    # ------------------------------------------------------------------

    def _save_session(self):
        """Persist the current session to disk (create new or update existing)."""
        if not self._session_messages:
            return

        api_url   = self.settings.value("api/deepseek_api_url", "http://10.161.112.104:3000/v1")
        api_key   = self.settings.value("api/deepseek_api_key", "")
        model_key = self._model_combo.currentText()
        actual_model = model_key
        if MODEL_CONFIG_AVAILABLE:
            try:
                actual_model = ModelConfig(model_key).get_model_name()
            except Exception:
                pass

        user_msgs = [m for m in self._session_messages if m["role"] == "user"]
        asst_msgs = [m for m in self._session_messages if m["role"] == "assistant"]
        class_name = (self._class_path or "").split("\\")[-1]
        key_hint   = (
            f"{api_key[:8]}…{api_key[-4:]}" if len(api_key) > 12 else "***"
        )

        session_data = {
            "session_id":    self._session_start_time or datetime.now().isoformat(),
            "created_at":    self._session_start_time or datetime.now().isoformat(),
            "updated_at":    datetime.now().isoformat(),
            "class_path":    self._class_path or "",
            "class_name":    class_name,
            "esdl_snapshot": self._esdl_code or "",
            "config": {
                "model_key":    model_key,
                "model_name":   actual_model,
                "api_url":      api_url,
                "api_key_hint": key_hint,
            },
            "messages": self._session_messages,
            "stats": {
                "total_turns":        len(user_msgs),
                "user_messages":      len(user_msgs),
                "assistant_messages": len(asst_msgs),
            },
        }

        if self._active_session_path and Path(self._active_session_path).exists():
            self._history_manager.update_session(self._active_session_path, session_data)
        else:
            self._active_session_path = self._history_manager.save_session(session_data)

    def _open_history_dialog(self):
        """Open the chat history browser dialog."""
        dlg = ChatHistoryDialog(self._history_manager, parent=self)
        dlg.session_load_requested.connect(self._load_session)
        dlg.exec()

    def _load_session(self, session_data: dict):
        """Restore a previously saved chat session into the panel."""
        # Persist any in-progress session, then pre-clear so _on_clear_chat won't double-save
        if self._session_messages:
            self._save_session()
        self._session_messages.clear()
        self._active_session_path = None
        self._session_start_time  = None

        # Clear the UI (does NOT save again because _session_messages is empty)
        self._on_clear_chat()

        # ── Restore class / ESDL ───────────────────────────────────────
        class_path = session_data.get("class_path", "")
        class_name = session_data.get("class_name", "")
        esdl       = session_data.get("esdl_snapshot", "")

        self._class_path = class_path or None
        self._esdl_code  = esdl or None
        self._selected_class_label.setText(
            f"Selected: {class_name}" if class_name else "No class selected"
        )
        self._selected_class_label.setToolTip(class_path)
        self._load_btn.setEnabled(bool(class_path))

        if esdl:
            self._esdl_display.setPlainText(esdl)
            lines = esdl.count("\n") + 1
            self._esdl_status_lbl.setText(f"Loaded from history  ({lines} lines)")
            self._esdl_status_lbl.setStyleSheet(
                "color: #4dabf7; font-size: 8pt; font-weight: 600;"
            )
            self._load_btn.setText("↺ Reload")

        # ── Restore model ──────────────────────────────────────────────
        model_key = session_data.get("config", {}).get("model_key", "gpt5-mini")
        idx = self._model_combo.findText(model_key)
        if idx >= 0:
            self._model_combo.setCurrentIndex(idx)

        # ── Rebuild conversation ────────────────────────────────────────
        self._append_system_message()
        for msg in session_data.get("messages", []):
            role    = msg.get("role", "")
            content = msg.get("content", "")
            if role in ("user", "assistant"):
                self._chat_history.append({"role": role, "content": content})
                self._add_bubble(content, role)

        # ── Resume session tracking (further msgs extend this session) ───
        self._session_messages   = [{k: v for k, v in m.items()}
                                    for m in session_data.get("messages", [])]
        self._session_start_time = session_data.get("created_at")
        self._active_session_path = None  # new file if session is extended

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _append_system_message(self):
        """Build system + ESDL context system message."""
        system_content = _ESDL_SYSTEM_PROMPT
        if self._esdl_code:
            class_name = (self._class_path or "unknown").split("\\")[-1]
            system_content += (
                f"\n\n--- Current ESDL source for class '{class_name}' (Main.calc) ---\n"
                f"```esdl\n{self._esdl_code}\n```\n"
                "--- End of current ESDL source ---"
            )
        self._chat_history.append({"role": "system", "content": system_content})

    def _add_bubble(self, text: str, role: str) -> ChatBubble:
        """Insert a new chat bubble into the history layout."""
        bubble = ChatBubble(text, role)
        # Insert before the trailing stretch
        insert_pos = self._history_layout.count() - 1
        self._history_layout.insertWidget(insert_pos, bubble)
        self._bubble_widgets.append(bubble)
        QTimer.singleShot(30, self._scroll_to_bottom)
        return bubble

    def _scroll_to_bottom(self):
        vsb = self._history_scroll.verticalScrollBar()
        vsb.setValue(vsb.maximum())
