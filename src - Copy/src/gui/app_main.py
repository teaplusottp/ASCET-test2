import sys
import os
import json
import re
import time
import traceback
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
import multiprocessing
import webbrowser

try:
    import win32com.client
    WIN32COM_AVAILABLE = True
except ImportError:
    WIN32COM_AVAILABLE = False

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QLineEdit, QPushButton, QComboBox, QTreeWidget, QTextEdit,
    QGroupBox, QSplitter, QTabWidget, QMessageBox, QProgressBar,
    QStatusBar, QFileDialog, QInputDialog, QTreeWidgetItem, QListWidget,
    QListWidgetItem, QTextBrowser, QFrame, QCheckBox, QSpinBox,
    QFormLayout, QDialogButtonBox, QDialog, QScrollArea, QAbstractItemView,
    QTableWidget, QTableWidgetItem, QHeaderView, QMenu,
    QSizePolicy, QRadioButton, QButtonGroup,QStyle  
  
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QSettings, QRect, QSize, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import (
    QIcon, QFont, QPalette, QColor, QPixmap, QKeySequence, QPainter, QMovie,
    QShortcut, QAction ,QTextCursor
)
from PySide6.QtSvg import QSvgRenderer



try:
    from src.gui.spinner import MultiStyleSpinnerWidget, create_spinner
    SPINNER_AVAILABLE = True
except ImportError:
    SPINNER_AVAILABLE = False
try:
    import markdown
    MARKDOWN_AVAILABLE = True
except ImportError:
    MARKDOWN_AVAILABLE = False

# Ascet Folder Scanner 
from src.ascet.structure_filter import ASCETStructureScannerAPI
SCANNER_AVAILABLE = True

# Diagram Viewer
try:
    from src.diagrams.diagram_viewer import DiagramViewerDialog
    import xml.etree.ElementTree as ET
    DIAGRAM_VIEWER_AVAILABLE = True
except ImportError:
    DIAGRAM_VIEWER_AVAILABLE = False

try:
# Ascet 版本选择模块
    from src.utils.detect_ascet import detect_current_ascet
    ASCET_DETECTOR_AVAILABLE = True
    print("ASCET版本自动检测模块加载成功")
except ImportError as e:
    ASCET_DETECTOR_AVAILABLE = False
    print(f"Warning: ASCET版本自动检测模块不可用: {e}")

# 模型和规则检测协调收集器
try:
    from src.agents.ascet_agent import run_integrated_code_review
    AGENT_AVAILABLE = True
    print("AI Agent module loaded successfully")
except ImportError as e:
    AGENT_AVAILABLE = False
    print(f"Warning: AI Agent module unavailable: {e}")

# Import RAG core modules
# RAG 模块
try:
    from src.ai_core.rag_core import CodeAnalysisKnowledgeBuilder
    RAG_AVAILABLE = True
    print("RAG knowledge base module loaded successfully")
except ImportError as e:
    RAG_AVAILABLE = False
    print(f"Warning: RAG knowledge base module unavailable: {e}")

# Code Chat Panel
try:
    from src.gui.chat_panel import CodeChatPanel
    CHAT_PANEL_AVAILABLE = True
    print("Code Chat Panel module loaded successfully")
except ImportError as e:
    CHAT_PANEL_AVAILABLE = False
    print(f"Warning: Code Chat Panel module unavailable: {e}")


import multiprocessing


# ===============================================================
def _run_review_entry_subproc_with_logging(config: Dict[str, Any], mode: str, q: "multiprocessing.Queue"):
        """子进程入口"""
        try:
            try:
                import pythoncom
                pythoncom.CoInitialize()
            except Exception:
                pass

            # 子进程内再次导入，避免主进程引用在 spawn 下不可用
            from src.agents.ascet_agent import run_integrated_code_review_with_logging
            
            # 创建回调处理函数
            def agent_callback(message):
                try:
                    q.put(('agent_log', message))
                except:
                    pass
            
            def status_callback(message):
                try:
                    q.put(('status', message))
                except:
                    pass
            
            # 设置回调函数
            config['agent_callback'] = agent_callback
            config['status_callback'] = status_callback
            
            res = run_integrated_code_review_with_logging(config, mode=mode)
            q.put(('ok', res))
            
        except Exception as e:
            q.put(('err', {'status': 'error', 'error_message': str(e)}))
        finally:
            try:
                import pythoncom
                pythoncom.CoUninitialize()
            except Exception:
                pass



# ==================== SVG Icon Manager ====================

class SVGIconManager:
    """SVG icon manager"""
    
    def __init__(self):
        self.svg_cache = {}
        self.icon_cache = {}
        
        # Built-in SVG icons
        self.svg_data = {
            'check-circle': '''<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#27ae60" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                <polyline points="22,4 12,14.01 9,11.01"></polyline>
            </svg>''',
            
            'x-circle': '''<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#e74c3c" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="15" y1="9" x2="9" y2="15"></line>
                <line x1="9" y1="9" x2="15" y2="15"></line>
            </svg>''',
            
            'alert-circle': '''<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#f39c12" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="12" y1="8" x2="12" y2="12"></line>
                <line x1="12" y1="16" x2="12.01" y2="16"></line>
            </svg>''',
            
            'circle': '''<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#95a5a6" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="12" r="10"></circle>
            </svg>''',
            
            'arrow-right-circle': '''<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#3498db" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="12" r="10"></circle>
                <polyline points="12,8 16,12 12,16"></polyline>
                <line x1="8" y1="12" x2="16" y2="12"></line>
            </svg>'''
        }
    
    def get_icon(self, icon_name: str, size: QSize = QSize(16, 16)) -> QIcon:
        """Get SVG icon"""
        cache_key = f"{icon_name}_{size.width()}x{size.height()}"
        
        if cache_key in self.icon_cache:
            return self.icon_cache[cache_key]
        
        if icon_name in self.svg_data:
            svg_data = self.svg_data[icon_name]
        else:
            svg_path = f"svg/{icon_name}.svg"
            if os.path.exists(svg_path):
                with open(svg_path, 'r', encoding='utf-8') as f:
                    svg_data = f.read()
            else:
                svg_data = self.svg_data.get('circle', '')
        
        if svg_data:
            renderer = QSvgRenderer()
            renderer.load(svg_data.encode('utf-8'))
            
            pixmap = QPixmap(size)
            pixmap.fill(Qt.transparent)
            
            painter = QPainter(pixmap)
            renderer.render(painter)
            painter.end()
            
            icon = QIcon(pixmap)
            self.icon_cache[cache_key] = icon
            return icon
        
        return QIcon()

# Global icon manager
icon_manager = SVGIconManager()

# ==================== RAG Worker Thread (Keep original) ====================

class RAGWorker(QThread):
    """RAG knowledge base operation worker thread"""
    
    status_signal = Signal(str)
    progress_signal = Signal(int, str)
    finished_signal = Signal(bool, str, dict)
    entry_added_signal = Signal(str)
    
    def __init__(self, action: str, params: Dict[str, Any]):
        super().__init__()
        self.action = action
        self.params = params
        self.builder = None
        
    def run(self):
        """Run RAG operation"""
        try:
            if not RAG_AVAILABLE:
                self.finished_signal.emit(False, "RAG knowledge base module unavailable", {})
                return
            
            api_key = self.params.get("api_key", "")
            kb_path = self.params.get("knowledge_base_path", "")
            
            if not api_key:
                self.finished_signal.emit(False, "API key not set", {})
                return
                
            if not kb_path:
                self.finished_signal.emit(False, "Knowledge base path not set", {})
                return
            
            self.status_signal.emit("Initializing RAG knowledge base...")
            self.builder = CodeAnalysisKnowledgeBuilder(
                api_key=api_key,
                knowledge_base_path=kb_path
            )
            
            if self.action == "get_status":
                self._get_status()
            elif self.action == "add_single_entry":
                self._add_single_entry()
            elif self.action == "add_single_entry_with_rebuild":
                self._add_single_entry_with_rebuild()
            elif self.action == "add_batch_entries":
                self._add_batch_entries()
            elif self.action == "add_batch_entries_with_rebuild":
                self._add_batch_entries_with_rebuild()
            elif self.action == "build_index":
                self._build_index()
            elif self.action == "search":
                self._search()
            elif self.action == "delete_entries":
                self._delete_entries()
            else:
                self.finished_signal.emit(False, f"Unknown operation: {self.action}", {})
                
        except Exception as e:
            error_msg = f"RAG operation failed: {str(e)}"
            self.status_signal.emit(error_msg)
            self.finished_signal.emit(False, error_msg, {})

    def _add_single_entry_with_rebuild(self):
        """Add single entry and optionally rebuild index"""
        entry_config = self.params.get("entry_config", {})
        auto_rebuild = self.params.get("auto_rebuild_index", True)
        
        self.status_signal.emit(f"Adding entry: {entry_config.get('error_type', 'Unknown')}")
        
        try:
            success = self.builder.add_knowledge_entries([entry_config])
            
            if success and auto_rebuild:
                self.status_signal.emit("Auto rebuilding index...")
                self.progress_signal.emit(50, "Rebuilding index...")
                
                rebuild_success = self.builder.build_vector_index()
                if rebuild_success:
                    self.progress_signal.emit(100, "Entry added and index rebuilt successfully")
                    self.finished_signal.emit(True, "Entry added successfully, index rebuilt", {})
                else:
                    self.finished_signal.emit(True, "Entry added successfully, but index rebuild failed", {})
            elif success:
                self.progress_signal.emit(100, "Entry added successfully")
                self.finished_signal.emit(True, "Entry added successfully (index not rebuilt)", {})
            else:
                self.finished_signal.emit(False, "Failed to add entry", {})
                
        except Exception as e:
            self.finished_signal.emit(False, f"Failed to add entry: {str(e)}", {})
    
    def _add_batch_entries_with_rebuild(self):
        """Batch add entries and optionally rebuild index"""
        entries_config = self.params.get("entries_config", [])
        auto_rebuild = self.params.get("auto_rebuild_index", True)
        total = len(entries_config)
        
        self.status_signal.emit(f"Starting batch addition of {total} entries...")
        self.progress_signal.emit(10, "Preparing to add...")
        
        try:
            success = self.builder.add_knowledge_entries(entries_config)
            
            if success and auto_rebuild:
                self.status_signal.emit("Auto rebuilding index...")
                self.progress_signal.emit(70, "Rebuilding index...")
                
                rebuild_success = self.builder.build_vector_index()
                if rebuild_success:
                    self.progress_signal.emit(100, "Batch addition and index rebuild completed")
                    self.finished_signal.emit(True, f"Successfully added {total} entries, index rebuilt", {})
                else:
                    self.finished_signal.emit(True, f"Successfully added {total} entries, but index rebuild failed", {})
            elif success:
                self.progress_signal.emit(100, "Batch addition completed")
                self.finished_signal.emit(True, f"Successfully added {total} entries (index not rebuilt)", {})
            else:
                self.finished_signal.emit(False, "Batch addition failed", {})
                
        except Exception as e:
            self.finished_signal.emit(False, f"Batch addition failed: {str(e)}", {})

    def _get_status(self):
        """Get knowledge base status"""
        self.status_signal.emit("Getting knowledge base status...")
        status = self.builder.get_knowledge_base_status()
        self.finished_signal.emit(True, "Status retrieved successfully", {"status": status})
    
    def _add_single_entry(self):
        """Add single entry"""
        entry_config = self.params.get("entry_config", {})
        self.status_signal.emit(f"Adding entry: {entry_config.get('error_type', 'Unknown')}")
        
        try:
            self.builder.add_knowledge_entries([entry_config])
            self.entry_added_signal.emit("Single entry added successfully")
            self.finished_signal.emit(True, "Entry added successfully", {})
        except Exception as e:
            self.finished_signal.emit(False, f"Failed to add entry: {str(e)}", {})
    
    def _add_batch_entries(self):
        """Batch add entries"""
        entries_config = self.params.get("entries_config", [])
        total = len(entries_config)
        
        self.status_signal.emit(f"Starting batch addition of {total} entries...")
        self.progress_signal.emit(10, "Preparing to add...")
        
        try:
            self.builder.add_knowledge_entries(entries_config)
            self.progress_signal.emit(100, "Batch addition completed")
            self.finished_signal.emit(True, f"Successfully added {total} entries", {})
        except Exception as e:
            self.finished_signal.emit(False, f"Batch addition failed: {str(e)}", {})
    
    def _build_index(self):
        """Build vector index"""
        self.status_signal.emit("Building vector index...")
        self.progress_signal.emit(20, "Starting index build...")
        
        try:
            success = self.builder.build_vector_index()
            if success:
                self.progress_signal.emit(100, "Index build completed")
                self.finished_signal.emit(True, "Index built successfully", {})
            else:
                self.finished_signal.emit(False, "Index build failed", {})
        except Exception as e:
            self.finished_signal.emit(False, f"Index build failed: {str(e)}", {})
    
    def _search(self):
        """Search knowledge base"""
        query = self.params.get("query", "")
        top_k = self.params.get("top_k", 5)
        
        self.status_signal.emit(f"Searching: {query}")
        
        try:
            results = self.builder.search_similar(query, top_k)
            self.finished_signal.emit(True, f"Search completed, found {len(results)} results", {"results": results})
        except Exception as e:
            self.finished_signal.emit(False, f"Search failed: {str(e)}", {})
    
    def _delete_entries(self):
        """Delete entries"""
        entry_ids = self.params.get("entry_ids", [])
        
        try:
            deleted_count = self.builder.delete_entries_by_ids(entry_ids)
            self.finished_signal.emit(True, f"Successfully deleted {deleted_count} entries", {"deleted_count": deleted_count})
        except Exception as e:
            self.finished_signal.emit(False, f"Failed to delete entries: {str(e)}", {})


    # ==================== RAG Management Dialog (Keep original) ====================

class RAGManagementDialog(QDialog):
    """RAG knowledge base management dialog - 完整修复版本"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("RAG Knowledge Base Management")
        self.setModal(False)
        self.resize(1200, 800)  # 保持合理窗口尺寸
        
        self.settings = QSettings('AscetAgent', 'AscetAgentv3')
        self.rag_worker = None
        self.current_entries = []
        self.builder = None
        
        self.init_ui()
        self.load_rag_settings()
        
        self.init_rag_builder()
    
    def init_rag_builder(self):
        """Initialize RAG knowledge base builder"""
        try:
            if not RAG_AVAILABLE:
                self.append_log("RAG module unavailable")
                return
            
            api_key = self.settings.value("api/embedding_api_key", "")
            kb_path = self.settings.value("paths/knowledge_base_path", "")
            
            if api_key and kb_path:
                self.builder = CodeAnalysisKnowledgeBuilder(
                    api_key=api_key,
                    knowledge_base_path=kb_path
                )
                self.append_log("RAG knowledge base builder initialized successfully")
                QTimer.singleShot(500, self.refresh_entries)
            else:
                self.append_log("RAG configuration incomplete, unable to initialize knowledge base builder")
                
        except Exception as e:
            self.append_log(f"Failed to initialize RAG builder: {str(e)}")
        
    def init_ui(self):
        """Initialize UI - 优化布局和尺寸"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # 创建tab widget，设置合适的尺寸
        self.tab_widget = QTabWidget()
        self.tab_widget.setMinimumSize(1100, 600)
        
        # 设置tab样式，确保文本完整显示
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 2px solid #dee2e6;
                background-color: #ffffff;
                border-radius: 8px;
                margin-top: -1px;
            }
            QTabBar::tab {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f8f9fa, stop:1 #e9ecef);
                border: 1px solid #dee2e6;
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                padding: 8px 25px;
                margin-right: 3px;
                font-size: 9pt;
                font-weight: 500;
                color: #6c757d;
                min-width: 120px;
            }
            QTabBar::tab:selected {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ffffff, stop:1 #f8f9fa);
                color: #4dabf7;
                border-color: #4dabf7;
                font-weight: 600;
            }
            QTabBar::tab:hover:!selected {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ffffff, stop:1 #f1f3f4);
                color: #495057;
            }
        """)
        
        self.create_status_tab()
        self.create_add_entry_tab()
        self.create_manage_tab()
        self.create_search_tab()
        
        layout.addWidget(self.tab_widget)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMinimumHeight(22)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #dee2e6;
                border-radius: 6px;
                background-color: #f8f9fa;
                text-align: center;
                font-size: 9pt;
                font-weight: 500;
                color: #495057;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4dabf7, stop:1 #74c0fc);
                border-radius: 4px;
                margin: 2px;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        # 状态显示区域
        self.status_text = QTextEdit()
        self.status_text.setMaximumHeight(90)
        self.status_text.setMinimumHeight(80)
        self.status_text.setReadOnly(True)
        self.status_text.setPlaceholderText("System logs and status messages will be displayed here...")
        self.status_text.setStyleSheet("""
            QTextEdit {
                border: 2px solid #dee2e6;
                border-radius: 6px;
                background-color: #ffffff;
                font-family: "Consolas", "Monaco", "Courier New", monospace;
                font-size: 8pt;
                padding: 6px;
            }
        """)
        layout.addWidget(self.status_text)
    
    def create_status_tab(self):
        """Create status tab - 优化布局"""
        status_widget = QWidget()
        status_layout = QVBoxLayout(status_widget)
        status_layout.setContentsMargins(15, 15, 15, 15)
        status_layout.setSpacing(12)
        
        # 按钮区域
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        
        self.refresh_status_btn = QPushButton("Refresh Status")
        self.refresh_status_btn.clicked.connect(self.refresh_status)
        self.refresh_status_btn.setMinimumWidth(120)
        self.refresh_status_btn.setMinimumHeight(32)
        self.refresh_status_btn.setStyleSheet("""
            QPushButton {
                background-color: #4dabf7;
                color: white;
                font-weight: bold;
                font-size: 9pt;
                padding: 8px 16px;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #339af0;
            }
            QPushButton:pressed {
                background-color: #228be6;
            }
        """)
        
        btn_layout.addWidget(self.refresh_status_btn)
        btn_layout.addStretch()
        
        status_layout.addLayout(btn_layout)
        
        # 状态显示区域
        self.status_display = QTextEdit()
        self.status_display.setReadOnly(True)
        self.status_display.setMinimumHeight(400)
        self.status_display.setStyleSheet("""
            QTextEdit {
                border: 2px solid #dee2e6;
                border-radius: 6px;
                background-color: #ffffff;
                font-family: "Consolas", "Monaco", "Courier New", monospace;
                font-size: 9pt;
                padding: 12px;
                line-height: 1.3;
            }
        """)
        status_layout.addWidget(self.status_display)
        
        self.tab_widget.addTab(status_widget, "Kb Status")
    
    def create_add_entry_tab(self):
        """Create add entry tab - """
        add_widget = QWidget()
        add_layout = QVBoxLayout(add_widget)
        add_layout.setContentsMargins(15, 15, 15, 15)
        add_layout.setSpacing(15)
        
        # ========== 单条目添加区域 ==========
        single_group = QGroupBox("Add Single Entry")
        single_group.setMinimumHeight(320)
        single_group.setStyleSheet("""
            QGroupBox {
                font-weight: 600;
                font-size: 10pt;
                color: #495057;
                border: 2px solid #e9ecef;
                border-radius: 8px;
                margin: 6px 3px;
                padding-top: 12px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ffffff, stop:1 #f8f9fa);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 3px 8px;
                background-color: #ffffff;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                font-size: 9pt;
            }
        """)
        single_layout = QFormLayout(single_group)
        single_layout.setContentsMargins(15, 20, 15, 15)
        single_layout.setSpacing(8)
        
        # 类别选择
        self.category_combo = QComboBox()
        self.category_combo.addItems(["Error Code", "False Positive Code","误报代码","错误代码"])
        self.category_combo.setMinimumHeight(28)
        self.category_combo.setStyleSheet("""
            QComboBox {
                border: 2px solid #ced4da;
                border-radius: 5px;
                padding: 6px 10px;
                font-size: 9pt;
                background-color: #ffffff;
            }
            QComboBox:focus {
                border-color: #4dabf7;
            }
            QComboBox::drop-down {
                border: none;
                width: 18px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid #6c757d;
                margin-right: 4px;
            }
        """)
        single_layout.addRow("Category:", self.category_combo)
        
        # 错误类型
        self.error_type_edit = QLineEdit()
        self.error_type_edit.setMinimumHeight(28)
        self.error_type_edit.setPlaceholderText("Enter error type description...")
        self.error_type_edit.setStyleSheet("""
            QLineEdit {
                border: 2px solid #ced4da;
                border-radius: 5px;
                padding: 6px 10px;
                font-size: 9pt;
                background-color: #ffffff;
            }
            QLineEdit:focus {
                border-color: #4dabf7;
            }
        """)
        single_layout.addRow("Error Type:", self.error_type_edit)
        
        # 代码片段
        self.code_snippet_edit = QTextEdit()
        self.code_snippet_edit.setMaximumHeight(120)
        self.code_snippet_edit.setMinimumHeight(80)
        self.code_snippet_edit.setPlaceholderText("Paste your code snippet here...")
        self.code_snippet_edit.setStyleSheet("""
            QTextEdit {
                border: 2px solid #ced4da;
                border-radius: 5px;
                background-color: #ffffff;
                font-family: "Consolas", "Monaco", "Courier New", monospace;
                font-size: 8pt;
                padding: 8px;
            }
            QTextEdit:focus {
                border-color: #4dabf7;
            }
        """)
        single_layout.addRow("Code Snippet:", self.code_snippet_edit)
        
        # 错误描述
        self.error_desc_edit = QTextEdit()
        self.error_desc_edit.setMaximumHeight(80)
        self.error_desc_edit.setMinimumHeight(60)
        self.error_desc_edit.setPlaceholderText("Describe the error in detail...")
        self.error_desc_edit.setStyleSheet("""
            QTextEdit {
                border: 2px solid #ced4da;
                border-radius: 5px;
                background-color: #ffffff;
                font-size: 9pt;
                padding: 8px;
            }
            QTextEdit:focus {
                border-color: #4dabf7;
            }
        """)
        single_layout.addRow("Error Description:", self.error_desc_edit)
        
        # 附加信息
        self.additional_info_edit = QTextEdit()
        self.additional_info_edit.setMaximumHeight(60)
        self.additional_info_edit.setMinimumHeight(45)
        self.additional_info_edit.setPlaceholderText("Any additional information...")
        self.additional_info_edit.setStyleSheet("""
            QTextEdit {
                border: 2px solid #ced4da;
                border-radius: 5px;
                background-color: #ffffff;
                font-size: 9pt;
                padding: 8px;
            }
            QTextEdit:focus {
                border-color: #4dabf7;
            }
        """)
        single_layout.addRow("Additional Info:", self.additional_info_edit)
        
        # 自动重建索引选项
        self.auto_rebuild_index_check = QCheckBox("Auto rebuild index after adding (recommended)")
        self.auto_rebuild_index_check.setChecked(True)
        self.auto_rebuild_index_check.setToolTip("Automatically rebuild index after adding entry to ensure search functionality works properly")
        self.auto_rebuild_index_check.setStyleSheet("""
            QCheckBox {
                font-size: 9pt;
                color: #495057;
                spacing: 6px;
                padding: 4px;
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
                border-radius: 3px;
                border: 2px solid #ced4da;
                background-color: #ffffff;
            }
            QCheckBox::indicator:checked {
                background-color: #4dabf7;
                border-color: #228be6;
            }
        """)
        single_layout.addRow("Index Management:", self.auto_rebuild_index_check)
        
        # 按钮区域 - 优化布局和样式
        single_btn_layout = QHBoxLayout()
        single_btn_layout.setSpacing(10)
        single_btn_layout.setContentsMargins(0, 8, 0, 0)
        
        self.add_single_btn = QPushButton("Add Entry")
        self.add_single_btn.clicked.connect(self.add_single_entry)
        self.add_single_btn.setMinimumWidth(100)
        self.add_single_btn.setMinimumHeight(32)
        self.add_single_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                font-weight: bold;
                font-size: 9pt;
                padding: 8px 16px;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
            QPushButton:pressed {
                background-color: #1e8449;
            }
        """)
        
        self.clear_form_btn = QPushButton("Clear Form")
        self.clear_form_btn.clicked.connect(self.clear_single_form)
        self.clear_form_btn.setMinimumWidth(100)
        self.clear_form_btn.setMinimumHeight(32)
        self.clear_form_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                font-weight: bold;
                font-size: 9pt;
                padding: 8px 16px;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
            QPushButton:pressed {
                background-color: #495057;
            }
        """)
        
        self.manual_rebuild_btn = QPushButton("Rebuild Index")
        self.manual_rebuild_btn.clicked.connect(self.manual_rebuild_index)
        self.manual_rebuild_btn.setMinimumWidth(110)
        self.manual_rebuild_btn.setMinimumHeight(32)
        self.manual_rebuild_btn.setStyleSheet("""
            QPushButton {
                background-color: #f39c12;
                color: white;
                font-weight: bold;
                font-size: 9pt;
                padding: 8px 16px;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #e67e22;
            }
            QPushButton:pressed {
                background-color: #d68910;
            }
        """)
        
        single_btn_layout.addWidget(self.add_single_btn)
        single_btn_layout.addWidget(self.clear_form_btn)
        single_btn_layout.addWidget(self.manual_rebuild_btn)
        single_btn_layout.addStretch()
        
        single_layout.addRow(single_btn_layout)
        
        add_layout.addWidget(single_group)
        
        # ========== JSON批量添加区域 ==========
        batch_group = QGroupBox("JSON Batch Addition")
        batch_group.setMinimumHeight(280)
        batch_group.setStyleSheet("""
            QGroupBox {
                font-weight: 600;
                font-size: 10pt;
                color: #495057;
                border: 2px solid #e9ecef;
                border-radius: 8px;
                margin: 6px 3px;
                padding-top: 12px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ffffff, stop:1 #f8f9fa);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 3px 8px;
                background-color: #ffffff;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                font-size: 9pt;
            }
        """)
        batch_layout = QVBoxLayout(batch_group)
        batch_layout.setContentsMargins(15, 20, 15, 15)
        batch_layout.setSpacing(12)
        
        # JSON控制按钮区域
        json_ctrl_layout = QHBoxLayout()
        json_ctrl_layout.setSpacing(10)
        
        self.load_json_btn = QPushButton("Load File")
        self.load_json_btn.clicked.connect(self.load_json_file)
        self.load_json_btn.setMinimumWidth(80)
        self.load_json_btn.setMinimumHeight(30)
        
        self.save_json_btn = QPushButton("Save File")
        self.save_json_btn.clicked.connect(self.save_json_file)
        self.save_json_btn.setMinimumWidth(80)
        self.save_json_btn.setMinimumHeight(30)
        
        self.load_template_btn = QPushButton("Load Template")
        self.load_template_btn.clicked.connect(self.load_json_template)
        self.load_template_btn.setMinimumWidth(100)
        self.load_template_btn.setMinimumHeight(30)
        
        # 统一JSON控制按钮样式
        json_btn_style = """
            QPushButton {
                background-color: #3498db;
                color: white;
                font-weight: bold;
                font-size: 9pt;
                padding: 6px 12px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #21618c;
            }
        """
        self.load_json_btn.setStyleSheet(json_btn_style)
        self.save_json_btn.setStyleSheet(json_btn_style)
        self.load_template_btn.setStyleSheet(json_btn_style)
        
        json_ctrl_layout.addWidget(self.load_json_btn)
        json_ctrl_layout.addWidget(self.save_json_btn)
        json_ctrl_layout.addWidget(self.load_template_btn)
        json_ctrl_layout.addStretch()
        
        batch_layout.addLayout(json_ctrl_layout)
        
        # JSON编辑器
        self.json_edit = QTextEdit()
        self.json_edit.setPlainText("[]")
        self.json_edit.setMinimumHeight(140)
        self.json_edit.setStyleSheet("""
            QTextEdit {
                border: 2px solid #ced4da;
                border-radius: 5px;
                background-color: #ffffff;
                font-family: "Consolas", "Monaco", "Courier New", monospace;
                font-size: 8pt;
                padding: 10px;
            }
            QTextEdit:focus {
                border-color: #4dabf7;
            }
        """)
        batch_layout.addWidget(self.json_edit)
        
        # 批量选项区域
        batch_options_layout = QHBoxLayout()
        batch_options_layout.setSpacing(12)
        
        self.batch_auto_rebuild_check = QCheckBox("Auto rebuild index after batch addition")
        self.batch_auto_rebuild_check.setChecked(True)
        self.batch_auto_rebuild_check.setStyleSheet("""
            QCheckBox {
                font-size: 9pt;
                color: #495057;
                spacing: 6px;
                padding: 4px;
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
                border-radius: 3px;
                border: 2px solid #ced4da;
                background-color: #ffffff;
            }
            QCheckBox::indicator:checked {
                background-color: #4dabf7;
                border-color: #228be6;
            }
        """)
        batch_options_layout.addWidget(self.batch_auto_rebuild_check)
        batch_options_layout.addStretch()
        
        batch_layout.addLayout(batch_options_layout)
        
        # 批量添加按钮
        self.add_batch_btn = QPushButton("Batch Add")
        self.add_batch_btn.clicked.connect(self.add_batch_entries)
        self.add_batch_btn.setMinimumWidth(120)
        self.add_batch_btn.setMinimumHeight(36)
        self.add_batch_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                font-weight: bold;
                font-size: 10pt;
                padding: 10px 20px;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #21618c;
            }
        """)
        batch_layout.addWidget(self.add_batch_btn)
        
        add_layout.addWidget(batch_group)
        
        self.tab_widget.addTab(add_widget, "Add Entries")
    
    def create_manage_tab(self):
        """Create management tab - """
        manage_widget = QWidget()
        manage_layout = QVBoxLayout(manage_widget)
        manage_layout.setContentsMargins(20, 20, 20, 20)
        manage_layout.setSpacing(15)
        
        # 工具栏区域
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setSpacing(15)
        
        self.refresh_entries_btn = QPushButton("Refresh List")
        self.refresh_entries_btn.clicked.connect(self.force_refresh_entries)
        self.refresh_entries_btn.setMinimumWidth(120)
        self.refresh_entries_btn.setMinimumHeight(40)
        self.refresh_entries_btn.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71;
                color: white;
                font-weight: bold;
                font-size: 11pt;
                padding: 10px 20px;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #27ae60;
            }
            QPushButton:pressed {
                background-color: #229954;
            }
        """)
        
        self.delete_selected_btn = QPushButton("Delete Selected")
        self.delete_selected_btn.clicked.connect(self.delete_selected_entries)
        self.delete_selected_btn.setMinimumWidth(140)
        self.delete_selected_btn.setMinimumHeight(40)
        self.delete_selected_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                font-weight: bold;
                font-size: 11pt;
                padding: 10px 20px;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:pressed {
                background-color: #a93226;
            }
        """)
        
        # 过滤器
        filter_label = QLabel("Filter:")
        filter_label.setStyleSheet("font-size: 11pt; font-weight: 600; color: #495057;")
        
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["All", "Error Code", "False Positive Code"])
        self.filter_combo.currentTextChanged.connect(self.filter_entries)
        self.filter_combo.setMinimumWidth(150)
        self.filter_combo.setMinimumHeight(35)
        self.filter_combo.setStyleSheet("""
            QComboBox {
                border: 2px solid #ced4da;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 10pt;
                background-color: #ffffff;
            }
            QComboBox:focus {
                border-color: #4dabf7;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid #6c757d;
                margin-right: 5px;
            }
        """)
        
        toolbar_layout.addWidget(self.refresh_entries_btn)
        toolbar_layout.addWidget(self.delete_selected_btn)
        toolbar_layout.addWidget(filter_label)
        toolbar_layout.addWidget(self.filter_combo)
        toolbar_layout.addStretch()
        
        manage_layout.addLayout(toolbar_layout)
        
        # 条目表格
        self.entries_table = QTableWidget()
        self.entries_table.setColumnCount(5)
        self.entries_table.setHorizontalHeaderLabels(["ID", "Category", "Error Type", "Error Description", "Created Time"])
        self.entries_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.entries_table.itemSelectionChanged.connect(self.on_entry_selection_changed)
        self.entries_table.setMinimumHeight(350)
        self.entries_table.setAlternatingRowColors(True)
        
        # 设置表格样式
        self.entries_table.setStyleSheet("""
            QTableWidget {
                border: 2px solid #dee2e6;
                border-radius: 8px;
                background-color: #ffffff;
                alternate-background-color: #f8f9fa;
                selection-background-color: #e3f2fd;
                selection-color: #1565c0;
                font-size: 10pt;
                gridline-color: #e9ecef;
            }
            QHeaderView::section {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f8f9fa, stop:1 #e9ecef);
                border: 1px solid #dee2e6;
                border-radius: 0px;
                padding: 8px 12px;
                font-weight: 600;
                font-size: 10pt;
                color: #495057;
            }
        """)
        
        # 设置列宽
        header = self.entries_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # ID
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Category
        header.setSectionResizeMode(2, QHeaderView.Interactive)       # Error Type
        header.setSectionResizeMode(3, QHeaderView.Stretch)          # Description
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents) # Time
        
        # 设置初始列宽
        self.entries_table.setColumnWidth(2, 200)  # Error Type 列宽
        
        manage_layout.addWidget(self.entries_table)
        
        # 详情显示区域
        details_label = QLabel("Entry Details:")
        details_label.setStyleSheet("font-size: 11pt; font-weight: 600; color: #495057; margin-top: 10px;")
        manage_layout.addWidget(details_label)
        
        self.entry_details = QTextEdit()
        self.entry_details.setMaximumHeight(150)
        self.entry_details.setMinimumHeight(120)
        self.entry_details.setReadOnly(True)
        self.entry_details.setPlaceholderText("Select an entry to view details...")
        self.entry_details.setStyleSheet("""
            QTextEdit {
                border: 2px solid #dee2e6;
                border-radius: 6px;
                background-color: #f8f9fa;
                font-family: "Consolas", "Monaco", "Courier New", monospace;
                font-size: 9pt;
                padding: 10px;
            }
        """)
        manage_layout.addWidget(self.entry_details)
        
        self.tab_widget.addTab(manage_widget, "Manage Entries")

    
    def create_search_tab(self):
        """Create search tab - 简洁布局，避免遮盖问题"""
        search_widget = QWidget()
        search_layout = QVBoxLayout(search_widget)
        search_layout.setContentsMargins(20, 20, 20, 20)
        search_layout.setSpacing(15)
        
        # =================  搜索输入区域 =================
        # 使用简单的标题标签，避免GroupBox遮盖问题
        search_title = QLabel("Knowledge Base Search")
        search_title.setStyleSheet("""
            font-size: 12pt; 
            font-weight: 600; 
            color: #2c3e50;
            margin-bottom: 5px;
            padding: 5px 0px;
        """)
        search_layout.addWidget(search_title)
        
        # 搜索输入框架
        search_frame = QFrame()
        search_frame.setFrameStyle(QFrame.StyledPanel)
        search_frame.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                padding: 10px;
            }
        """)
        
        search_frame_layout = QVBoxLayout(search_frame)
        search_frame_layout.setContentsMargins(15, 15, 15, 15)
        search_frame_layout.setSpacing(10)
        
        # 搜索输入行
        input_row_layout = QHBoxLayout()
        input_row_layout.setSpacing(12)
        
        # 查询输入框
        query_label = QLabel("Query:")
        query_label.setMinimumWidth(50)
        query_label.setStyleSheet("font-size: 9pt; font-weight: 600; color: #495057;")
        
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Enter search keywords...")
        self.search_edit.returnPressed.connect(self.perform_search)
        self.search_edit.setMinimumHeight(32)
        self.search_edit.setStyleSheet("""
            QLineEdit {
                border: 1px solid #ced4da;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 9pt;
                background-color: #ffffff;
            }
            QLineEdit:focus {
                border-color: #4dabf7;
            }
        """)
        
        # 结果数量
        count_label = QLabel("Results:")
        count_label.setMinimumWidth(50)
        count_label.setStyleSheet("font-size: 9pt; font-weight: 600; color: #495057;")
        
        self.search_k_spin = QSpinBox()
        self.search_k_spin.setRange(1, 20)
        self.search_k_spin.setValue(5)
        self.search_k_spin.setMinimumHeight(32)
        self.search_k_spin.setFixedWidth(70)
        self.search_k_spin.setStyleSheet("""
            QSpinBox {
                border: 1px solid #ced4da;
                border-radius: 4px;
                padding: 6px 8px;
                font-size: 9pt;
                background-color: #ffffff;
            }
            QSpinBox:focus {
                border-color: #4dabf7;
            }
        """)
        
        # 搜索按钮
        self.search_btn = QPushButton("Search")
        self.search_btn.clicked.connect(self.perform_search)
        self.search_btn.setFixedWidth(80)
        self.search_btn.setMinimumHeight(32)
        self.search_btn.setStyleSheet("""
            QPushButton {
                background-color: #4dabf7;
                color: white;
                font-weight: bold;
                font-size: 9pt;
                padding: 6px 12px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #339af0;
            }
            QPushButton:pressed {
                background-color: #228be6;
            }
        """)
        
        # 组合搜索行
        input_row_layout.addWidget(query_label)
        input_row_layout.addWidget(self.search_edit, 1)  # 占最多空间
        input_row_layout.addWidget(count_label)
        input_row_layout.addWidget(self.search_k_spin)
        input_row_layout.addWidget(self.search_btn)
        
        search_frame_layout.addLayout(input_row_layout)
        search_layout.addWidget(search_frame)
        
        # =================  快速查询区域 =================
        quick_title = QLabel("Quick Search")
        quick_title.setStyleSheet("""
            font-size: 11pt; 
            font-weight: 600; 
            color: #2c3e50;
            margin-bottom: 5px;
            padding: 5px 0px;
        """)
        search_layout.addWidget(quick_title)
        
        # 快速查询按钮
        position_error_btn = QPushButton("Position Variable Mapping Error")
        position_error_btn.clicked.connect(lambda: self.set_search_query("Position Variable Mapping Error"))
        position_error_btn.setFixedHeight(32)
        position_error_btn.setMaximumWidth(280)
        position_error_btn.setStyleSheet("""
            QPushButton {
                background-color: #17a2b8;
                color: white;
                font-size: 9pt;
                font-weight: 500;
                padding: 6px 15px;
                border: none;
                border-radius: 4px;
                text-align: center;
            }
            QPushButton:hover {
                background-color: #138496;
            }
            QPushButton:pressed {
                background-color: #0f6674;
            }
        """)
        
        # 按钮容器，左对齐
        quick_btn_layout = QHBoxLayout()
        quick_btn_layout.addWidget(position_error_btn)
        quick_btn_layout.addStretch()
        search_layout.addLayout(quick_btn_layout)
        
        # =================  搜索结果显示 =================
        results_title = QLabel("Search Results")
        results_title.setStyleSheet("""
            font-size: 11pt; 
            font-weight: 600; 
            color: #2c3e50;
            margin-bottom: 5px;
            padding: 5px 0px;
        """)
        search_layout.addWidget(results_title)
        
        self.search_results = QTextEdit()
        self.search_results.setReadOnly(True)
        self.search_results.setMinimumHeight(300)
        self.search_results.setPlaceholderText("Enter a search query above to find relevant knowledge entries...")
        self.search_results.setStyleSheet("""
            QTextEdit {
                border: 1px solid #dee2e6;
                border-radius: 4px;
                background-color: #ffffff;
                font-family: "Consolas", "Monaco", "Courier New", monospace;
                font-size: 8pt;
                padding: 12px;
                line-height: 1.4;
            }
            QTextEdit:focus {
                border-color: #4dabf7;
            }
        """)
        
        search_layout.addWidget(self.search_results)
        
        # 设置布局的伸缩因子，让结果区域占主要空间
        search_layout.addStretch(0)  # 不添加额外的弹性空间
        
        self.tab_widget.addTab(search_widget, "Search Test")
    
    def load_rag_settings(self):
        """Load RAG settings"""
        pass
    
    def manual_rebuild_index(self):
        """Manually rebuild index"""
        reply = QMessageBox.question(
            self, "Confirm Rebuild", 
            "Manual index rebuild may take a long time, continue?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.No:
            return
        
        params = {
            "api_key": self.settings.value("api/embedding_api_key", ""),
            "knowledge_base_path": self.settings.value("paths/knowledge_base_path", "")
        }
        
        self.start_rag_operation("build_index", params)
    
    def force_refresh_entries(self):
        """Force refresh entry list"""
        try:
            self.append_log("Force refreshing entry list...")
            
            api_key = self.settings.value("api/embedding_api_key", "")
            kb_path = self.settings.value("paths/knowledge_base_path", "")
            
            if not api_key or not kb_path:
                QMessageBox.warning(self, "Configuration Error", "Please configure API key and knowledge base path in settings first")
                return
            
            self.builder = CodeAnalysisKnowledgeBuilder(
                api_key=api_key,
                knowledge_base_path=kb_path
            )
            
            self.append_log("RAG builder reinitialized successfully")
            
            self.refresh_entries()
            
        except Exception as e:
            self.append_log(f"Force refresh failed: {str(e)}")
            QMessageBox.critical(self, "Refresh Failed", f"Failed to force refresh entry list:\n{str(e)}")
    
    def refresh_entries(self):
        """Refresh entry list"""
        if not self.builder:
            self.append_log("RAG builder not initialized, trying to reinitialize...")
            self.force_refresh_entries()
            return
        
        try:
            self.entries_table.setRowCount(0)
            
            filter_category = self.filter_combo.currentText()
            
            all_entries = self.builder.knowledge_entries if self.builder else []
            self.current_entries = []
            
            filtered_count = 0
            for entry in all_entries:
                category = entry.get('category', '')
                
                if filter_category != "All" and category != filter_category:
                    continue
                
                self.current_entries.append(entry)
                filtered_count += 1
            
            self.entries_table.setRowCount(filtered_count)
            
            for row, entry in enumerate(self.current_entries):
                entry_id = entry.get('id', 'N/A')
                display_id = entry_id[:8] + "..." if len(entry_id) > 8 else entry_id
                self.entries_table.setItem(row, 0, QTableWidgetItem(display_id))
                
                category = entry.get('category', '')
                self.entries_table.setItem(row, 1, QTableWidgetItem(category))
                
                error_type = entry.get('error_type', '')
                self.entries_table.setItem(row, 2, QTableWidgetItem(error_type))
                
                error_description = entry.get('error_description', '')
                display_desc = error_description[:60] + "..." if len(error_description) > 60 else error_description
                self.entries_table.setItem(row, 3, QTableWidgetItem(display_desc))
                
                metadata = entry.get('metadata', {})
                timestamp = metadata.get('timestamp', 0)
                if timestamp:
                    time_str = datetime.fromtimestamp(timestamp).strftime("%m-%d %H:%M")
                else:
                    time_str = "Unknown"
                self.entries_table.setItem(row, 4, QTableWidgetItem(time_str))
                
                self.entries_table.item(row, 0).setData(Qt.UserRole, entry)
            
            self.entries_table.resizeColumnsToContents()
            
            total_entries = len(all_entries)
            self.append_log(f"✅ Refresh completed: Showing {filtered_count}/{total_entries} entries")
            
            self.entry_details.clear()
            
        except Exception as e:
            self.append_log(f"Failed to refresh entry list: {str(e)}")
            QMessageBox.critical(self, "Refresh Failed", f"Failed to refresh entry list:\n{str(e)}")
    
    def filter_entries(self, filter_text):
        """Filter entries"""
        self.append_log(f"Applying filter: {filter_text}")
        self.refresh_entries()
    
    def on_entry_selection_changed(self):
        """Entry selection changed"""
        try:
            selected_items = self.entries_table.selectedItems()
            if not selected_items:
                self.entry_details.clear()
                return
            
            row = selected_items[0].row()
            first_item = self.entries_table.item(row, 0)
            
            if not first_item:
                return
            
            entry = first_item.data(Qt.UserRole)
            
            if not entry:
                if 0 <= row < len(self.current_entries):
                    entry = self.current_entries[row]
                else:
                    self.entry_details.setText("Unable to get entry details")
                    return
            
            details = self.format_entry_details(entry)
            self.entry_details.setText(details)
            
        except Exception as e:
            self.append_log(f"Failed to show entry details: {str(e)}")
            self.entry_details.setText(f"Error showing details: {str(e)}")
    
    def format_entry_details(self, entry):
        """Format entry detailed information"""
        try:
            details = f"ID: {entry.get('id', 'N/A')}\n"
            details += f"Category: {entry.get('category', '')}\n"
            details += f"Error Type: {entry.get('error_type', '')}\n\n"
            
            details += f"Error Description:\n{entry.get('error_description', 'No description')}\n\n"
            
            details += f"Code Snippet:\n{entry.get('code_snippet', 'No code')}\n\n"
            
            code_with_lines = entry.get('code_with_lines', '')
            if code_with_lines and code_with_lines != entry.get('code_snippet', ''):
                details += f"Code with Line Numbers:\n{code_with_lines}\n\n"
            
            additional_info = entry.get('additional_info', '')
            if additional_info:
                details += f"Additional Info:\n{additional_info}\n\n"
            
            metadata = entry.get('metadata', {})
            if metadata:
                timestamp = metadata.get('timestamp', 0)
                if timestamp:
                    time_str = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
                    details += f"Created Time: {time_str}\n"
                
                content_hash = metadata.get('content_hash', '')
                if content_hash:
                    details += f"Content Hash: {content_hash[:16]}...\n"
            
            return details
            
        except Exception as e:
            return f"Error formatting details: {str(e)}"
    
    def delete_selected_entries(self):
        """Delete selected entries - 自动重建索引"""
        try:
            selected_rows = set()
            selected_items = self.entries_table.selectedItems()
            
            for item in selected_items:
                selected_rows.add(item.row())
            
            if not selected_rows:
                QMessageBox.information(self, "Notice", "Please select entries to delete first")
                return
            
            reply = QMessageBox.question(
                self, "Confirm Delete", 
                f"Are you sure you want to delete the selected {len(selected_rows)} entries?\n"
                f"The index will be automatically rebuilt after deletion.",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply != QMessageBox.Yes:
                return
            
            ids_to_delete = []
            for row in selected_rows:
                if 0 <= row < len(self.current_entries):
                    entry = self.current_entries[row]
                    entry_id = entry.get('id')
                    if entry_id:
                        ids_to_delete.append(entry_id)
            
            if not ids_to_delete:
                QMessageBox.warning(self, "Error", "Unable to get entry IDs to delete")
                return
            
            if self.builder:
                # 显示进度条
                self.progress_bar.setVisible(True)
                self.progress_bar.setValue(0)
                self.append_log("Deleting entries and rebuilding index...")
                
                # 删除条目（自动重建索引）
                deleted_count = self.builder.delete_entries_by_ids(ids_to_delete)
                
                self.progress_bar.setValue(100)
                self.progress_bar.setVisible(False)
                
                self.append_log(f"Deleted {deleted_count} entries")
                self.append_log("Index automatically rebuilt")
                
                self.refresh_entries()
                
                QMessageBox.information(self, "Delete Completed", 
                    f"Successfully deleted {deleted_count} entries\n"
                    f"Index has been automatically rebuilt")
            else:
                QMessageBox.warning(self, "Error", "RAG builder not initialized")
                
        except Exception as e:
            self.append_log(f"Failed to delete entries: {str(e)}")
            QMessageBox.critical(self, "Delete Failed", f"Failed to delete entries:\n{str(e)}")
    
    def refresh_status(self):
        """Refresh knowledge base status"""
        if not RAG_AVAILABLE:
            self.append_log("RAG module unavailable")
            return
        
        params = {
            "api_key": self.settings.value("api/embedding_api_key", ""),
            "knowledge_base_path": self.settings.value("paths/knowledge_base_path", "")
        }
        
        self.start_rag_operation("get_status", params)
    
    def add_single_entry(self):
        """Add single entry"""
        if not all([
            self.category_combo.currentText(),
            self.error_type_edit.text().strip(),
            self.code_snippet_edit.toPlainText().strip(),
            self.error_desc_edit.toPlainText().strip()
        ]):
            QMessageBox.warning(self, "Input Error", "Please fill in all required fields")
            return
        
        entry_config = {
            "category": self.category_combo.currentText(),
            "error_type": self.error_type_edit.text().strip(),
            "code_snippet": self.code_snippet_edit.toPlainText().strip(),
            "error_description": self.error_desc_edit.toPlainText().strip(),
            "additional_info": self.additional_info_edit.toPlainText().strip()
        }
        
        auto_rebuild = self.auto_rebuild_index_check.isChecked()
        
        params = {
            "api_key": self.settings.value("api/embedding_api_key", ""),
            "knowledge_base_path": self.settings.value("paths/knowledge_base_path", ""),
            "entry_config": entry_config,
            "auto_rebuild_index": auto_rebuild
        }
        
        self.start_rag_operation("add_single_entry_with_rebuild", params)
    
    def clear_single_form(self):
        """Clear single entry form"""
        self.category_combo.setCurrentIndex(0)
        self.error_type_edit.clear()
        self.code_snippet_edit.clear()
        self.error_desc_edit.clear()
        self.additional_info_edit.clear()
    
    def load_json_template(self):
        """Load JSON template"""
        template = [
            {
                "category": "Error Code",
                "error_type": "Wrong Vehicle Position variable assignment",
                "code_snippet": '''if(FR_wheel_brake_req)
{
    Loc_CM_vRef_VehX = WheelSpeed_FL;  // Error: Should use WheelSpeed_FR
    Loc_CM_iTAS_SasInCor = SasInCor4BrakeOnly;
    Loc_CM_iTAS_WhlCtrlReq += iTAS_WhlCtrl_FR;
    Loc_RequestWhlNum = Loc_RequestWhlNum + 1;
}''',
                "error_description": "When processing front right wheel brake request, incorrectly used front left wheel speed variable WheelSpeed_FL, should use corresponding WheelSpeed_FR. This error causes wheel position mapping inconsistency, affecting brake control precision.",
                "additional_info": "This is a typical wheel variable mapping error, common when copying and pasting code and forgetting to modify variable names. Fix by changing WheelSpeed_FL to WheelSpeed_FR."
            }
        ]
        
        self.json_edit.setPlainText(json.dumps(template, indent=2, ensure_ascii=False))
    
    def load_json_file(self):
        """Load JSON file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load JSON File", "", "JSON Files (*.json);;All Files (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.json_edit.setPlainText(content)
                self.append_log(f"Loaded JSON file: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Load Failed", f"Failed to load JSON file:\n{str(e)}")
    
    def save_json_file(self):
        """Save JSON file"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save JSON File", "", "JSON Files (*.json);;All Files (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.json_edit.toPlainText())
                self.append_log(f"Saved JSON file: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Save Failed", f"Failed to save JSON file:\n{str(e)}")
    
    def add_batch_entries(self):
        """Batch add entries"""
        try:
            json_text = self.json_edit.toPlainText().strip()
            entries_config = json.loads(json_text)
            
            if not isinstance(entries_config, list):
                QMessageBox.warning(self, "Format Error", "JSON format should be an array")
                return
            
            if not entries_config:
                QMessageBox.warning(self, "Empty Content", "No entries to add")
                return
            
            auto_rebuild = self.batch_auto_rebuild_check.isChecked()
            
            params = {
                "api_key": self.settings.value("api/embedding_api_key", ""),
                "knowledge_base_path": self.settings.value("paths/knowledge_base_path", ""),
                "entries_config": entries_config,
                "auto_rebuild_index": auto_rebuild
            }
            
            self.start_rag_operation("add_batch_entries_with_rebuild", params)
            
        except json.JSONDecodeError as e:
            QMessageBox.critical(self, "JSON Error", f"JSON format error:\n{str(e)}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Batch addition failed:\n{str(e)}")
    
    def set_search_query(self, query):
        """Set search query"""
        self.search_edit.setText(query)
        self.perform_search()
    
    def perform_search(self):
        """Perform search"""
        query = self.search_edit.text().strip()
        if not query:
            QMessageBox.information(self, "Notice", "Please enter search keywords")
            return
        
        params = {
            "api_key": self.settings.value("api/embedding_api_key", ""),
            "knowledge_base_path": self.settings.value("paths/knowledge_base_path", ""),
            "query": query,
            "top_k": self.search_k_spin.value()
        }
        
        self.start_rag_operation("search", params)
    
    def start_rag_operation(self, action: str, params: Dict[str, Any]):
        """Start RAG operation"""
        if self.rag_worker and self.rag_worker.isRunning():
            QMessageBox.warning(self, "Operation in Progress", "Please wait for current operation to complete")
            return
        
        self.rag_worker = RAGWorker(action, params)
        
        self.rag_worker.status_signal.connect(self.append_log)
        self.rag_worker.progress_signal.connect(self.update_progress)
        self.rag_worker.finished_signal.connect(self.on_rag_operation_finished)
        self.rag_worker.entry_added_signal.connect(self.on_entry_added)
        
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        self.rag_worker.start()
    
    def update_progress(self, value: int, text: str):
        """Update progress"""
        self.progress_bar.setValue(value)
        if text:
            self.append_log(text)
    
    def on_entry_added(self, message: str):
        """Entry addition completed"""
        self.append_log(message)
        self.clear_single_form()
    
    def on_rag_operation_finished(self, success: bool, message: str, data: Dict[str, Any]):
        """RAG operation completed callback"""
        self.progress_bar.setVisible(False)
        
        if success:
            self.append_log(f"Operation successful: {message}")
            
            if "status" in data:
                self.display_status(data["status"])
            elif "results" in data:
                self.display_search_results(data["results"])
            elif "deleted_count" in data:
                QTimer.singleShot(500, self.force_refresh_entries)
            
            if "added" in message or "imported" in message or "rebuilt" in message:
                self.append_log("Refreshing entry list...")
                QTimer.singleShot(1000, self.force_refresh_entries)
                
                if "single entry" in message:
                    self.clear_single_form()
            
        else:
            self.append_log(f"Operation failed: {message}")
            QMessageBox.critical(self, "Operation Failed", message)
    
    def display_status(self, status: Dict[str, Any]):
        """Display knowledge base status"""
        status_text = f"""Knowledge Base Status Report
=====================================

📊 Basic Information:
   Total Entries: {status.get('total_entries', 0)}
   Unique Hashes: {status.get('unique_hashes', 0)}

🗂️ File Status:
   Index File: {'✅ Exists' if status.get('index_file_exists') else '❌ Not Found'}
   Documents File: {'✅ Exists' if status.get('documents_file_exists') else '❌ Not Found'}
   Metadata File: {'✅ Exists' if status.get('metadata_file_exists') else '❌ Not Found'}

🔍 Index Status:
   Memory Index: {'✅ Loaded' if status.get('has_index') else '❌ Not Loaded'}

⏰ Time Information:
   Last Updated: {datetime.fromtimestamp(status.get('last_updated', 0)).strftime('%Y-%m-%d %H:%M:%S') if status.get('last_updated') else 'Never updated'}
   Current Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        categories = status.get('categories', {})
        if categories:
            status_text += "\n\n📂 Category Statistics:\n"
            for category, error_types in categories.items():
                status_text += f"   {category}:\n"
                for error_type, count in error_types.items():
                    status_text += f"     - {error_type}: {count} entries\n"
        
        self.status_display.setText(status_text)
    
    def display_search_results(self, results: List[Dict[str, Any]]):
        """Display search results"""
        if not results:
            self.search_results.setText("❌ No similar entries found")
            return
        
        result_text = f"Search Results ({len(results)} entries):\n\n"
        
        for i, result in enumerate(results, 1):
            result_text += f"📋 Result {i} (Similarity Score: {result.get('similarity_score', 0):.4f})\n"
            result_text += f"Category: {result.get('category', '')}\n"
            result_text += f"Error Type: {result.get('error_type', '')}\n"
            result_text += f"Error Description: {result.get('error_description', '')}\n"
            result_text += f"Entry ID: {result.get('id', 'N/A')[:12]}...\n"
            result_text += f"\nCode Snippet:\n{result.get('code_snippet', 'No code')[:200]}...\n"
            result_text += "\n" + "="*50 + "\n\n"
        
        self.search_results.setText(result_text)
    
    def append_log(self, message: str):
        """Append log message"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        self.status_text.append(formatted_message)
        
        cursor = self.status_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.status_text.setTextCursor(cursor)
# ==================== Settings Dialog (Keep original) ====================

class SettingsDialog(QDialog):
    """Settings Dialog - Enhanced version with RAG configuration"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("System Settings")
        self.setFixedSize(900, 750)
        self.settings = QSettings('AscetAgent', 'AscetAgentv3')
        self.init_ui()
        QTimer.singleShot(100, self.load_settings)
        # self.load_settings()
    
    def init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)
        
        self.tab_widget = QTabWidget()
        
        self.tab_widget.tabBar().setExpanding(False)  # 不强制展开填满
        self.tab_widget.tabBar().setUsesScrollButtons(True)  # 如果太多可以滚动
    
        # 设置标签页样式，调小字体
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 2px solid #dee2e6;
                background-color: #ffffff;
                border-radius: 8px;
                margin-top: -1px;
            }
            QTabBar::tab {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f8f9fa, stop:1 #e9ecef);
                border: 1px solid #dee2e6;
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                padding: 8px 20px;
                margin-right: 3px;
                font-size: 8pt;  /* 从9pt改为8pt */
                font-weight: 500;
                color: #6c757d;
                min-width: 150px;
            }
            QTabBar::tab:selected {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ffffff, stop:1 #f8f9fa);
                color: #4dabf7;
                border-color: #4dabf7;
                font-weight: 600;
            }
            QTabBar::tab:hover:!selected {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ffffff, stop:1 #f1f3f4);
                color: #495057;
            }
        """)
        self.create_api_tab()
        self.create_rag_tab()
        self.create_paths_tab()
        self.create_ascet_tab()
        self.create_advanced_tab()
        
        layout.addWidget(self.tab_widget)
        
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.Apply
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        button_box.button(QDialogButtonBox.Apply).clicked.connect(self.apply_settings)
        
        layout.addWidget(button_box)
    
   

    def create_ascet_tab(self):
        """Create ASCET configuration tab - 确保所有组件正确创建"""
        try:
            ascet_widget = QWidget()
            ascet_layout = QFormLayout(ascet_widget)
            
            # 确保这些组件被正确创建和添加到实例
            self.diagram_name_edit = QLineEdit()
            self.diagram_name_edit.setPlaceholderText("Main")
            ascet_layout.addRow("Default Diagram Name:", self.diagram_name_edit)
            
            self.method_name_edit = QLineEdit()
            self.method_name_edit.setPlaceholderText("calc")
            ascet_layout.addRow("Default Method Name:", self.method_name_edit)
            
            self.scan_timeout_spin = QSpinBox()
            self.scan_timeout_spin.setRange(30, 3600)
            self.scan_timeout_spin.setValue(300)
            self.scan_timeout_spin.setSuffix(" seconds")
            ascet_layout.addRow("Scan Timeout:", self.scan_timeout_spin)
            
            # 确保tab被正确添加
            self.tab_widget.addTab(ascet_widget, "ASCET Configuration")
            
            print("ASCET tab created successfully")  # 调试信息
            
        except Exception as e:
            print(f"Error creating ASCET tab: {e}")
            # 创建占位符组件以防止属性错误
            self.diagram_name_edit = QLineEdit()
            self.method_name_edit = QLineEdit()
            self.scan_timeout_spin = QSpinBox()

    def create_api_tab(self):
        """Create API configuration tab"""
        api_widget = QWidget()
        api_layout = QVBoxLayout(api_widget)
        
        api_status_group = QGroupBox("API Status")
        api_status_layout = QVBoxLayout(api_status_group)
        
        self.api_status_label = QLabel("Click 'Check API' button to verify API connection status")
        self.api_status_label.setWordWrap(True)
        self.check_api_btn = QPushButton("Check API")
        self.check_api_btn.clicked.connect(self.check_api_status)
        
        api_status_layout.addWidget(self.api_status_label)
        api_status_layout.addWidget(self.check_api_btn)
        
        api_layout.addWidget(api_status_group)
        
        # 添加模型配置组
        model_group = QGroupBox("AI Model Configuration")
        model_layout = QFormLayout(model_group)
        
        self.model_type_combo = QComboBox()
        self.model_type_combo.addItems([
            "gpt5-mini", 
            "gpt-oss-120b", 
            "DeepSeek-r1-0528-fp16-671b",
            
        ])
        self.model_type_combo.setToolTip("Select the AI model type for analysis")
        model_layout.addRow("Model Type:", self.model_type_combo)
        
        api_layout.addWidget(model_group)
        
        deepseek_group = QGroupBox("API Configuration")
        deepseek_layout = QFormLayout(deepseek_group)
        
        self.deepseek_api_key_edit = QLineEdit()
        self.deepseek_api_key_edit.setEchoMode(QLineEdit.Password)
        self.deepseek_api_key_edit.setPlaceholderText("Enter DeepSeek API key")
        deepseek_layout.addRow("API Key:", self.deepseek_api_key_edit)
        
        self.deepseek_api_url_edit = QLineEdit()
        self.deepseek_api_url_edit.setPlaceholderText("http://10.161.112.104:3000/v1")
        deepseek_layout.addRow("API URL:", self.deepseek_api_url_edit)
        
        # self.deepseek_model_edit = QLineEdit()
        # self.deepseek_model_edit.setPlaceholderText("DeepSeek-r1-0528-fp16-671b")
        # # deepseek_layout.addRow("Model Name:", self.deepseek_model_edit)
        
        api_layout.addWidget(deepseek_group)
        
        self.tab_widget.addTab(api_widget, "API Configuration")
    
    def create_rag_tab(self):
        """Create RAG configuration tab"""
        rag_widget = QWidget()
        rag_layout = QVBoxLayout(rag_widget)
        
        rag_status_group = QGroupBox("RAG Status")
        rag_status_layout = QVBoxLayout(rag_status_group)
        
        self.rag_status_label = QLabel("RAG knowledge base not initialized")
        self.rag_status_label.setWordWrap(True)
        
        self.check_rag_btn = QPushButton("Check RAG Status")
        self.check_rag_btn.clicked.connect(self.check_rag_status)
        
        self.open_rag_manager_btn = QPushButton("Open RAG Manager")
        self.open_rag_manager_btn.clicked.connect(self.open_rag_manager)
        
        rag_status_layout.addWidget(self.rag_status_label)
        rag_status_layout.addWidget(self.check_rag_btn)
        rag_status_layout.addWidget(self.open_rag_manager_btn)
        
        rag_layout.addWidget(rag_status_group)
        
        embedding_group = QGroupBox("Embedding Vector API Configuration")
        embedding_layout = QFormLayout(embedding_group)
        
        self.embedding_api_key_edit = QLineEdit()
        self.embedding_api_key_edit.setEchoMode(QLineEdit.Password)
        self.embedding_api_key_edit.setPlaceholderText("Enter embedding vector API key")
        embedding_layout.addRow("API Key:", self.embedding_api_key_edit)
        
        self.embedding_api_url_edit = QLineEdit()
        self.embedding_api_url_edit.setPlaceholderText("http://10.161.112.104:3000/v1")
        embedding_layout.addRow("API URL:", self.embedding_api_url_edit)
        
        self.embedding_model_edit = QLineEdit()
        self.embedding_model_edit.setPlaceholderText("text-embedding-3-small")
        embedding_layout.addRow("Model Name:", self.embedding_model_edit)
        
        rag_layout.addWidget(embedding_group)
        
        kb_group = QGroupBox("Knowledge Base Configuration")
        kb_layout = QFormLayout(kb_group)
        
        kb_path_layout = QHBoxLayout()
        self.knowledge_base_path_edit = QLineEdit()
        self.knowledge_base_path_edit.setPlaceholderText("Select RAG knowledge base path")
        kb_browse_btn = QPushButton("Browse...")
        kb_browse_btn.clicked.connect(self.browse_knowledge_base_path)
        kb_path_layout.addWidget(self.knowledge_base_path_edit)
        kb_path_layout.addWidget(kb_browse_btn)
        kb_layout.addRow("Knowledge Base Path:", kb_path_layout)
        
        self.kb_status_label = QLabel("Not Set")
        self.kb_status_label.setWordWrap(True)
        kb_layout.addRow("Status:", self.kb_status_label)
        
        rag_layout.addWidget(kb_group)
        
        self.tab_widget.addTab(rag_widget, "RAG Configuration")
        
    
    def create_paths_tab(self):
        """Create path configuration tab"""
        paths_widget = QWidget()
        paths_layout = QFormLayout(paths_widget)
        
        output_layout = QHBoxLayout()
        self.output_dir_edit = QLineEdit()
        self.output_dir_edit.setPlaceholderText("Select report output directory")
        output_browse_btn = QPushButton("Browse...")
        output_browse_btn.clicked.connect(self.browse_output_dir)
        output_layout.addWidget(self.output_dir_edit)
        output_layout.addWidget(output_browse_btn)
        paths_layout.addRow("Report Output Directory:", output_layout)
        
        cache_layout = QHBoxLayout()
        self.cache_dir_edit = QLineEdit()
        self.cache_dir_edit.setPlaceholderText("Select cache directory")
        cache_browse_btn = QPushButton("Browse...")
        cache_browse_btn.clicked.connect(self.browse_cache_dir)
        cache_layout.addWidget(self.cache_dir_edit)
        cache_layout.addWidget(cache_browse_btn)
        paths_layout.addRow("Cache Directory:", cache_layout)
        
        self.auto_create_dirs_check = QCheckBox("Auto create non-existing directories")
        self.auto_create_dirs_check.setChecked(True)
        paths_layout.addRow("Directory Management:", self.auto_create_dirs_check)
        
        self.tab_widget.addTab(paths_widget, "Path Configuration")
    
    
    
    def create_advanced_tab(self):
        """Create advanced configuration tab"""
        advanced_widget = QWidget()
        advanced_layout = QFormLayout(advanced_widget)
        
        agent_group = QGroupBox("AI Agent Configuration")
        agent_group_layout = QFormLayout(agent_group)
        
        self.auto_cleanup_check = QCheckBox("Auto cleanup failed reports")
        self.auto_cleanup_check.setChecked(True)
        agent_group_layout.addRow("Report Management:", self.auto_cleanup_check)
        
        self.mark_failed_reports_check = QCheckBox("Mark failed reports")
        self.mark_failed_reports_check.setChecked(True)
        agent_group_layout.addRow("", self.mark_failed_reports_check)
        
        self.max_retries_spin = QSpinBox()
        self.max_retries_spin.setRange(1, 10)
        self.max_retries_spin.setValue(2)
        agent_group_layout.addRow("Max Retry Count:", self.max_retries_spin)
        
        log_group = QGroupBox("Log Configuration")
        log_group_layout = QFormLayout(log_group)
        
        self.enable_debug_check = QCheckBox("Enable debug logging")
        log_group_layout.addRow("Debug Mode:", self.enable_debug_check)
        
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["INFO", "DEBUG", "WARNING", "ERROR"])
        log_group_layout.addRow("Log Level:", self.log_level_combo)
        
        advanced_layout.addWidget(agent_group)
        advanced_layout.addWidget(log_group)
        
        self.tab_widget.addTab(advanced_widget, "Advanced Configuration")
    
    def browse_knowledge_base_path(self):
        """Browse knowledge base path"""
        path = QFileDialog.getExistingDirectory(self, "Select RAG Knowledge Base Directory")
        if path:
            self.knowledge_base_path_edit.setText(path)
            self.update_kb_status()
    
    def browse_output_dir(self):
        """Browse output directory"""
        path = QFileDialog.getExistingDirectory(self, "Select Report Output Directory")
        if path:
            self.output_dir_edit.setText(path)
    
    def browse_cache_dir(self):
        """Browse cache directory"""
        path = QFileDialog.getExistingDirectory(self, "Select Cache Directory")
        if path:
            self.cache_dir_edit.setText(path)
    
    def update_kb_status(self):
        """Update knowledge base status"""
        kb_path = self.knowledge_base_path_edit.text()
        if kb_path and os.path.exists(kb_path):
            self.kb_status_label.setText("Path Valid")
            self.kb_status_label.setStyleSheet("color: green;")
        elif kb_path:
            self.kb_status_label.setText("Path Invalid")
            self.kb_status_label.setStyleSheet("color: red;")
        else:
            self.kb_status_label.setText("Not Set")
            self.kb_status_label.setStyleSheet("color: gray;")
    
    def create_directories_if_needed(self):
        """Create necessary directories if auto creation is enabled"""
        if not self.auto_create_dirs_check.isChecked():
            return
        
        paths_to_create = [
            self.output_dir_edit.text(),
            self.cache_dir_edit.text(),
            self.knowledge_base_path_edit.text()
        ]
        
        for path in paths_to_create:
            if path and not os.path.exists(path):
                try:
                    os.makedirs(path, exist_ok=True)
                    print(f"Auto created directory: {path}")
                except Exception as e:
                    print(f"Failed to create directory {path}: {e}")
    
    def check_rag_status(self):
        """Check RAG status"""
        if not RAG_AVAILABLE:
            self.rag_status_label.setText("RAG module unavailable")
            self.rag_status_label.setStyleSheet("color: red;")
            return
        
        try:
            api_key = self.embedding_api_key_edit.text()
            kb_path = self.knowledge_base_path_edit.text()
            
            status_parts = []
            
            if api_key:
                status_parts.append("Embedding Vector API: Configured")
            else:
                status_parts.append("Embedding Vector API: Not Configured")
            
            if kb_path and os.path.exists(kb_path):
                status_parts.append("Knowledge Base Path: Valid")
            else:
                status_parts.append("Knowledge Base Path: Invalid or Not Set")
            
            status_text = "\n".join(status_parts)
            self.rag_status_label.setText(status_text)
            
            if api_key and kb_path and os.path.exists(kb_path):
                self.rag_status_label.setStyleSheet("color: green;")
                QMessageBox.information(self, "RAG Check", "RAG configuration check passed")
            else:
                self.rag_status_label.setStyleSheet("color: orange;")
                QMessageBox.warning(self, "RAG Check", "RAG configuration incomplete, please complete settings")
            
        except Exception as e:
            self.rag_status_label.setStyleSheet("color: red;")
            self.append_status(f"RAG status check failed: {str(e)}")
    
    def open_rag_manager(self):
        """Open RAG manager"""
        if not RAG_AVAILABLE:
            QMessageBox.warning(self, "RAG Unavailable", "RAG module unavailable, cannot open manager")
            return
        
        self.save_settings()
        
        rag_dialog = RAGManagementDialog(self)
        rag_dialog.show()
    
    def check_api_status(self):
        """Check API status"""
        deepseek_key = self.deepseek_api_key_edit.text()
        embedding_key = self.embedding_api_key_edit.text()
        kb_path = self.knowledge_base_path_edit.text()
        
        status_parts = []
        
        if deepseek_key:
            status_parts.append("DeepSeek API Key: Configured")
        else:
            status_parts.append("DeepSeek API Key: Not Configured")
        
        if embedding_key:
            status_parts.append("Embedding Vector API Key: Configured")
        else:
            status_parts.append("Embedding Vector API Key: Not Configured")
        
        if kb_path and os.path.exists(kb_path):
            status_parts.append("RAG Knowledge Base: Path Valid")
        else:
            status_parts.append("RAG Knowledge Base: Path Invalid or Not Set")
        
        if AGENT_AVAILABLE:
            status_parts.append("AI Agent Module: Available")
        else:
            status_parts.append("AI Agent Module: Unavailable")
        
        if RAG_AVAILABLE:
            status_parts.append("RAG Module: Available")
        else:
            status_parts.append("RAG Module: Unavailable")
        
        status_text = "\n".join(status_parts)
        self.api_status_label.setText(status_text)
        
        all_ready = (deepseek_key and embedding_key and 
                    kb_path and os.path.exists(kb_path) and 
                    AGENT_AVAILABLE and RAG_AVAILABLE)
        
        if all_ready:
            QMessageBox.information(self, "API Check", "All component status checks passed, system ready")
        else:
            QMessageBox.warning(self, "API Check", "Issues found, please check related settings")
    
    def load_settings(self):
        """Load settings - 移除版本加载"""
        self.model_type_combo.setCurrentText(
            self.settings.value("api/model_type", "gpt5-mini")
        )
        self.deepseek_api_key_edit.setText(
            self.settings.value("api/deepseek_api_key", "sk-jwVMOs8ac7gNmnBkB57e670f6cBd49B7A126713bF451451b")
        )
        self.deepseek_api_url_edit.setText(
            self.settings.value("api/deepseek_api_url", "http://10.161.112.104:3000/v1")
        )
        
        self.embedding_api_key_edit.setText(
            self.settings.value("api/embedding_api_key", "sk-yAYNtyvvu1JUE8zV0f13A3DdDeC14f6aAf442a81E6C58333")
        )
        self.embedding_api_url_edit.setText(
            self.settings.value("api/embedding_api_url", "http://10.161.112.104:3000/v1")
        )
        self.embedding_model_edit.setText(
            self.settings.value("api/embedding_model", "text-embedding-3-small")
        )
        
        self.knowledge_base_path_edit.setText(
            self.settings.value("paths/knowledge_base_path", r"RAG\code_analysis_knowledge")
        )
        
        self.output_dir_edit.setText(
            self.settings.value("paths/output_dir", "agent_reports")
        )
        self.cache_dir_edit.setText(
            self.settings.value("paths/cache_dir", "embedding_cache")
        )
        self.auto_create_dirs_check.setChecked(
            self.settings.value("paths/auto_create_dirs", True, type=bool)
        )
        

        self.diagram_name_edit.setText(
            self.settings.value("ascet/diagram_name", "Main")
        )
        self.method_name_edit.setText(
            self.settings.value("ascet/method_name", "calc")
        )
        self.scan_timeout_spin.setValue(
            int(self.settings.value("ascet/scan_timeout", 300))
        )
        
        self.auto_cleanup_check.setChecked(
            self.settings.value("agent/auto_cleanup", True, type=bool)
        )
        self.mark_failed_reports_check.setChecked(
            self.settings.value("agent/mark_failed_reports", True, type=bool)
        )
        self.max_retries_spin.setValue(
            int(self.settings.value("agent/max_retries", 2))
        )
        self.enable_debug_check.setChecked(
            self.settings.value("log/enable_debug", False, type=bool)
        )
        self.log_level_combo.setCurrentText(
            self.settings.value("log/level", "INFO")
        )
        
        self.update_kb_status()
    
    def save_settings(self):
        """Save settings"""
        self.create_directories_if_needed()
        self.settings.setValue("api/model_type", self.model_type_combo.currentText())
        self.settings.setValue("api/deepseek_api_key", self.deepseek_api_key_edit.text())
        self.settings.setValue("api/deepseek_api_url", self.deepseek_api_url_edit.text())
        # self.settings.setValue("api/deepseek_model", self.deepseek_model_edit.text())
        
        self.settings.setValue("api/embedding_api_key", self.embedding_api_key_edit.text())
        self.settings.setValue("api/embedding_api_url", self.embedding_api_url_edit.text())
        self.settings.setValue("api/embedding_model", self.embedding_model_edit.text())
        self.settings.setValue("paths/knowledge_base_path", self.knowledge_base_path_edit.text())
        
        self.settings.setValue("paths/output_dir", self.output_dir_edit.text())
        self.settings.setValue("paths/cache_dir", self.cache_dir_edit.text())
        self.settings.setValue("paths/auto_create_dirs", self.auto_create_dirs_check.isChecked())
        
        
        self.settings.setValue("ascet/diagram_name", self.diagram_name_edit.text())
        self.settings.setValue("ascet/method_name", self.method_name_edit.text())
        self.settings.setValue("ascet/scan_timeout", self.scan_timeout_spin.value())
        
        self.settings.setValue("agent/auto_cleanup", self.auto_cleanup_check.isChecked())
        self.settings.setValue("agent/mark_failed_reports", self.mark_failed_reports_check.isChecked())
        self.settings.setValue("agent/max_retries", self.max_retries_spin.value())
        self.settings.setValue("log/enable_debug", self.enable_debug_check.isChecked())
        self.settings.setValue("log/level", self.log_level_combo.currentText())
        
        self.settings.sync()
    
    def apply_settings(self):
        """Apply settings"""
        self.save_settings()
        QMessageBox.information(self, "Settings", "Settings have been saved and applied")
    
    def accept(self):
        """OK button"""
        self.save_settings()
        super().accept()

# ==================== Error Statistics Dialog ====================

class ErrorStatisticsDialog(QDialog):
    """Error statistics display dialog - 修复标签显示问题"""
    
    def __init__(self, statistics_data: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.statistics_data = statistics_data
        self.setWindowTitle("Error Statistics Details")
        self.resize(900, 800)  # 增加窗口宽度以容纳更多标签
        self.init_ui()
    
    def init_ui(self):
        """Initialize UI - 优化标签页显示"""
        layout = QVBoxLayout(self)
        
        overview_group = QGroupBox("Statistics Overview")
        overview_layout = QFormLayout(overview_group)
        
        stats = self.statistics_data.get('error_statistics', {})
        rule_errors = stats.get('rule_errors', 0)
        ai_errors = stats.get('ai_errors', 0)
        total_errors = stats.get('total_errors', 0)
        
        overview_layout.addRow("Rule Detection Errors:", QLabel(str(rule_errors)))
        overview_layout.addRow("AI Detection Errors:", QLabel(str(ai_errors)))
        overview_layout.addRow("Total Errors:", QLabel(str(total_errors)))
        
        layout.addWidget(overview_group)
        
        tab_widget = QTabWidget()
        
        # 优化标签页样式 - 减少最小宽度，启用滚动
        tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 2px solid #dee2e6;
                background-color: #ffffff;
                border-radius: 8px;
                margin-top: -1px;
            }
            QTabBar {
                qproperty-usesScrollButtons: true;
                qproperty-expanding: false;
            }
            QTabBar::tab {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f8f9fa, stop:1 #e9ecef);
                border: 1px solid #dee2e6;
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                padding: 6px 12px;  /* 减少内边距 */
                margin-right: 2px;   /* 减少右边距 */
                font-size: 8pt;      /* 减小字体 */
                font-weight: 500;
                color: #6c757d;
                min-width: 80px;     /* 减少最小宽度 */
                max-width: 150px;    /* 设置最大宽度 */
            }
            QTabBar::tab:selected {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ffffff, stop:1 #f8f9fa);
                color: #4dabf7;
                border-color: #4dabf7;
                font-weight: 600;
            }
            QTabBar::tab:hover:!selected {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ffffff, stop:1 #f1f3f4);
                color: #495057;
            }
            QTabBar::scroller {
                width: 20px;
            }
            QTabBar QToolButton {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 3px;
                margin: 2px;
            }
            QTabBar QToolButton:hover {
                background-color: #e9ecef;
            }
        """)
        
        
        tab_widget.tabBar().setExpanding(False)
        tab_widget.tabBar().setUsesScrollButtons(True)
        
        # 创建标签页 - 使用更短的标题
        if rule_errors > 0:
            rule_tab = self.create_rule_errors_tab(stats.get('rule_error_details', []))
            # 缩短标签文本
            tab_title = f"Rules ({rule_errors})" if rule_errors <= 99 else "Rules (99+)"
            tab_widget.addTab(rule_tab, tab_title)
        
        if ai_errors > 0:
            ai_tab = self.create_ai_errors_tab(stats.get('ai_error_details', []))
            # 缩短标签文本
            tab_title = f"AI ({ai_errors})" if ai_errors <= 99 else "AI (99+)"
            tab_widget.addTab(ai_tab, tab_title)
        
        json_tab = self.create_json_tab()
        tab_widget.addTab(json_tab, "Logs")  # 简化为"JSON"
        
        layout.addWidget(tab_widget)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)
    
    def create_rule_errors_tab(self, rule_errors: List[Dict[str, Any]]) -> QWidget:
        """Create rule errors tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 添加标题说明
        title_label = QLabel(f"Rule Detection Errors ({len(rule_errors)} total)")
        title_label.setStyleSheet("font-weight: bold; font-size: 10pt; color: #495057; margin-bottom: 5px;")
        layout.addWidget(title_label)
        
        table = QTableWidget()
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(["Error Type", "Error Description"])
        table.setRowCount(len(rule_errors))
        
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setWordWrap(True)
        table.verticalHeader().setDefaultSectionSize(80)
        
        for i, error in enumerate(rule_errors):
            table.setItem(i, 0, QTableWidgetItem(error.get('type', '')))
            table.setItem(i, 1, QTableWidgetItem(error.get('message', '')))
        
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        
        layout.addWidget(table)
        return widget
    
    def create_ai_errors_tab(self, ai_errors: List[Dict[str, Any]]) -> QWidget:
        """Create AI errors tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 添加标题说明
        title_label = QLabel(f"AI Detection Errors ({len(ai_errors)} total)")
        title_label.setStyleSheet("font-weight: bold; font-size: 10pt; color: #495057; margin-bottom: 5px;")
        layout.addWidget(title_label)
        
        table = QTableWidget()
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(["Error Type", "Error Description"])
        table.setRowCount(len(ai_errors))

        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setWordWrap(True)
        table.verticalHeader().setDefaultSectionSize(80)
        
        for i, error in enumerate(ai_errors):
            table.setItem(i, 0, QTableWidgetItem(error.get('type', '')))
            table.setItem(i, 1, QTableWidgetItem(error.get('message', '')))
        
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        
        layout.addWidget(table)
        return widget
    
    def create_json_tab(self) -> QWidget:
        """Create JSON format tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 添加标题说明
        title_label = QLabel("JSON Format - Complete Statistics Data")
        title_label.setStyleSheet("font-weight: bold; font-size: 10pt; color: #495057; margin-bottom: 5px;")
        layout.addWidget(title_label)
        
        json_text = QTextEdit()
        json_text.setReadOnly(True)
        json_text.setFont(QFont("Courier New", 9))
        
        try:
            formatted_json = json.dumps(self.statistics_data, ensure_ascii=False, indent=2)
            json_text.setText(formatted_json)
        except Exception as e:
            json_text.setText(f"JSON formatting failed: {str(e)}")
        
        layout.addWidget(json_text)
        
        copy_btn = QPushButton("Copy JSON")
        copy_btn.clicked.connect(lambda: QApplication.clipboard().setText(json_text.toPlainText()))
        layout.addWidget(copy_btn)
        
        return widget
# ==================== Other Helper Classes ====================

class SelectableTreeWidget(QTreeWidget):
    """Tree widget supporting box selection and select all"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        
        self.select_all_shortcut = QShortcut(QKeySequence.SelectAll, self)
        self.select_all_shortcut.activated.connect(self.selectAll)
    
    def selectAll(self):
        """Select all items"""
        for i in range(self.topLevelItemCount()):
            self.select_all_recursive(self.topLevelItem(i))
    
    def select_all_recursive(self, item):
        """Recursively select all child items"""
        item.setSelected(True)
        for i in range(item.childCount()):
            self.select_all_recursive(item.child(i))

class EnhancedListWidgetItem(QListWidgetItem):
    """Enhanced list item supporting class name display"""
    
    def __init__(self, class_path: str, show_class_name: bool = True):
        self.class_path = class_path
        self.class_name = self.extract_class_name(class_path)
        
        if show_class_name:
            display_text = self.class_name
        else:
            display_text = class_path
        
        super().__init__(display_text)
        
        self.setToolTip(f"Full path: {class_path}")
        self.setData(Qt.UserRole, class_path)
    
    @staticmethod
    def extract_class_name(class_path: str) -> str:
        """Extract class name from full path"""
        if not class_path:
            return ""
        
        parts = class_path.replace('\\', '/').split('/')
        parts = [p for p in parts if p.strip()]
        
        if parts:
            return parts[-1]
        else:
            return class_path

class ReportPreviewDialog(QDialog):
    """Report preview dialog"""
    
    def __init__(self, report_path: str, parent=None):
        super().__init__(parent)
        self.report_path = report_path
        self.setWindowTitle(f"Report Preview - {os.path.basename(report_path)}")
        self.resize(1000, 700)
        self.init_ui()
        self.load_report()
    
    def init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)
        
        toolbar_layout = QHBoxLayout()
        
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.load_report)
        
        self.export_html_btn = QPushButton("Export HTML")
        self.export_html_btn.clicked.connect(self.export_html)
        
        self.open_file_btn = QPushButton("Open File")
        self.open_file_btn.clicked.connect(self.open_file)
        
        toolbar_layout.addWidget(self.refresh_btn)
        toolbar_layout.addWidget(self.export_html_btn)
        toolbar_layout.addWidget(self.open_file_btn)
        toolbar_layout.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        toolbar_layout.addWidget(close_btn)
        
        layout.addLayout(toolbar_layout)
        
        if MARKDOWN_AVAILABLE:
            self.content_browser = QTextBrowser()
            self.content_browser.setOpenExternalLinks(True)
        else:
            self.content_browser = QTextEdit()
            self.content_browser.setReadOnly(True)
        
        layout.addWidget(self.content_browser)
    
    def load_report(self):
        """Load report content"""
        try:
            if not os.path.exists(self.report_path):
                self.content_browser.setText("Report file does not exist")
                return
            
            with open(self.report_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if MARKDOWN_AVAILABLE and isinstance(self.content_browser, QTextBrowser):
                html = markdown.markdown(content, extensions=['tables', 'fenced_code', 'codehilite'])
                
                styled_html = f"""
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 20px; }}
                    h1, h2, h3 {{ color: #2c3e50; }}
                    h1 {{ border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
                    h2 {{ border-bottom: 1px solid #bdc3c7; padding-bottom: 5px; }}
                    code {{ 
                        background-color: #f7f7f7; 
                        padding: 2px 4px; 
                        border-radius: 4px; 
                        font-family: 'Courier New', monospace;
                    }}
                    pre {{ 
                        background-color: #f7f7f7; 
                        padding: 15px; 
                        border-radius: 4px; 
                        overflow-x: auto;
                        border-left: 4px solid #3498db;
                    }}
                    blockquote {{ 
                        background-color: #f9f9f9; 
                        border-left: 4px solid #ccc; 
                        margin: 15px 0; 
                        padding: 5px 15px; 
                    }}
                    table {{
                        border-collapse: collapse;
                        width: 100%;
                        margin: 15px 0;
                    }}
                    table, th, td {{
                        border: 1px solid #ddd;
                    }}
                    th, td {{
                        padding: 8px;
                        text-align: left;
                    }}
                    th {{
                        background-color: #f2f2f2;
                    }}
                    .success {{ color: #27ae60; }}
                    .warning {{ color: #f39c12; }}
                    .error {{ color: #e74c3c; }}
                </style>
                {html}
                """
                
                self.content_browser.setHtml(styled_html)
            else:
                self.content_browser.setText(content)
                
        except Exception as e:
            error_msg = f"Failed to load report: {str(e)}"
            self.content_browser.setText(error_msg)
    
    def export_html(self):
        """Export HTML"""
        try:
            if not MARKDOWN_AVAILABLE:
                QMessageBox.warning(self, "Warning", "Markdown module unavailable, cannot export HTML")
                return
            
            base_name = os.path.splitext(self.report_path)[0]
            html_path, _ = QFileDialog.getSaveFileName(
                self, "Save HTML File", f"{base_name}.html", "HTML Files (*.html)"
            )
            
            if not html_path:
                return
            
            with open(self.report_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            html = markdown.markdown(content, extensions=['tables', 'fenced_code', 'codehilite'])
            
            full_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>{os.path.basename(self.report_path)}</title>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 40px; }}
                    h1, h2, h3 {{ color: #2c3e50; }}
                    h1 {{ border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
                    h2 {{ border-bottom: 1px solid #bdc3c7; padding-bottom: 5px; }}
                    code {{ background-color: #f7f7f7; padding: 2px 4px; border-radius: 4px; }}
                    pre {{ background-color: #f7f7f7; padding: 15px; border-radius: 4px; overflow-x: auto; }}
                    blockquote {{ background-color: #f9f9f9; border-left: 4px solid #ccc; margin: 15px 0; padding: 5px 15px; }}
                    table {{ border-collapse: collapse; width: 100%; margin: 15px 0; }}
                    table, th, td {{ border: 1px solid #ddd; }}
                    th, td {{ padding: 8px; text-align: left; }}
                    th {{ background-color: #f2f2f2; }}
                </style>
            </head>
            <body>
                {html}
            </body>
            </html>
            """
            
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(full_html)
            
            QMessageBox.information(self, "Success", f"HTML file saved to:\n{html_path}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export HTML:\n{str(e)}")
    
    def open_file(self):
        """Open file"""
        try:
            os.startfile(self.report_path)
        except Exception as e:
            QMessageBox.warning(self, "Warning", f"Unable to open file:\n{str(e)}")

# ==================== Worker Thread Classes (Remove progress bar functionality) ====================

class DatabaseScanWorker(QThread):
    """Database scanning worker thread"""
    
    status_signal = Signal(str)
    finished_signal = Signal(bool, str, dict)
    progress_signal = Signal(int, str)  # Keep scan progress signal
    
    def __init__(self, action: str, params: Dict[str, Any]):
        super().__init__()
        self.action = action
        self.params = params
        self.scanner = None
    
    def run(self):
        """Run scanning task"""
        try:
            try:
                import pythoncom
                pythoncom.CoInitialize()
            except ImportError:
                pass
            except Exception as e:
                self.status_signal.emit(f"COM initialization warning: {str(e)}")
            
            if not SCANNER_AVAILABLE:
                self.finished_signal.emit(False, "ASCET scanner module unavailable", {})
                return
            
            version = self.params.get("version", "6.1.4")
            debug = self.params.get("debug", False)
            
            self.status_signal.emit("Initializing ASCET scanner...")
            self.progress_signal.emit(10, "Initializing scanner...")
            self.scanner = ASCETStructureScannerAPI(version=version, debug=debug)
            
            self.status_signal.emit("Connecting to ASCET database...")
            self.progress_signal.emit(20, "Connecting to database...")
            connect_result = self.scanner.connect()
            
            if not connect_result.success:
                self.finished_signal.emit(False, connect_result.error or connect_result.message, {})
                return
            
            self.status_signal.emit(f"Connected to database: {connect_result.data.get('database_name', 'Unknown')}")
            
            if self.action == "scan_all":
                self._scan_all_classes()
            elif self.action == "scan_folder":
                self._scan_folder()
            else:
                self.finished_signal.emit(False, f"Unknown operation: {self.action}", {})
                
        except Exception as e:
            error_msg = f"Error occurred during scanning: {str(e)}"
            self.status_signal.emit(error_msg)
            self.finished_signal.emit(False, error_msg, {})
        finally:
            try:
                import pythoncom
                pythoncom.CoUninitialize()
            except ImportError:
                pass
            except Exception:
                pass
    
    def _scan_all_classes(self):
        """Scan all classes and export diagrams"""
        self.status_signal.emit("Starting full database scan...")
        self.progress_signal.emit(30, "Scanning database structure...")
        
        # 从设置中获取过滤参数，确保使用过滤
        diagram_name = self.params.get("diagram_name", "Main")
        method_name = self.params.get("method_name", "calc")
        require_calc = True  # 强制启用过滤
        
        # 添加调试信息
        self.status_signal.emit(f"Scanning with filter: {diagram_name}/{method_name} method required")
        
        # 传递过滤参数
        scan_result = self.scanner.scan_all_classes(
            require_calc=require_calc,
            diagram_name=diagram_name,
            method_name=method_name
        )
        
        if scan_result.success:
            self.status_signal.emit("Building structure tree...")
            self.progress_signal.emit(80, "Building structure tree...")
            
            tree_result = self.scanner.build_structure_tree()
            
            # Export and scan diagrams
            diagram_files = []
            self.status_signal.emit("Exporting and scanning diagrams...")
            self.progress_signal.emit(85, "Exporting diagrams...")
            
            export_dir = self.export_all_diagrams()
            if export_dir:
                self.progress_signal.emit(90, "Scanning diagrams...")
                diagram_files = self.scan_diagram_files(export_dir)
            
            self.status_signal.emit("Scan completed")
            self.progress_signal.emit(100, "Scan completed")
            
            result_data = {
                "class_paths": scan_result.data.get("class_paths", []),
                "structure_tree": tree_result.data.get("structure_tree", {}) if tree_result.success else {},
                "statistics": self.scanner.get_statistics(),
                "diagram_files": diagram_files
            }
            
            self.finished_signal.emit(True, f"Filtered scan completed: {scan_result.classes_found} classes found, {len(diagram_files)} diagrams found", result_data)
        else:
            self.finished_signal.emit(False, scan_result.error or scan_result.message, {})
    
    def _scan_folder(self):
        """Scan specified folder and export diagrams"""
        folder_path = self.params.get("folder_path", "")
        
        if not folder_path:
            self.finished_signal.emit(False, "No folder path specified", {})
            return
        
        self.status_signal.emit(f"Scanning folder: {folder_path}")
        self.progress_signal.emit(30, "Scanning folder...")
        
        scan_result = self.scanner.scan_folder(folder_path)
        
        if scan_result.success:
            self.status_signal.emit("Building structure tree...")
            self.progress_signal.emit(80, "Building structure tree...")
            
            tree_result = self.scanner.build_structure_tree(folder_path)
            
            # Export and scan diagrams
            diagram_files = []
            self.status_signal.emit("Exporting and scanning diagrams...")
            self.progress_signal.emit(85, "Exporting diagrams...")
            
            export_dir = self.export_all_diagrams()
            if export_dir:
                self.progress_signal.emit(90, "Scanning diagrams...")
                diagram_files = self.scan_diagram_files(export_dir)
            
            self.status_signal.emit("Scan completed")
            self.progress_signal.emit(100, "Scan completed")
            
            result_data = {
                "class_paths": scan_result.data.get("class_paths", []),
                "structure_tree": tree_result.data.get("structure_tree", {}) if tree_result.success else {},
                "folder_path": folder_path,
                "diagram_files": diagram_files
            }
            
            self.finished_signal.emit(True, f"Folder scan completed, found {scan_result.classes_found} classes, {len(diagram_files)} diagrams found", result_data)
        else:
            self.finished_signal.emit(False, scan_result.error or scan_result.message, {})
    
    # ==================== Diagram Export & Scanning Methods ====================
    
    def get_ascet_instance(self):
        """Get ASCET COM instance"""
        try:
            return win32com.client.GetActiveObject("Ascet.Ascet.6.1.5")
        except:
            try:
                return win32com.client.Dispatch("Ascet.Ascet.6.1.5")
            except:
                return None
    
    def export_all_diagrams(self) -> Optional[str]:
        """Export all diagrams from ASCET database to temp location"""
        if not WIN32COM_AVAILABLE:
            self.status_signal.emit("Win32COM not available for diagram export")
            return None
        
        try:
            self.status_signal.emit("Initializing ASCET COM connection for diagram export...")
            ascet = self.get_ascet_instance()
            if not ascet:
                self.status_signal.emit("Could not connect to ASCET")
                return None
            
            db = ascet.GetCurrentDataBase()
            if not db:
                self.status_signal.emit("Could not get database from ASCET")
                return None
            
            # Create temp directory for exports
            temp_base = tempfile.gettempdir()
            output_dir = os.path.join(temp_base, "ASCET_Auto_Exports")
            
            # Clean old cache if exists
            if os.path.exists(output_dir):
                try:
                    shutil.rmtree(output_dir)
                except:
                    pass
            os.makedirs(output_dir, exist_ok=True)
            
            self.status_signal.emit("Exporting diagrams from database...")
            
            # Get all folders
            try:
                folders = db.GetAllFolders()
            except:
                try:
                    folders = db.GetAllAscetFolders()
                except:
                    folders = []
            
            if folders:
                folder = folders[0]
                safe_name = folder.GetName() if hasattr(folder, 'GetName') else 'Database'
                safe_name = safe_name[:30] if safe_name else 'Database'
                xml_path = os.path.normpath(os.path.join(output_dir, f"{safe_name}_MasterDatabase.xml"))
                
                try:
                    folder.ExportXMLToFile(xml_path, True)
                    self.status_signal.emit(f"Exported diagrams to {xml_path}")
                    return output_dir
                except Exception as e:
                    self.status_signal.emit(f"Export error: {str(e)}")
                    return None
            else:
                self.status_signal.emit("No folders found in database")
                return None
                
        except Exception as e:
            self.status_signal.emit(f"Diagram export failed: {str(e)}")
            return None
    
    def scan_diagram_files(self, export_dir: str) -> List[dict]:
        """Scan exported directory for diagram files (.amd files)
        Returns list of dicts with diagram_name, file_path, and relative_path"""
        diagram_files = []
        
        try:
            if not os.path.exists(export_dir):
                return diagram_files
            
            self.status_signal.emit("Scanning for diagram files...")
            
            for root_dir, _, files in os.walk(export_dir):
                for file_name in files:
                    if file_name.endswith('.amd'):
                        fpath = os.path.join(root_dir, file_name)
                        try:
                            with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read()
                                # Filter for valid diagram files
                                if '<SimpleElement' in content or '<Connection' in content:
                                    clean_name = file_name.replace('.specification.amd', '').replace('.dp.amd', '').replace('.amd', '')
                                    
                                    # Calculate relative path from export_dir
                                    rel_path = os.path.relpath(fpath, export_dir)
                                    
                                    diagram_files.append({
                                        'name': clean_name,
                                        'file_path': fpath,
                                        'relative_path': rel_path
                                    })
                        except:
                            pass
            
            self.status_signal.emit(f"Found {len(diagram_files)} diagram files")
            return diagram_files
            
        except Exception as e:
            self.status_signal.emit(f"Diagram scanning error: {str(e)}")
            return []

class AgentWorker(QThread):
    """AI Agent worker thread with detailed logging"""
    
    status_signal = Signal(str)
    agent_step_signal = Signal(str)  # 新增：Agent步骤信号
    finished_signal = Signal(bool, dict)

    def __init__(self, config: Dict[str, Any]):
        super().__init__()
        self.config = config
        self.timeout = int(self.config.get('per_class_timeout_sec', 180))
        self.active_proc: Optional["multiprocessing.Process"] = None
        self._should_stop = False

    def stop(self):
        self._should_stop = True
        if self.active_proc and self.active_proc.is_alive():
            try:
                self.active_proc.terminate()
            except Exception:
                pass

    def run(self):
        try:
            try:
                import pythoncom
                pythoncom.CoInitialize()
            except Exception as e:
                self.status_signal.emit(f"COM initialization warning: {str(e)}")

            if not AGENT_AVAILABLE:
                self.finished_signal.emit(False, {
                    "status": "error",
                    "error_message": "AI Agent module unavailable"
                })
                return

            mode = self.config.get("mode", "agent")
            class_path = self.config.get("class_path", "")
            class_name = EnhancedListWidgetItem.extract_class_name(class_path) if class_path else "Unknown"

            self.status_signal.emit(f"Starting {mode} mode analysis for: {class_name}")

            # 启用详细日志
            verbose_config = self.config.copy()
            verbose_config['enable_agent_logging'] = True

            ctx = multiprocessing.get_context('spawn')
            q = ctx.Queue()
            p = ctx.Process(target=_run_review_entry_subproc_with_logging, args=(verbose_config, mode, q))
            self.active_proc = p
            p.start()

            start_ts = time.time()
            result_obj: Optional[Dict[str, Any]] = None
            timed_out = False

            while p.is_alive():
                if self._should_stop:
                    self.status_signal.emit("Stop requested, terminating current analysis...")
                    try:
                        p.terminate()
                    except Exception:
                        pass
                    p.join(5)
                    break

                try:
                    tag, payload = q.get_nowait()
                    
                    if tag == 'agent_log':
                        # Agent执行日志
                        self.agent_step_signal.emit(payload)
                    elif tag == 'status':
                        # 普通状态消息
                        self.status_signal.emit(payload)
                    elif tag == 'ok':
                        # 最终结果
                        result_obj = payload
                        try:
                            p.join(0.5)
                        except Exception:
                            pass
                        break
                    elif tag == 'err':
                        # 错误结果
                        result_obj = payload
                        try:
                            p.join(0.5)
                        except Exception:
                            pass
                        break
                        
                except Exception:
                    pass

                if time.time() - start_ts > self.timeout:
                    timed_out = True
                    self.status_signal.emit(f"Timeout: {class_name} (> {self.timeout}s). Killing process.")
                    try:
                        p.terminate()
                    except Exception:
                        pass
                    p.join(5)
                    break

                time.sleep(0.1)

            if result_obj is None and not timed_out and not self._should_stop:
                try:
                    tag, payload = q.get(timeout=1.0)
                    if tag == 'ok' or tag == 'err':
                        result_obj = payload
                    # 处理剩余的日志消息
                    while True:
                        try:
                            tag, payload = q.get_nowait()
                            if tag == 'agent_log':
                                self.agent_step_signal.emit(payload)
                            elif tag == 'status':
                                self.status_signal.emit(payload)
                        except:
                            break
                except Exception:
                    pass

            self.active_proc = None

            if self._should_stop:
                self.finished_signal.emit(False, {
                    "status": "terminated",
                    "error_message": "User stopped single analysis"
                })
                return

            if timed_out:
                self.finished_signal.emit(False, {
                    "status": "timeout",
                    "error_message": f"Per-class timeout ({self.timeout}s)"
                })
                return

            if not result_obj:
                self.finished_signal.emit(False, {
                    "status": "error",
                    "error_message": "Unknown failure (no result returned)"
                })
                return

            ok = (result_obj.get("status") or "").lower() == "success"
            self.finished_signal.emit(ok, result_obj)

        except Exception as e:
            self.finished_signal.emit(False, {
                "status": "error",
                "error_message": f"Code review execution failed: {str(e)}"
            })
        finally:
            try:
                import pythoncom
                pythoncom.CoUninitialize()
            except Exception:
                pass
    
    

class BatchProcessWorker(QThread):
    """Batch processing worker thread with detailed logging"""
    status_signal = Signal(str)
    agent_step_signal = Signal(str)  # 新增：Agent步骤信号
    current_class_signal = Signal(str, int, int)
    class_finished_signal = Signal(bool, str, dict)
    all_finished_signal = Signal(dict)

    def __init__(self, class_list: List[str], base_config: Dict[str, Any], diagram_files_dict: Dict = None):
        super().__init__()
        self.class_list = class_list
        self.base_config = base_config
        self.diagram_files_dict = diagram_files_dict or {}  # Store diagram files dict for display names
        self.should_stop = False
        self.active_proc: Optional["multiprocessing.Process"] = None
        self.per_class_timeout = int(self.base_config.get('per_class_timeout_sec', 180))

    def stop(self):
        """Request stop and hard-kill active child process if any."""
        self.should_stop = True
        if self.active_proc and self.active_proc.is_alive():
            try:
                self.active_proc.terminate()
            except Exception:
                pass

    def run(self):
        """Run batch processing with per-class subprocess + timeout (hard-stoppable)."""
        try:
            try:
                import pythoncom
                pythoncom.CoInitialize()
            except Exception as e:
                self.status_signal.emit(f"COM initialization warning: {str(e)}")

            total_classes = len(self.class_list)
            success_count = 0
            failed_count = 0
            results: List[Dict[str, Any]] = []

            mode = self.base_config.get("mode", "agent")
            self.status_signal.emit(f"Starting batch processing of {total_classes} classes ({mode} mode)...")

            ctx = multiprocessing.get_context('spawn')

            for i, class_path in enumerate(self.class_list, 1):
                if self.should_stop:
                    self.status_signal.emit("Batch processing stopped")
                    break

                # Get display name for both classes and diagrams
                if class_path in self.diagram_files_dict:
                    class_name = self.diagram_files_dict[class_path]['name']
                else:
                    class_name = EnhancedListWidgetItem.extract_class_name(class_path)

                self.current_class_signal.emit(class_path, i, total_classes)
                self.status_signal.emit(f"Processing ({i}/{total_classes}): {class_name}")

                config = self.base_config.copy()
                config["class_path"] = class_path
                config["enable_agent_logging"] = True  # 启用详细日志
                mode = self.base_config.get("mode", "agent")

                if not AGENT_AVAILABLE:
                    failed_count += 1
                    res = {"status": "error", "error_message": "AI Agent module unavailable"}
                    self.class_finished_signal.emit(False, class_path, res)
                    self.status_signal.emit(f"Skipped: {class_name} - AI Agent module unavailable")
                    results.append({
                        "class_path": class_path,
                        "class_name": class_name,
                        "success": False,
                        "result": res
                    })
                    continue

                # 子进程执行 + 超时控制 + 日志处理
                q = ctx.Queue()
                p = ctx.Process(target=_run_review_entry_subproc_with_logging, args=(config, mode, q))
                self.active_proc = p
                p.start()

                start_ts = time.time()
                result_obj: Optional[Dict[str, Any]] = None
                timed_out = False

                while p.is_alive():
                    if self.should_stop:
                        self.status_signal.emit("Stop requested by user, terminating current analysis...")
                        try:
                            p.terminate()
                        except Exception:
                            pass
                        p.join(5)
                        break

                    # 处理各种消息类型
                    try:
                        tag, payload = q.get_nowait()
                        
                        if tag == 'agent_log':
                            # Agent执行日志
                            self.agent_step_signal.emit(f"[{class_name}] {payload}")
                        elif tag == 'status':
                            # 普通状态消息
                            self.status_signal.emit(f"[{class_name}] {payload}")
                        elif tag == 'ok':
                            # 成功结果
                            result_obj = payload
                            try:
                                p.join(0.5)
                            except Exception:
                                pass
                            break
                        elif tag == 'err':
                            # 错误结果
                            result_obj = payload
                            try:
                                p.join(0.5)
                            except Exception:
                                pass
                            break
                            
                    except Exception:
                        pass

                    # 超时检查
                    if time.time() - start_ts > self.per_class_timeout:
                        timed_out = True
                        self.status_signal.emit(
                            f"Timeout: {class_name} (> {self.per_class_timeout}s). Killing process."
                        )
                        try:
                            p.terminate()
                        except Exception:
                            pass
                        p.join(5)
                        break

                    time.sleep(0.1)

                # 处理剩余消息
                if result_obj is None and not timed_out and not self.should_stop:
                    try:
                        while True:
                            tag, payload = q.get(timeout=0.5)
                            if tag == 'agent_log':
                                self.agent_step_signal.emit(f"[{class_name}] {payload}")
                            elif tag == 'status':
                                self.status_signal.emit(f"[{class_name}] {payload}")
                            elif tag in ['ok', 'err']:
                                result_obj = payload
                                break
                    except Exception:
                        pass

                self.active_proc = None

                if self.should_stop:
                    break

                # 处理结果
                if timed_out:
                    failed_count += 1
                    res = {"status": "timeout", "error_message": f"Per-class timeout ({self.per_class_timeout}s)"}
                    self.class_finished_signal.emit(False, class_path, res)
                    self.status_signal.emit(f"Failed (timeout): {class_name}")
                    results.append({
                        "class_path": class_path,
                        "class_name": class_name,
                        "success": False,
                        "result": res
                    })
                    continue

                if not result_obj:
                    failed_count += 1
                    res = {"status": "error", "error_message": "Unknown failure (no result returned)"}
                    self.class_finished_signal.emit(False, class_path, res)
                    self.status_signal.emit(f"Failed: {class_name} - Unknown failure")
                    results.append({
                        "class_path": class_path,
                        "class_name": class_name,
                        "success": False,
                        "result": res
                    })
                    continue

                # 结果判定
                status = (result_obj.get("status") or "").lower()
                if status == "success":
                    success_count += 1
                    self.class_finished_signal.emit(True, class_path, result_obj)
                    self.status_signal.emit(f"Completed: {class_name}")
                    results.append({
                        "class_path": class_path,
                        "class_name": class_name,
                        "success": True,
                        "result": result_obj
                    })
                else:
                    failed_count += 1
                    err = result_obj.get("error_message", status or "Processing failed")
                    self.class_finished_signal.emit(False, class_path, result_obj)
                    self.status_signal.emit(f"Failed: {class_name} - {err}")
                    results.append({
                        "class_path": class_path,
                        "class_name": class_name,
                        "success": False,
                        "result": result_obj
                    })

            summary = {
                "total_classes": total_classes,
                "success_count": success_count,
                "failed_count": failed_count,
                "results": results,
                "stopped": self.should_stop
            }
            self.all_finished_signal.emit(summary)

            if not self.should_stop:
                self.status_signal.emit(
                    f"Batch processing completed: Success {success_count}, Failed {failed_count}"
                )

        except Exception as e:
            error_msg = f"Batch processing error: {str(e)}"
            self.status_signal.emit(error_msg)
            self.all_finished_signal.emit({"error": error_msg})
        finally:
            try:
                import pythoncom
                pythoncom.CoUninitialize()
            except Exception:
                pass
    

# ==================== Main Interface Class (Remove progress bar functionality) ====================

class AscetAgentMainWindow(QMainWindow):
    """ASCET AI code review agent main interface - Remove progress bar functionality, use SVG animation"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ASCET Unit Copilot v3.3 - EAS2")
        self.setGeometry(100, 100, 1600, 900)
        
        self.settings = QSettings('AscetAgent', 'AscetAgentv3')
        
        # Original data storage
        self.available_classes = {}
        self.structure_tree = {}
        self.diagram_files = []  # Store diagram files: [dict with name, file_path, relative_path, ...]
        self.diagram_files_dict = {}  # Map diagram_file_path -> {name, file_path, relative_path}
        self.selected_classes = []
        self.scan_worker = None
        self.agent_worker = None
        self.batch_worker = None
        self.last_report_path = None
        self.current_processing_index = -1
        self.show_class_names = True

        self.loading_animation = None
        
        # RAG related variables
        self.rag_manager_dialog = None
        
        # New: Store analysis results for each class
        self.class_analysis_results = {}  # class_path -> result dict
        
        # New: Current running mode
        self.current_mode = "agent"  # Default agent mode
        
        # SVG animation widget
        self.loading_animation = None
        
        self.init_ui()
        self.apply_styles()
        self.setup_button_styles()  # Add button style setup
        self.load_ui_state()
        self.auto_apply_settings()
        self.refresh_reports_list()
    
    def init_ui(self):
        """Initialize user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)
        
        # Toolbar
        self.create_enhanced_toolbar(main_layout)
        
        # Main content area
        content_splitter = QSplitter(Qt.Horizontal)
        content_splitter.setChildrenCollapsible(False)
        
        # Left: Database panel
        self.create_database_panel(content_splitter)
        
        # Right: tab widget – Code Review  |  Code Chat
        right_tab_widget = QTabWidget()
        right_tab_widget.tabBar().setExpanding(False)
        right_tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #dee2e6;
                background-color: #f8f9fa;
                border-radius: 0px;
            }
            QTabBar::tab {
                background: #f0f2f5;
                border: 1px solid #dee2e6;
                border-bottom: none;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
                padding: 6px 18px;
                margin-right: 2px;
                font-size: 9pt;
                font-weight: 500;
                color: #6c757d;
                min-width: 110px;
            }
            QTabBar::tab:selected {
                background: #ffffff;
                color: #4dabf7;
                border-color: #4dabf7;
                font-weight: 600;
            }
            QTabBar::tab:hover:!selected {
                background: #e9ecef;
                color: #495057;
            }
        """)

        # ── Tab 1: Code Review (existing layout) ──────────────────────
        review_container = QWidget()
        review_layout = QVBoxLayout(review_container)
        review_layout.setContentsMargins(0, 0, 0, 0)
        review_layout.setSpacing(0)

        review_splitter = QSplitter(Qt.Vertical)
        review_splitter.setChildrenCollapsible(False)
        self.create_enhanced_control_panel(review_splitter)
        self.create_status_panel(review_splitter)
        review_splitter.widget(0).setMinimumHeight(400)
        review_splitter.widget(1).setMinimumHeight(150)
        review_splitter.widget(1).setMaximumHeight(250)
        review_splitter.setSizes([500, 200])
        review_splitter.setStretchFactor(0, 1)
        review_splitter.setStretchFactor(1, 0)
        review_layout.addWidget(review_splitter)

        right_tab_widget.addTab(review_container, "📋  Code Review")

        # ── Tab 2: Code Chat ──────────────────────────────────────────
        if CHAT_PANEL_AVAILABLE:
            self.chat_panel = CodeChatPanel(self.settings)
            right_tab_widget.addTab(self.chat_panel, "💬  Code Chat")
        else:
            placeholder = QLabel("Code Chat panel is unavailable.\nPlease check that chat_panel.py is present.")
            placeholder.setAlignment(Qt.AlignCenter)
            right_tab_widget.addTab(placeholder, "💬  Code Chat")
            self.chat_panel = None

        content_splitter.addWidget(right_tab_widget)
        
        # Set minimum sizes
        content_splitter.widget(0).setMinimumWidth(350)
        content_splitter.widget(0).setMaximumWidth(500)
        
        # Set initial split ratios
        content_splitter.setSizes([400, 1000])
        
        # Set stretch factors
        content_splitter.setStretchFactor(0, 0)
        content_splitter.setStretchFactor(1, 1)
        
        main_layout.addWidget(content_splitter)
        
        self.create_enhanced_status_bar()
    
    def detect_ascet_version_silently(self) -> str:
        """静默检测当前运行的ASCET版本"""
        if not ASCET_DETECTOR_AVAILABLE:
            return "6.1.4"  # 默认版本，不显示错误
        
        try:
            detection_result = detect_current_ascet()
            
            if detection_result is None:
            
                self.append_status("使用默认ASCET版本: 6.1.4")
                return "6.1.4"
            
            version, pid, exe_path = detection_result
            
            if version == "unknown":
                # 检测到进程但版本未知，使用默认版本
                self.append_status(f"检测到ASCET进程 (PID: {pid})，使用默认版本: 6.1.4")
                return "6.1.4"
            else:
                # 成功检测到版本
                self.append_status(f"自动检测ASCET版本: {version}")
                return version
                
        except Exception:
            # 检测失败，静默使用默认版本
            return "6.1.4"

    def create_enhanced_toolbar(self, parent_layout):
        """Create enhanced toolbar """
        toolbar_frame = QFrame()
        toolbar_frame.setFrameStyle(QFrame.StyledPanel)
        toolbar_frame.setFixedHeight(85)  # 修复：使用setFixedHeight而不是setFixedSize
        toolbar_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        toolbar_layout = QHBoxLayout(toolbar_frame)
        toolbar_layout.setContentsMargins(10, 5, 10, 5)
        toolbar_layout.setSpacing(20)
        
        # Mode selection group (保持不变)
        mode_group = QGroupBox("Mode")
        mode_group.setMinimumSize(120, 70)
        mode_group.setMaximumHeight(70)
        mode_layout = QHBoxLayout(mode_group)
        mode_layout.setContentsMargins(8, 5, 8, 5)
        mode_layout.setSpacing(5)
        
        self.mode_button_group = QButtonGroup()
        
        self.direct_mode_radio = QRadioButton("Rule")
        self.direct_mode_radio.setToolTip("Direct mode: Basic rule checking only")
        self.direct_mode_radio.setMinimumWidth(50)
        
        self.agent_mode_radio = QRadioButton("AI+Rule")
        self.agent_mode_radio.setToolTip("Agent mode: Includes AI deep analysis")
        self.agent_mode_radio.setChecked(True)
        self.agent_mode_radio.setMinimumWidth(50)
        
        self.mode_button_group.addButton(self.direct_mode_radio)
        self.mode_button_group.addButton(self.agent_mode_radio)
        
        self.direct_mode_radio.toggled.connect(lambda checked: self.on_mode_changed("direct" if checked else "agent"))
        
        mode_layout.addWidget(self.direct_mode_radio)
        mode_layout.addWidget(self.agent_mode_radio)
        
        # ASCET connection group - 移除版本选择
        ascet_group = QGroupBox("ASCET")
        ascet_group.setMinimumSize(220, 70)
        ascet_group.setMaximumHeight(70)
        ascet_layout = QHBoxLayout(ascet_group)
        ascet_layout.setContentsMargins(8, 5, 8, 5)
        ascet_layout.setSpacing(8)
        
        self.scan_all_btn = QPushButton("Scan Database")
        self.scan_all_btn.clicked.connect(self.scan_all_database)
        self.scan_all_btn.setMinimumSize(100, 30)
        
        self.scan_folder_btn = QPushButton("Scan Folder")
        self.scan_folder_btn.clicked.connect(self.scan_folder)
        self.scan_folder_btn.setMinimumSize(100, 30)
        
        ascet_layout.addWidget(self.scan_all_btn)
        ascet_layout.addWidget(self.scan_folder_btn)
        
        # Right side buttons (保持不变)
        right_widget = QWidget()
        right_layout = QHBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(15)
        
        self.rag_manager_btn = QPushButton("Knowledge")
        self.rag_manager_btn.clicked.connect(self.open_rag_manager)
        self.rag_manager_btn.setMinimumSize(80, 35)
        self.rag_manager_btn.setEnabled(True)
        
        self.rag_status_indicator = QLabel("●")
        self.rag_status_indicator.setStyleSheet("color: #6c757d; font-size: 16px;")
        self.rag_status_indicator.setToolTip("RAG Status")
        self.rag_status_indicator.setFixedSize(20, 35)
        self.rag_status_indicator.setAlignment(Qt.AlignCenter)
        
        self.browse_reports_btn = QPushButton("Reports")
        self.browse_reports_btn.clicked.connect(self.browse_reports)
        self.browse_reports_btn.setMinimumSize(70, 35)
        
        self.feedback_btn = QPushButton("Feedback")
        self.feedback_btn.clicked.connect(self.open_feedback_link)
        self.feedback_btn.setMinimumSize(70, 35)
        self.feedback_btn.setToolTip("Submit feedback or suggestions")
        
        self.settings_btn = QPushButton("Settings")
        self.settings_btn.clicked.connect(self.open_settings)
        self.settings_btn.setMinimumSize(70, 35)
        
        right_layout.addWidget(self.rag_manager_btn)
        right_layout.addWidget(self.rag_status_indicator)
        right_layout.addWidget(self.browse_reports_btn)
        right_layout.addWidget(self.feedback_btn)
        right_layout.addWidget(self.settings_btn)
        
        # Main layout
        toolbar_layout.addWidget(mode_group)
        toolbar_layout.addWidget(ascet_group)
        toolbar_layout.addStretch()
        toolbar_layout.addWidget(right_widget)
        
        parent_layout.addWidget(toolbar_frame)

    def on_mode_changed(self, mode: str):
        """Mode switching event handler"""
        self.current_mode = mode
        self.append_status(f"Switched to {mode.upper()} mode")
        
        # Update UI hints
        if mode == "direct":
            self.agent_status_label.setText("Mode: Direct")
            # RAG knowledge base management can be used in Direct mode too
            self.rag_manager_btn.setEnabled(True)
            self.rag_status_indicator.setToolTip("RAG Status Indicator")
        else:
            self.agent_status_label.setText("Mode: Agent")
            self.rag_manager_btn.setEnabled(True)
            self.rag_status_indicator.setToolTip("RAG Status Indicator")
    
    def create_database_panel(self, parent):
        """Create database structure panel"""
        db_widget = QWidget()
        db_widget.setMinimumWidth(350)
        db_widget.setMaximumWidth(500)
        db_widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        
        db_layout = QVBoxLayout(db_widget)
        db_layout.setContentsMargins(5, 5, 5, 5)
        db_layout.setSpacing(5)
        
        # Title and search bar
        header_layout = QHBoxLayout()
        
        db_label = QLabel("Database Structure")
        db_label.setFont(QFont("Arial", 10, QFont.Bold))
        
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search classes...")
        self.search_edit.textChanged.connect(self.filter_tree)
        self.search_edit.setMaximumWidth(120)
        
        search_btn = QPushButton("Search")
        search_btn.clicked.connect(self.search_classes)
        search_btn.setMaximumWidth(100)
        
        header_layout.addWidget(db_label)
        header_layout.addStretch()
        header_layout.addWidget(self.search_edit)
        header_layout.addWidget(search_btn)
        
        db_layout.addLayout(header_layout)
        
        # Class structure tree
        self.class_tree = SelectableTreeWidget()
        self.class_tree.setHeaderLabels(["ASCET Class Structure"])
        self.class_tree.itemClicked.connect(self.on_tree_item_clicked)
        self.class_tree.itemSelectionChanged.connect(lambda: self.on_tree_item_clicked(None, 0))
        self.class_tree.itemDoubleClicked.connect(self.on_tree_item_double_clicked)
        self.class_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.class_tree.customContextMenuRequested.connect(self.show_tree_context_menu)
        self.class_tree.setMinimumHeight(300)
        
        db_layout.addWidget(self.class_tree)
        
        # Tree operation buttons
        tree_btn_layout = QVBoxLayout()
        
        btn_row1 = QHBoxLayout()
        self.add_selected_btn = QPushButton("Add Selected")
        self.add_selected_btn.clicked.connect(self.add_selected_classes)
        self.add_selected_btn.setEnabled(False)
        
        self.select_all_btn = QPushButton("Select All")
        self.select_all_btn.clicked.connect(self.class_tree.selectAll)
        
        btn_row1.addWidget(self.add_selected_btn)
        btn_row1.addWidget(self.select_all_btn)
        
        btn_row2 = QHBoxLayout()
        self.expand_all_btn = QPushButton("Expand All")
        self.expand_all_btn.clicked.connect(self.class_tree.expandAll)
        
        self.collapse_all_btn = QPushButton("Collapse All")
        self.collapse_all_btn.clicked.connect(self.class_tree.collapseAll)
        
        btn_row2.addWidget(self.expand_all_btn)
        btn_row2.addWidget(self.collapse_all_btn)
        
        tree_btn_layout.addLayout(btn_row1)
        tree_btn_layout.addLayout(btn_row2)
        
        db_layout.addLayout(tree_btn_layout)
        
        parent.addWidget(db_widget)
    
    def create_enhanced_control_panel(self, parent):
        """Create enhanced control panel"""
        control_widget = QWidget()
        control_layout = QVBoxLayout(control_widget)
        
        # Analysis queue
        self.create_queue_widget(control_layout)
        
        # Execution control
        self.create_execution_control(control_layout)
        
        parent.addWidget(control_widget)
    
    # def create_queue_widget(self, parent_layout):
    #     """Create analysis queue widget"""
    #     queue_group = QGroupBox("Analysis Queue")
    #     queue_group_layout = QVBoxLayout(queue_group)
        
    #     queue_header_layout = QHBoxLayout()
    #     queue_label = QLabel("Classes to analyze:")
    #     self.queue_count_label = QLabel("(0 items)")
    #     self.current_processing_label = QLabel("")
    #     self.current_processing_label.setStyleSheet("color: #3498db; font-weight: bold;")
        
    #     # Create SVG animation widget
    #     self.loading_animation = SVGAnimationWidget()
    #     self.loading_animation.setVisible(False)
        
    #     queue_header_layout.addWidget(queue_label)
    #     queue_header_layout.addWidget(self.queue_count_label)
    #     queue_header_layout.addStretch()
    #     queue_header_layout.addWidget(self.loading_animation)
    #     queue_header_layout.addWidget(self.current_processing_label)
        
    #     queue_group_layout.addLayout(queue_header_layout)
        
    #     # Use QTableWidget to display status and class names
    #     self.queue_table = QTableWidget()
    #     self.queue_table.setColumnCount(2)
    #     self.queue_table.setHorizontalHeaderLabels(["Class Name", "Status"])
    #     self.queue_table.setSelectionBehavior(QAbstractItemView.SelectRows)
    #     self.queue_table.setAlternatingRowColors(True)
        
    #     header = self.queue_table.horizontalHeader()
    #     header.setSectionResizeMode(0, QHeaderView.Stretch)
    #     header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        
    #     self.queue_table.itemDoubleClicked.connect(self.on_queue_item_double_clicked)
    #     self.queue_table.setContextMenuPolicy(Qt.CustomContextMenu)
    #     self.queue_table.customContextMenuRequested.connect(self.show_queue_context_menu)
        
    #     queue_group_layout.addWidget(self.queue_table)
        
    #     queue_btn_layout = QHBoxLayout()
        
    #     self.remove_class_btn = QPushButton("Remove")
    #     self.remove_class_btn.clicked.connect(self.remove_selected_class)
        
    #     self.clear_queue_btn = QPushButton("Clear Queue")
    #     self.clear_queue_btn.clicked.connect(self.clear_class_queue)
        
    #     self.move_up_btn = QPushButton("Move Up")
    #     self.move_up_btn.clicked.connect(self.move_class_up)
        
    #     self.move_down_btn = QPushButton("Move Down")
    #     self.move_down_btn.clicked.connect(self.move_class_down)
        
    #     queue_btn_layout.addWidget(self.remove_class_btn)
    #     queue_btn_layout.addWidget(self.clear_queue_btn)
    #     queue_btn_layout.addWidget(self.move_up_btn)
    #     queue_btn_layout.addWidget(self.move_down_btn)
        
    #     queue_group_layout.addLayout(queue_btn_layout)
        
    #     parent_layout.addWidget(queue_group)

    def create_queue_widget(self, parent_layout):
        """Create analysis queue widget with filtering"""
        queue_group = QGroupBox("Analysis Queue")
        queue_group_layout = QVBoxLayout(queue_group)
        
        # 队列头部布局
        queue_header_layout = QHBoxLayout()
        queue_label = QLabel("Classes to analyze:")
        self.queue_count_label = QLabel("(0 items)")
        self.current_processing_label = QLabel("")
        self.current_processing_label.setStyleSheet("color: #3498db; font-weight: bold;")
        
        # Create SVG animation widget
        self.loading_animation = create_spinner("ocean", size=24)
        self.loading_animation.setVisible(False)
        
        queue_header_layout.addWidget(queue_label)
        queue_header_layout.addWidget(self.queue_count_label)
        queue_header_layout.addStretch()
        queue_header_layout.addWidget(self.loading_animation)
        queue_header_layout.addWidget(self.current_processing_label)
        
        queue_group_layout.addLayout(queue_header_layout)
        
        # 新增：筛选控件区域
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(8)
        filter_layout.setContentsMargins(5, 5, 5, 5)
        
        filter_label = QLabel("Filter:")
        filter_label.setStyleSheet("font-weight: 600; color: #495057; font-size: 9pt;")
        filter_layout.addWidget(filter_label)
        
        # 状态筛选
        self.status_filter_combo = QComboBox()
        self.status_filter_combo.addItems([
            "All Status", "Error Only", "Warning Only", "Passed Only", 
            "Problems Only", "Processing", "Waiting"
        ])
        self.status_filter_combo.setCurrentText("All Status")
        self.status_filter_combo.currentTextChanged.connect(self.apply_queue_filter)
        self.status_filter_combo.setMinimumWidth(100)
        self.status_filter_combo.setMaximumHeight(26)
        self.status_filter_combo.setToolTip("Filter classes by analysis status")
        self.status_filter_combo.setStyleSheet("""
            QComboBox {
                border: 1px solid #ced4da;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 8pt;
                background-color: #ffffff;
            }
            QComboBox:focus {
                border-color: #4dabf7;
            }
            QComboBox::drop-down {
                border: none;
                width: 16px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid #6c757d;
                margin-right: 4px;
            }
        """)
        
        filter_layout.addWidget(self.status_filter_combo)
        
        # 错误类型筛选
        self.error_type_filter_combo = QComboBox()
        self.error_type_filter_combo.addItems([
            "All Types", "Rule Errors", "AI Errors", "High Severity", 
            "Medium Severity", "Low Severity"
        ])
        self.error_type_filter_combo.setCurrentText("All Types")
        self.error_type_filter_combo.currentTextChanged.connect(self.apply_queue_filter)
        self.error_type_filter_combo.setMinimumWidth(100)
        self.error_type_filter_combo.setMaximumHeight(26)
        self.error_type_filter_combo.setToolTip("Filter classes by error type")
        self.error_type_filter_combo.setStyleSheet("""
            QComboBox {
                border: 1px solid #ced4da;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 8pt;
                background-color: #ffffff;
            }
            QComboBox:focus {
                border-color: #4dabf7;
            }
            QComboBox::drop-down {
                border: none;
                width: 16px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid #6c757d;
                margin-right: 4px;
            }
        """)
        
        filter_layout.addWidget(self.error_type_filter_combo)
        
        # 快速筛选按钮
        self.show_problems_btn = QPushButton("Problems Only")
        self.show_problems_btn.setCheckable(True)
        self.show_problems_btn.toggled.connect(self.toggle_problems_only)
        self.show_problems_btn.setMinimumHeight(26)
        self.show_problems_btn.setMinimumWidth(90)
        self.show_problems_btn.setToolTip("Show only classes with errors or warnings")
        self.show_problems_btn.setStyleSheet("""
            QPushButton {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 8pt;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #e9ecef;
                border-color: #adb5bd;
            }
            QPushButton:checked {
                background-color: #fff3cd;
                border-color: #ffc107;
                color: #856404;
                font-weight: 600;
            }
            QPushButton:checked:hover {
                background-color: #ffeaa7;
                border-color: #ffb400;
            }
        """)
        
        filter_layout.addWidget(self.show_problems_btn)
        
        # 重置筛选
        self.reset_filter_btn = QPushButton("Reset")
        self.reset_filter_btn.clicked.connect(self.reset_queue_filter)
        self.reset_filter_btn.setMinimumHeight(26)
        self.reset_filter_btn.setMinimumWidth(50)
        self.reset_filter_btn.setToolTip("Reset all filters")
        self.reset_filter_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: 1px solid #6c757d;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 8pt;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #5a6268;
                border-color: #545b62;
            }
            QPushButton:pressed {
                background-color: #495057;
                border-color: #3d4549;
            }
        """)
        
        filter_layout.addWidget(self.reset_filter_btn)
        filter_layout.addStretch()
        
        # 筛选统计标签
        self.filter_stats_label = QLabel("")
        self.filter_stats_label.setStyleSheet("color: #6c757d; font-size: 8pt; font-weight: 500;")
        filter_layout.addWidget(self.filter_stats_label)
        
        queue_group_layout.addLayout(filter_layout)
        
        # Use QTableWidget to display status and class names
        self.queue_table = QTableWidget()
        self.queue_table.setColumnCount(2)
        self.queue_table.setHorizontalHeaderLabels(["Class Name", "Status"])
        self.queue_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.queue_table.setAlternatingRowColors(True)
        
        header = self.queue_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        
        self.queue_table.itemDoubleClicked.connect(self.on_queue_item_double_clicked)
        self.queue_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.queue_table.customContextMenuRequested.connect(self.show_queue_context_menu)
        
        queue_group_layout.addWidget(self.queue_table)
        
        queue_btn_layout = QHBoxLayout()
        
        self.remove_class_btn = QPushButton("Remove")
        self.remove_class_btn.clicked.connect(self.remove_selected_class)
        
        self.clear_queue_btn = QPushButton("Clear Queue")
        self.clear_queue_btn.clicked.connect(self.clear_class_queue)
        
        self.move_up_btn = QPushButton("Move Up")
        self.move_up_btn.clicked.connect(self.move_class_up)
        
        self.move_down_btn = QPushButton("Move Down")
        self.move_down_btn.clicked.connect(self.move_class_down)
        
        queue_btn_layout.addWidget(self.remove_class_btn)
        queue_btn_layout.addWidget(self.clear_queue_btn)
        queue_btn_layout.addWidget(self.move_up_btn)
        queue_btn_layout.addWidget(self.move_down_btn)
        
        queue_group_layout.addLayout(queue_btn_layout)
        
        parent_layout.addWidget(queue_group)
    
    def create_execution_control(self, parent_layout):
        """Create execution control section"""
        execution_group = QGroupBox("Execution Control")
        execution_layout = QVBoxLayout(execution_group)
        
        # Add scan progress bar (for database scanning only)
        self.scan_progress_bar = QProgressBar()
        self.scan_progress_bar.setVisible(False)
        self.scan_progress_bar.setFormat("Database Scan: %p%")  # Only show percentage
        execution_layout.addWidget(self.scan_progress_bar)
        
        btn_layout = QHBoxLayout()
        
        self.run_batch_btn = QPushButton("Start ALL")
        self.run_batch_btn.clicked.connect(self.start_batch_processing)
        self.run_batch_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                font-size: 14px;
                font-weight: bold;
                padding: 12px;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
            QPushButton:pressed {
                background-color: #1e8449;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
                color: #7f8c8d;
            }
        """)
        
        self.stop_batch_btn = QPushButton("Stop Processing")
        self.stop_batch_btn.clicked.connect(self.stop_batch_processing)
        self.stop_batch_btn.setEnabled(False)
        self.stop_batch_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                font-size: 12px;
                font-weight: bold;
                padding: 8px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:pressed {
                background-color: #a93226;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
                color: #7f8c8d;
            }
        """)
        
        btn_layout.addWidget(self.run_batch_btn)
        btn_layout.addWidget(self.stop_batch_btn)
        
        execution_layout.addLayout(btn_layout)
        
        parent_layout.addWidget(execution_group)
    
    def create_status_panel(self, parent):
        """Create status display panel"""
        status_widget = QWidget()
        status_widget.setMinimumHeight(150)
        status_widget.setMaximumHeight(250)
        status_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        status_layout = QVBoxLayout(status_widget)
        status_layout.setContentsMargins(5, 5, 5, 5)
        status_layout.setSpacing(5)
        
        status_label = QLabel("Logs")
        status_label.setFont(QFont("Arial", 10, QFont.Bold))
        status_layout.addWidget(status_label)
        
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setPlaceholderText("System status and logs will be displayed here...")
        self.status_text.setMaximumHeight(200)
        status_layout.addWidget(self.status_text)
        
        parent.addWidget(status_widget)
    
    def create_enhanced_status_bar(self):
        """Create enhanced status bar"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        self.connection_status_label = QLabel("Not Connected")
        self.classes_count_label = QLabel("Classes: 0")
        self.agent_status_label = QLabel("Mode: Agent")
        self.rag_count_label = QLabel("RAG: Unknown")
        self.model_status_label = QLabel("Model: gpt5-mini") 
        self.reports_count_label = QLabel("Reports: 0")
        
        self.status_bar.addWidget(self.connection_status_label)
        self.status_bar.addPermanentWidget(self.classes_count_label)
        self.status_bar.addPermanentWidget(self.agent_status_label)
        self.status_bar.addPermanentWidget(self.rag_count_label)
        self.status_bar.addPermanentWidget(self.reports_count_label)
    
    def apply_styles(self):
        """Apply modern styles - unified font system"""
        self.setStyleSheet("""
            /* Main window styles */
            QMainWindow {
                background-color: #f8f9fa;
                color: #2c3e50;
                font-family: "Microsoft YaHei UI", "Segoe UI", "Arial", sans-serif;
                font-size: 9pt;  /* Set base font size */
            }
            
            /* Toolbar styles */
            QFrame[frameShape="4"] {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ffffff, stop:1 #f1f3f4);
                border: 1px solid #e1e5e9;
                border-radius: 8px;
                margin: 2px;
            }
            
            /* Group box styles - modern design */
            QGroupBox {
                font-weight: 600;
                font-size: 9pt;  /* Unified font size */
                color: #495057;
                border: 2px solid #e9ecef;
                border-radius: 8px;
                margin: 5px 2px;
                padding-top: 12px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ffffff, stop:1 #f8f9fa);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 3px 8px;
                background-color: #ffffff;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                font-size: 8pt;  /* Title slightly smaller */
            }
            
            /* Button styles - modern flat */
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ffffff, stop:1 #f8f9fa);
                border: 1px solid #ced4da;
                border-radius: 6px;
                padding: 5px 10px;
                font-size: 9pt;  /* Unified button font */
                font-weight: 500;
                color: #495057;
                min-height: 18px;
                min-width: 50px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f8f9fa, stop:1 #e9ecef);
                border-color: #adb5bd;
                color: #212529;
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #e9ecef, stop:1 #dee2e6);
                border-color: #6c757d;
            }
            QPushButton:disabled {
                background-color: #e9ecef;
                color: #6c757d;
                border-color: #dee2e6;
            }
            
            /* Primary action buttons */
            QPushButton#primaryButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #4dabf7, stop:1 #339af0);
                color: white;
                font-weight: 600;
                font-size: 9pt;  /* Keep consistent */
                border: 1px solid #228be6;
            }
            QPushButton#primaryButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #339af0, stop:1 #228be6);
            }
            
            /* Danger action buttons */
            QPushButton#dangerButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ff6b6b, stop:1 #ee5a52);
                color: white;
                font-weight: 600;
                font-size: 9pt;  /* Keep consistent */
                border: 1px solid #e03131;
            }
            QPushButton#dangerButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ee5a52, stop:1 #e03131);
            }
            
            /* Success action buttons */
            QPushButton#successButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #51cf66, stop:1 #40c057);
                color: white;
                font-weight: 600;
                font-size: 9pt;  /* Keep consistent */
                border: 1px solid #37b24d;
            }
            QPushButton#successButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #40c057, stop:1 #37b24d);
            }
            
            /* Input field styles */
            QLineEdit, QComboBox {
                border: 1px solid #ced4da;
                border-radius: 5px;
                padding: 4px 8px;
                font-size: 9pt;  /* Unified font size */
                background-color: #ffffff;
                selection-background-color: #74c0fc;
            }
            QLineEdit:focus, QComboBox:focus {
                border-color: #4dabf7;
                outline: none;
            }
            
            /* Combo box arrow */
            QComboBox::drop-down {
                border: none;
                width: 18px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid #6c757d;
                margin-right: 4px;
            }
            
            /* Tree widget and table styles */
            QTreeWidget, QTableWidget, QListWidget {
                border: 1px solid #dee2e6;
                border-radius: 6px;
                background-color: #ffffff;
                alternate-background-color: #f8f9fa;
                selection-background-color: #e3f2fd;
                selection-color: #1565c0;
                font-size: 9pt;  /* Unified font size */
                gridline-color: #e9ecef;
            }
            
            /* Tree widget header */
            QHeaderView::section {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f8f9fa, stop:1 #e9ecef);
                border: 1px solid #dee2e6;
                border-radius: 0px;
                padding: 4px 6px;
                font-weight: 600;
                font-size: 8pt;  /* Header slightly smaller */
                color: #495057;
            }
            
            /* Text editor styles */
            QTextEdit {
                border: 1px solid #dee2e6;
                border-radius: 6px;
                background-color: #ffffff;
                font-family: "Consolas", "Monaco", "Courier New", monospace;
                font-size: 8pt;  /* Code area font slightly smaller */
                selection-background-color: #e3f2fd;
                line-height: 1.4;
            }
            
            /* Progress bar styles */
            QProgressBar {
                border: 1px solid #dee2e6;
                border-radius: 6px;
                background-color: #f8f9fa;
                text-align: center;
                font-size: 8pt;  /* Progress bar font slightly smaller */
                font-weight: 500;
                color: #495057;
                height: 18px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4dabf7, stop:1 #74c0fc);
                border-radius: 5px;
                margin: 1px;
            }
            
            /* Radio button and checkbox styles */
            QRadioButton, QCheckBox {
                font-size: 9pt;  /* Unified font size */
                color: #495057;
                spacing: 6px;
                padding: 2px;
            }
            QRadioButton::indicator, QCheckBox::indicator {
                width: 14px;
                height: 14px;
                border-radius: 7px;
                border: 2px solid #ced4da;
                background-color: #ffffff;
            }
            QRadioButton::indicator:checked {
                background-color: #4dabf7;
                border-color: #228be6;
            }
            QCheckBox::indicator {
                border-radius: 3px;
            }
            QCheckBox::indicator:checked {
                background-color: #4dabf7;
                border-color: #228be6;
            }
            
            /* Status bar styles */
            QStatusBar {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f8f9fa, stop:1 #e9ecef);
                border-top: 1px solid #dee2e6;
                font-size: 8pt;  /* Status bar font slightly smaller */
                color: #6c757d;
                padding: 2px;
            }
            QStatusBar QLabel {
                border: none;
                padding: 2px 6px;
                color: #495057;
                font-weight: 500;
                font-size: 8pt;  /* Keep consistent */
            }
            
            /* Splitter styles */
            QSplitter::handle {
                background-color: #dee2e6;
                border: 1px solid #ced4da;
                border-radius: 2px;
                margin: 1px;
            }
            QSplitter::handle:horizontal {
                width: 6px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #f8f9fa, stop:1 #e9ecef);
            }
            QSplitter::handle:vertical {
                height: 6px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f8f9fa, stop:1 #e9ecef);
            }
            
            /* Tab widget styles */
            QTabWidget::pane {
                border: 1px solid #dee2e6;
                background-color: #ffffff;
                border-radius: 6px;
                margin-top: -1px;
            }
            QTabBar::tab {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f8f9fa, stop:1 #e9ecef);
                border: 1px solid #dee2e6;
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                padding: 6px 12px;
                margin-right: 2px;
                font-size: 9pt;  /* Unified font size */
                color: #6c757d;
            }
            QTabBar::tab:selected {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ffffff, stop:1 #f8f9fa);
                color: #4dabf7;
                border-color: #4dabf7;
            }
            QTabBar::tab:hover:!selected {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ffffff, stop:1 #f1f3f4);
                color: #495057;
            }
            
            /* Label styles */
            QLabel {
                font-size: 9pt;  /* Unified label font */
                color: #495057;
            }
        """)
    
 

    def setup_button_styles(self):
        """Set special button styles"""
        # Primary action buttons
        self.run_batch_btn.setObjectName("primaryButton")
        self.scan_all_btn.setObjectName("primaryButton")
        self.rag_manager_btn.setObjectName("primaryButton")
        
        # Feedback按钮使用默认样式（与Settings按钮相同），不设置特殊objectName
        # self.feedback_btn 保持默认样式
        
        # Danger action buttons
        self.stop_batch_btn.setObjectName("dangerButton")
        
     
#-------------------------------------------------------------------
    def open_feedback_link(self):
        """Open feedback SharePoint link"""
        feedback_url = "https://bosch.sharepoint.com/:x:/r/sites/msteams_2302380/Shared%20Documents/General/06_Mgr/Efficiency/AI/ASCET_Unit_Copilot/ASCET_Copilot_Feedback.xlsx?d=w7d31c090927347a99f5d88ffd663652f&csf=1&web=1&e=pUmOFz&wdOrigin=TEAMS-MAGLEV.p2p_ns.rwc&wdExp=TEAMS-TREATMENT&wdhostclicktime=1755653240840&web=1"
        
        try:
            # 使用webbrowser模块打开链接
            webbrowser.open(feedback_url)
            self.append_status("Opening feedback form in browser...")
        except Exception as e:
           pass

        
# ==================== Queue Operation Related ====================
    
    # def update_queue_display(self):
    #     """Update queue display with robust status icons and texts."""
    #     self.queue_table.setRowCount(len(self.selected_classes))

    #     for i, class_path in enumerate(self.selected_classes):
    #         # Class name
    #         class_name = EnhancedListWidgetItem.extract_class_name(class_path)
    #         name_item = QTableWidgetItem(class_name)
    #         name_item.setToolTip(f"Full path: {class_path}")
    #         name_item.setData(Qt.UserRole, class_path)

    #         if i == self.current_processing_index:
    #             name_item.setBackground(QColor(52, 152, 219, 50))

    #         self.queue_table.setItem(i, 0, name_item)

    #         # Status column
    #         status_item = QTableWidgetItem()
    #         result = self.class_analysis_results.get(class_path)

    #         if result:
    #             status = (result.get('status') or '').lower()
    #             err_msg = result.get('error_message')

    #             # 明确错误（包含 error/timeout/terminated）
    #             if err_msg or status in ('error', 'timeout', 'terminated'):
    #                 status_item.setIcon(icon_manager.get_icon('x-circle'))
    #                 status_item.setText("Error")
    #                 tip = err_msg or status.capitalize() or "Error"
    #                 status_item.setToolTip(f"Analysis failed: {tip}")

    #             # 明确成功
    #             elif status == 'success':
    #                 error_stats = result.get('error_statistics', {})
    #                 rule_errors = error_stats.get('rule_errors', 0)
    #                 ai_errors = error_stats.get('ai_errors', 0)
                    
    #                 # ✅ 调试：检查数据完整性
    #                 print(f"🔍 error_statistics keys: {list(error_stats.keys())}")
    #                 rule_severity_stats = error_stats.get('rule_severity_stats')
    #                 if not rule_severity_stats:
    #                     print(f"   ❌ 缺少 rule_severity_stats 字段！")
    #                     # 创建默认值
    #                     rule_severity_stats = {
    #                         "high_severity": 0,
    #                         "medium_severity": 0,
    #                         "low_severity": 0,
    #                         "has_high_severity": False
    #                     }
    #                     # 尝试从 rule_error_details 重新计算
    #                     rule_error_details = error_stats.get('rule_error_details', [])
    #                     for detail in rule_error_details:
    #                         severity = str(detail.get('severity', '')).strip().lower()
    #                         if severity in ['high', 'h', '高', 'critical']:
    #                             rule_severity_stats['high_severity'] += 1
    #                             rule_severity_stats['has_high_severity'] = True
    #                         elif severity in ['medium', 'med', 'm', '中', 'warning']:
    #                             rule_severity_stats['medium_severity'] += 1
    #                         elif severity in ['low', 'l', '低', 'info']:
    #                             rule_severity_stats['low_severity'] += 1
    #                     print(f"   🔧 重新计算severity统计: {rule_severity_stats}")
    #                 else:
    #                     print(f"   ✅ rule_severity_stats: {rule_severity_stats}")
                    
    #                 has_high_severity = rule_severity_stats.get('has_high_severity', False)
                    
    #                 # 状态判断逻辑
    #                 if rule_errors == 0 and ai_errors == 0:
    #                     # 🟢 通过：无任何错误
    #                     status_item.setIcon(icon_manager.get_icon('check-circle'))
    #                     status_item.setText("Passed")
    #                     status_item.setToolTip("Analysis completed - no errors found")
    #                     print(f"   ✅ 设置为Passed")
    #                 elif has_high_severity:
    #                     # 🔴 错误：存在High severity规则错误
    #                     status_item.setIcon(icon_manager.get_icon('x-circle'))
    #                     status_item.setText("Error")
    #                     high_count = rule_severity_stats.get('high_severity', 0)
    #                     if ai_errors > 0:
    #                         status_item.setToolTip(f"High severity rule errors: {high_count}, AI errors: {ai_errors}")
    #                     else:
    #                         status_item.setToolTip(f"High severity rule errors detected: {high_count}")
    #                     print(f"   🔴 设置为Error (High severity: {high_count})")
    #                 else:
    #                     # 🟡 警告：只有Medium/Low severity规则错误 或 AI错误
    #                     status_item.setIcon(icon_manager.get_icon('alert-circle'))
    #                     status_item.setText("Warning")
    #                     medium_count = rule_severity_stats.get('medium_severity', 0)
    #                     low_count = rule_severity_stats.get('low_severity', 0)
                        
    #                     tooltip_parts = []
    #                     if rule_errors > 0:
    #                         tooltip_parts.append(f"Rule errors: {rule_errors} (Medium: {medium_count}, Low: {low_count})")
    #                     if ai_errors > 0:
    #                         tooltip_parts.append(f"AI errors: {ai_errors}")
                        
    #                     status_item.setToolTip("; ".join(tooltip_parts))
    #                     print(f"   🟡 设置为Warning (Medium: {medium_count}, Low: {low_count}, AI: {ai_errors})")
    #             else:
    #                 # 未知/处理中
    #                 if i == self.current_processing_index:
    #                     status_item.setIcon(icon_manager.get_icon('arrow-right-circle'))
    #                     status_item.setText("Processing")
    #                     status_item.setToolTip("Analysis in progress...")
    #                 else:
    #                     status_item.setIcon(icon_manager.get_icon('circle'))
    #                     status_item.setText("Waiting")
    #                     status_item.setToolTip("Waiting for analysis")
    #         else:
    #             # 无结果（等待/处理中）
    #             if i == self.current_processing_index:
    #                 status_item.setIcon(icon_manager.get_icon('arrow-right-circle'))
    #                 status_item.setText("Processing")
    #                 status_item.setToolTip("Analysis in progress...")
    #             else:
    #                 status_item.setIcon(icon_manager.get_icon('circle'))
    #                 status_item.setText("Waiting")
    #                 status_item.setToolTip("Waiting for analysis")

    #         status_item.setTextAlignment(Qt.AlignCenter)
    #         if i == self.current_processing_index:
    #             status_item.setBackground(QColor(52, 152, 219, 50))

    #         self.queue_table.setItem(i, 1, status_item)

    #     count = len(self.selected_classes)
    #     self.queue_count_label.setText(f"({count} items)")
    #     self.run_batch_btn.setEnabled(count > 0 and not (self.batch_worker and self.batch_worker.isRunning()))
    
    def update_queue_display(self):
        """Update queue display with robust status icons and filtering support."""
        self.queue_table.setRowCount(len(self.selected_classes))

        for i, class_path in enumerate(self.selected_classes):
            # Get name - handle both classes and diagrams
            if class_path in self.diagram_files_dict:
                class_name = self.diagram_files_dict[class_path]['name']
            else:
                class_name = EnhancedListWidgetItem.extract_class_name(class_path)
            
            name_item = QTableWidgetItem(class_name)
            name_item.setToolTip(f"Full path: {class_path}")
            name_item.setData(Qt.UserRole, class_path)

            if i == self.current_processing_index:
                name_item.setBackground(QColor(52, 152, 219, 50))

            self.queue_table.setItem(i, 0, name_item)

            # Status column
            status_item = QTableWidgetItem()
            result = self.class_analysis_results.get(class_path)

            if result:
                status = (result.get('status') or '').lower()
                err_msg = result.get('error_message')

                # 明确错误（包含 error/timeout/terminated）
                if err_msg or status in ('error', 'timeout', 'terminated'):
                    status_item.setIcon(icon_manager.get_icon('x-circle'))
                    status_item.setText("Error")
                    tip = err_msg or status.capitalize() or "Error"
                    status_item.setToolTip(f"Analysis failed: {tip}")

                # 明确成功
                elif status == 'success':
                    error_stats = result.get('error_statistics', {})
                    rule_errors = error_stats.get('rule_errors', 0)
                    ai_errors = error_stats.get('ai_errors', 0)
                    
                    # 调试：检查数据完整性
                    rule_severity_stats = error_stats.get('rule_severity_stats')
                    if not rule_severity_stats:
                        # 创建默认值
                        rule_severity_stats = {
                            "high_severity": 0,
                            "medium_severity": 0,
                            "low_severity": 0,
                            "has_high_severity": False
                        }
                        # 尝试从 rule_error_details 重新计算
                        rule_error_details = error_stats.get('rule_error_details', [])
                        for detail in rule_error_details:
                            severity = str(detail.get('severity', '')).strip().lower()
                            if severity in ['high', 'h', '高', 'critical']:
                                rule_severity_stats['high_severity'] += 1
                                rule_severity_stats['has_high_severity'] = True
                            elif severity in ['medium', 'med', 'm', '中', 'warning']:
                                rule_severity_stats['medium_severity'] += 1
                            elif severity in ['low', 'l', '低', 'info']:
                                rule_severity_stats['low_severity'] += 1
                    
                    has_high_severity = rule_severity_stats.get('has_high_severity', False)
                    
                    # 状态判断逻辑
                    if rule_errors == 0 and ai_errors == 0:
                        # 通过：无任何错误
                        status_item.setIcon(icon_manager.get_icon('check-circle'))
                        status_item.setText("Passed")
                        status_item.setToolTip("Analysis completed - no errors found")
                    elif has_high_severity:
                        # 错误：存在High severity规则错误
                        status_item.setIcon(icon_manager.get_icon('x-circle'))
                        status_item.setText("Error")
                        high_count = rule_severity_stats.get('high_severity', 0)
                        if ai_errors > 0:
                            status_item.setToolTip(f"High severity rule errors: {high_count}, AI errors: {ai_errors}")
                        else:
                            status_item.setToolTip(f"High severity rule errors detected: {high_count}")
                    else:
                        # 警告：只有Medium/Low severity规则错误 或 AI错误
                        status_item.setIcon(icon_manager.get_icon('alert-circle'))
                        status_item.setText("Warning")
                        medium_count = rule_severity_stats.get('medium_severity', 0)
                        low_count = rule_severity_stats.get('low_severity', 0)
                        
                        tooltip_parts = []
                        if rule_errors > 0:
                            tooltip_parts.append(f"Rule errors: {rule_errors} (Medium: {medium_count}, Low: {low_count})")
                        if ai_errors > 0:
                            tooltip_parts.append(f"AI errors: {ai_errors}")
                        
                        status_item.setToolTip("; ".join(tooltip_parts))
                else:
                    # 未知/处理中
                    if i == self.current_processing_index:
                        status_item.setIcon(icon_manager.get_icon('arrow-right-circle'))
                        status_item.setText("Processing")
                        status_item.setToolTip("Analysis in progress...")
                    else:
                        status_item.setIcon(icon_manager.get_icon('circle'))
                        status_item.setText("Waiting")
                        status_item.setToolTip("Waiting for analysis")
            else:
                # 无结果（等待/处理中）
                if i == self.current_processing_index:
                    status_item.setIcon(icon_manager.get_icon('arrow-right-circle'))
                    status_item.setText("Processing")
                    status_item.setToolTip("Analysis in progress...")
                else:
                    status_item.setIcon(icon_manager.get_icon('circle'))
                    status_item.setText("Waiting")
                    status_item.setToolTip("Waiting for analysis")

            status_item.setTextAlignment(Qt.AlignCenter)
            if i == self.current_processing_index:
                status_item.setBackground(QColor(52, 152, 219, 50))

            self.queue_table.setItem(i, 1, status_item)

        # 应用当前筛选
        self.apply_queue_filter()
        
        # 更新运行状态按钮 
        actual_count = len(self.selected_classes)  # 使用实际队列项目数
        self.run_batch_btn.setEnabled(actual_count > 0 and not (self.batch_worker and self.batch_worker.isRunning()))
        # visible_count = sum(1 for i in range(self.queue_table.rowCount()) if not self.queue_table.isRowHidden(i))
        # self.run_batch_btn.setEnabled(visible_count > 0 and not (self.batch_worker and self.batch_worker.isRunning()))

    def apply_queue_filter(self):
        """应用队列筛选"""
        if not hasattr(self, 'queue_table') or not hasattr(self, 'status_filter_combo'):
            return
        
        status_filter = self.status_filter_combo.currentText()
        error_type_filter = self.error_type_filter_combo.currentText()
        problems_only = self.show_problems_btn.isChecked()
        
        visible_count = 0
        total_count = len(self.selected_classes)
        
        for i in range(self.queue_table.rowCount()):
            should_show = self._should_show_queue_item(i, status_filter, error_type_filter, problems_only)
            self.queue_table.setRowHidden(i, not should_show)
            if should_show:
                visible_count += 1
        
        # 更新筛选统计
        if visible_count != total_count:
            self.filter_stats_label.setText(f"Showing {visible_count}/{total_count}")
            self.queue_count_label.setText(f"({visible_count}/{total_count} items)")
        else:
            self.filter_stats_label.setText("")
            self.queue_count_label.setText(f"({total_count} items)")

    def _should_show_queue_item(self, row: int, status_filter: str, error_type_filter: str, problems_only: bool) -> bool:
        """判断队列项是否应该显示"""
        if row >= len(self.selected_classes):
            return False
        
        class_path = self.selected_classes[row]
        result = self.class_analysis_results.get(class_path)
        
        # 确定当前状态
        current_status = self._get_queue_item_status(row, result)
        
        # 应用状态筛选
        if status_filter != "All Status":
            if status_filter == "Error Only" and current_status != "Error":
                return False
            elif status_filter == "Warning Only" and current_status != "Warning":
                return False
            elif status_filter == "Passed Only" and current_status != "Passed":
                return False
            elif status_filter == "Problems Only" and current_status not in ["Error", "Warning"]:
                return False
            elif status_filter == "Processing" and current_status != "Processing":
                return False
            elif status_filter == "Waiting" and current_status != "Waiting":
                return False
        
        # 应用快速问题筛选
        if problems_only and current_status not in ["Error", "Warning"]:
            return False
        
        # 应用错误类型筛选
        if error_type_filter != "All Types" and result:
            error_stats = result.get('error_statistics', {})
            rule_errors = error_stats.get('rule_errors', 0)
            ai_errors = error_stats.get('ai_errors', 0)
            rule_severity_stats = error_stats.get('rule_severity_stats', {})
            
            if error_type_filter == "Rule Errors" and rule_errors == 0:
                return False
            elif error_type_filter == "AI Errors" and ai_errors == 0:
                return False
            elif error_type_filter == "High Severity" and rule_severity_stats.get('high_severity', 0) == 0:
                return False
            elif error_type_filter == "Medium Severity" and rule_severity_stats.get('medium_severity', 0) == 0:
                return False
            elif error_type_filter == "Low Severity" and rule_severity_stats.get('low_severity', 0) == 0:
                return False
        
        return True

    def _get_queue_item_status(self, row: int, result: dict) -> str:
        """获取队列项的状态"""
        if row == self.current_processing_index:
            return "Processing"
        
        if not result:
            return "Waiting"
        
        status = (result.get('status') or '').lower()
        if status != 'success':
            return "Error"
        
        # 分析成功的情况下，根据错误统计判断
        error_stats = result.get('error_statistics', {})
        rule_errors = error_stats.get('rule_errors', 0)
        ai_errors = error_stats.get('ai_errors', 0)
        rule_severity_stats = error_stats.get('rule_severity_stats', {})
        has_high_severity = rule_severity_stats.get('has_high_severity', False)
        
        if rule_errors == 0 and ai_errors == 0:
            return "Passed"
        elif has_high_severity:
            return "Error"
        else:
            return "Warning"

    def toggle_problems_only(self, checked: bool):
        """切换只显示问题的模式"""
        if checked:
            # 当Problems Only被选中时，同步状态筛选器
            self.status_filter_combo.setCurrentText("Problems Only")
        else:
            # 当Problems Only被取消时，重置为显示所有状态
            self.status_filter_combo.setCurrentText("All Status")
        self.apply_queue_filter()

    def reset_queue_filter(self):
        """重置所有筛选"""
        self.status_filter_combo.setCurrentText("All Status")
        self.error_type_filter_combo.setCurrentText("All Types")
        self.show_problems_btn.setChecked(False)
        self.apply_queue_filter()

    def on_queue_item_double_clicked(self, item):
        """Queue item double click event - view error statistics"""
        row = self.queue_table.currentRow()
        if row < 0 or row >= len(self.selected_classes):
            return
        
        class_path = self.selected_classes[row]
        result = self.class_analysis_results.get(class_path)
        
        if not result:
            QMessageBox.information(self, "Info", "This class has not been analyzed yet")
            return
        
        # Find corresponding statistics file
        report_path = result.get('current_report_path')
        if report_path:
            stats_path = os.path.splitext(report_path)[0] + "_statistics.json"
            
            if os.path.exists(stats_path):
                try:
                    with open(stats_path, 'r', encoding='utf-8') as f:
                        statistics_data = json.load(f)
                    
                    dialog = ErrorStatisticsDialog(statistics_data, self)
                    dialog.exec()
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to load error statistics:\n{str(e)}")
            else:
                QMessageBox.information(self, "Info", "Error statistics file not found")
        else:
            # Display statistics from memory directly
            error_stats = result.get('error_statistics', {})
            statistics_data = {
                'error_statistics': error_stats,
                'class_path': class_path,
                'class_name': EnhancedListWidgetItem.extract_class_name(class_path)
            }
            dialog = ErrorStatisticsDialog(statistics_data, self)
            dialog.exec()
    
    def show_queue_context_menu(self, position):
        """Show enhanced queue right-click menu"""
        row = self.queue_table.currentRow()
        if row < 0 or row >= len(self.selected_classes) or self.queue_table.isRowHidden(row):
            return
        
        menu = QMenu(self)
        
        # 查看相关菜单项
        view_stats_action = QAction("View Error Statistics", self)
        view_stats_action.triggered.connect(lambda: self.on_queue_item_double_clicked(None))
        menu.addAction(view_stats_action)
        
        view_report_action = QAction("View Analysis Report", self)
        view_report_action.triggered.connect(self.view_selected_class_report)
        menu.addAction(view_report_action)

        # Show "View Diagram with Review" for .amd files that have been reviewed
        class_path = self.selected_classes[row]
        result = self.class_analysis_results.get(class_path)

        if class_path.lower().endswith('.amd') and result and (result.get('status') or '').lower() == 'success':
            view_diagram_review_action = QAction("📊 View Diagram with Review", self)
            _cp, _res = class_path, result
            view_diagram_review_action.triggered.connect(
                lambda checked=False, cp=_cp, r=_res: self.view_diagram_with_review(cp, r))
            menu.addAction(view_diagram_review_action)
        
        menu.addSeparator()
        
        # 筛选相关菜单
        filter_menu = QMenu("Filter Similar", self)
        
        result = self.class_analysis_results.get(class_path)
        status = self._get_queue_item_status(row, result)
        
        # 按状态筛选
        filter_same_status_action = QAction(f"Show Only {status}", self)
        filter_same_status_action.triggered.connect(lambda: self.filter_by_status(status))
        filter_menu.addAction(filter_same_status_action)
        
        # 如果有错误，添加按错误类型筛选的选项
        if result and status in ["Error", "Warning"]:
            error_stats = result.get('error_statistics', {})
            
            if error_stats.get('rule_errors', 0) > 0:
                filter_rule_errors_action = QAction("Show Only Rule Errors", self)
                filter_rule_errors_action.triggered.connect(lambda: self.filter_by_error_type("Rule Errors"))
                filter_menu.addAction(filter_rule_errors_action)
            
            if error_stats.get('ai_errors', 0) > 0:
                filter_ai_errors_action = QAction("Show Only AI Errors", self)
                filter_ai_errors_action.triggered.connect(lambda: self.filter_by_error_type("AI Errors"))
                filter_menu.addAction(filter_ai_errors_action)
            
            # 按严重程度筛选
            rule_severity_stats = error_stats.get('rule_severity_stats', {})
            if rule_severity_stats.get('high_severity', 0) > 0:
                filter_high_action = QAction("Show Only High Severity", self)
                filter_high_action.triggered.connect(lambda: self.filter_by_error_type("High Severity"))
                filter_menu.addAction(filter_high_action)
            
            if rule_severity_stats.get('medium_severity', 0) > 0:
                filter_medium_action = QAction("Show Only Medium Severity", self)
                filter_medium_action.triggered.connect(lambda: self.filter_by_error_type("Medium Severity"))
                filter_menu.addAction(filter_medium_action)
        
        menu.addMenu(filter_menu)
        
        # 快速筛选动作
        if status in ["Error", "Warning"]:
            problems_only_action = QAction("Show Problems Only", self)
            problems_only_action.triggered.connect(lambda: self.set_problems_only_filter(True))
            menu.addAction(problems_only_action)
        
        # 重置筛选
        reset_filter_action = QAction("Reset Filters", self)
        reset_filter_action.triggered.connect(self.reset_queue_filter)
        menu.addAction(reset_filter_action)
        
        menu.addSeparator()
        
        # 重新分析
        reanalyze_action = QAction("Analyze Selected", self)
        reanalyze_action.triggered.connect(self.reanalyze_selected_class)
        menu.addAction(reanalyze_action)
        
        menu.addSeparator()
        
        # 移除操作
        remove_action = QAction("Remove from Queue", self)
        remove_action.triggered.connect(self.remove_selected_class)
        menu.addAction(remove_action)
        
        menu.exec(self.queue_table.mapToGlobal(position))

    def filter_by_status(self, status: str):
        """按状态筛选"""
        status_map = {
            "Error": "Error Only",
            "Warning": "Warning Only", 
            "Passed": "Passed Only",
            "Processing": "Processing",
            "Waiting": "Waiting"
        }
        
        filter_text = status_map.get(status, "All Status")
        self.status_filter_combo.setCurrentText(filter_text)
        
        # 如果是问题状态，也勾选Problems Only按钮
        if status in ["Error", "Warning"]:
            self.show_problems_btn.setChecked(True)
        else:
            self.show_problems_btn.setChecked(False)
        
        self.apply_queue_filter()

    def filter_by_error_type(self, error_type: str):
        """按错误类型筛选"""
        self.error_type_filter_combo.setCurrentText(error_type)
        
        # 如果筛选特定错误类型，自动启用Problems Only
        self.show_problems_btn.setChecked(True)
        self.status_filter_combo.setCurrentText("Problems Only")
        
        self.apply_queue_filter()

    def set_problems_only_filter(self, enabled: bool):
        """设置只显示问题的筛选"""
        self.show_problems_btn.setChecked(enabled)
        if enabled:
            self.status_filter_combo.setCurrentText("Problems Only")
        self.apply_queue_filter()
    
    def view_selected_class_report(self):
        """View analysis report for selected class"""
        row = self.queue_table.currentRow()
        if row < 0 or row >= len(self.selected_classes):
            return
        
        class_path = self.selected_classes[row]
        result = self.class_analysis_results.get(class_path)
        
        if not result:
            QMessageBox.information(self, "Info", "This class has not been analyzed yet")
            return
        
        report_path = result.get('current_report_path')
        if report_path and os.path.exists(report_path):
            dialog = ReportPreviewDialog(report_path, self)
            dialog.exec()
        else:
            QMessageBox.warning(self, "Warning", "Report file does not exist")
    
    def reanalyze_selected_class(self):
        """Re-analyze selected class with detailed logging"""
        row = self.queue_table.currentRow()
        if row < 0 or row >= len(self.selected_classes):
            return
        
        class_path = self.selected_classes[row]
        class_name = EnhancedListWidgetItem.extract_class_name(class_path)
        
        reply = QMessageBox.question(
            self, "Confirm Re-analysis",
            f"Are you sure you want to re-analyze class {class_name}?\nCurrent mode: {self.current_mode.upper()}",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.No:
            return
        
        # Clear previous results
        if class_path in self.class_analysis_results:
            del self.class_analysis_results[class_path]
        
        # Update display
        self.update_queue_display()
        
        # Start single analysis with logging
        config = self.build_base_agent_config()
        config["class_path"] = class_path
        config["mode"] = self.current_mode
        config["enable_agent_logging"] = True  # 启用Agent日志
        
        self.agent_worker = AgentWorker(config)
        self.agent_worker.status_signal.connect(self.append_status)
        self.agent_worker.agent_step_signal.connect(self.append_agent_step)  # 连接Agent步骤信号
        self.agent_worker.finished_signal.connect(lambda success, result: self.on_single_analysis_finished(success, result, class_path))
        
        self.agent_status_label.setText(f"{self.current_mode.capitalize()}: Analyzing")
        self.append_status(f"Starting re-analysis: {class_name} ({self.current_mode} mode)")
        
        # Show loading animation
        self.loading_animation.start_animation()
        
        self.agent_worker.start()

    def append_agent_step(self, message: str):
        """添加Agent执行步骤消息（特殊格式）"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        # 使用特殊格式来区分Agent步骤和普通状态
        formatted_message = f"[{timestamp}] AGENT: {message}"
        
        self.status_text.append(formatted_message)
        
        # 自动滚动到底部
        cursor = self.status_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)  
        self.status_text.setTextCursor(cursor)
        
        QApplication.processEvents()
    
    def on_single_analysis_finished(self, success: bool, result: Dict[str, Any], class_path: str):
        """Single analysis completed"""
        class_name = EnhancedListWidgetItem.extract_class_name(class_path)
        
        if success:
            self.class_analysis_results[class_path] = result
            self.append_status(f"Re-analysis completed: {class_name}")
            
            # Display error statistics
            error_stats = result.get('error_statistics')
            if error_stats:
                rule_errors = error_stats.get('rule_errors', 0)
                ai_errors = error_stats.get('ai_errors', 0)
                if self.current_mode == "direct":
                    self.append_status(f"   Error statistics: Rule {rule_errors} errors")
                else:
                    self.append_status(f"   Error statistics: Rule {rule_errors} errors, AI {ai_errors} errors")
        else:
            error_msg = result.get('error_message', 'Analysis failed')
            self.append_status(f"Re-analysis failed: {class_name} - {error_msg}")
        
        self.agent_status_label.setText(f"Mode: {self.current_mode.capitalize()}")
        self.loading_animation.stop_animation()
        self.update_queue_display()
        self.refresh_reports_list()
    
    def remove_selected_class(self):
        """Remove selected class"""
        row = self.queue_table.currentRow()
        if row < 0 or row >= len(self.selected_classes):
            return
        
        class_path = self.selected_classes[row]
        class_name = EnhancedListWidgetItem.extract_class_name(class_path)
        
        self.selected_classes.pop(row)
        
        # Also remove analysis results
        if class_path in self.class_analysis_results:
            del self.class_analysis_results[class_path]
        
        self.update_queue_display()
        self.append_status(f"Removed from queue: {class_name}")
    
    def clear_class_queue(self):
        """Clear class queue"""
        if self.selected_classes:
            reply = QMessageBox.question(
                self, "Confirm Clear", 
                f"Are you sure you want to clear {len(self.selected_classes)} classes in the queue?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.selected_classes.clear()
                self.class_analysis_results.clear()
                self.update_queue_display()
                self.append_status("Class queue cleared")
    
    def move_class_up(self):
        """Move class up"""
        row = self.queue_table.currentRow()
        if row > 0:
            # Swap positions in list
            self.selected_classes[row], self.selected_classes[row - 1] = \
                self.selected_classes[row - 1], self.selected_classes[row]
            
            self.update_queue_display()
            self.queue_table.setCurrentCell(row - 1, 0)
    
    def move_class_down(self):
        """Move class down"""
        row = self.queue_table.currentRow()
        if 0 <= row < len(self.selected_classes) - 1:
            # Swap positions in list
            self.selected_classes[row], self.selected_classes[row + 1] = \
                self.selected_classes[row + 1], self.selected_classes[row]
            
            self.update_queue_display()
            self.queue_table.setCurrentCell(row + 1, 0)
    
    # ==================== Report Related Functions ====================
    
    def browse_reports(self):
        """Browse reports - open report list dialog"""
        dialog = ReportBrowserDialog(self)
        dialog.exec()
    
    def open_reports_directory(self):
        """Open reports directory"""
        # Choose different directory based on current mode
        if self.current_mode == "direct":
            output_dir = self.settings.value("paths/output_dir", "direct_reports")
        else:
            output_dir = self.settings.value("paths/output_dir", "agent_reports")
            
        if output_dir and os.path.exists(output_dir):
            try:
                os.startfile(output_dir)
            except Exception as e:
                QMessageBox.warning(self, "Warning", f"Unable to open directory:\n{str(e)}")
        else:
            QMessageBox.warning(self, "Warning", "Output directory does not exist")
    
    def refresh_reports_list(self):
        """Refresh reports list - update status bar count"""
        user_output_dir = self.settings.value("paths/output_dir", "agent_reports")
        
        possible_dirs = ["agent_reports", "direct_reports"]
        
        if user_output_dir and user_output_dir.strip():
            possible_dirs.insert(0, user_output_dir.strip())
        
        report_count = 0
        
        for output_dir in possible_dirs:
            if output_dir and os.path.exists(output_dir):
                try:
                    for ext in ['*.md', '*.html']:
                        report_count += len(list(Path(output_dir).glob('**/' + ext)))
                        report_count += len(list(Path(output_dir).glob(ext)))
                except Exception:
                    pass
        
        self.reports_count_label.setText(f"Reports: {report_count}")
    
    # ==================== Batch Processing Related ====================
    
    def start_batch_processing(self):
        """Start batch processing with detailed logging"""
        if not self.selected_classes:
            QMessageBox.warning(self, "Warning", "Queue is empty, please add classes to process first")
            return
        
        # Validate configuration based on current mode
        if self.current_mode == "agent":
            config_valid, error_msg = self.validate_agent_config()
            if not config_valid:
                QMessageBox.warning(self, "Configuration Error", error_msg)
                return
        
        class_count = len(self.selected_classes)
        if class_count > 2:
        
            reply = QMessageBox.question(
                self, "Batch Processing Confirmation",
                f"Are you sure you want to batch process {len(self.selected_classes)} classes?\n"
                f"Current mode: {self.current_mode.upper()}\n"
                f"This may take a long time.",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.No:
                return
        
        # Clear previous results
        self.class_analysis_results.clear()
        
        base_config = self.build_base_agent_config()
        base_config["mode"] = self.current_mode
        base_config["enable_agent_logging"] = True  # 启用详细日志
        
        self.batch_worker = BatchProcessWorker(self.selected_classes.copy(), base_config, self.diagram_files_dict)
        
        # 连接信号
        self.batch_worker.status_signal.connect(self.append_status)
        self.batch_worker.agent_step_signal.connect(self.append_agent_step)  # 连接Agent步骤信号
        self.batch_worker.current_class_signal.connect(self.on_current_class_changed)
        self.batch_worker.class_finished_signal.connect(self.on_class_finished)
        self.batch_worker.all_finished_signal.connect(self.on_batch_finished)
        
        self.run_batch_btn.setEnabled(False)
        self.stop_batch_btn.setEnabled(True)
        
        # Show loading animation
        self.loading_animation.start_animation()
        
        self.agent_status_label.setText(f"{self.current_mode.capitalize()}: Batch Processing")
        self.current_processing_index = -1
        
        self.batch_worker.start()
    
    def stop_batch_processing(self):
        """Stop batch processing"""
        if self.batch_worker and self.batch_worker.isRunning():
            reply = QMessageBox.question(
                self, "Confirm Stop",
                "Are you sure you want to stop batch processing?\nCurrent analysis will be terminated.",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return

            # UI 先行反馈
            self.stop_batch_btn.setEnabled(False)
            self.run_batch_btn.setEnabled(False)
            self.append_status("Stopping batch processing...")

            # 硬停子进程
            try:
                self.batch_worker.stop()
            except Exception:
                pass

            # 轮询等待线程结束，结束后恢复 UI
            def _poll_finish():
                if self.batch_worker and self.batch_worker.isRunning():
                    QTimer.singleShot(150, _poll_finish)
                    return
                # 恢复 UI
                self.loading_animation.stop_animation()
                self.agent_status_label.setText(f"Mode: {self.current_mode.capitalize()}")
                self.current_processing_index = -1
                self.current_processing_label.setText("")
                self.update_queue_display()
                self.run_batch_btn.setEnabled(True)
                self.stop_batch_btn.setEnabled(False)
                self.append_status("Batch processing stopped.")
            QTimer.singleShot(150, _poll_finish)
    
    def on_current_class_changed(self, class_path: str, current_index: int, total_count: int):
        """Current processing class changed"""
        self.current_processing_index = current_index - 1
        class_name = EnhancedListWidgetItem.extract_class_name(class_path)
        self.current_processing_label.setText(f"Processing: {class_name} ({current_index}/{total_count})")
        
        self.update_queue_display()
    
    def on_class_finished(self, success: bool, class_path: str, result: Dict[str, Any]):
        """Single class processing completed"""
        class_name = EnhancedListWidgetItem.extract_class_name(class_path)
        
        # 保存result前，先检查error_statistics是否完整
        if success and result.get('error_statistics'):
            error_stats = result['error_statistics']
            print(f"🔍 保存结果检查 {class_name}:")
            print(f"   error_statistics keys: {list(error_stats.keys())}")
            
            if 'rule_severity_stats' in error_stats:
                rule_severity_stats = error_stats['rule_severity_stats']
                print(f"   rule_severity_stats: {rule_severity_stats}")
                print(f"   has_high_severity: {rule_severity_stats.get('has_high_severity', False)}")
            else:
                print(f"   缺少 rule_severity_stats 字段！")
        
        # 保存result到全局状态
        self.class_analysis_results[class_path] = result
        
        if success:
            self.append_status(f"Completed: {class_name}")
            
            # 显示brief results and error statistics
            if result.get('current_report_path'):
                report_name = os.path.basename(result['current_report_path'])
                self.append_status(f"   Generated report: {report_name}")
            
            # 显示error statistics
            error_stats = result.get('error_statistics')
            if error_stats:
                rule_errors = error_stats.get('rule_errors', 0)
                ai_errors = error_stats.get('ai_errors', 0)
                
                # 新增：显示仲裁信息（仅添加这一段）
                arbitration_info = error_stats.get('arbitration_info', {})
                if arbitration_info.get('enabled'):
                    if arbitration_info.get('completed'):
                        primary_count = arbitration_info.get('primary_errors_found', 0)
                        fallback_count = arbitration_info.get('fallback_errors_found', 0) 
                        final_count = arbitration_info.get('final_confirmed', 0)
                        self.append_status(f"   AI仲裁: {primary_count}个→{fallback_count}个→最终{final_count}个错误")
                    else:
                        self.append_status(f"   AI仲裁: 未触发（无AI错误检测到）")
                # 仲裁信息显示结束
                
                # 新增：显示severity统计
                rule_severity_stats = error_stats.get('rule_severity_stats', {})
                if rule_severity_stats:
                    high_count = rule_severity_stats.get('high_severity', 0)
                    medium_count = rule_severity_stats.get('medium_severity', 0)
                    low_count = rule_severity_stats.get('low_severity', 0)
                    
                    if self.current_mode == "direct":
                        self.append_status(f"   Error statistics: Rule {rule_errors} errors (High: {high_count}, Medium: {medium_count}, Low: {low_count})")
                    else:
                        self.append_status(f"   Error statistics: Rule {rule_errors} errors (High: {high_count}, Medium: {medium_count}, Low: {low_count}), AI {ai_errors} errors")
                else:
                    if self.current_mode == "direct":
                        self.append_status(f"   Error statistics: Rule {rule_errors} errors")
                    else:
                        self.append_status(f"   Error statistics: Rule {rule_errors} errors, AI {ai_errors} errors")
            
            # 立即更新queue display，确保使用最新数据
            self.update_queue_display()
            
            # Refresh report count
            QTimer.singleShot(1000, self.refresh_reports_list)
        else:
            error_msg = result.get('error_message', 'Processing failed')
            self.append_status(f"Failed: {class_name} - {error_msg}")
            
            self.update_queue_display()
    
    def on_batch_finished(self, summary: Dict[str, Any]):
        """Batch processing completed"""
        # Reset UI state
        self.run_batch_btn.setEnabled(True)
        self.stop_batch_btn.setEnabled(False)
        
        # Stop loading animation
        self.loading_animation.stop_animation()
        
        self.agent_status_label.setText(f"Mode: {self.current_mode.capitalize()}")
        self.current_processing_index = -1
        self.current_processing_label.setText("")
        self.update_queue_display()
        
        # Refresh reports list
        self.refresh_reports_list()
        
        if "error" in summary:
            QMessageBox.critical(self, "Batch Processing Error", f"Batch processing error:\n{summary['error']}")
            return
        
        # Display completion notification
        total = summary.get('total_classes', 0)
        success = summary.get('success_count', 0)
        failed = summary.get('failed_count', 0)
        stopped = summary.get('stopped', False)
        
        # Calculate total errors
        total_rule_errors = 0
        total_ai_errors = 0
        # 新增：计算仲裁统计（仅添加这一段）
        total_arbitrations = 0
        total_filtered_errors = 0
        
        for class_path, result in self.class_analysis_results.items():
            error_stats = result.get('error_statistics', {})
            total_rule_errors += error_stats.get('rule_errors', 0)
            total_ai_errors += error_stats.get('ai_errors', 0)
            
            # 统计仲裁信息
            arbitration_info = error_stats.get('arbitration_info', {})
            if arbitration_info.get('enabled') and arbitration_info.get('completed'):
                total_arbitrations += 1
                primary_errors = arbitration_info.get('primary_errors_found', 0)
                fallback_errors = arbitration_info.get('fallback_errors_found', 0)
                final_errors = arbitration_info.get('final_confirmed', 0)
                
                total_filtered_errors += max(0, primary_errors - final_errors)
        # 仲裁统计计算结束
        
        result_text = f"""Batch Processing Completed!
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    Processing Statistics:
    Mode: {self.current_mode.upper()}
    Total: {total} classes
    Success: {success} classes
    Failed: {failed} classes
    Success Rate: {(success/total*100) if total > 0 else 0:.1f}%

    Error Statistics:
    Rule Errors: {total_rule_errors} errors"""
        
        if self.current_mode == "agent":
            result_text += f"""
    AI Errors: {total_ai_errors} errors (Arbitration)
    Total Errors: {total_rule_errors + total_ai_errors} errors"""
            
            
            if total_arbitrations > 0:
                result_text += f"""

    AI Error Arbitration Summary:
    Classes with Arbitration: {total_arbitrations} / {success}
    Arbitration Effectiveness: {(total_arbitrations/success*100) if success > 0 else 0:.1f}% coverage"""
            # 仲裁统计显示结束
        else:
            result_text += f"""
    Total Errors: {total_rule_errors} errors"""
        
        result_text += f"""

    Status: {'User Stopped' if stopped else 'Normal Completion'}"""
        
        # Show completion dialog
        if stopped:
            QMessageBox.information(self, "Batch Processing Stopped", f"Batch processing has been stopped\n\n{result_text}")
        else:
            QMessageBox.information(self, "Batch Processing Completed", f"Batch processing completed\n\n{result_text}")

    def validate_agent_config(self) -> tuple:
        """Validate Agent configuration"""
        deepseek_key = self.settings.value("api/deepseek_api_key", "")
        if not deepseek_key:
            return False, "API key not configured, please set in settings"
        
        embedding_key = self.settings.value("api/embedding_api_key", "")
        if not embedding_key:
            return False, "Embedding vector API key not configured, please set in settings"
        
        kb_path = self.settings.value("paths/knowledge_base_path", "")
        if not kb_path:
            return False, "RAG knowledge base path not configured, please set in settings"
        
        if not os.path.exists(kb_path):
            return False, f"RAG knowledge base path does not exist: {kb_path}"
        
        if not AGENT_AVAILABLE:
            return False, "AI Agent module unavailable, please check dependency installation"
        
        return True, ""
    
    
    
    def build_base_agent_config(self) -> Dict[str, Any]:
        """构建基础Agent配置（添加仲裁设置）"""
        # 根据模式选择输出目录
        if self.current_mode == "direct":
            output_dir = self.settings.value("paths/output_dir", "direct_reports")
        else:
            output_dir = self.settings.value("paths/output_dir", "agent_reports")

        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        per_class_timeout = int(self.settings.value("agent/per_class_timeout_sec", 360))
        model_type = self.settings.value("api/model_type", "gpt5-mini")
        
        config = {
          
            "api_key": self.settings.value("api/deepseek_api_key", ""),
            "embedding_api_key": self.settings.value("api/embedding_api_key", ""),
            "knowledge_base_path": self.settings.value("paths/knowledge_base_path", ""),
            "output_dir": output_dir,
            "report_output_dir": output_dir,
            "ascet_version": self.detect_ascet_version_silently(),
            "diagram_name": self.settings.value("ascet/diagram_name", "Main"),
            "method_name": self.settings.value("ascet/method_name", "calc"),
            "auto_cleanup": self.settings.value("agent/auto_cleanup", True, type=bool),
            "mark_failed_reports": self.settings.value("agent/mark_failed_reports", True, type=bool),
            "max_retries": int(self.settings.value("agent/max_retries", 2)),
            "mode": self.current_mode,
            "model_type": model_type,
            "per_class_timeout_sec": per_class_timeout,
            # 仲裁相关配置
            "enable_ai_arbitration": True,
            "arbitration_strategy": "conservative", 
            "arbitration_log_level": "INFO"
        }

    
        return config

# ==================== RAG Related Methods ====================
    
    def open_rag_manager(self):
        """Open RAG manager"""
        if not RAG_AVAILABLE:
            QMessageBox.warning(self, "RAG Unavailable", "RAG module unavailable, please check if RagCore.py is correctly imported")
            return
        
        api_key = self.settings.value("api/embedding_api_key", "")
        kb_path = self.settings.value("paths/knowledge_base_path", "")
        
        if not api_key or not kb_path:
            reply = QMessageBox.question(
                self, "Configuration Incomplete", 
                "RAG configuration incomplete, would you like to open settings first to configure?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.open_settings()
                return
        
        if self.rag_manager_dialog is None:
            self.rag_manager_dialog = RAGManagementDialog(self)
        
        self.rag_manager_dialog.show()
        self.rag_manager_dialog.raise_()
        self.rag_manager_dialog.activateWindow()
    
    def refresh_rag_status(self):
        """Refresh RAG status"""
        if not RAG_AVAILABLE:
            self.rag_status_indicator.setStyleSheet("color: red; font-size: 16px;")
            self.rag_count_label.setText("RAG: Unavailable")
            return
        
        try:
            api_key = self.settings.value("api/embedding_api_key", "")
            kb_path = self.settings.value("paths/knowledge_base_path", "")
            
            if not api_key:
                self.rag_status_indicator.setStyleSheet("color: orange; font-size: 16px;")
            elif not kb_path or not os.path.exists(kb_path):
                self.rag_status_indicator.setStyleSheet("color: orange; font-size: 16px;")
            else:
                self.rag_status_indicator.setStyleSheet("color: green; font-size: 16px;")
            
            self.append_status("RAG status check completed")
            
        except Exception as e:
            self.rag_status_indicator.setStyleSheet("color: red; font-size: 16px;")
            self.append_status(f"RAG status check failed: {str(e)}")
    
    # ==================== Database Scanning Related ====================
    
    def scan_all_database(self):
        """Scan entire database - 自动检测版本"""
        if self.scan_worker and self.scan_worker.isRunning():
            QMessageBox.warning(self, "Warning", "Scan task is in progress, please wait for completion")
            return
        
        reply = QMessageBox.question(
            self, "Confirm Scan", 
            "Scanning the entire database may take a long time.\n"
            "Only classes with 'calc' method in 'Main' diagram will be included.\n"
            "Continue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.No:
            return
        
        # 静默检测版本
        detected_version = self.detect_ascet_version_silently()
        
        params = {
            "version": detected_version,
            "debug": self.settings.value("log/enable_debug", False, type=bool),
            "diagram_name": self.settings.value("ascet/diagram_name", "Main"),
            "method_name": self.settings.value("ascet/method_name", "calc")
        }
        
        self.start_scan_task("scan_all", params)

    def scan_folder(self):
        """Scan specified folder - 自动检测版本"""
        if self.scan_worker and self.scan_worker.isRunning():
            QMessageBox.warning(self, "Warning", "Scan task is in progress, please wait for completion")
            return
        
        folder_path, ok = QInputDialog.getText(
            self, "Scan Folder", 
            "Please enter the folder path to scan:",
            text=self.settings.value("last_scanned_folder", "")
        )
        
        if not ok or not folder_path.strip():
            return
        
        self.settings.setValue("last_scanned_folder", folder_path.strip())
        
        # 静默检测版本
        detected_version = self.detect_ascet_version_silently()
        
        params = {
            "version": detected_version,
            "debug": self.settings.value("log/enable_debug", False, type=bool),
            "folder_path": folder_path.strip()
        }
        
        self.start_scan_task("scan_folder", params)
    
    def start_scan_task(self, action: str, params: Dict[str, Any]):
        """Start scan task"""
        self.scan_worker = DatabaseScanWorker(action, params)
        
        self.scan_worker.status_signal.connect(self.append_status)
        self.scan_worker.finished_signal.connect(self.on_scan_finished)
        self.scan_worker.progress_signal.connect(self.update_scan_progress)  # Connect scan progress signal
        
        self.scan_all_btn.setEnabled(False)
        self.scan_folder_btn.setEnabled(False)
        
        # Show scan progress bar and loading animation
        self.scan_progress_bar.setVisible(True)
        self.scan_progress_bar.setValue(0)
        self.loading_animation.start_animation()
        
        self.connection_status_label.setText("Scanning...")
        self.append_status(f"Starting {action} scan...")
        
        self.scan_worker.start()
    
    def update_scan_progress(self, progress: int, text: str):
        """Update scan progress"""
        if self.scan_progress_bar.isVisible():
            self.scan_progress_bar.setValue(progress)
            # Progress bar only shows percentage, specific text in status log
        self.append_status(text)
    
    def on_scan_finished(self, success: bool, message: str, data: Dict[str, Any]):
        """Scan completion handling"""
        self.scan_all_btn.setEnabled(True)
        self.scan_folder_btn.setEnabled(True)  # Fix: Scan folder button should also be re-enabled
        
        # Hide scan progress bar and animation
        self.scan_progress_bar.setVisible(False)
        self.loading_animation.stop_animation()
        
        if success:
            self.connection_status_label.setText("Connected")
            
            self.available_classes = {path: {} for path in data.get("class_paths", [])}
            self.structure_tree = data.get("structure_tree", {})
            self.diagram_files = data.get("diagram_files", [])  # Store diagram files
            
            self.populate_class_tree()
            
            class_count = len(self.available_classes)
            diagram_count = len(self.diagram_files)
            self.classes_count_label.setText(f"Classes: {class_count}, Diagrams: {diagram_count}")
            
            self.append_status(f"Scan successful: {message}")
            
            stats = data.get("statistics")
            if stats:
                stats_text = f"Scan statistics: Total classes={stats.total_classes}, Time taken={stats.scan_duration:.2f}s"
                self.append_status(stats_text)
        else:
            self.connection_status_label.setText("Scan Failed")
            self.append_status(f"Scan failed: {message}")
            QMessageBox.critical(self, "Scan Failed", f"Scan failed:\n{message}")
    
    def populate_class_tree(self):
        """Populate class structure tree with classes and diagrams in correct hierarchy"""
        self.class_tree.clear()
        self.diagram_files_dict.clear()  # Clear diagram dict for fresh population
        
        if not self.available_classes and not self.diagram_files:
            return
        
        path_dict = {}
        
        # Add classes to tree
        for class_path in self.available_classes.keys():
            parts = class_path.split('\\')
            parts = [p for p in parts if p]
            
            current_dict = path_dict
            current_path = ""
            
            for i, part in enumerate(parts):
                if current_path:
                    current_path += "\\"
                current_path += part
                
                if part not in current_dict:
                    current_dict[part] = {
                        "__path": current_path,
                        "__children": {},
                        "__is_class": i == len(parts) - 1,
                        "__is_diagram": False
                    }
                
                if i < len(parts) - 1:
                    current_dict = current_dict[part]["__children"]
        
        # Add diagrams to tree in their correct folder positions
        if self.diagram_files:
            for diagram_info in self.diagram_files:
                diagram_name = diagram_info['name']
                diagram_path = diagram_info['file_path']
                relative_path = diagram_info['relative_path']
                
                # Parse relative path to find correct position in tree
                # Convert backslashes to forward slashes for consistency
                rel_parts = relative_path.replace('\\', '/').split('/')
                
                # Remove file extension from last part if it's there
                if rel_parts[-1].endswith('.amd'):
                    rel_parts[-1] = diagram_name
                else:
                    rel_parts[-1] = diagram_name
                
                # Navigate/create path in path_dict
                current_dict = path_dict
                current_path = ""
                
                # Process all parts except the last one (which is the diagram itself)
                for i, part in enumerate(rel_parts[:-1]):
                    if not part:  # Skip empty parts
                        continue
                    
                    if current_path:
                        current_path += "\\"
                    current_path += part
                    
                    if part not in current_dict:
                        current_dict[part] = {
                            "__path": current_path,
                            "__children": {},
                            "__is_class": False,
                            "__is_diagram": False
                        }
                    current_dict = current_dict[part]["__children"]
                
                # Add the diagram as final item
                if current_path:
                    current_path += "\\"
                current_path += diagram_name
                
                safe_name = f"📊 {diagram_name}"
                current_dict[safe_name] = {
                    "__path": diagram_path,
                    "__children": {},
                    "__is_class": False,
                    "__is_diagram": True,
                    "__diagram_file": diagram_path
                }
                
                # Store diagram in dict for quick lookup during tree clicks
                self.diagram_files_dict[diagram_path] = diagram_info
        
        def add_items(parent, children_dict):
            for key, value in sorted(children_dict.items()):
                if key.startswith("__"):
                    continue
                
                item = QTreeWidgetItem([key])
                item.setData(0, Qt.UserRole, value["__path"])
                
                # Setup icons
                if value.get("__is_diagram", False):
                    item.setIcon(0, self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon))
                elif value["__is_class"]:
                    item.setIcon(0, self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon))
                else:
                    item.setIcon(0, self.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon))
                
                parent.addChild(item)
                
                if value["__children"]:
                    add_items(item, value["__children"])
        
        # Add all items to the tree
        for key, value in sorted(path_dict.items()):
            item = QTreeWidgetItem([key])
            item.setData(0, Qt.UserRole, value["__path"])
            
            # Setup icons
            if value.get("__is_diagram", False):
                item.setIcon(0, self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon))
            elif value["__is_class"]:
                item.setIcon(0, self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon))
            else:
                item.setIcon(0, self.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon))
            
            self.class_tree.addTopLevelItem(item)
            
            if value["__children"]:
                add_items(item, value["__children"])
        
        self.class_tree.expandToDepth(0)
    
    def filter_tree(self, text: str):
        """Filter tree content"""
        if not text.strip():
            self.show_all_tree_items()
            return
        
        text = text.lower()
        
        def should_show_item(item):
            path = item.data(0, Qt.UserRole) or ""
            name = item.text(0)
            
            if text in name.lower() or text in path.lower():
                return True
            
            for i in range(item.childCount()):
                if should_show_item(item.child(i)):
                    return True
            
            return False
        
        def set_item_visibility(item, visible):
            item.setHidden(not visible)
            for i in range(item.childCount()):
                child_visible = should_show_item(item.child(i))
                set_item_visibility(item.child(i), child_visible)
        
        for i in range(self.class_tree.topLevelItemCount()):
            top_item = self.class_tree.topLevelItem(i)
            visible = should_show_item(top_item)
            set_item_visibility(top_item, visible)
    
    def show_all_tree_items(self):
        """Show all tree items"""
        def show_item(item):
            item.setHidden(False)
            for i in range(item.childCount()):
                show_item(item.child(i))
        
        for i in range(self.class_tree.topLevelItemCount()):
            show_item(self.class_tree.topLevelItem(i))
    
    def search_classes(self):
        """Search classes"""
        text = self.search_edit.text().strip()
        if not text:
            QMessageBox.information(self, "Search", "Please enter search keywords")
            return
        
        matches = []
        for class_path in self.available_classes.keys():
            if text.lower() in class_path.lower():
                matches.append(class_path)
        
        if matches:
            self.show_search_results(text, matches)
        else:
            QMessageBox.information(self, "Search Results", f"No classes found containing '{text}'")
    
    def show_search_results(self, search_text: str, matches: List[str]):
        """Show search results dialog"""
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Search Results - '{search_text}'")
        dialog.setModal(True)
        dialog.resize(600, 400)
        
        layout = QVBoxLayout(dialog)
        
        results_label = QLabel(f"Found {len(matches)} matching classes:")
        layout.addWidget(results_label)
        
        results_list = QListWidget()
        for match in matches:
            item = EnhancedListWidgetItem(match, self.show_class_names)
            results_list.addItem(item)
        
        results_list.itemDoubleClicked.connect(
            lambda item: self.add_class_from_search(item.data(Qt.UserRole), dialog)
        )
        
        layout.addWidget(results_list)
        
        btn_layout = QHBoxLayout()
        
        add_btn = QPushButton("Add to Queue")
        add_btn.clicked.connect(
            lambda: self.add_class_from_search(
                results_list.currentItem().data(Qt.UserRole) if results_list.currentItem() else "", 
                dialog
            )
        )
        
        add_all_btn = QPushButton("Add All")
        add_all_btn.clicked.connect(
            lambda: self.add_multiple_classes_from_search(matches, dialog)
        )
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.close)
        
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(add_all_btn)
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)
        
        dialog.exec()
    
    def add_class_from_search(self, class_path: str, dialog: QDialog):
        """Add single class from search results"""
        if class_path and class_path not in self.selected_classes:
            self.selected_classes.append(class_path)
            self.update_queue_display()
            class_name = EnhancedListWidgetItem.extract_class_name(class_path)
            self.append_status(f"Added to queue: {class_name}")
            dialog.close()
    
    def add_multiple_classes_from_search(self, class_paths: List[str], dialog: QDialog):
        """Add multiple classes from search results"""
        added_count = 0
        for class_path in class_paths:
            if class_path not in self.selected_classes:
                self.selected_classes.append(class_path)
                added_count += 1
        
        if added_count > 0:
            self.update_queue_display()
            self.append_status(f"Added {added_count} classes to queue")
        
        dialog.close()
    
    # ==================== Tree Operations Related ====================
    
    def on_tree_item_clicked(self, item, column):
        """Tree item click event"""
        selected_items = self.class_tree.selectedItems()
        valid_items = []
        
        for item in selected_items:
            path = item.data(0, Qt.UserRole)
            # Check if it's a class or a diagram
            if path:
                if path in self.available_classes or path in self.diagram_files_dict:
                    valid_items.append(path)
        
        self.add_selected_btn.setEnabled(len(valid_items) > 0)

        # Push the single selected class to the chat panel (if exactly one class selected)
        if (
            hasattr(self, "chat_panel")
            and self.chat_panel is not None
            and len(valid_items) == 1
            and valid_items[0] in self.available_classes
        ):
            self.chat_panel.set_class(valid_items[0], self.available_classes)
    
    def on_tree_item_double_clicked(self, item, column):
        """Tree item double click event - add to queue for both classes and diagrams"""
        path = item.data(0, Qt.UserRole)
        
        # Check if it's a class or a diagram
        if path:
            item_name = None
            item_type = None
            
            if path in self.available_classes:
                item_type = "class"
                item_name = EnhancedListWidgetItem.extract_class_name(path)
            elif path in self.diagram_files_dict:
                item_type = "diagram"
                diagram_info = self.diagram_files_dict[path]
                item_name = diagram_info['name']
            
            if item_type and item_name:
                if path not in self.selected_classes:
                    self.selected_classes.append(path)
                    self.update_queue_display()
                    self.append_status(f"Added to queue: {item_name} ({item_type})")
                else:
                    QMessageBox.information(self, "Info", f"This {item_type} is already in the queue")
    
    def add_selected_classes(self):
        """Add selected classes and diagrams to queue"""
        selected_items = self.class_tree.selectedItems()
        added_count = 0
        
        for item in selected_items:
            path = item.data(0, Qt.UserRole)
            # Check if it's a class or a diagram
            if path:
                if (path in self.available_classes or path in self.diagram_files_dict) and path not in self.selected_classes:
                    self.selected_classes.append(path)
                    added_count += 1
        
        if added_count > 0:
            self.update_queue_display()
            self.append_status(f"Added {added_count} items to queue")
        elif selected_items:
            QMessageBox.information(self, "Info", "All selected items are already in the queue")
    
    def show_tree_context_menu(self, position):
        """Show context menu for tree items"""
        item = self.class_tree.itemAt(position)
        if not item:
            return
        
        path = item.data(0, Qt.UserRole)
        if not path:
            return
        
        # Check if it's a diagram
        if path in self.diagram_files_dict:
            menu = QMenu()
            
            view_diagram_action = menu.addAction("📊 View Diagram")
            view_diagram_action.triggered.connect(lambda: self.view_diagram(path))
            
            add_to_queue_action = menu.addAction("➕ Add to Queue")
            add_to_queue_action.triggered.connect(lambda: self.add_diagram_to_queue(path))
            
            menu.exec(self.class_tree.mapToGlobal(position))
    
    def view_diagram(self, diagram_path: str):
        """View diagram in viewer dialog"""
        if not DIAGRAM_VIEWER_AVAILABLE:
            QMessageBox.warning(self, "Warning", "Diagram viewer not available")
            return
        
        diagram_info = self.diagram_files_dict.get(diagram_path)
        if not diagram_info:
            return
        
        # Parse diagram XML
        diagram_data = self.parse_diagram_xml(diagram_path, diagram_info['name'])
        
        if diagram_data:
            # Build scope+range dict from sibling .amd files so the viewer can annotate elements
            scope_dict = {}
            try:
                from src.diagrams.diagram_ai_review import DiagramNetlistExtractor
                scope_dict = DiagramNetlistExtractor.build_element_dict(diagram_path)
            except Exception:
                pass
            # Merge global_dict range info for broader signal coverage
            try:
                from src.diagrams.diagram_ai_review import DiagramAIReviewFlow
                from src.diagrams.rule_base import build_global_dict
                export_folder = DiagramAIReviewFlow._find_export_folder(diagram_path)
                if export_folder:
                    gd = build_global_dict(export_folder)
                    for sig, cfg in gd.items():
                        if sig not in scope_dict:
                            scope_dict[sig] = {}
                        # Map global_dict PascalCase keys → scope_dict camelCase keys
                        for gkey, skey in (("Min", "min"), ("Max", "max"), ("ImplMin", "implMin"), ("ImplMax", "implMax")):
                            if cfg.get(gkey) is not None and not scope_dict[sig].get(skey):
                                scope_dict[sig][skey] = cfg[gkey]
            except Exception:
                pass
            # Show viewer dialog
            viewer = DiagramViewerDialog(diagram_data, self, scope_dict=scope_dict)
            viewer.exec()
        else:
            QMessageBox.critical(self, "Error", "Failed to parse diagram file")

    def view_diagram_with_review(self, diagram_path: str, result: dict):
        """View diagram with AI review wire colour coding (green = OK, red = defective)
        and rule-base wire colour coding (orange)."""
        if not DIAGRAM_VIEWER_AVAILABLE:
            QMessageBox.warning(self, "Warning", "Diagram viewer not available")
            return

        diagram_info = self.diagram_files_dict.get(diagram_path)
        if not diagram_info:
            QMessageBox.warning(self, "Warning", "Diagram info not found")
            return

        diagram_data = self.parse_diagram_xml(diagram_path, diagram_info['name'])
        if not diagram_data:
            QMessageBox.critical(self, "Error", "Failed to parse diagram file")
            return

        try:
            from src.diagrams.diagram_ai_review import parse_defective_wires
            defective_wire_indices = parse_defective_wires(result.get('ai_review', ''))
        except Exception:
            defective_wire_indices = None

        # Build scope dict (scope + implType + range per variable) from sibling .main.amd / .implementation.dp.amd
        scope_dict = {}
        try:
            from src.diagrams.diagram_ai_review import DiagramNetlistExtractor
            scope_dict = DiagramNetlistExtractor.build_element_dict(diagram_path)
        except Exception:
            pass

        # Merge global_dict range info for broader signal coverage
        try:
            from src.diagrams.diagram_ai_review import DiagramAIReviewFlow
            from src.diagrams.rule_base import build_global_dict
            export_folder = DiagramAIReviewFlow._find_export_folder(diagram_path)
            if export_folder:
                gd = build_global_dict(export_folder)
                for sig, cfg in gd.items():
                    if sig not in scope_dict:
                        scope_dict[sig] = {}
                    # Map global_dict PascalCase keys → scope_dict camelCase keys
                    for gkey, skey in (("Min", "min"), ("Max", "max"), ("ImplMin", "implMin"), ("ImplMax", "implMax")):
                        if cfg.get(gkey) is not None and not scope_dict[sig].get(skey):
                            scope_dict[sig][skey] = cfg[gkey]
        except Exception:
            pass

        # Extract rule-base errors and map to wire indices
        rule_defective_wire_indices = None
        rule_error_details = []
        try:
            error_stats = result.get('error_statistics', {})
            rule_error_details = error_stats.get('rule_error_details', [])
            if rule_error_details:
                from src.diagrams.rule_base import map_rule_errors_to_wire_indices
                rule_defective_wire_indices = map_rule_errors_to_wire_indices(
                    rule_error_details, diagram_data
                )
        except Exception:
            pass

        viewer = DiagramViewerDialog(diagram_data, self, defective_wire_indices,
                                     scope_dict=scope_dict,
                                     rule_defective_wire_indices=rule_defective_wire_indices,
                                     rule_error_details=rule_error_details)
        viewer.exec()

    def parse_diagram_xml(self, xml_file_path: str, diagram_name: str) -> Optional[Dict]:
        """Parse diagram XML file and extract block/connection data"""
        try:
            tree = ET.parse(xml_file_path)
            root = tree.getroot()
            
            # Remove namespaces
            for el in root.iter():
                if '}' in el.tag:
                    el.tag = el.tag.split('}', 1)[1]

            # Build parent map for hierarchy traversal (needed for port name resolution)
            parent_map = {c: p for p in root.iter() for c in p}

            data = {
                "diagram_name": diagram_name,
                "source_xml_file": xml_file_path,
                "blocks": [],
                "connections": [],
                "sequence_calls": []
            }
            
            # Find main specification
            main_spec = root.find('.//Specification[@name="Main"]')
            if main_spec is None:
                main_spec = root.find('.//Specification')
            
            if main_spec is None:
                return data
            
            TARGET_TAGS = ['ComplexElement', 'SimpleElement', 'Literal', 'Operator', 'Junction', 'Connector', 'ConnectionPoint']
            DIAGRAM_PORTS = ['ReturnPort', 'ArgumentPort', 'MessagePort', 'Parameter', 'TriggerPort', 'SelectorPort']
            VALID_PORT_TAGS = ['ReturnPort', 'SelectorPort', 'ArgumentPort', 'TriggerPort', 'MessagePort']
            parsed_blocks = {}
            
            # Parse blocks
            for elem in main_spec.iter():
                if elem.tag not in TARGET_TAGS and elem.tag not in DIAGRAM_PORTS:
                    continue
                
                b_oid = elem.attrib.get('graphicOID', '')
                if not b_oid or b_oid == "-1":
                    continue
                
                pos = elem.find('./Position')
                if pos is None:
                    continue
                
                bx = float(pos.attrib.get('x', 0))
                by = float(pos.attrib.get('y', 0))
                
                b_type = elem.tag

                # Standalone diagram ports (e.g. ReturnPort, ArgumentPort at top level)
                # become SimpleElement blocks so they render as named boxes
                if b_type in DIAGRAM_PORTS:
                    elem_parent = parent_map.get(elem)
                    if elem_parent is not None and elem_parent.tag == 'DiagramElement':
                        b_name = (elem.get('elementName') or elem.get('methodName') or
                                  elem.get('name') or b_type)
                        if b_type == 'ReturnPort':
                            b_name = f"return / {b_name}"
                        b_type = 'SimpleElement'
                    else:
                        continue  # port is a child inside Interfaces — skip
                else:
                    if b_type == 'Literal':
                        b_name = elem.attrib.get('value', '???')
                    elif b_type == 'Operator':
                        b_name = elem.attrib.get('operator', elem.attrib.get('kind', elem.attrib.get('type', 'Op')))
                    elif b_type in ['Junction', 'Connector', 'ConnectionPoint']:
                        b_name = ''
                    else:
                        b_name = elem.attrib.get('elementName', elem.tag)
                
                block_data = {
                    "id": b_oid,
                    "name": b_name,
                    "type": b_type,
                    "position": {"x": bx, "y": by},
                    "ports": []
                }
                
                # Parse ports — only VALID_PORT_TAGS, with full parent-hierarchy name resolution
                interfaces = elem.find('.//Interfaces')
                if interfaces is not None:
                    for port in interfaces.iter():
                        if port.tag not in VALID_PORT_TAGS:
                            continue

                        p_oid = port.attrib.get('graphicOID')
                        if not p_oid or p_oid == "-1":
                            continue
                        
                        is_visible = port.attrib.get('visibility', 'true').lower() == 'true'
                        
                        p_pos = port.find('./Position')
                        if p_pos is not None:
                            px = float(p_pos.attrib.get('x', 0))
                            py = float(p_pos.attrib.get('y', 0))
                        else:
                            px, py = bx, by
                        
                        # Robust port name: direct attrs → parent MethodPort → grandparent
                        p_name = (port.get('name') or port.get('elementName') or
                                  port.get('methodName') or port.get('instanceName'))
                        if not p_name:
                            port_parent = parent_map.get(port)
                            if port_parent is not None:
                                if port_parent.tag == 'MethodPort':
                                    p_name = port_parent.get('methodName') or port_parent.get('name')
                                if not p_name:
                                    grand_el = parent_map.get(port_parent)
                                    if grand_el is not None:
                                        p_name = (grand_el.get('elementName') or grand_el.get('instanceName') or
                                                  grand_el.get('methodName') or grand_el.get('ClassName'))
                        if not p_name:
                            p_name = port.tag
                        if port.attrib.get('nameVisibility', 'true').lower() == 'false':
                            p_name = ""
                        
                        block_data["ports"].append({
                            "id": p_oid,
                            "name": p_name,
                            "tag": port.tag,
                            "position": {"x": px, "y": py},
                            "is_visible": is_visible
                        })
                
                if b_oid not in parsed_blocks or len(block_data["ports"]) > len(parsed_blocks.get(b_oid, {}).get("ports", [])):
                    parsed_blocks[b_oid] = block_data
            
            data["blocks"] = list(parsed_blocks.values())

            # Parse sequence call markers (execution order labels on the diagram)
            for seq in main_spec.findall('.//SequenceCall'):
                seq_num = seq.get('sequenceNumber', '0')
                is_seq_visible = seq.get('userVisibility', 'true').lower() == 'true'

                if is_seq_visible and seq_num != '0':
                    pos_el = seq.find('./Position')
                    if pos_el is not None:
                        sx = float(pos_el.get('x', 0))
                        sy = float(pos_el.get('y', 0))

                        method_name = seq.get('methodName', '')
                        text = f"/{seq_num}/{method_name}" if method_name else f"/{seq_num}/"

                        port_method = ""
                        seq_parent = parent_map.get(seq)
                        if seq_parent is not None and seq_parent.tag == 'MethodPort':
                            port_method = seq_parent.get('methodName', '')

                        # Walk up parent hierarchy to find the enclosing block's graphicOID
                        _BLOCK_TAGS_SEQ = {'ComplexElement', 'SimpleElement', 'Literal',
                                           'Operator', 'Junction', 'Connector', 'ConnectionPoint'}
                        block_oid = None
                        ancestor = parent_map.get(seq)
                        while ancestor is not None:
                            if ancestor.tag in _BLOCK_TAGS_SEQ:
                                candidate_oid = ancestor.get('graphicOID')
                                if candidate_oid and candidate_oid != "-1":
                                    block_oid = candidate_oid
                                    break
                            ancestor = parent_map.get(ancestor)

                        data["sequence_calls"].append({
                            "text": text,
                            "port_method": port_method,
                            "position": {"x": sx, "y": sy},
                            "block_oid": block_oid,
                            "calc_num": int(seq_num)
                        })
            
            # Parse connections
            parsed_conns = set()
            for conn in main_spec.findall('.//Connection'):
                start_elem = conn.find('.//Start')
                end_elem = conn.find('.//End')
                
                if start_elem is None or end_elem is None:
                    continue
                
                src_oid = start_elem.attrib.get('graphicOID')
                tgt_oid = end_elem.attrib.get('graphicOID')
                
                if not src_oid or not tgt_oid:
                    continue
                
                bends = tuple((float(b.attrib.get('x', 0)), float(b.attrib.get('y', 0))) for b in conn.findall('.//BendPoint'))
                c_key = (src_oid, tgt_oid, bends)
                
                if c_key not in parsed_conns:
                    parsed_conns.add(c_key)
                    data["connections"].append({
                        "source_oid": src_oid,
                        "target_oid": tgt_oid,
                        "bend_points": [{"x": pt[0], "y": pt[1]} for pt in bends]
                    })
            
            return data
        except Exception as e:
            self.append_status(f"Error parsing diagram XML: {str(e)}")
            return None
    
    def add_diagram_to_queue(self, diagram_path: str):
        """Add diagram to queue"""
        if diagram_path not in self.selected_classes:
            self.selected_classes.append(diagram_path)
            self.update_queue_display()
            diagram_info = self.diagram_files_dict.get(diagram_path)
            if diagram_info:
                self.append_status(f"Added to queue: {diagram_info['name']} (diagram)")
        else:
            QMessageBox.information(self, "Info", "This diagram is already in the queue")
    
    # ==================== Helper Methods ====================
    
    def get_display_name_for_path(self, path: str) -> str:
        """Get display name for both class paths and diagram paths"""
        if not path:
            return "Unknown"
        
        # Check if it's a diagram
        if path in self.diagram_files_dict:
            return self.diagram_files_dict[path]['name']
        
        # Otherwise treat as class path
        return EnhancedListWidgetItem.extract_class_name(path)
    
    # ==================== General Functions ====================
    
    def append_status(self, message: str):
        """Add status message"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        
        self.status_text.append(formatted_message)
        
        cursor = self.status_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End) 
        self.status_text.setTextCursor(cursor)
        
        QApplication.processEvents()
    
    def open_settings(self):
        """Open settings dialog"""
        dialog = SettingsDialog(self)
        if dialog.exec() == QDialog.Accepted:
            self.update_ui_from_settings()
            self.append_status("Settings updated")
            self.auto_apply_settings()
            self.refresh_rag_status()
    
    def update_ui_from_settings(self):
        """Update UI from settings"""
        # version = self.settings.value("ascet/version", "6.1.4")
        # self.version_combo.setCurrentText(version)

        model_type = self.settings.value("api/model_type", "gpt5-mini")
        if hasattr(self, 'model_status_label'):
            self.model_status_label.setText(f"Model: {model_type}")
    
    def load_ui_state(self):
        """Load UI state"""
        self.update_ui_from_settings()
        
        # Load last mode setting
        last_mode = self.settings.value("ui/last_mode", "agent")
        if last_mode == "direct":
            self.direct_mode_radio.setChecked(True)
        else:
            self.agent_mode_radio.setChecked(True)
    
    def auto_apply_settings(self):
        """Auto apply settings - improved version to ensure default values are properly set"""
        try:
            # Check and set default configuration
            self.ensure_default_settings()
            
            self.settings.sync()
            
            # Create output directories based on mode
            output_dir = self.settings.value("paths/output_dir", "agent_reports")
            cache_dir = self.settings.value("paths/cache_dir", "embedding_cache")
            kb_path = self.settings.value("paths/knowledge_base_path", "")
            
            # Also create mode-specific directories
            for mode_dir in ["agent_reports", "direct_reports"]:
                if not os.path.exists(mode_dir):
                    os.makedirs(mode_dir, exist_ok=True)
            
            auto_create = self.settings.value("paths/auto_create_dirs", True, type=bool)
            if auto_create:
                for dir_path in [output_dir, cache_dir, kb_path]:
                    if dir_path and not os.path.exists(dir_path):
                        try:
                            os.makedirs(dir_path, exist_ok=True)
                            self.append_status(f"Auto created directory: {dir_path}")
                        except Exception as e:
                            self.append_status(f"Failed to create directory {dir_path}: {e}")
            
            self.refresh_rag_status()
            
            self.append_status("Settings auto-applied successfully")
            
        except Exception as e:
            self.append_status(f"Failed to auto-apply settings: {str(e)}")

    def ensure_default_settings(self):
        """Ensure default settings are properly saved"""
        # Define default configuration
        default_settings = {
            "api/model_type": "gpt5-mini",
            "api/deepseek_api_key": "sk-jwVMOs8ac7gNmnBkB57e670f6cBd49B7A126713bF451451b",
            "api/deepseek_api_url": "http://10.161.112.104:3000/v1",
            "api/embedding_api_key": "sk-yAYNtyvvu1JUE8zV0f13A3DdDeC14f6aAf442a81E6C58333",
            "api/embedding_api_url": "http://10.161.112.104:3000/v1",
            "api/embedding_model": "text-embedding-3-small",
            "paths/knowledge_base_path": r"RAG\code_analysis_knowledge",
            "paths/output_dir": "agent_reports",
            "paths/cache_dir": "embedding_cache",
            "paths/auto_create_dirs": True,
            "ascet/diagram_name": "Main",
            "ascet/method_name": "calc",
            "ascet/scan_timeout": 300,
            "agent/auto_cleanup": True,
            "agent/mark_failed_reports": True,
            "agent/max_retries": 2,
            "agent/per_class_timeout_sec": 360,
            "log/enable_debug": False,
            "log/level": "INFO"
        }
        
        # Check if this is the first run (check if key settings exist)
        is_first_run = not self.settings.contains("api/deepseek_api_key")
        
        if is_first_run:
            self.append_status("First run detected, applying default settings...")
            
            # Save all default settings
            for key, value in default_settings.items():
                self.settings.setValue(key, value)
            
            self.settings.sync()
            self.append_status("Default settings have been automatically applied")

    
    def show_help(self):
        """Show help information"""
        help_text = f"""
# ASCET AI Code Review Agent v3.2 - Dual Mode Support

## 🆕 New Features
- **Dual Mode Support**: Direct mode and Agent mode
- **Direct Mode**: Fast basic checking, no AI analysis required
- **Agent Mode**: Complete AI analysis and consistency checking
- **Mode Switching**: Mode selector at top of interface
- **Smart Output Directories**: Different modes use different output directories
- **SVG Animation**: Uses rotating animation to show processing status

## Operating Mode Description

### Direct Mode
- Executes basic rule checking only
- No AI deep analysis
- No consistency checking required
- Fast execution speed
- Suitable for quick preliminary checks
- Output directory: direct_reports/

### Agent Mode
- Includes basic rule checking
- Executes AI deep analysis
- Performs consistency checking
- Supports retry mechanism
- Suitable for deep code review
- Output directory: agent_reports/

## Current Configuration
- Current Mode: {self.current_mode.upper()}
- RAG Status: {'Available' if RAG_AVAILABLE else 'Unavailable'}
- Agent Module: {'Available' if AGENT_AVAILABLE else 'Unavailable'}

## Usage Steps

### 1. Select Operating Mode
- Choose Direct or Agent mode at top of interface
- Direct mode for quick checking
- Agent mode for deep analysis

### 2. Configure System
- Click "Settings" button
- Configure API keys (required for Agent mode)
- Set output directories

### 3. Scan ASCET Database
- Select ASCET version
- Click "Scan Database" or "Scan Folder"
- Select classes to analyze from left tree

### 4. Manage Analysis Queue
- Double-click classes or click "Add Selected to Queue"
- Can adjust order, remove classes
- Queue status icons update in real-time

### 5. Execute Analysis
- Click "Start Batch Processing"
- View SVG animation indicator showing processing status
- Support stop and re-analysis

### 6. View Results
- Double-click queue items to view error statistics
- Right-click menu provides more operations
- Browse and export reports

## Status Icon Legend
- 🟢 Passed: No errors found
- 🟡 Warning: Only rule detection found issues
- 🔴 Error: AI detected errors (Agent mode)
- 🔵 Processing: Analysis in progress (with animation)
- ⚪ Waiting: Awaiting processing

## Processing Status Indicators
- 🔄 Rotating Animation: System is processing
- Animation Location: Right side of queue title
- Auto Show/Hide: Based on processing status

## Keyboard Shortcuts
- Ctrl+A: Select all classes in tree
- Double-click: Quick add to queue
- Right-click: Show context menu

Technical Support: Please ensure all dependency modules are correctly installed
        """
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Help")
        dialog.setModal(True)
        dialog.resize(800, 600)
        
        layout = QVBoxLayout(dialog)
        
        if MARKDOWN_AVAILABLE:
            help_browser = QTextBrowser()
            help_browser.setOpenExternalLinks(True)
            html = markdown.markdown(help_text)
            help_browser.setHtml(html)
        else:
            help_browser = QTextEdit()
            help_browser.setReadOnly(True)
            help_browser.setText(help_text)
        
        layout.addWidget(help_browser)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.close)
        layout.addWidget(close_btn)
        
        dialog.exec()
    
    def closeEvent(self, event):
        """Close event handling"""
        running_tasks = []
        
        if self.scan_worker and self.scan_worker.isRunning():
            running_tasks.append("Database scanning")
        
        if self.batch_worker and self.batch_worker.isRunning():
            running_tasks.append("Batch analysis")
        
        if running_tasks:
            reply = QMessageBox.question(
                self, "Confirm Exit",
                f"The following tasks are running:\n{', '.join(running_tasks)}\n\n"
                f"Are you sure you want to exit? Running tasks will be force stopped.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.No:
                event.ignore()
                return
        
        # Save UI state
        self.settings.setValue("ui/geometry", self.saveGeometry())
        self.settings.setValue("ui/window_state", self.saveState())
        self.settings.setValue("ui/last_mode", self.current_mode)
        
        if self.scan_worker and self.scan_worker.isRunning():
            self.scan_worker.terminate()
            self.scan_worker.wait(2000)
        
        if self.batch_worker and self.batch_worker.isRunning():
            self.batch_worker.stop()
            self.batch_worker.wait(3000)
        
        event.accept()

# ==================== Report Browser Dialog ====================

class ReportBrowserDialog(QDialog):
    """Report browser dialog"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Report Browser")
        self.resize(900, 600)
        self.settings = QSettings('AscetAgent', 'AscetAgentv3')
        self.init_ui()
        self.refresh_reports_list()
    
    def init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)
        
        # Toolbar
        toolbar_layout = QHBoxLayout()
        
        self.refresh_btn = QPushButton("Refresh List")
        self.refresh_btn.clicked.connect(self.refresh_reports_list)
        
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Filter reports...")
        self.filter_edit.textChanged.connect(self.filter_reports)
        
        toolbar_layout.addWidget(self.refresh_btn)
        toolbar_layout.addWidget(QLabel("Filter:"))
        toolbar_layout.addWidget(self.filter_edit)
        toolbar_layout.addStretch()
        
        layout.addLayout(toolbar_layout)
        
        # Reports list
        self.reports_list = QListWidget()
        self.reports_list.itemDoubleClicked.connect(self.preview_selected_report)
        layout.addWidget(self.reports_list)
        
        # Operation buttons
        btn_layout = QHBoxLayout()
        
        self.preview_btn = QPushButton("Preview")
        self.preview_btn.clicked.connect(self.preview_selected_report)
        
        self.view_stats_btn = QPushButton("View Statistics")
        self.view_stats_btn.clicked.connect(self.view_error_statistics)
        
        self.open_file_btn = QPushButton("Open File")
        self.open_file_btn.clicked.connect(self.open_selected_file)
        
        self.delete_btn = QPushButton("Delete")
        self.delete_btn.clicked.connect(self.delete_selected_report)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        
        btn_layout.addWidget(self.preview_btn)
        btn_layout.addWidget(self.view_stats_btn)
        btn_layout.addWidget(self.open_file_btn)
        btn_layout.addWidget(self.delete_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)
    
    def refresh_reports_list(self):
        """Refresh reports list"""
        self.reports_list.clear()
        
        user_output_dir = self.settings.value("paths/output_dir", "agent_reports")
        
        possible_dirs = ["agent_reports", "direct_reports"]
        
        if user_output_dir and user_output_dir.strip():
            possible_dirs.insert(0, user_output_dir.strip())
        
        report_files = []
        
        for output_dir in possible_dirs:
            if output_dir and os.path.exists(output_dir):
                try:
                    for ext in ['*.md', '*.html']:
                        report_files.extend(Path(output_dir).glob('**/' + ext))
                        report_files.extend(Path(output_dir).glob(ext))
                except Exception:
                    pass
        
        if not report_files:
            return
        
        try:
            report_files = list(set(report_files))
            report_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            for report_file in report_files:
                # Show directory information
                parent_dir = report_file.parent.name
                item_text = f"[{parent_dir}] {report_file.name} ({self.format_file_time(report_file)})"
                item = QListWidgetItem(item_text)
                item.setData(Qt.UserRole, str(report_file))
                
                if "CONSISTENCY_FAILED" in report_file.name:
                    item.setIcon(self.style().standardIcon(self.style().SP_MessageBoxWarning))
                else:
                    item.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon))
                
                self.reports_list.addItem(item)
                
        except Exception:
            pass
    
    def format_file_time(self, file_path: Path) -> str:
        """Format file time"""
        try:
            mtime = file_path.stat().st_mtime
            return datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
        except:
            return "Unknown time"
    
    def filter_reports(self, text: str):
        """Filter reports"""
        for i in range(self.reports_list.count()):
            item = self.reports_list.item(i)
            item.setHidden(text.lower() not in item.text().lower())
    
    def preview_selected_report(self):
        """Preview selected report"""
        current_item = self.reports_list.currentItem()
        if current_item:
            report_path = current_item.data(Qt.UserRole)
            dialog = ReportPreviewDialog(report_path, self)
            dialog.exec()
    
    def view_error_statistics(self):
        """View error statistics"""
        current_item = self.reports_list.currentItem()
        if not current_item:
            QMessageBox.information(self, "Notice", "Please select a report first")
            return
        
        report_path = current_item.data(Qt.UserRole)
        stats_path = os.path.splitext(report_path)[0] + "_statistics.json"
        
        if not os.path.exists(stats_path):
            QMessageBox.information(self, "Notice", "This report has no corresponding error statistics file")
            return
        
        try:
            with open(stats_path, 'r', encoding='utf-8') as f:
                statistics_data = json.load(f)
            
            dialog = ErrorStatisticsDialog(statistics_data, self)
            dialog.exec()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load error statistics:\n{str(e)}")
    
    def open_selected_file(self):
        """Open selected file"""
        current_item = self.reports_list.currentItem()
        if current_item:
            report_path = current_item.data(Qt.UserRole)
            try:
                os.startfile(report_path)
            except Exception as e:
                QMessageBox.warning(self, "Warning", f"Unable to open file:\n{str(e)}")
    
    def delete_selected_report(self):
        """Delete selected report"""
        current_item = self.reports_list.currentItem()
        if not current_item:
            return
        
        report_path = current_item.data(Qt.UserRole)
        report_name = os.path.basename(report_path)
        
        reply = QMessageBox.question(
            self, "Confirm Delete", 
            f"Are you sure you want to delete the report file?\n{report_name}",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                os.remove(report_path)
                
                stats_path = os.path.splitext(report_path)[0] + "_statistics.json"
                if os.path.exists(stats_path):
                    os.remove(stats_path)
                
                self.refresh_reports_list()
                
            except Exception as e:
                QMessageBox.critical(self, "Delete Failed", f"Failed to delete report:\n{str(e)}")

# ==================== Main Function ====================

def main():
    """Main function"""
    app = QApplication(sys.argv)
    app.setApplicationName("ASCET AI Agent v3.0")
    app.setOrganizationName("ASCET Tools")
    
    # Check dependencies
    missing_deps = []
    if not SCANNER_AVAILABLE:
        missing_deps.append("ASCET Scanner Module")
    if not AGENT_AVAILABLE:
        missing_deps.append("AI Agent Module (AscetAgentv4.py)")
    if not MARKDOWN_AVAILABLE:
        missing_deps.append("Markdown Module")
    if not RAG_AVAILABLE:
        missing_deps.append("RAG Core Module")
    
    # Check SVG support
 
    
    
    if missing_deps:
        QMessageBox.warning(
            None, "Dependency Check", 
            f"The following modules are unavailable, some functions may be limited:\n" + 
            "\n".join(f"- {dep}" for dep in missing_deps) +
            "\n\nThe program will continue running, but it's recommended to install missing dependencies."
        )
    
    # Create main window
    window = AscetAgentMainWindow()
    
    # Restore window state
    geometry = window.settings.value("ui/geometry")
    if geometry:
        window.restoreGeometry(geometry)
    
    window_state = window.settings.value("ui/window_state")
    if window_state:
        window.restoreState(window_state)
    
    window.show()
    
    return app.exec()

if __name__ == "__main__":
    # 关键：multiprocessing保护
    multiprocessing.freeze_support()
    
    # 确保只有主进程运行Qt应用
    if multiprocessing.current_process().name == 'MainProcess':
        sys.exit(main())