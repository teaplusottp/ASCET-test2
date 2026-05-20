#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Gradient Spinner Widget - 支持渐变色的旋转加载动画组件
提供多种样式和渐变效果的Spinner控件

作者:jiarui zhang
"""

import time
from math import sin, cos, radians

from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import Qt
from PySide6.QtGui import (
    QPainter, QPen, QColor, QBrush, 
    QConicalGradient, QLinearGradient, QRadialGradient
)


class GradientSpinner(QWidget):
    """支持渐变色的基础Spinner类"""
    
    def __init__(self, width, color, gradient_type=None):
        """
        初始化渐变Spinner
        
        Args:
            width: 线条宽度
            color: 基础颜色（非渐变时使用）
            gradient_type: 渐变类型 ("rainbow", "sunset", "ocean", "purple")
        """
        super().__init__()
        
        self.w = width
        self.color = color
        self.gradient_type = gradient_type
        
        self.angle = 0
        self.speed = 4.8
        self.animType = 1
        self.play = True
        self.last_call = time.time()
        
        # 渐变颜色配置
        self.setup_gradient_colors()
    
    def setup_gradient_colors(self):
        """设置渐变颜色方案"""
        self.gradient_colors = {
            "rainbow": [  # 彩虹色
                QColor(255, 0, 0),      # 红
                QColor(255, 127, 0),    # 橙
                QColor(255, 255, 0),    # 黄
                QColor(0, 255, 0),      # 绿
                QColor(0, 0, 255),      # 蓝
                QColor(75, 0, 130),     # 靛
                QColor(148, 0, 211)     # 紫
            ],
            "sunset": [  # 日落色
                QColor(255, 94, 77),    # 珊瑚红
                QColor(255, 154, 0),    # 橙色
                QColor(255, 206, 84),   # 金黄
                QColor(255, 154, 0),    # 橙色
                QColor(255, 94, 77)     # 珊瑚红
            ],
            "ocean": [  # 海洋色
                QColor(0, 119, 190),    # 深蓝
                QColor(0, 180, 216),    # 天蓝
                QColor(144, 224, 239),  # 淡蓝
                QColor(0, 180, 216),    # 天蓝
                QColor(0, 119, 190)     # 深蓝
            ],
            "purple": [  # 紫色系
                QColor(155, 89, 182),   # 紫色
                QColor(142, 68, 173),   # 深紫
                QColor(155, 89, 182),   # 紫色
                QColor(187, 143, 206),  # 淡紫
                QColor(155, 89, 182)    # 紫色
            ]
        }
    
    def create_conical_gradient(self, center_x, center_y):
        """创建圆锥渐变（最适合旋转动画）"""
        gradient = QConicalGradient(center_x, center_y, self.angle / 16)
        
        colors = self.gradient_colors.get(self.gradient_type, self.gradient_colors["rainbow"])
        
        # 根据动画角度动态调整渐变
        for i, color in enumerate(colors):
            position = i / (len(colors) - 1) if len(colors) > 1 else 0
            gradient.setColorAt(position, color)
        
        return gradient
    
    def create_radial_gradient(self, center_x, center_y, radius):
        """创建径向渐变"""
        gradient = QRadialGradient(center_x, center_y, radius)
        
        colors = self.gradient_colors.get(self.gradient_type, self.gradient_colors["rainbow"])
        
        # 从中心到边缘的渐变
        gradient.setColorAt(0, colors[0])
        gradient.setColorAt(0.5, colors[len(colors)//2])
        gradient.setColorAt(1, colors[-1])
        
        return gradient
    
    def create_linear_gradient(self, rect_width, rect_height):
        """创建线性渐变"""
        # 根据角度设置渐变方向
        angle_rad = radians(self.angle / 16)
        x1 = rect_width/2 + cos(angle_rad) * rect_width/2
        y1 = rect_height/2 + sin(angle_rad) * rect_height/2
        x2 = rect_width/2 - cos(angle_rad) * rect_width/2
        y2 = rect_height/2 - sin(angle_rad) * rect_height/2
        
        gradient = QLinearGradient(x1, y1, x2, y2)
        
        colors = self.gradient_colors.get(self.gradient_type, self.gradient_colors["rainbow"])
        
        for i, color in enumerate(colors):
            position = i / (len(colors) - 1) if len(colors) > 1 else 0
            gradient.setColorAt(position, color)
        
        return gradient
    
    def set_speed(self, speed):
        """设置动画速度"""
        self.speed = speed
    
    def set_gradient_type(self, gradient_type):
        """设置渐变类型"""
        self.gradient_type = gradient_type
    
    def start_animation(self):
        """开始动画"""
        self.play = True
        self.update()
    
    def stop_animation(self):
        """停止动画"""
        self.play = False
    
    def paintEvent(self, event):
        """支持渐变的绘制方法"""
        if not self.play:
            return
        
        painter = QPainter(self)
        
        try:
            painter.setRenderHint(QPainter.Antialiasing, True)
            
            w = self.w
            rect_x = int(w)
            rect_y = int(w)
            rect_width = int(self.width() - w * 2)
            rect_height = int(self.height() - w * 2)
            start_angle = int(self.angle)
            
            if rect_width <= 0 or rect_height <= 0:
                return
            
            # 根据是否有渐变类型选择画笔
            if self.gradient_type:
                center_x = self.width() / 2
                center_y = self.height() / 2
                radius = min(center_x, center_y) - w
                
                if self.gradient_type in ["rainbow", "sunset", "ocean", "purple"]:
                    # 使用圆锥渐变（最佳效果）
                    gradient = self.create_conical_gradient(center_x, center_y)
                    pen = QPen(QBrush(gradient), w)
                else:
                    # 回退到单色
                    pen = QPen(self.color, w)
            else:
                # 普通单色
                pen = QPen(self.color, w)
            
            painter.setPen(pen)
            
            if self.animType == 0:
                span_angle = int(90 * 16)
                painter.drawArc(rect_x, rect_y, rect_width, rect_height, start_angle, span_angle)
                
            elif self.animType == 1:
                angle_rad = radians(self.angle / 16)
                angle_rad2 = radians((self.angle / 16) + 130)
                
                sa = ((sin(angle_rad) + 1) / 2) * (180 * 16) + ((sin(angle_rad2) + 1) / 2) * (180 * 16)
                span_angle = max(1, int(sa))
                
                painter.drawArc(rect_x, rect_y, rect_width, rect_height, start_angle, span_angle)
                
        except Exception as e:
            print(f"Gradient Spinner paint error: {e}")
        
        # 更新角度
        ep = (time.time() - self.last_call) * 1000
        self.last_call = time.time()
        
        self.angle += self.speed * ep
        if self.angle > 360 * 16:
            self.angle = 0
        elif self.angle < 0:
            self.angle = 360 * 16
        
        if self.play:
            self.update()


class MultiStyleSpinnerWidget(QWidget):
    """渐变的多样式Spinner控件"""
    
    
    STYLE_CONFIGS = {
        "thin": {
            "width": 1.5,
            "color": QColor(52, 152, 219),
            "gradient_type": None,
            "speed": 12.0
        },
        "thick": {
            "width": 3,
            "color": QColor(46, 204, 113),
            "gradient_type": None,
            "speed": 8.0
        },
        "colorful": {
            "width": 2,
            "color": QColor(155, 89, 182),
            "gradient_type": "rainbow",
            "speed": 5.0
        },
        "sunset": {
            "width": 2.5,
            "color": QColor(255, 94, 77),
            "gradient_type": "sunset",
            "speed": 8.0
        },
        "ocean": {
            "width": 2,
            "color": QColor(0, 119, 190),
            "gradient_type": "ocean",
            "speed": 9.0
        },
        "purple": {
            "width": 2.5,
            "color": QColor(155, 89, 182),
            "gradient_type": "purple",
            "speed": 7.0
        },
        "default": {
            "width": 2,
            "color": QColor(52, 152, 219),
            "gradient_type": None,
            "speed": 10.0
        }
    }
    
    def __init__(self, parent=None, style="default", size=24):
        """
        初始化多样式Spinner控件
        
        Args:
            parent: 父控件
            style: 样式名称 ("thin", "thick", "colorful", "sunset", "ocean", "purple", "default")
            size: 控件尺寸
        """
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.is_animating = False
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignCenter)
        
        # 根据样式创建Spinner
        self.spinner = self.create_gradient_spinner(style)
        spinner_size = max(16, size - 4)  # 稍小于容器尺寸
        self.spinner.setFixedSize(spinner_size, spinner_size)
        
        layout.addWidget(self.spinner)
        self.setLayout(layout)
        self.setVisible(False)
    
    def create_gradient_spinner(self, style):
        """创建支持渐变的Spinner"""
        config = self.STYLE_CONFIGS.get(style, self.STYLE_CONFIGS["default"])
        
        spinner = GradientSpinner(
            width=config["width"],
            color=config["color"],
            gradient_type=config["gradient_type"]
        )
        spinner.speed = config["speed"]
        spinner.animType = 1
        
        return spinner
    
    def start_animation(self):
        """开始动画"""
        if not self.is_animating:
            self.is_animating = True
            self.setVisible(True)
            self.spinner.start_animation()
    
    def stop_animation(self):
        """停止动画"""
        if self.is_animating:
            self.is_animating = False
            self.spinner.stop_animation()
            self.setVisible(False)
    
    def set_style(self, style):
        """动态切换样式"""
        if style in self.STYLE_CONFIGS:
            config = self.STYLE_CONFIGS[style]
            self.spinner.set_gradient_type(config["gradient_type"])
            self.spinner.set_speed(config["speed"])
            self.spinner.color = config["color"]
    
    def set_visible_when_stopped(self, visible):
        """设置停止时是否可见"""
        if not self.is_animating:
            self.setVisible(visible)


# 便捷函数
def create_spinner(style="default", size=24, parent=None):
    """
    便捷函数：创建指定样式的Spinner
    
    Args:
        style: 样式名称
        size: 尺寸
        parent: 父控件
    
    Returns:
        MultiStyleSpinnerWidget实例
    """
    return MultiStyleSpinnerWidget(parent=parent, style=style, size=size)


def create_rainbow_spinner(size=24, parent=None):
    """创建彩虹样式的Spinner"""
    return create_spinner("colorful", size, parent)


def create_ocean_spinner(size=24, parent=None):
    """创建海洋样式的Spinner"""
    return create_spinner("ocean", size, parent)


if __name__ == "__main__":
    # 测试代码
    import sys
    from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QHBoxLayout
    
    class SpinnerTestWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("Gradient Spinner Test")
            self.setGeometry(200, 200, 400, 300)
            
            central_widget = QWidget()
            self.setCentralWidget(central_widget)
            
            layout = QVBoxLayout(central_widget)
            
            # 创建不同样式的Spinner
            self.spinners = {}
            styles = ["default", "thin", "thick", "colorful", "sunset", "ocean", "purple"]
            
            for style in styles:
                container = QWidget()
                container_layout = QHBoxLayout(container)
                
                spinner = create_spinner(style, size=32)
                self.spinners[style] = spinner
                
                start_btn = QPushButton(f"Start {style}")
                stop_btn = QPushButton(f"Stop {style}")
                
                start_btn.clicked.connect(lambda checked, s=spinner: s.start_animation())
                stop_btn.clicked.connect(lambda checked, s=spinner: s.stop_animation())
                
                container_layout.addWidget(spinner)
                container_layout.addWidget(start_btn)
                container_layout.addWidget(stop_btn)
                container_layout.addStretch()
                
                layout.addWidget(container)
            
            # 全局控制按钮
            global_layout = QHBoxLayout()
            start_all_btn = QPushButton("Start All")
            stop_all_btn = QPushButton("Stop All")
            
            start_all_btn.clicked.connect(self.start_all)
            stop_all_btn.clicked.connect(self.stop_all)
            
            global_layout.addWidget(start_all_btn)
            global_layout.addWidget(stop_all_btn)
            global_layout.addStretch()
            
            layout.addLayout(global_layout)
        
        def start_all(self):
            for spinner in self.spinners.values():
                spinner.start_animation()
        
        def stop_all(self):
            for spinner in self.spinners.values():
                spinner.stop_animation()
    
    app = QApplication(sys.argv)
    window = SpinnerTestWindow()
    window.show()
    sys.exit(app.exec())