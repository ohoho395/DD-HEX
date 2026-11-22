"""设置里「三选一标签位置」旁边的示意图：一张海克斯卡，标签画在选中的位置。"""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget

POSITIONS = [("top", "卡片上方（默认，压在图标下半）"), ("bottom", "卡片下方（描述下面的空白处）")]


class BadgePosPreview(QWidget):
    def __init__(self, position: str = "top", parent=None):
        super().__init__(parent)
        self.position = position
        self.setFixedSize(112, 150)

    def set_position(self, position: str) -> None:
        self.position = position
        self.update()

    def paintEvent(self, _):
        # Load lazily: settings imports this widget before overlay startup.
        from .overlay import TAG_BORDER, TAG_EMPHASIS, TAG_MUTED, TAG_SURFACE, TAG_TEXT

        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        card = QRectF(6, 4, 100, 142)
        p.setPen(QPen(QColor(116, 116, 116), 2))
        p.setBrush(QColor(26, 26, 26))
        p.drawRoundedRect(card, 8, 8)
        p.setPen(QPen(QColor(132, 132, 132), 2))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QRectF(36, 18, 40, 40))           # 海克斯图标
        p.setPen(Qt.NoPen)
        p.setBrush(TAG_TEXT)
        p.drawRect(QRectF(30, 66, 52, 6))                # 名字
        p.setBrush(TAG_MUTED)
        for i, w in enumerate((76, 70, 56)):             # 描述
            p.drawRect(QRectF(56 - w / 2, 80 + 8 * i, w, 3))
        box = QRectF(20, 40, 72, 22) if self.position != "bottom" else QRectF(20, 110, 72, 22)
        p.setBrush(TAG_SURFACE)
        p.setPen(QPen(TAG_BORDER, 1))
        p.drawRoundedRect(box, 4, 4)
        p.setPen(Qt.NoPen)
        p.setBrush(TAG_EMPHASIS)
        p.drawRoundedRect(QRectF(box.left()+3, box.top()+5, 2, 12), 1, 1)
        f = QFont("Microsoft YaHei UI")
        f.setPixelSize(11)
        f.setBold(True)
        p.setFont(f)
        p.setPen(TAG_EMPHASIS)
        p.drawText(box, Qt.AlignCenter, "首选  58%")
        p.end()
