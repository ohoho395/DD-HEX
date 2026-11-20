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
QWidget#desktop {background:#f2f3ee; color:#182f30;}
QLabel {color:#233d3d; background:transparent;}
QFrame#card {background:#ffffff; border:1px solid #d7dfda; border-radius:10px;}
QFrame#card[recommended="yes"] {background:#e4f4eb; border:2px solid #187666;}
QFrame#heroBand {background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #122f32, stop:1 #244d49); border-radius:12px;}
QLabel#heroText {color:#eff9f2;}
QLabel#heroMetric {color:#eff9f2;}
QPushButton {color:#264442; background:#fff; border:1px solid #bdcbc5; border-radius:6px; padding:4px 10px;}
QPushButton:hover {background:#e9f3ed; border-color:#498776;}
QPushButton:pressed {background:#d1e8dc;}
QPushButton:focus, QLineEdit:focus, QComboBox:focus, QSpinBox:focus {border:1px solid #007567;}
QPushButton#primary {background:#16695e; border:1px solid #16695e; color:white; font-weight:600;}
QPushButton#primary:hover {background:#10564c;}
QLineEdit,QComboBox,QSpinBox,QKeySequenceEdit {background:white;color:#203838;border:1px solid #c8d4cd;border-radius:6px;padding:4px 7px;selection-background-color:#136859;selection-color:white;}
QKeySequenceEdit QLineEdit {border:none;padding:0;}
QTabWidget::pane {background:white; border:1px solid #d4ded7; border-radius:8px;}
QTabBar::tab {background:transparent; color:#586d69; border:none; border-bottom:3px solid transparent; padding:8px 16px; margin-right:4px;}
QTabBar::tab:selected {color:#085e51; border-bottom:3px solid #167667; font-weight:700;}
QTabBar::tab:hover:!selected {background:#e5ece6;}
QWidget#page,QWidget#settingsForm,QScrollArea {background:#fff;}
QLabel#sectionName {color:#244641; font-size:17px; font-weight:700; padding-bottom:5px;}
QFrame#settingGroup {background:#f6f8f4; border:1px solid #d7dfda; border-radius:8px;}
QPushButton#heroChoice {text-align:left; padding:10px; font-size:15px; font-weight:600;}
QKeySequenceEdit QLineEdit {background:transparent;}

QCheckBox {color:#2c4440; spacing:7px;}
QProgressBar {border:1px solid #c4d6cb;border-radius:4px;text-align:center;}
QProgressBar::chunk {background:#7abaa1;}
"""
