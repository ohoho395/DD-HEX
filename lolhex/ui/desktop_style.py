"""Visuals scoped to the desktop window; game overlays use their own palette."""
import base64
import json
from functools import lru_cache
from importlib import resources

from PySide6.QtGui import QPixmap

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

STYLE = """
QWidget#desktop {background:#111318; color:#E9E7E1;}
QLabel {color:#E9E7E1; background:transparent;}
QFrame#card {background:#1E222A; border:1px solid #383D48; border-radius:9px;}
QFrame#card[recommended="yes"] {background:#302A20; border:1px solid #D8AA64;}
QFrame#heroBand {background:#23272F; border:1px solid #3A3F48; border-radius:10px;}
QLabel#heroText, QLabel#heroMetric {color:#F4F1E9;}
QPushButton {color:#EEEAE0; background:#252932; border:1px solid #404652; border-radius:6px; padding:5px 11px;}
QPushButton:hover {background:#323640; border-color:#6B6E78;}
QPushButton:pressed {background:#39342C;}
QPushButton:focus, QLineEdit:focus, QComboBox:focus, QSpinBox:focus {border:1px solid #E6B973;}
QPushButton#primary {background:#E6B973; border:1px solid #E6B973; color:#20190F; font-weight:700;}
QPushButton#primary:hover {background:#F2CA8F;}
QPushButton:disabled {background:#1C1F26; color:#82848A;}
QLineEdit,QComboBox,QSpinBox,QKeySequenceEdit {background:#1A1D24;color:#E9E7E1;border:1px solid #3D424D;border-radius:6px;padding:5px 9px;selection-background-color:#D5A76C;selection-color:#20190F;}
QComboBox QAbstractItemView, QAbstractItemView {background:#242832; color:#E9E7E1; selection-background-color:#51412D;}
QKeySequenceEdit QLineEdit {border:none;padding:0; background:transparent;}
QTabWidget::pane {background:#1A1D24; border:1px solid #333844; border-radius:8px;}
QTabBar::tab {background:transparent; color:#B3B6BE; border:none; border-bottom:3px solid transparent; padding:10px 18px; margin-right:4px;}
QTabBar::tab:selected {color:#E6B973; border-bottom:3px solid #E6B973; font-weight:700;}
QTabBar::tab:hover:!selected {background:#20242C;}
QWidget#page,QWidget#settingsForm,QScrollArea {background:#1A1D24;}
QLabel#sectionName {color:#F0E5D4; font-size:17px; font-weight:700; padding-bottom:5px;}
QFrame#settingGroup {background:#22262E; border:1px solid #343946; border-radius:8px;}
QPushButton#heroChoice {text-align:left; padding:10px; font-size:15px; font-weight:600;}
QCheckBox {color:#E9E7E1; spacing:8px;}
QProgressBar {border:1px solid #655742;border-radius:4px;text-align:center;color:#F7E5C7;}
QProgressBar::chunk {background:#AC8856;}
QScrollBar:vertical {background:#181B21; width:9px; margin:0;}
QScrollBar::handle:vertical {background:#4E5360; border:2px solid #181B21; border-radius:4px; min-height:28px;}
QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical {height:0;}
QScrollBar::add-page:vertical,QScrollBar::sub-page:vertical {background:transparent;}
"""
