# UI/themes.py
# MintNTE 主题样式库

THEMES = {
    "薄荷风格": """
        QMainWindow { background-color: #1e1e2f; }
        #MainTabWidget::pane { border: 1px solid #0ff; background-color: #1e1e2f; }
        QTabBar::tab {
            background-color: #2a2a3a; color: #0ff; padding: 8px 20px; margin: 2px;
            border-top-left-radius: 5px; border-top-right-radius: 5px;
        }
        QTabBar::tab:selected { background-color: #0ff; color: #1e1e2f; }
        QTabBar::tab:hover { background-color: #3a3a4a; }
    """,
    "樱花风格": """
        QMainWindow { background-color: #2a1a2a; }
        #MainTabWidget::pane { border: 1px solid #f0f; background-color: #2a1a2a; }
        QTabBar::tab {
            background-color: #3a2a3a; color: #f0f; padding: 8px 20px; margin: 2px;
            border-top-left-radius: 5px; border-top-right-radius: 5px;
        }
        QTabBar::tab:selected { background-color: #f0f; color: #2a1a2a; }
        QTabBar::tab:hover { background-color: #4a3a4a; }
    """,
    "极简白": """
        QMainWindow { background-color: #f0f0f0; }
        #MainTabWidget::pane { border: 1px solid #aaa; background-color: #f0f0f0; }
        QTabBar::tab {
            background-color: #ddd; color: #333; padding: 8px 20px; margin: 2px;
            border-top-left-radius: 5px; border-top-right-radius: 5px;
        }
        QTabBar::tab:selected { background-color: #aaa; color: #fff; }
        QTabBar::tab:hover { background-color: #bbb; }
    """,
    "暗金荣耀": """
        QMainWindow { background-color: #1e1a0f; }
        #MainTabWidget::pane { border: 1px solid #ffaa00; background-color: #1e1a0f; }
        QTabBar::tab {
            background-color: #2a261a; color: #ffaa00; padding: 8px 20px; margin: 2px;
            border-top-left-radius: 5px; border-top-right-radius: 5px;
        }
        QTabBar::tab:selected { background-color: #ffaa00; color: #1e1a0f; }
        QTabBar::tab:hover { background-color: #3a362a; }
    """,
    "海洋蓝": """
        QMainWindow { background-color: #0f1a2a; }
        #MainTabWidget::pane { border: 1px solid #0066ff; background-color: #0f1a2a; }
        QTabBar::tab {
            background-color: #1a2636; color: #0066ff; padding: 8px 20px; margin: 2px;
            border-top-left-radius: 5px; border-top-right-radius: 5px;
        }
        QTabBar::tab:selected { background-color: #0066ff; color: #0f1a2a; }
        QTabBar::tab:hover { background-color: #2a3646; }
    """,
    "赛博朋克": """
        QMainWindow { background-color: #0a001a; }
        #MainTabWidget::pane { border: 1px solid #ff00ff; background-color: #0a001a; }
        QTabBar::tab {
            background-color: #1a0033; color: #00ffff; padding: 8px 20px; margin: 2px;
            border-top-left-radius: 5px; border-top-right-radius: 5px;
        }
        QTabBar::tab:selected { background-color: #ff00ff; color: #0a001a; }
        QTabBar::tab:hover { background-color: #330066; }
    """
}

def get_theme(name="薄荷风格"):
    """返回主题对应的 QSS 样式表，默认为薄荷风格"""
    return THEMES.get(name, THEMES["薄荷风格"])