# UI/themes.py
# 主题样式表定义 - 毛玻璃风格主题
# 
# 主题结构说明：
# 1. 主窗口样式 - QMainWindow, centralWidget
# 2. 头部样式 - HeaderWidget
# 3. 标签页样式 - QTabWidget, QTabBar
# 4. 按钮样式 - QPushButton（通用按钮）, QPushButton#ActionButton（操作按钮）
# 5. 输入框样式 - QLineEdit, QTextEdit, QPlainTextEdit
# 6. 下拉框样式 - QComboBox
# 7. 标签样式 - QLabel（通用）, #TitleLabel, #SubtitleLabel, #InfoLabel, #StatusLabel
# 8. 分组框样式 - QGroupBox, QGroupBox#InfoGroup
# 9. 进度条样式 - QProgressBar
# 10. 复选框样式 - QCheckBox, QCheckBox#ActionCheckBox
# 11. 框架样式 - QFrame, #LeftPanel, #RightPanel, #GuideCard, #LockCard, #PreviewCard
# 12. 数值输入框样式 - QSpinBox#InfoField
# 
# 颜色主题：
# - 主色调：青色系（rgba(0, 160, 200)）
# - 辅助色：绿色系（rgba(0, 180, 160)）
# - 背景色：深色调渐变（rgba(28, 30, 45) -> rgba(15, 16, 28)）
# - 文字色：浅青色（rgba(180, 210, 240)）

def get_theme():
    """返回毛玻璃风格主题的 QSS 样式表"""
    return _build_theme()


def _build_theme():
    """构建完整的主题样式表"""
    return "\n".join([
        _window_styles(),
        _header_styles(),
        _tab_styles(),
        _button_styles(),
        _input_styles(),
        _combo_styles(),
        _label_styles(),
        _group_styles(),
        _progress_styles(),
        _checkbox_styles(),
        _frame_styles(),
        _spinbox_styles(),
        _textedit_styles(),
    ])


# ========== 主窗口样式 ==========

def _window_styles():
    """主窗口和中央控件样式"""
    return """
/* 主窗口背景渐变 */
QMainWindow {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
        stop:0 rgba(28, 30, 45, 255), 
        stop:0.5 rgba(20, 22, 35, 255), 
        stop:1 rgba(15, 16, 28, 255));
}

/* 中央控件 */
QWidget#centralWidget {
    background: transparent;
    font-family: "Microsoft YaHei", "SimHei", sans-serif;
}
"""


# ========== 头部样式 ==========

def _header_styles():
    """头部区域样式"""
    return """
/* 头部容器 */
QWidget#HeaderWidget {
    background: rgba(35, 38, 55, 0.85);
    border-bottom: 1px solid rgba(0, 160, 200, 0.15);
}
"""


# ========== 标签页样式 ==========

def _tab_styles():
    """标签页控件样式"""
    return """
/* 主标签页容器 */
QTabWidget#MainTabWidget {
    background: transparent;
}

/* 标签页内容区域 */
QTabWidget#MainTabWidget::pane {
    border: none;
    background: rgba(35, 38, 55, 0.6);
    border-radius: 16px;
    margin: 12px;
}

/* 标签栏位置调整 */
QTabWidget#MainTabWidget::tab-bar {
    left: 15px;
}

/* 标签栏 */
QTabBar {
    background: transparent;
    font-family: "Microsoft YaHei", "SimHei", sans-serif;
    font-size: 20px;
    font-weight: 500;
}

/* 单个标签 */
QTabBar::tab {
    background: transparent;
    color: rgba(180, 210, 240, 0.85);
    border: 1px solid rgba(0, 191, 255, 0.15);
    border-radius: 8px 8px 0 0;
    padding: 10px 24px;
    margin-right: 6px;
    min-width: 80px;
    min-height: 36px;
}

/* 选中的标签 */
QTabBar::tab:selected {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
        stop:0 rgba(0, 160, 210, 0.25), 
        stop:1 rgba(0, 180, 160, 0.15));
    color: white;
    border: 1px solid rgba(0, 220, 180, 0.3);
    border-bottom: none;
}

/* 悬停的未选中标签 */
QTabBar::tab:hover:!selected {
    background: rgba(0, 160, 210, 0.08);
    color: rgba(220, 240, 255, 0.9);
    border: 1px solid rgba(0, 191, 255, 0.15);
}
"""


# ========== 按钮样式 ==========

def _button_styles():
    """按钮控件样式"""
    return """
/* 通用按钮 */
QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
        stop:0 rgba(0, 160, 200, 0.32), 
        stop:1 rgba(0, 180, 150, 0.22));
    color: rgba(220, 245, 255, 0.95);
    border: 1px solid rgba(0, 191, 255, 0.4);
    border-radius: 10px;
    padding: 12px 28px;
    font-family: "Microsoft YaHei", "SimHei", sans-serif;
    font-size: 19px;
    font-weight: 500;
}

QPushButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
        stop:0 rgba(0, 180, 230, 0.5), 
        stop:1 rgba(0, 200, 170, 0.4));
    border: 1px solid rgba(0, 220, 180, 0.6);
    color: white;
}

QPushButton:pressed {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
        stop:0 rgba(0, 120, 160, 0.55), 
        stop:1 rgba(0, 140, 120, 0.45));
}

/* 操作按钮（ActionButton） */
QPushButton#ActionButton {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
        stop:0 rgba(0, 160, 200, 0.32), 
        stop:1 rgba(0, 180, 150, 0.22));
    color: rgba(220, 245, 255, 0.95);
    border: 1px solid rgba(0, 191, 255, 0.4);
    border-radius: 10px;
    padding: 10px 28px;
    font-family: "Microsoft YaHei", "SimHei", sans-serif;
    font-size: 15px;
    font-weight: 500;
    min-width: 120px;
}

QPushButton#ActionButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
        stop:0 rgba(0, 180, 220, 0.45), 
        stop:1 rgba(0, 200, 170, 0.35));
    border-color: rgba(0, 191, 255, 0.6);
}

QPushButton#ActionButton:pressed {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
        stop:0 rgba(0, 140, 180, 0.5), 
        stop:1 rgba(0, 160, 130, 0.4));
}
"""


# ========== 输入框样式 ==========

def _input_styles():
    """文本输入框样式"""
    return """
/* 单行输入框 */
QLineEdit {
    background: rgba(18, 20, 32, 0.95);
    color: #ffffff;
    border: 1px solid rgba(0, 160, 200, 0.35);
    border-radius: 12px;
    padding: 8px 12px;
    font-family: "Microsoft YaHei", "SimHei", sans-serif;
    font-size: 14px;
}

QLineEdit:focus {
    border: 1px solid rgba(0, 220, 180, 0.55);
}

/* 多行输入框 */
QTextEdit, QPlainTextEdit {
    background: rgba(18, 20, 32, 0.95);
    color: #ffffff;
    border: 1px solid rgba(0, 160, 200, 0.35);
    border-radius: 12px;
    padding: 8px 12px;
    font-family: "Microsoft YaHei", "SimHei", sans-serif;
    font-size: 14px;
}

QTextEdit:focus, QPlainTextEdit:focus {
    border: 1px solid rgba(0, 220, 180, 0.55);
}

/* 信息字段输入框 */
QLineEdit#InfoField {
    background: rgba(20, 24, 40, 0.95);
    color: #ffffff;
    border: 1px solid rgba(0, 180, 160, 0.3);
    border-radius: 6px;
    padding: 0;
    font-size: 15px;
    font-family: "Microsoft YaHei", "SimHei", sans-serif;
}
"""


# ========== 下拉框样式 ==========

def _combo_styles():
    """下拉选择框样式"""
    return """
/* 下拉框 */
QComboBox {
    background: rgba(18, 20, 32, 0.85);
    color: rgba(200, 230, 245, 0.95);
    border: 1px solid rgba(0, 160, 200, 0.25);
    border-radius: 12px;
    padding: 10px 14px;
    font-family: "Microsoft YaHei", "SimHei", sans-serif;
    font-size: 16px;
    min-width: 120px;
}

QComboBox:hover {
    border: 1px solid rgba(0, 200, 170, 0.45);
}

QComboBox:focus {
    border: 1px solid rgba(0, 220, 180, 0.55);
}

/* 下拉箭头区域 */
QComboBox::drop-down {
    border: none;
    width: 24px;
}

/* 下拉列表 */
QComboBox QAbstractItemView {
    background: rgba(25, 28, 45, 0.98);
    color: rgba(200, 230, 245, 0.95);
    border: 1px solid rgba(0, 160, 200, 0.3);
    selection-background-color: rgba(0, 160, 200, 0.35);
    border-radius: 12px;
    padding: 4px;
}

/* 操作下拉框 */
QComboBox#ActionComboBox {
    background: rgba(18, 20, 32, 0.85);
    color: rgba(200, 230, 245, 0.95);
    border: 1px solid rgba(0, 160, 200, 0.25);
    border-radius: 12px;
    padding: 8px 12px;
    font-family: "Microsoft YaHei", "SimHei", sans-serif;
    font-size: 14px;
    min-width: 110px;
}
"""


# ========== 标签样式 ==========

def _label_styles():
    """标签控件样式"""
    return """
/* 通用标签 */
QLabel {
    color: rgba(180, 210, 240, 0.9);
    background: transparent;
    font-family: "Microsoft YaHei", "SimHei", sans-serif;
}

/* 标题标签 */
QLabel#TitleLabel {
    color: white;
    font-size: 20px;
    font-weight: 700;
    font-family: "Microsoft YaHei", "SimHei", sans-serif;
}

/* 副标题标签 */
QLabel#SubtitleLabel {
    color: rgba(160, 190, 220, 0.6);
    font-size: 16px;
    font-family: "Microsoft YaHei", "SimHei", sans-serif;
}

/* 信息标签 */
QLabel#InfoLabel {
    color: rgba(0, 200, 180, 0.95);
    font-size: 20px;
    font-family: "Microsoft YaHei", "SimHei", sans-serif;
    font-weight: 400;
    padding-right: 10px;
    min-height: 28px;
    line-height: 28px;
}

/* 状态标签 */
QLabel#StatusLabel {
    color: rgba(0, 200, 180, 0.85);
    font-family: "Microsoft YaHei", "SimHei", sans-serif;
    font-size: 20px;
    padding-top: 8px;
    padding-left: 2px;
}

/* 锁定状态标签 */
QLabel#LockStatus {
    color: rgba(255, 180, 100, 0.9);
    font-size: 16px;
    font-weight: 600;
    font-family: "Microsoft YaHei", "SimHei", sans-serif;
    padding-left: 2px;
}

/* 统计标签 */
QLabel#StatLabel {
    color: rgba(0, 220, 180, 0.95);
    font-size: 22px;
    font-weight: bold;
    font-family: "Microsoft YaHei", "SimHei", sans-serif;
}

/* 信息分组标题 */
QLabel#InfoGroupTitle {
    color: rgba(0, 220, 180, 0.95);
    font-family: "Microsoft YaHei", "SimHei", sans-serif;
    font-weight: 700;
    padding-bottom: 4px;
    border-bottom: 1px solid rgba(0, 160, 200, 0.2);
    margin-bottom: 4px;
}

/* 预览标签 */
QLabel#PreviewLabel {
    background: rgba(0, 0, 0, 0.6);
    border: none;
}
"""


# ========== 分组框样式 ==========

def _group_styles():
    """分组框控件样式"""
    return """
/* 通用分组框 */
QGroupBox {
    background: rgba(30, 33, 52, 0.7);
    border: 1px solid rgba(0, 160, 200, 0.2);
    border-radius: 12px;
    margin-top: 12px;
    padding-top: 12px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 12px;
    color: rgba(0, 220, 180, 0.95);
    font-family: "Microsoft YaHei", "SimHei", sans-serif;
    font-size: 17px;
    font-weight: 600;
}

/* 信息分组框 */
QGroupBox#InfoGroup {
    background: rgba(30, 33, 52, 0.6);
    border: 1px solid rgba(0, 160, 200, 0.15);
    border-radius: 16px;
    margin-top: 12px;
    padding-top: 10px;
}

QGroupBox#InfoGroup::title {
    color: rgba(0, 220, 180, 0.95);
    font-family: "Microsoft YaHei", "SimHei", sans-serif;
    font-size: 20px;
    font-weight: 800;
    padding: 0 12px;
}

/* 信息框架分组（用于QFrame模拟QGroupBox） */
QFrame#InfoGroup {
    background: rgba(30, 33, 52, 0.6);
    border: 1px solid rgba(0, 160, 200, 0.15);
    border-radius: 16px;
}
"""


# ========== 进度条样式 ==========

def _progress_styles():
    """进度条控件样式"""
    return """
/* 进度条 */
QProgressBar {
    background: rgba(20, 23, 35, 0.8);
    border: 1px solid rgba(0, 160, 200, 0.2);
    border-radius: 6px;
    height: 10px;
    text-align: center;
}

QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
        stop:0 rgba(0, 160, 200, 0.8), 
        stop:1 rgba(0, 180, 160, 0.8));
    border-radius: 4px;
}
"""


# ========== 复选框样式 ==========

def _checkbox_styles():
    """复选框控件样式"""
    return """
/* 通用复选框 */
QCheckBox {
    color: rgba(180, 210, 240, 0.9);
    font-family: "Microsoft YaHei", "SimHei", sans-serif;
    font-size: 15px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 1px solid rgba(0, 160, 200, 0.4);
    border-radius: 4px;
    background: rgba(20, 23, 35, 0.8);
}

QCheckBox::indicator:checked {
    background: rgba(0, 160, 200, 0.6);
    border-color: rgba(0, 191, 255, 0.6);
}

/* 操作复选框 */
QCheckBox#ActionCheckBox {
    color: rgba(180, 210, 240, 0.9);
    font-family: "Microsoft YaHei", "SimHei", sans-serif;
    font-size: 16px;
}

QCheckBox#ActionCheckBox::indicator {
    width: 20px;
    height: 20px;
    border: 1px solid rgba(0, 160, 200, 0.4);
    border-radius: 4px;
    background: rgba(20, 23, 35, 0.8);
}

QCheckBox#ActionCheckBox::indicator:checked {
    background: rgba(0, 160, 200, 0.6);
    border-color: rgba(0, 191, 255, 0.6);
}
"""


# ========== 框架样式 ==========

def _frame_styles():
    """框架控件样式"""
    return """
/* 通用框架 */
QFrame {
    background: transparent;
}

/* 表单布局 */
QFormLayout {
    spacing: 10px;
}

/* 左侧面板 */
QFrame#LeftPanel {
    background: transparent;
}

/* 右侧面板 */
QFrame#RightPanel {
    background: transparent;
}

/* 引导卡片 */
QFrame#GuideCard {
    background: rgba(30, 33, 52, 0.6);
    border: 1px solid rgba(0, 160, 200, 0.15);
    border-radius: 16px;
}

/* 锁定卡片 */
QFrame#LockCard {
    background: rgba(0, 160, 200, 0.1);
    border: 1px solid rgba(0, 191, 255, 0.25);
    border-radius: 10px;
}

/* 预览卡片 */
QFrame#PreviewCard {
    background: rgba(15, 18, 30, 0.85);
    border: 1px solid rgba(0, 160, 200, 0.2);
    border-radius: 16px;
}
"""


# ========== 数值输入框样式 ==========

def _spinbox_styles():
    """数值输入框样式"""
    return """
/* 信息字段数值输入框 */
QSpinBox#InfoField {
    background: rgba(20, 24, 40, 0.95);
    color: #ffffff;
    border: 1px solid rgba(0, 180, 160, 0.3);
    border-radius: 6px;
    padding: 10px 14px;
    font-size: 17px;
    font-family: "Microsoft YaHei", "SimHei", sans-serif;
    min-width: 90px;
}

QSpinBox#InfoField::up-button, QSpinBox#InfoField::down-button {
    width: 24px;
}

QSpinBox#InfoField QLineEdit {
    font-size: 17px;
    font-family: "Microsoft YaHei", "SimHei", sans-serif;
    background: transparent;
    border: none;
    color: #ffffff;
}
"""


# ========== 文本编辑框样式 ==========

def _textedit_styles():
    """文本编辑框样式"""
    return """
QTextEdit {
    background: transparent;
    color: #ffffff;
    border: 1px solid rgba(0, 180, 160, 0.3);
    border-radius: 8px;
    padding: 10px;
    font-size: 15px;
    font-family: "Microsoft YaHei", "SimHei", sans-serif;
}
"""