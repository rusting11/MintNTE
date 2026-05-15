# UI/ui_base.py
# UI基类模块 - 提供通用的UI组件和工具方法
# 所有功能界面应继承此类或使用其中的工具方法

import os
from PyQt5.QtWidgets import (
    QWidget, QFrame, QLabel, QLineEdit, QPushButton,
    QGroupBox, QGridLayout, QVBoxLayout, QHBoxLayout,
    QCheckBox, QComboBox, QSpinBox, QSizePolicy
)
from PyQt5.QtCore import Qt


class BaseUI(QWidget):
    """
    UI基类，提供通用的UI初始化和工具方法
    
    所有功能界面应继承此类，以获得统一的样式和行为
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._base_dir = self._get_base_dir()
    
    def _get_base_dir(self):
        """获取项目根目录"""
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    def apply_theme(self):
        """应用全局主题样式"""
        from UI.themes import get_theme
        self.setStyleSheet(get_theme())
    
    # ========== 通用组件创建方法 ==========
    
    def create_info_group(self, title: str = "") -> QFrame:
        """
        创建信息分组框
        
        Args:
            title: 分组标题
        
        Returns:
            QFrame: 带有样式的分组框
        """
        group = QFrame()
        group.setObjectName("InfoGroup")
        
        layout = QVBoxLayout(group)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        
        if title:
            title_label = QLabel(title)
            title_label.setObjectName("InfoGroupTitle")
            layout.addWidget(title_label)
        
        return group, layout
    
    def create_action_button(self, text: str, object_name: str = "ActionButton") -> QPushButton:
        """
        创建操作按钮
        
        Args:
            text: 按钮文本
            object_name: 对象名称（用于样式）
        
        Returns:
            QPushButton: 带有样式的按钮
        """
        btn = QPushButton(text)
        btn.setObjectName(object_name)
        return btn
    
    def create_info_label(self, text: str) -> QLabel:
        """
        创建信息标签
        
        Args:
            text: 标签文本
        
        Returns:
            QLabel: 带有样式的标签
        """
        label = QLabel(text)
        label.setObjectName("InfoLabel")
        return label
    
    def create_info_field(self, text: str = "", read_only: bool = True) -> QLineEdit:
        """
        创建信息输入框
        
        Args:
            text: 初始文本
            read_only: 是否只读
        
        Returns:
            QLineEdit: 带有样式的输入框
        """
        field = QLineEdit(text)
        field.setObjectName("InfoField")
        field.setReadOnly(read_only)
        return field
    
    def create_check_box(self, text: str, checked: bool = False) -> QCheckBox:
        """
        创建复选框
        
        Args:
            text: 复选框文本
            checked: 是否选中
        
        Returns:
            QCheckBox: 带有样式的复选框
        """
        checkbox = QCheckBox(text)
        checkbox.setChecked(checked)
        checkbox.setObjectName("ActionCheckBox")
        return checkbox
    
    def create_combo_box(self, items: list = None) -> QComboBox:
        """
        创建下拉框
        
        Args:
            items: 选项列表
        
        Returns:
            QComboBox: 带有样式的下拉框
        """
        combo = QComboBox()
        combo.setObjectName("ActionComboBox")
        if items:
            combo.addItems(items)
        return combo
    
    def create_spin_box(self, min_val: int = 0, max_val: int = 9999, value: int = 0) -> QSpinBox:
        """
        创建数字输入框
        
        Args:
            min_val: 最小值
            max_val: 最大值
            value: 当前值
        
        Returns:
            QSpinBox: 带有样式的数字输入框
        """
        spin = QSpinBox()
        spin.setObjectName("InfoField")
        spin.setRange(min_val, max_val)
        spin.setValue(value)
        return spin
    
    # ========== 布局辅助方法 ==========
    
    def create_grid_layout(self, rows: int = 0, cols: int = 0, 
                          h_spacing: int = 12, v_spacing: int = 16) -> QGridLayout:
        """
        创建网格布局
        
        Args:
            rows: 行数（可选，设置最小行高）
            cols: 列数（可选，设置最小列宽）
            h_spacing: 水平间距
            v_spacing: 垂直间距
        
        Returns:
            QGridLayout: 配置好的网格布局
        """
        layout = QGridLayout()
        layout.setHorizontalSpacing(h_spacing)
        layout.setVerticalSpacing(v_spacing)
        
        if rows > 0:
            for i in range(rows):
                layout.setRowMinimumHeight(i, 40)
        
        if cols > 0:
            for i in range(cols):
                layout.setColumnMinimumWidth(i, 100)
        
        return layout
    
    def create_v_layout(self, spacing: int = 12, margins: tuple = None) -> QVBoxLayout:
        """
        创建垂直布局
        
        Args:
            spacing: 间距
            margins: 边距 (left, top, right, bottom)
        
        Returns:
            QVBoxLayout: 配置好的垂直布局
        """
        layout = QVBoxLayout()
        layout.setSpacing(spacing)
        if margins:
            layout.setContentsMargins(*margins)
        else:
            layout.setContentsMargins(0, 0, 0, 0)
        return layout
    
    def create_h_layout(self, spacing: int = 12, margins: tuple = None) -> QHBoxLayout:
        """
        创建水平布局
        
        Args:
            spacing: 间距
            margins: 边距 (left, top, right, bottom)
        
        Returns:
            QHBoxLayout: 配置好的水平布局
        """
        layout = QHBoxLayout()
        layout.setSpacing(spacing)
        if margins:
            layout.setContentsMargins(*margins)
        else:
            layout.setContentsMargins(0, 0, 0, 0)
        return layout


# ========== 预定义组件类 ==========

class InfoPanel(QFrame):
    """
    信息面板组件
    用于显示一组相关信息的容器
    """
    
    def __init__(self, title: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("InfoGroup")
        
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(16, 16, 16, 16)
        self._layout.setSpacing(12)
        
        if title:
            self._title_label = QLabel(title)
            self._title_label.setObjectName("InfoGroupTitle")
            self._layout.addWidget(self._title_label)
        
        # 内容布局
        self._content_layout = QVBoxLayout()
        self._content_layout.setSpacing(8)
        self._layout.addLayout(self._content_layout)
    
    def add_content(self, widget):
        """添加内容组件"""
        self._content_layout.addWidget(widget)
    
    def add_layout(self, layout):
        """添加子布局"""
        self._content_layout.addLayout(layout)


class ActionButton(QPushButton):
    """
    操作按钮组件
    带有统一样式的按钮
    """
    
    def __init__(self, text: str, parent=None, object_name: str = "ActionButton"):
        super().__init__(text, parent)
        self.setObjectName(object_name)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)


class StatusLabel(QLabel):
    """
    状态标签组件
    用于显示状态信息
    """
    
    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setObjectName("StatusLabel")


class LockStatusLabel(QLabel):
    """
    锁定状态标签
    用于显示窗口锁定状态
    """
    
    def __init__(self, text: str = "未锁定", parent=None):
        super().__init__(text, parent)
        self.setObjectName("LockStatus")


class InfoLabel(QLabel):
    """
    信息标签
    用于显示表单标签等
    """
    
    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setObjectName("InfoLabel")


class InfoField(QLineEdit):
    """
    信息输入框
    用于显示只读信息
    """
    
    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setObjectName("InfoField")
        self.setReadOnly(True)


# ========== 常量定义 ==========

# 布局常量
LAYOUT_SPACING_SMALL = 8
LAYOUT_SPACING_MEDIUM = 12
LAYOUT_SPACING_LARGE = 20

LAYOUT_MARGIN_SMALL = 8
LAYOUT_MARGIN_MEDIUM = 12
LAYOUT_MARGIN_LARGE = 16

# 组件尺寸常量
BUTTON_MIN_WIDTH = 100
BUTTON_MIN_HEIGHT = 36

FIELD_MIN_WIDTH = 150
FIELD_MIN_HEIGHT = 32

# 对齐方式常量
ALIGN_LEFT = Qt.AlignLeft
ALIGN_RIGHT = Qt.AlignRight
ALIGN_CENTER = Qt.AlignCenter
ALIGN_TOP = Qt.AlignTop
ALIGN_BOTTOM = Qt.AlignBottom
ALIGN_VCENTER = Qt.AlignVCenter
ALIGN_HCENTER = Qt.AlignHCenter


# ========== 工具函数 ==========

def get_base_dir() -> str:
    """获取项目根目录"""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_image_path(image_name: str, sub_dir: str = "logo") -> str:
    """
    获取图片路径
    
    Args:
        image_name: 图片文件名
        sub_dir: 子目录（默认为logo）
    
    Returns:
        str: 图片完整路径
    """
    base_dir = get_base_dir()
    return os.path.join(base_dir, "Image", sub_dir, image_name)


def is_image_exists(image_name: str, sub_dir: str = "logo") -> bool:
    """
    检查图片是否存在
    
    Args:
        image_name: 图片文件名
        sub_dir: 子目录
    
    Returns:
        bool: 是否存在
    """
    return os.path.exists(get_image_path(image_name, sub_dir))