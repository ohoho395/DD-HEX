"""Visuals scoped to the desktop window; game overlays use their own palette."""
import base64
import json
from functools import lru_cache
from importlib import resources

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QFrame

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

class PearlToolbar(QFrame):
    """A static opal surface for desktop navigation; no backdrop sampling."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(54)

    def paintEvent(self, event):
        face = QRectF(self.rect()).adjusted(2.5, 1.5, -2.5, -3.5)
        path = QPainterPath()
        path.addRoundedRect(face, 14, 14)
        tint = QLinearGradient(face.topLeft(), face.bottomRight())
        tint.setColorAt(0, QColor("#dce7df"))
        tint.setColorAt(.39, QColor("#e6ece8"))
        tint.setColorAt(.68, QColor("#eaeae8"))
        tint.setColorAt(1, QColor("#eee8db"))

        sheen = QLinearGradient(0, face.top(), 0, face.bottom())
        sheen.setColorAt(0, QColor(255, 255, 255, 85))
        sheen.setColorAt(.50, QColor(255, 255, 255, 18))
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
            painter.fillPath(path.translated(0, 1.5), QColor(36, 54, 43, 25))
            painter.fillPath(path, tint)
            painter.save()
            painter.setClipPath(path)
            painter.fillPath(reflection, QColor(255, 255, 252, 56))
            painter.fillRect(face, sheen)
            painter.restore()
            edge = QLinearGradient(0, face.top(), 0, face.bottom())
            edge.setColorAt(0, QColor(255, 255, 255, 245))
            edge.setColorAt(.55, QColor(255, 255, 255, 150))
            edge.setColorAt(1, QColor(145, 158, 147, 104))
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(edge, 1))
            painter.drawPath(path)


STYLE = """
QWidget#desktop, QWidget#page, QWidget#settingsForm, QScrollArea {
    background: #fafaf8; color: #222d27;
}
QLabel {color: #233129; background: transparent;}
QFrame#heroBand {background: #fafaf8; border: none; border-bottom: 1px solid #cbd2cb;}
QLabel#heroText, QLabel#heroMetric {color: #1d3428;}
QFrame#card {background: #ffffff; border: 1px solid #cbd3cb; border-radius: 6px;}
QFrame#card[recommended="yes"] {background: #edf5ec; border: 2px solid #38725a;}
QFrame#settingGroup {background: #f3f5f0; border: 1px solid #d7ded6; border-radius: 6px;}
QLabel#toolbarBrand {font-size: 20px; font-weight: 700; color: #213229;}
QLabel#sectionName {color: #243b2c; font-size: 17px; font-weight: 650; padding-bottom: 4px;}

QPushButton {
    color: #283a2e; background: #ffffff; border: 1px solid #c0cbc0;
    border-radius: 5px; padding: 4px 10px;
}
QPushButton:hover {background: #f0f4ee; border-color: #8fa392;}
QPushButton:pressed {background: #e4ebe1;}
QPushButton:focus {border-color: #316b50;}
QPushButton#toolbarNav {
    background: transparent; color: #405348; border: 1px solid transparent;
    border-radius: 5px; padding: 5px 10px;
}
QPushButton#toolbarNav:hover {background: rgba(255,255,255,128); color: #203e2e;}
QPushButton#toolbarNav:checked {
    background: rgba(255,255,255,190); color: #174634; border-color: #bbcbbd; font-weight: 650;
}
QPushButton#toolbarNav:focus {border-color: #316b50;}
QPushButton#primary {background: #2b5e48; color: #ffffff; border-color: #2b5e48; font-weight: 600;}
QPushButton#primary:hover {background: #224d3a;}
QPushButton#primary:focus {border: 2px solid #102c1b; padding: 3px 9px;}
QPushButton#heroChoice {text-align: left; padding: 8px; font-size: 15px; font-weight: 600;}
QPushButton:disabled {background: #f2f3ef; color: #737a74; border-color: #d5dbd4;}

QLineEdit, QComboBox, QSpinBox, QKeySequenceEdit {
    background: #ffffff; color: #26392d; border: 1px solid #becabe; border-radius: 5px;
    padding: 4px 7px; selection-background-color: #2f634c; selection-color: #ffffff;
}
QLineEdit#toolbarSearch {background: rgba(255,255,255,190); border-color: #b8c5b9;}
QLineEdit:focus, QLineEdit#toolbarSearch:focus, QComboBox:focus, QSpinBox:focus, QKeySequenceEdit:focus {
    border: 1px solid #316b50;
}
QComboBox QAbstractItemView, QAbstractItemView {
    background: #fff; color: #24362b; selection-background-color: #dce9dc;
    selection-color: #203a29;
}
QKeySequenceEdit QLineEdit {background: transparent; border: none; padding: 0;}
QCheckBox {color: #2b3c30; spacing: 7px;}
QCheckBox:disabled {color: #737a74;}
QTabWidget::pane {background: #fafaf8; border: none;}
QTabBar::tab {background: transparent; color: #556057; padding: 6px 12px; border-bottom: 2px solid transparent;}
QTabBar::tab:selected {color: #20513b; border-bottom: 2px solid #32654c;}
QProgressBar {background: #f6f7f2; border: 1px solid #bdc8ba; border-radius: 3px; color: #1e3527; text-align: center;}
QProgressBar::chunk {background: #a0c4ad;}
QScrollBar:vertical {background: #f4f5ef; width: 10px; margin: 0;}
QScrollBar::handle:vertical {background: #bcc7bc; border: 2px solid #f4f5ef; border-radius: 4px; min-height: 25px;}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {height: 0;}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {background: transparent;}
"""
