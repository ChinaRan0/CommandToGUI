import sys
import os
import json
import platform
import requests
from functools import partial
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QTreeWidget, QTreeWidgetItem,
    QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog,
    QLineEdit, QLabel, QFormLayout, QMenuBar, QAction, QInputDialog,
    QDialog, QMessageBox, QPlainTextEdit, QSplitter, QStatusBar, QMenu
)
from PyQt5.QtCore import Qt, QProcess, QTimer
from PyQt5.QtGui import QFont, QTextCursor
import time

CONFIG_FILE = 'commands.json'

class ParamInputDialog(QDialog):
    def __init__(self, template, param_types, parent=None):
        super().__init__(parent)
        self.setWindowTitle('运行命令')
        self.template = template
        self.param_types = param_types
        self.values = {}
        
        # 设置对话框样式
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f5f5;
            }
            QLabel {
                font-weight: bold;
                color: #333;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QLineEdit {
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: white;
            }
            QLineEdit:focus {
                border: 1px solid #4CAF50;
            }
            QPlainTextEdit {
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: white;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 添加标题和说明
        title = QLabel('运行命令参数输入')
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #333; margin-bottom: 10px;")
        layout.addWidget(title)
        
        desc = QLabel('请填写以下参数，示例仅供参考：')
        desc.setStyleSheet("color: #666; margin-bottom: 15px;")
        layout.addWidget(desc)
        
        form = QFormLayout()
        form.setSpacing(15)
        form.setContentsMargins(0, 0, 0, 0)
        
        self.inputs = {}
        import re
        self.params = re.findall(r"\{(.*?)\}", template)
        
        for p in self.params:
            ptype = param_types.get(p, '字符串')
            hbox = QHBoxLayout()
            hbox.setSpacing(10)
            
            line = QLineEdit()
            line.setStyleSheet("""
                QLineEdit {
                    padding: 8px;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                    background-color: white;
                }
                QLineEdit:focus {
                    border: 1px solid #4CAF50;
                }
            """)
            
            if ptype == '文件':
                line.setReadOnly(True)
                line.setPlaceholderText('请选择文件')
                btn = QPushButton('浏览')
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #2196F3;
                        padding: 6px 12px;
                    }
                    QPushButton:hover {
                        background-color: #0b7dda;
                    }
                """)
                btn.clicked.connect(partial(self.browse_file, line))
                hbox.addWidget(line, 1)
                hbox.addWidget(btn)
            elif ptype == '文件或字符串':
                line.setPlaceholderText(f'示例: /path/to/{p}.txt 或 文本_{p}')
                btn = QPushButton('浏览')
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #2196F3;
                        padding: 6px 12px;
                    }
                    QPushButton:hover {
                        background-color: #0b7dda;
                    }
                """)
                btn.clicked.connect(partial(self.browse_file, line))
                hbox.addWidget(line, 1)
                hbox.addWidget(btn)
            else:
                line.setPlaceholderText(f'示例: 文本_{p}')
                hbox.addWidget(line)
                
            # 美化参数标签
            param_label = QLabel(f'参数 {p} （类型：{ptype}）：')
            param_label.setStyleSheet("color: #555;")
            form.addRow(param_label, hbox)
            self.inputs[p] = line
        
        # 添加运行按钮
        run_btn = QPushButton('运行命令')
        run_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                font-weight: bold;
                padding: 10px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #0b7dda;
            }
        """)
        run_btn.setToolTip('点击开始在内置终端中运行命令')
        run_btn.clicked.connect(self.accept)
        
        layout.addLayout(form)
        layout.addWidget(run_btn)
        self.setLayout(layout)
        self.resize(600, 400)

    def browse_file(self, line_edit):
        path, _ = QFileDialog.getOpenFileName(self, '选择文件')
        if path:
            line_edit.setText(path)

    def get_values(self):
        return {p: self.inputs[p].text() for p in self.params}

class ToolRunner(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('CommandToGUI工具箱 By  公众号:知攻善防实验室 ChinaRan404')
        
        # 主题相关初始化
        self.current_theme = 'light'  # 默认使用浅色主题
        self.themes = {
            'light': {
                'background': '#f0f0f0',
                'foreground': '#333333',
                'primary': '#2196F3',
                'secondary': '#4CAF50',
                'error': '#f44336',
                'border': '#ddd',
                'text': '#333',
                'highlight': '#e3f2fd'
            },
            'dark': {
                'background': '#1e1e1e',
                'foreground': '#ffffff',
                'primary': '#64b5f6',
                'secondary': '#81c784',
                'error': '#ef5350',
                'border': '#333',
                'text': '#fff',
                'highlight': '#2d2d2d'
            }
        }
        
        # 获取屏幕尺寸并设置初始大小为屏幕的40%
        screen = QApplication.primaryScreen().availableGeometry()
        self.resize(int(screen.width() * 0.6), int(screen.height() * 0.8))
        
        # 初始化配置
        self.config = {'categories': [], 'use_internal_terminal': True}
        self.load_config()
        
        # 终端相关初始化
        self.command_history = []
        self.history_index = -1
        self.current_input = ""
        self.prompt = "> "
        self.is_input_mode = False
        
        self.init_ui()
        self.start_shell()
        self.refresh_tree()
        
        # 状态栏
        self.statusBar().showMessage('就绪')
        
        # 设置窗口最小大小
        self.setMinimumSize(800, 600)
        
        # 应用默认主题
        self.apply_theme()

    def apply_theme(self):
        theme = self.themes[self.current_theme]
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {theme['background']};
            }}
            QMenuBar {{
                background-color: {theme['background']};
                color: {theme['text']};
                border-bottom: 1px solid {theme['border']};
            }}
            QMenuBar::item {{
                padding: 5px 10px;
                background: transparent;
            }}
            QMenuBar::item:selected {{
                background: {theme['highlight']};
            }}
            QMenu {{
                background-color: {theme['background']};
                color: {theme['text']};
                border: 1px solid {theme['border']};
            }}
            QMenu::item:selected {{
                background-color: {theme['primary']};
                color: white;
            }}
            QTreeWidget {{
                border: 1px solid {theme['border']};
                border-radius: 4px;
                background-color: {theme['background']};
                color: {theme['text']};
            }}
            QTreeWidget::item {{
                padding: 5px;
                border-radius: 3px;
            }}
            QTreeWidget::item:hover {{
                background-color: {theme['highlight']};
            }}
            QTreeWidget::item:selected {{
                background-color: {theme['primary']};
                color: white;
            }}
            QPlainTextEdit {{
                border: 1px solid {theme['border']};
                border-radius: 4px;
                background-color: {theme['background']};
                color: {theme['text']};
                font-family: 'Consolas', 'Courier New', monospace;
            }}
            QPushButton {{
                background-color: {theme['primary']};
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {theme['secondary']};
            }}
            QPushButton:disabled {{
                background-color: {theme['border']};
            }}
            QStatusBar {{
                background-color: {theme['background']};
                color: {theme['text']};
                border-top: 1px solid {theme['border']};
            }}
            QLabel {{
                color: {theme['text']};
            }}
            QSplitter::handle {{
                background-color: {theme['border']};
            }}
            QSplitter::handle:hover {{
                background-color: {theme['primary']};
            }}
        """)

    def init_ui(self):
        # 创建菜单栏
        self.create_menus()
        
        # 主布局
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)
        
        # 使用分割器
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(5)  # 设置分割线宽度
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #ddd;
            }
            QSplitter::handle:hover {
                background-color: #2196F3;
            }
        """)

        # 左侧面板 - 命令树
        left_panel = QWidget()
        left_panel.setMinimumWidth(250)  # 设置最小宽度
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(10, 10, 10, 10)
        left_layout.setSpacing(10)
        
        # 添加树控件标题
        tree_title = QLabel('命令分类')
        tree_title.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #333;
                padding: 5px;
                border-bottom: 2px solid #2196F3;
            }
        """)
        left_layout.addWidget(tree_title)
        
        # 树状结构
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.itemDoubleClicked.connect(self.on_item_double)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_context_menu)
        self.tree.setStyleSheet("""
            QTreeWidget {
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: white;
                padding: 5px;
            }
            QTreeWidget::item {
                padding: 5px;
                border-radius: 3px;
            }
            QTreeWidget::item:hover {
                background-color: #f0f0f0;
            }
            QTreeWidget::item:selected {
                background-color: #e3f2fd;
                color: #2196F3;
            }
        """)
        left_layout.addWidget(self.tree)
        
        # 右侧面板 - 终端
        right_panel = QWidget()
        right_panel.setMinimumWidth(400)  # 设置最小宽度
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(10, 10, 10, 10)
        right_layout.setSpacing(10)
        
        # 添加终端标题
        terminal_title = QLabel('内置终端')
        terminal_title.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #333;
                padding: 5px;
                border-bottom: 2px solid #2196F3;
            }
        """)
        right_layout.addWidget(terminal_title)
        
        # 终端输出
        self.terminal = QPlainTextEdit()
        self.terminal.setReadOnly(False)
        self.terminal.setPlaceholderText('内置终端，支持交互式输入')
        self.terminal.setStyleSheet("""
            QPlainTextEdit {
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: #fafafa;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 12px;
                padding: 5px;
            }
        """)
        
        # 设置终端字体
        font = QFont("Consolas", 12)
        self.terminal.setFont(font)
        
        # 安装事件过滤器以处理键盘事件
        self.terminal.installEventFilter(self)
        
        right_layout.addWidget(self.terminal)
        
        # 添加面板到分割器
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 1)  # 左侧伸缩因子
        splitter.setStretchFactor(1, 2)  # 右侧伸缩因子
        
        main_layout.addWidget(splitter)
        self.setCentralWidget(main_widget)
        
        # 状态栏
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet("""
            QStatusBar {
                background-color: #f5f5f5;
                color: #666;
                border-top: 1px solid #ddd;
            }
        """)
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪")

        # 添加停止按钮
        stop_btn = QPushButton('强制停止')
        stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        stop_btn.clicked.connect(self.stop_shell)
        left_layout.addWidget(stop_btn)

    def create_menus(self):
        menubar = self.menuBar()
        menubar.setStyleSheet("""
            QMenuBar {
                background-color: #e0e0e0;
                padding: 5px;
            }
            QMenuBar::item {
                padding: 5px 10px;
                background: transparent;
            }
            QMenuBar::item:selected {
                background: #d0d0d0;
            }
            QMenu {
                background-color: #f5f5f5;
                border: 1px solid #ccc;
            }
            QMenu::item:selected {
                background-color: #2196F3;
                color: white;
            }
        """)
        
        # 分类菜单
        cat_menu = menubar.addMenu('分类')
        
        add_cat = QAction('添加分类', self)
        add_cat.setStatusTip('新建一个分类，例如：文档处理')
        add_cat.triggered.connect(self.add_category)
        cat_menu.addAction(add_cat)
        
        edit_cat = QAction('修改分类', self)
        edit_cat.setStatusTip('修改选中的分类名称')
        edit_cat.triggered.connect(self.edit_category)
        cat_menu.addAction(edit_cat)
        
        del_cat = QAction('删除分类', self)
        del_cat.setStatusTip('删除选中的分类及其所有工具')
        del_cat.triggered.connect(self.delete_category)
        cat_menu.addAction(del_cat)
        
        # 工具菜单
        tool_menu = menubar.addMenu('工具')
        
        add_tool = QAction('添加工具', self)
        add_tool.setStatusTip('在分类下添加新工具，例如：pdftotext')
        add_tool.triggered.connect(self.add_tool)
        tool_menu.addAction(add_tool)
        
        edit_tool = QAction('修改工具', self)
        edit_tool.setStatusTip('修改选中的工具信息')
        edit_tool.triggered.connect(self.edit_tool)
        tool_menu.addAction(edit_tool)
        
        del_tool = QAction('删除工具', self)
        del_tool.setStatusTip('删除选中的工具及其所有命令')
        del_tool.triggered.connect(self.delete_tool)
        tool_menu.addAction(del_tool)
        
        add_cmd = QAction('添加命令', self)
        add_cmd.setStatusTip('为选中的工具添加新命令')
        add_cmd.triggered.connect(self.add_command)
        tool_menu.addAction(add_cmd)
        
        # 配置菜单
        config_menu = menubar.addMenu('配置')
        
        load_remote = QAction('从远程加载配置', self)
        load_remote.setStatusTip('从指定 URL 下载 commands.json 并刷新')
        load_remote.triggered.connect(self.load_remote_config)
        config_menu.addAction(load_remote)
        
        export_config = QAction('导出配置', self)
        export_config.setStatusTip('将当前配置导出到文件')
        export_config.triggered.connect(self.export_config)
        config_menu.addAction(export_config)
        
        import_config = QAction('导入配置', self)
        import_config.setStatusTip('从文件导入配置')
        import_config.triggered.connect(self.import_config)
        config_menu.addAction(import_config)
        
        # 帮助菜单
        help_menu = menubar.addMenu('帮助')
        
        about_action = QAction('关于', self)
        about_action.setStatusTip('显示关于信息')
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

        # 外置终端
        toggle_terminal_action = QAction('使用外置终端', self, checkable=True)
        toggle_terminal_action.setChecked(not self.config.get('use_internal_terminal', True))
        toggle_terminal_action.triggered.connect(self.toggle_terminal)
        config_menu.addAction(toggle_terminal_action)

        # 文件菜单
        file_menu = menubar.addMenu('文件')
        
        # 主题切换
        theme_menu = file_menu.addMenu('切换主题')
        light_action = QAction('浅色主题', self, checkable=True)
        light_action.setChecked(self.current_theme == 'light')
        light_action.triggered.connect(lambda: self.switch_theme('light'))
        theme_menu.addAction(light_action)
        
        dark_action = QAction('深色主题', self, checkable=True)
        dark_action.setChecked(self.current_theme == 'dark')
        dark_action.triggered.connect(lambda: self.switch_theme('dark'))
        theme_menu.addAction(dark_action)

    def toggle_terminal(self, checked):
        """切换终端类型"""
        self.config['use_internal_terminal'] = not checked
        self.save_config()
        mode = '外置' if checked else '内置'
        self.statusBar().showMessage(f'已切换为{mode}终端模式', 3000)

    def stop_shell(self):
        """强制停止当前命令"""
        if self.shell.state() == QProcess.Running:
            self.shell.terminate()
            if not self.shell.waitForFinished(1000):
                self.shell.kill()
            self.statusBar().showMessage('已强制停止当前命令', 3000)
        else:
            self.statusBar().showMessage('没有正在运行的进程', 3000)

    def show_context_menu(self, position):
        item = self.tree.itemAt(position)
        if not item:
            return
        
        menu = QMenu()
        typ, data = item.data(0, Qt.UserRole)
        
        if typ == 'category':
            edit_action = QAction('修改分类', self)
            edit_action.triggered.connect(self.edit_category)
            menu.addAction(edit_action)
            
            del_action = QAction('删除分类', self)
            del_action.triggered.connect(self.delete_category)
            menu.addAction(del_action)
            
            add_tool_action = QAction('添加工具', self)
            add_tool_action.triggered.connect(self.add_tool)
            menu.addAction(add_tool_action)
            
        elif typ == 'tool':
            edit_action = QAction('修改工具', self)
            edit_action.triggered.connect(self.edit_tool)
            menu.addAction(edit_action)
            
            del_action = QAction('删除工具', self)
            del_action.triggered.connect(self.delete_tool)
            menu.addAction(del_action)
            
            add_cmd_action = QAction('添加命令', self)
            add_cmd_action.triggered.connect(self.add_command)
            menu.addAction(add_cmd_action)
            
        elif typ == 'command':
            run_action = QAction('运行命令', self)
            run_action.triggered.connect(lambda: self.on_item_double(item, 0))
            menu.addAction(run_action)
            
            edit_action = QAction('修改命令', self)
            edit_action.triggered.connect(lambda: self.edit_command(item))
            menu.addAction(edit_action)
            
            del_action = QAction('删除命令', self)
            del_action.triggered.connect(lambda: self.delete_command(item))
            menu.addAction(del_action)
            
        menu.exec_(self.tree.viewport().mapToGlobal(position))

    def load_remote_config(self):
        url, ok = QInputDialog.getText(self, '远程配置 URL', '请输入 commands.json 的 URL：')
        if not ok or not url:
            return
        try:
            self.statusBar().showMessage('正在从远程加载配置...')
            QApplication.processEvents()  # 更新UI
            
            resp = requests.get(url)
            resp.raise_for_status()
            data = resp.json()
            
            # 覆盖本地配置
            self.config = {'categories': data} if isinstance(data, list) else data
            self.save_config()
            self.refresh_tree()
            
            self.statusBar().showMessage('已从远程加载并更新配置', 3000)
            QMessageBox.information(self, '成功', '已从远程加载并更新配置')
        except Exception as e:
            self.statusBar().showMessage('加载远程配置失败', 3000)
            QMessageBox.critical(self, '错误', f'加载远程配置失败：{e}')

    def start_shell(self):
        self.shell = QProcess(self)
        self.shell.setProcessChannelMode(QProcess.MergedChannels)
        self.shell.readyRead.connect(self.on_shell_output)
        shell_cmd, shell_args = self.get_shell_command()
        self.shell.start(shell_cmd, shell_args)
        
        # 定时检查shell状态
        self.shell_timer = QTimer(self)
        self.shell_timer.timeout.connect(self.check_shell_status)
        self.shell_timer.start(1000)

    def check_shell_status(self):
        if self.shell.state() == QProcess.NotRunning:
            self.statusBar().showMessage('终端未运行', 2000)
            self.shell_timer.stop()
            # 尝试重新启动
            QTimer.singleShot(2000, self.start_shell)

    def get_shell_command(self):
        system = platform.system()
        if system == 'Windows':
            return 'cmd.exe', ['/Q']
        else:
            return '/bin/bash', ['-i']

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                # 合并加载的配置和默认配置
                if isinstance(data, list):
                    self.config = {'categories': data, 'use_internal_terminal': True}
                else:
                    self.config = {'categories': data.get('categories', []), 
                                 'use_internal_terminal': data.get('use_internal_terminal', True)}
                self.statusBar().showMessage('配置已加载', 2000)
            except Exception as e:
                self.statusBar().showMessage('加载配置失败，使用默认配置', 3000)
                self.config = {'categories': [], 'use_internal_terminal': True}
                self.save_config()
        else:
            self.config = {'categories': [], 'use_internal_terminal': True}
            self.save_config()
            self.statusBar().showMessage('创建了新的配置文件', 2000)

    def save_config(self):
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            self.statusBar().showMessage('配置已保存', 2000)
        except Exception as e:
            self.statusBar().showMessage(f'保存配置失败: {str(e)}', 3000)

    def refresh_tree(self):
        self.tree.clear()
        for cat in self.config['categories']:
            cat_item = QTreeWidgetItem([f"📁 {cat['name']}"])
            cat_item.setData(0, Qt.UserRole, ('category', cat))
            cat_item.setToolTip(0, f"分类: {cat['name']}")
            self.tree.addTopLevelItem(cat_item)
            
            for tool in cat.get('tools', []):
                tool_item = QTreeWidgetItem([f"🛠️ {tool['name']}"])
                tool_item.setData(0, Qt.UserRole, ('tool', tool))
                tool_item.setToolTip(0, f"工具: {tool['name']}\n描述: {tool.get('description', '无描述')}")
                cat_item.addChild(tool_item)
                
                for cmd in tool.get('commands', []):
                    cmd_item = QTreeWidgetItem([f"▶ {cmd['name']}"])
                    cmd_item.setData(0, Qt.UserRole, ('command', cmd))
                    cmd_item.setToolTip(0, f"命令: {cmd['name']}\n模板: {cmd['template']}")
                    tool_item.addChild(cmd_item)
        
        self.tree.expandAll()
        self.statusBar().showMessage('命令树已刷新', 2000)

    def add_category(self):
        name, ok = QInputDialog.getText(self, '新建分类', '请输入分类名称（例如：文档处理）：')
        if ok and name:
            self.config['categories'].append({'name': name, 'tools': []})
            self.save_config()
            self.refresh_tree()
            self.statusBar().showMessage(f'已添加分类: {name}', 3000)

    def edit_category(self):
        item = self.tree.currentItem()
        if not item:
            QMessageBox.warning(self, '提示', '请先选择一个分类')
            return
            
        typ, cat = item.data(0, Qt.UserRole)
        if typ != 'category':
            QMessageBox.warning(self, '提示', '只能修改分类节点')
            return
            
        new_name, ok = QInputDialog.getText(self, '修改分类', '请输入新的分类名称：', text=cat['name'])
        if ok and new_name:
            cat['name'] = new_name
            self.save_config()
            self.refresh_tree()
            self.statusBar().showMessage(f'已更新分类: {new_name}', 3000)

    def delete_category(self):
        item = self.tree.currentItem()
        if not item:
            QMessageBox.warning(self, '提示', '请先选择一个分类')
            return
            
        typ, cat = item.data(0, Qt.UserRole)
        if typ != 'category':
            QMessageBox.warning(self, '提示', '只能删除分类节点')
            return
            
        reply = QMessageBox.question(
            self, '确认删除',
            f"确定要删除分类 '{cat['name']}' 及其所有工具吗?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.config['categories'].remove(cat)
            self.save_config()
            self.refresh_tree()
            self.statusBar().showMessage(f'已删除分类: {cat["name"]}', 3000)
        try:
            self.config['categories'].remove(cat)
        except ValueError:
            QMessageBox.warning(self, '错误', '删除分类失败，请重试')
            return
        self.save_config()
        self.refresh_tree()

    def add_tool(self):
        cats = [c['name'] for c in self.config['categories']]
        if not cats:
            QMessageBox.warning(self, '提示', '请先创建一个分类')
            return
            
        # 如果当前选中了分类，默认使用该分类
        current_item = self.tree.currentItem()
        default_cat = 0
        if current_item:
            typ, data = current_item.data(0, Qt.UserRole)
            if typ == 'category':
                default_cat = cats.index(data['name'])
                
        cat_name, ok = QInputDialog.getItem(
            self, '选择分类', '请选择工具所属分类：', 
            cats, default_cat, False
        )
        if not ok:
            return
            
        cat = next(c for c in self.config['categories'] if c['name'] == cat_name)
        
        tool_name, ok = QInputDialog.getText(self, '新建工具', '请输入工具名称：')
        if not ok or not tool_name:
            return
            
        desc, ok = QInputDialog.getText(self, '工具描述', '请输入工具说明：')
        if not ok:
            return
            
        template, ok = QInputDialog.getText(
            self, '命令模板', 
            '模板示例：pdftotext {input} {output}\n可用{}包裹参数名',
            text=f"{tool_name.lower()} {{input}} {{output}}"
        )
        if not ok or not template:
            return
            
        import re
        params = re.findall(r"\{(.*?)\}", template)
        param_types = {}
        for p in params:
            ptype, ok = QInputDialog.getItem(
                self, '参数类型', f'请选择参数 {p} 的类型：',
                ['字符串', '文件', '文件或字符串'], 0, False
            )
            if not ok:
                return
            param_types[p] = ptype
            
        tool = {
            'name': tool_name, 
            'description': desc, 
            'commands': [{
                'name': tool_name, 
                'template': template, 
                'param_types': param_types
            }]
        }
        
        cat.setdefault('tools', []).append(tool)
        self.save_config()
        self.refresh_tree()
        self.statusBar().showMessage(f'已添加工具: {tool_name}', 3000)

    def edit_tool(self):
        item = self.tree.currentItem()
        if not item:
            QMessageBox.warning(self, '提示', '请先选择一个工具')
            return
            
        typ, tool = item.data(0, Qt.UserRole)
        if typ != 'tool':
            QMessageBox.warning(self, '提示', '只能修改工具节点')
            return
            
        # 创建编辑对话框
        dialog = QDialog(self)
        dialog.setWindowTitle('修改工具')
        dialog.resize(400, 300)
        
        layout = QVBoxLayout()
        
        form = QFormLayout()
        
        name_edit = QLineEdit(tool['name'])
        desc_edit = QLineEdit(tool.get('description', ''))
        
        form.addRow('工具名称:', name_edit)
        form.addRow('工具描述:', desc_edit)
        
        layout.addLayout(form)
        
        # 命令列表
        cmd_label = QLabel('命令列表:')
        layout.addWidget(cmd_label)
        
        cmd_list = QPlainTextEdit()
        cmd_list.setReadOnly(True)
        cmd_list.setPlainText(
    '\n'.join([f"- {cmd['name']}" for cmd in tool.get('commands', [])])
)
        layout.addWidget(cmd_list)
        
        # 按钮
        btn_box = QHBoxLayout()
        save_btn = QPushButton('保存')
        save_btn.clicked.connect(dialog.accept)
        cancel_btn = QPushButton('取消')
        cancel_btn.clicked.connect(dialog.reject)
        
        btn_box.addWidget(save_btn)
        btn_box.addWidget(cancel_btn)
        layout.addLayout(btn_box)
        
        dialog.setLayout(layout)
        
        if dialog.exec_() == QDialog.Accepted:
            tool['name'] = name_edit.text()
            tool['description'] = desc_edit.text()
            self.save_config()
            self.refresh_tree()
            self.statusBar().showMessage(f'已更新工具: {tool["name"]}', 3000)

    def delete_tool(self):
        item = self.tree.currentItem()
        if not item:
            QMessageBox.warning(self, '提示', '请先选择一个工具')
            return
            
        typ, tool = item.data(0, Qt.UserRole)
        if typ != 'tool':
            QMessageBox.warning(self, '提示', '只能删除工具节点')
            return
            
        # 找到所属分类
        for cat in self.config['categories']:
            if tool in cat.get('tools', []):
                try:
                    cat['tools'].remove(tool)
                except ValueError:
                    QMessageBox.warning(self, '错误', '删除工具失败，请重试')
                    return
                self.save_config()
                self.refresh_tree()
                break

    def add_command(self):
        item = self.tree.currentItem()
        if not item:
            QMessageBox.warning(self, '提示', '请先选择一个工具')
            return
            
        typ, tool = item.data(0, Qt.UserRole)
        if typ != 'tool':
            QMessageBox.warning(self, '提示', '只能在工具节点下添加命令')
            return
            
        cmd_name, ok = QInputDialog.getText(self, '新建命令', '请输入命令名称：')
        if not ok or not cmd_name:
            return
            
        template, ok = QInputDialog.getText(
            self, '命令模板', 
            '模板示例：pdftotext {input} {output}\n可用{}包裹参数名',
            text=f"{cmd_name.lower()} {{param1}} {{param2}}"
        )
        if not ok or not template:
            return
            
        import re
        params = re.findall(r"\{(.*?)\}", template)
        param_types = {}
        for p in params:
            ptype, ok = QInputDialog.getItem(
                self, '参数类型', f'请选择参数 {p} 的类型：',
                ['字符串', '文件', '文件或字符串'], 0, False
            )
            if not ok:
                return
            param_types[p] = ptype
            
        tool.setdefault('commands', []).append({
            'name': cmd_name, 
            'template': template, 
            'param_types': param_types
        })
        
        self.save_config()
        self.refresh_tree()
        self.statusBar().showMessage(f'已添加命令: {cmd_name}', 3000)

    def edit_command(self, item):
        typ, cmd = item.data(0, Qt.UserRole)
        if typ != 'command':
            QMessageBox.warning(self, '提示', '只能修改命令节点')
            return
            
        # 创建编辑对话框
        dialog = QDialog(self)
        dialog.setWindowTitle('修改命令')
        dialog.resize(500, 300)
        
        layout = QVBoxLayout()
        
        form = QFormLayout()
        
        name_edit = QLineEdit(cmd['name'])
        template_edit = QPlainTextEdit(cmd['template'])
        template_edit.setMinimumHeight(100)
        
        form.addRow('命令名称:', name_edit)
        form.addRow('命令模板:', template_edit)
        
        layout.addLayout(form)
        
        # 参数类型
        param_label = QLabel('参数类型:')
        layout.addWidget(param_label)
        
        param_table = QPlainTextEdit()
        param_table.setReadOnly(True)
        param_text = '\n'.join([f"{k}: {v}" for k, v in cmd.get('param_types', {}).items()])
        param_table.setPlainText(param_text)
        layout.addWidget(param_table)
        
        # 按钮
        btn_box = QHBoxLayout()
        save_btn = QPushButton('保存')
        save_btn.clicked.connect(dialog.accept)
        cancel_btn = QPushButton('取消')
        cancel_btn.clicked.connect(dialog.reject)
        
        btn_box.addWidget(save_btn)
        btn_box.addWidget(cancel_btn)
        layout.addLayout(btn_box)
        
        dialog.setLayout(layout)
        
        if dialog.exec_() == QDialog.Accepted:
            cmd['name'] = name_edit.text()
            cmd['template'] = template_edit.toPlainText()
            self.save_config()
            self.refresh_tree()
            self.statusBar().showMessage(f'已更新命令: {cmd["name"]}', 3000)

    def delete_command(self, item):
        typ, cmd = item.data(0, Qt.UserRole)
        if typ != 'command':
            QMessageBox.warning(self, '提示', '只能删除命令节点')
            return
            
        # 找到所属工具
        for cat in self.config['categories']:
            for tool in cat.get('tools', []):
                if cmd in tool.get('commands', []):
                    try:
                        tool['commands'].remove(cmd)
                    except ValueError:
                        QMessageBox.warning(self, '错误', '删除命令失败，请重试')
                        return
                    self.save_config()
                    self.refresh_tree()
                    return

    def on_item_double(self, item, _):
        typ, data = item.data(0, Qt.UserRole)
        if typ == 'command':
            cmd = data
            dlg = ParamInputDialog(cmd['template'], cmd.get('param_types', {}), self)
            if dlg.exec_() == QDialog.Accepted:  # 确保只执行一次
                vals = dlg.get_values()
                # 改进的替换逻辑 - 处理各种大括号情况
                tpl = cmd['template']
                for k, v in vals.items():
                    # 处理 {param} 和 {{param}} 两种情况
                    tpl = tpl.replace(f'{{{k}}}', v).replace(f'{{{{{k}}}}}', v)
                
                # 添加调试输出
                print(f"Final command: {tpl}")  # 调试用
                
                # 确保shell准备好
                if self.shell.state() != QProcess.Running:
                    shell_cmd, shell_args = self.get_shell_command()
                    self.shell.start(shell_cmd, shell_args)
                    self.shell.waitForStarted()  # 等待shell启动
                
                # 只发送一次命令
                self.run_command(tpl)

    def eventFilter(self, obj, event):
        if obj == self.terminal and event.type() == event.KeyPress:
            if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
                if not event.modifiers() & Qt.ShiftModifier:
                    self.handle_command_input()
                    return True
            elif event.key() == Qt.Key_Up:
                self.navigate_history(-1)
                return True
            elif event.key() == Qt.Key_Down:
                self.navigate_history(1)
                return True
            elif event.key() == Qt.Key_Backspace:
                if self.terminal.textCursor().positionInBlock() <= len(self.prompt):
                    return True
        return super().eventFilter(obj, event)

    def handle_command_input(self):
        cursor = self.terminal.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.movePosition(QTextCursor.StartOfBlock, QTextCursor.KeepAnchor)
        current_line = cursor.selectedText()
        
        # 提取用户输入的命令
        if current_line.startswith(self.prompt):
            command = current_line[len(self.prompt):].strip()
            if command:
                self.command_history.append(command)
                self.history_index = len(self.command_history)
                self.run_command(command)
        
        # 添加新的提示符
        self.terminal.appendPlainText(self.prompt)
        self.terminal.moveCursor(QTextCursor.End)

    def navigate_history(self, direction):
        if not self.command_history:
            return
            
        if direction < 0:  # 向上
            if self.history_index > 0:
                self.history_index -= 1
        else:  # 向下
            if self.history_index < len(self.command_history) - 1:
                self.history_index += 1
            else:
                self.history_index = len(self.command_history)
                self.current_input = ""
                return
                
        # 获取历史命令
        command = self.command_history[self.history_index]
        
        # 更新当前行
        cursor = self.terminal.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.movePosition(QTextCursor.StartOfBlock, QTextCursor.KeepAnchor)
        cursor.removeSelectedText()
        cursor.insertText(self.prompt + command)
        self.terminal.setTextCursor(cursor)

    def run_command(self, cmd):
        """执行命令（根据配置选择终端类型）"""
        if self.config.get('use_internal_terminal', True):
            # 内置终端执行
            self.terminal.appendPlainText(f"\n> {cmd}\n")
            self.terminal.moveCursor(QTextCursor.End)
            
            if not self.shell.isOpen():
                self.start_shell()
                self.shell.waitForStarted()
                
            try:
                self.shell.write((cmd + '\n').encode('utf-8'))
                self.statusBar().showMessage(f'正在运行: {cmd.split()[0]}...', 3000)
            except Exception as e:
                self.terminal.appendPlainText(f"错误: 无法执行命令 - {str(e)}\n")
                self.statusBar().showMessage('命令执行失败', 3000)
        else:
            # 外置终端执行
            system = platform.system()
            try:
                if system == 'Windows':
                    os.system(f'start cmd /k "{cmd}"')
                elif system == 'Linux':
                    os.system(f'x-terminal-emulator -e "bash -c \'{cmd}; exec bash\'"')
                elif system == 'Darwin':
                    os.system(f'''osascript -e 'tell app "Terminal" to do script "{cmd}"' ''')
                self.statusBar().showMessage(f'已在外置终端运行: {cmd}', 3000)
            except Exception as e:
                QMessageBox.critical(self, '错误', f'启动外置终端失败: {str(e)}')

    def on_shell_output(self):
        data = self.shell.readAll()
        text = bytes(data).decode(errors='replace')
        
        # 添加时间戳
        if not hasattr(self, 'last_output_time'):
            self.last_output_time = 0
        current_time = time.time()
        if current_time - self.last_output_time > 1:  # 如果距离上次输出超过1秒
            timestamp = time.strftime("%H:%M:%S", time.localtime())
            self.terminal.appendPlainText(f"\n[{timestamp}]")
            self.last_output_time = current_time
            
        self.terminal.insertPlainText(text)
        self.terminal.moveCursor(QTextCursor.End)
        
        # 更新状态栏
        if self.shell.state() == QProcess.Running:
            self.statusBar().showMessage('终端运行中...')
        else:
            self.statusBar().showMessage('终端已停止', 3000)

    def export_config(self):
        path, _ = QFileDialog.getSaveFileName(
            self, '导出配置', '', 'JSON Files (*.json)'
        )
        if path:
            try:
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(self.config, f, indent=2, ensure_ascii=False)
                self.statusBar().showMessage(f'配置已导出到: {path}', 3000)
            except Exception as e:
                QMessageBox.critical(self, '错误', f'导出失败: {str(e)}')

    def import_config(self):
        path, _ = QFileDialog.getOpenFileName(
            self, '导入配置', '', 'JSON Files (*.json)'
        )
        if path:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                self.config = {'categories': data} if isinstance(data, list) else data
                self.save_config()
                self.refresh_tree()
                self.statusBar().showMessage(f'已从 {path} 导入配置', 3000)
            except Exception as e:
                QMessageBox.critical(self, '错误', f'导入失败: {str(e)}')

    def show_about(self):
        about_text = """
        <h2>CommandToGUI</h2>
        <p>版本: 1.1.0</p>
        <p>一个方便管理和运行命令行工具的应用</p>
        <p>功能:</p>
        <ul>
            <li>分类管理命令行工具</li>
            <li>参数化命令模板</li>
            <li>内置交互式终端</li>
            <li>配置导入导出</li>
        </ul>
        <p>By:公众号 知攻善防实验室 ChinaRan404</p>
        """
        QMessageBox.about(self, '关于', about_text)

    def switch_theme(self, theme_name):
        self.current_theme = theme_name
        self.apply_theme()
        self.statusBar().showMessage(f'已切换到{theme_name}主题', 3000)

if __name__ ==  "__main__":
    app = QApplication(sys.argv)
    win = ToolRunner()
    win.show()
    sys.exit(app.exec_())
