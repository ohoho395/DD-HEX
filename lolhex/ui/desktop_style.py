"""Visuals scoped to the desktop window; game overlays use their own palette."""
import base64
import json
from functools import lru_cache
from importlib import resources

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPalette, QPen, QPixmap
from PySide6.QtWidgets import QCheckBox, QFrame, QStyle, QStyleOptionButton

@lru_cache(maxsize=1)
def _portraits():
    try:
        return json.loads(resources.files("lolhex.data").joinpath("hero_icons.json").read_bytes())["icons"]
    except (OSError, ValueError, KeyError):
        return {}

@lru_cache(maxsize=24)
def portrait(alias):
    image = QPixmap()
    data = _portraits().get(alias)
    if data:
        image.loadFromData(base64.b64decode(data))
    return image

class GlassToolbar(QFrame):
    """A static graphite-glass surface for desktop navigation; no backdrop sampling."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(54)

    def paintEvent(self, event):
        face = QRectF(self.rect()).adjusted(2.5, 1.5, -2.5, -3.5)
        path = QPainterPath()
        path.addRoundedRect(face, 14, 14)
        tint = QLinearGradient(face.topLeft(), face.bottomRight())
        tint.setColorAt(0, QColor("#3c3c3c"))
        tint.setColorAt(.39, QColor("#252525"))
        tint.setColorAt(.68, QColor("#212121"))
        tint.setColorAt(1, QColor("#353535"))

        sheen = QLinearGradient(0, face.top(), 0, face.bottom())
        sheen.setColorAt(0, QColor(255, 255, 255, 22))
        sheen.setColorAt(.50, QColor(255, 255, 255, 5))
        sheen.setColorAt(1, QColor(255, 255, 255, 0))

        # One shallow reflected curve carries the pearl effect even over a
        # uniform desktop surface. Keep the area behind labels almost flat.
        w, h = face.width(), face.height()
        reflection = QPainterPath()
        reflection.moveTo(face.left(), -h)
        reflection.lineTo(face.left(), h * .91)
        reflection.cubicTo(w * .24, h * .84, w * .53, -h * .12, w * .83, -h * .06)
        reflection.lineTo(face.right(), -h)
        reflection.closeSubpath()

        with QPainter(self) as painter:
            painter.setRenderHint(QPainter.Antialiasing)
            painter.fillPath(path.translated(0, 1.5), QColor(0, 0, 0, 85))
            painter.fillPath(path, tint)
            painter.save()
            painter.setClipPath(path)
            painter.fillPath(reflection, QColor(255, 255, 255, 12))
            painter.fillRect(face, sheen)
            painter.restore()
            edge = QLinearGradient(0, face.top(), 0, face.bottom())
            edge.setColorAt(0, QColor(255, 255, 255, 112))
            edge.setColorAt(.55, QColor(255, 255, 255, 26))
            edge.setColorAt(1, QColor(175, 175, 175, 65))
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(edge, 1))
            painter.drawPath(path)


class CheckBox(QCheckBox):
    """Keep native keyboard, accessibility and hit testing; draw the tick for dark QSS."""
    def paintEvent(self, event):
        super().paintEvent(event)
        if not self.isChecked():
            return
        option = QStyleOptionButton()
        self.initStyleOption(option)
        bounds = self.style().subElementRect(QStyle.SE_CheckBoxIndicator, option, self)
        x, y, w, h = bounds.x(), bounds.y(), bounds.width(), bounds.height()
        tick = QPainterPath()
        tick.moveTo(x + w*.22, y + h*.52)
        tick.lineTo(x + w*.43, y + h*.73)
        tick.lineTo(x + w*.78, y + h*.28)
        with QPainter(self) as painter:
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setPen(QPen(QColor("#141414"), 1.7, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            painter.drawPath(tick)


def palette():
    """Also theme the native glyphs and popup controls not covered by QSS."""
    pal = QPalette()
    colors = {
        QPalette.Window: "#111111", QPalette.WindowText: "#e7e7e7",
        QPalette.Base: "#191919", QPalette.AlternateBase: "#252525",
        QPalette.Text: "#e7e7e7", QPalette.Button: "#272727",
        QPalette.ButtonText: "#e7e7e7", QPalette.PlaceholderText: "#aaaaaa",
        QPalette.Highlight: "#cecece", QPalette.HighlightedText: "#111111",
        QPalette.Accent: "#cecece", QPalette.ToolTipBase: "#292929",
        QPalette.ToolTipText: "#f2f2f2", QPalette.Link: "#dedede",
        QPalette.LinkVisited: "#bfbfbf", QPalette.Light: "#606060",
        QPalette.Midlight: "#404040", QPalette.Mid: "#353535",
        QPalette.Dark: "#161616", QPalette.Shadow: "#090909",
    }
    for role, value in colors.items():
        pal.setColor(role, QColor(value))
    for role in (QPalette.Text, QPalette.WindowText, QPalette.ButtonText):
        pal.setColor(QPalette.Disabled, role, QColor("#929292"))
    return pal


def apply_app_palette(app):
    """Match top-level popups and platform controls to the scoped widget theme."""
    app.styleHints().setColorScheme(Qt.ColorScheme.Dark)
    app.setPalette(palette())


STYLE = """
QMainWindow, QWidget#desktop, QWidget#page, QWidget#settingsForm, QScrollArea, QMessageBox {
    background: #111111; color: #e7e7e7;
}
QLabel {color: #e7e7e7; background: transparent;}
QFrame#heroBand {background: #111111; border: none; border-bottom: 1px solid #363636;}
QLabel#heroText, QLabel#heroMetric {color: #f1f1f1;}
QFrame#card {background: #1b1b1b; border: 1px solid #404040; border-radius: 6px;}
QFrame#card[recommended="yes"] {background: #272727; border: 2px solid #c7c7c7;}
QFrame#settingGroup {background: #202020; border: 1px solid #3f3f3f; border-radius: 6px;}
QLabel#toolbarBrand {font-size: 20px; font-weight: 700; color: #f4f4f4;}
QLabel#sectionName {color: #e7e7e7; font-size: 17px; font-weight: 650; padding-bottom: 4px;}

QPushButton {
    color: #e7e7e7; background: #272727; border: 1px solid #535353;
    border-radius: 5px; padding: 4px 10px;
}
QPushButton:hover {background: #343434; border-color: #848484;}
QPushButton:pressed {background: #171717; border-color: #aaaaaa;}
QPushButton#toolbarNav {
    background: transparent; color: #d4d4d4; border: 1px solid transparent;
    border-radius: 5px; padding: 5px 10px;
}
QPushButton#toolbarNav:hover {background: rgba(255,255,255,24); color: #ffffff;}
QPushButton#toolbarNav:checked {
    background: #d8d8d8; color: #161616; border-color: #eeeeee; font-weight: 650;
}
QPushButton#primary {background: #dfdfdf; color: #141414; border-color: #dfdfdf; font-weight: 650;}
QPushButton#primary:hover {background: #f2f2f2;}
QPushButton#primary:pressed {background: #c3c3c3;}
QPushButton:focus, QPushButton#toolbarNav:focus {border-color: #eeeeee;}
QPushButton#primary:focus {border: 2px solid #8f8f8f; padding: 3px 9px;}
QPushButton#heroChoice {text-align: left; padding: 8px; font-size: 15px; font-weight: 600;}
QPushButton:disabled {background: #202020; color: #909090; border-color: #363636;}

QLineEdit, QComboBox, QSpinBox, QKeySequenceEdit {
    background: #181818; color: #e7e7e7; border: 1px solid #555555; border-radius: 5px;
    padding: 4px 7px; selection-background-color: #cecece; selection-color: #141414;
    placeholder-text-color: #aaaaaa;
}
QLineEdit#toolbarSearch {background: #1c1c1c; border-color: #626262;}
QLineEdit:focus, QLineEdit#toolbarSearch:focus, QComboBox:focus, QSpinBox:focus, QKeySequenceEdit:focus {
    border: 1px solid #c9c9c9;
}
QComboBox QAbstractItemView, QAbstractItemView, QMenu {
    background: #252525; color: #e7e7e7; border: 1px solid #545454;
    selection-background-color: #d5d5d5; selection-color: #151515;
}
QMenu::item:selected {background: #d5d5d5; color: #151515;}
QMenu::item:disabled {color: #969696;}
QMenu::separator {background: #4d4d4d; height: 1px; margin: 4px;}
QToolTip {background: #262626; color: #f0f0f0; border: 1px solid #606060; padding: 3px;}
QKeySequenceEdit QLineEdit {background: transparent; border: none; padding: 0;}
QCheckBox {color: #e7e7e7; spacing: 7px;}
QCheckBox:disabled {color: #929292;}
QCheckBox::indicator {width: 14px; height: 14px; border: 1px solid #838383; border-radius: 3px; background: #171717;}
QCheckBox::indicator:checked {background: #e0e0e0; border-color: #e0e0e0;}
QCheckBox::indicator:focus, QCheckBox::indicator:hover {border-color: #f5f5f5;}
QCheckBox::indicator:disabled {border-color: #505050; background: #202020;}
QCheckBox::indicator:checked:disabled {background: #858585;}
QTabWidget::pane {background: #111111; border: none;}
QTabBar::tab {background: transparent; color: #b3b3b3; padding: 6px 12px; border-bottom: 2px solid transparent;}
QTabBar::tab:selected {color: #f2f2f2; border-bottom: 2px solid #d2d2d2;}
QProgressBar {background: #161616; border: 1px solid #575757; border-radius: 3px; color: #fafafa; text-align: center;}
QProgressBar::chunk {background: #5f5f5f;}
QScrollBar:vertical {background: #161616; width: 10px; margin: 0;}
QScrollBar::handle:vertical {background: #606060; border: 2px solid #161616; border-radius: 4px; min-height: 25px;}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {height: 0;}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {background: transparent;}
"""
