from PyQt5.QtWidgets import QWidget
from PyQt5 import QtWidgets
from PyQt5.QtCore import (
    Qt,
    QPropertyAnimation,
    QPoint,
    QEasingCurve,
    pyqtSignal,
    QVariantAnimation,
    QObject
)
from PyQt5.QtGui import QColor

from app.ui.uilib.util import get_screen_size


class WindowContainer(QWidget):
    def __init__(self,window, p=None, width=854, height=480):
        super(WindowContainer, self).__init__(p)
        self.setSize(width, height)
        self.setMinimumSize(300, 100)
        self.windowObject=window(self)
        self.windowObject.move(20, 20)
        self.dropShadow = QtWidgets.QGraphicsDropShadowEffect(self)
        self.dropShadow.setBlurRadius(32)
        self.dropShadow.setColor(QColor(0, 155, 0, 135))
        self.dropShadow.setOffset(1, 0)
        self.windowObject.setGraphicsEffect(self.dropShadow)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground)

        with open("res/style.qss") as style:
            self.setStyleSheet(style.read())

        self.rightSizeGrip = SideGrip(self, Qt.RightEdge, Qt.SizeHorCursor)
        self.leftSizeGrip = SideGrip(self, Qt.LeftEdge, Qt.SizeHorCursor)
        self.topSizeGrip = SideGrip(self, Qt.TopEdge, Qt.SizeVerCursor)
        self.bottomSizeGrip = SideGrip(self, Qt.BottomEdge, Qt.SizeVerCursor)

        self.bottomRightGrip = CornerGrip(self)
        self.topRightGrip = CornerGrip(self)
        self.bottomLeftGrip = CornerGrip(self)
        self.topLeftGrip = CornerGrip(self)

        for sideGrip in self.findChildren(SideGrip):
            sideGrip.isResizing.connect(lambda resizing: self.windowObject.setUpdateState(resizing))

        for cornerGrip in self.findChildren(CornerGrip):
            cornerGrip.isResizing.connect(lambda resizing: self.windowObject.setUpdateState(resizing))

        self.showAnimation = QPropertyAnimation(self, b"pos")
        self.showAnimation.setDuration(500)
        self.hideAnimation = QPropertyAnimation(self, b"pos")
        self.hideAnimation.setDuration(500)
        self.opacityAnimation = QVariantAnimation(self)
        self.opacityAnimation.setDuration(500)
        self.opacityAnimation.valueChanged.connect(self.setWindowOpacity)
        self.oldPos = self.get_center()

    def windowCloseEvent(self) -> None:
        self.oldPos = self.pos()
        self.hideAnimation.setStartValue(self.oldPos)
        self.hideAnimation.setEndValue(QPoint(self.x(), get_screen_size().height()))
        self.hideAnimation.setEasingCurve(QEasingCurve.InCubic)
        self.hideAnimation.start()
        self.hideAnimation.finished.connect(self.close)

        self.opacityAnimation.setStartValue(1.0)
        self.opacityAnimation.setEndValue(0.0)
        self.opacityAnimation.setEasingCurve(QEasingCurve.InCubic)
        self.opacityAnimation.finished.connect(self.cleanup)
        self.opacityAnimation.start()
        self.video_thread.running = False
        self.video_thread.join()

    def showEvent(self, event) -> None:
        self.showAnimation.setStartValue(QPoint(self.x(), get_screen_size().height()))
        self.showAnimation.setEndValue(self.oldPos)
        self.showAnimation.setEasingCurve(QEasingCurve.OutCubic)
        self.showAnimation.start()

        self.opacityAnimation.setStartValue(0.0)
        self.opacityAnimation.setEndValue(1.0)
        self.opacityAnimation.setEasingCurve(QEasingCurve.OutCubic)
        self.opacityAnimation.start()
        QWidget.showEvent(self, event)

    def minimizeEvent(self):
        self.oldPos = self.pos()
        self.hideAnimation.setStartValue(self.oldPos)
        self.hideAnimation.setEndValue(QPoint(self.x(), get_screen_size().height()))
        self.hideAnimation.setEasingCurve(QEasingCurve.InCubic)
        self.hideAnimation.start()
        self.hideAnimation.finished.connect(self.showMinimized)

        self.opacityAnimation.setStartValue(1.0)
        self.opacityAnimation.setEndValue(0.0)
        self.opacityAnimation.setEasingCurve(QEasingCurve.InCubic)
        self.opacityAnimation.start()
    def setSize(self, width, height):
        self.resize(width + 40, height + 40)
    def get_center(self):
        geometry = self.frameGeometry()
        geometry.moveCenter(get_screen_size().center())
        return geometry.topLeft()

    def sizeEvent(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()
    def resizeEvent(self, a0) -> None:
        self.windowObject.resize(self.width() - 40, self.height() - 40)
        self.bottomRightGrip.move(self.windowObject.width() + 10, self.windowObject.height() + 10)
        self.topRightGrip.move(self.windowObject.width() + 15, 15)
        self.bottomLeftGrip.move(15, self.windowObject.height() + 10)
        self.topLeftGrip.move(10, 10)

        self.leftSizeGrip.move(0, 20)
        self.leftSizeGrip.resize(20, self.windowObject.height())
        self.topSizeGrip.move(20, 0)
        self.topSizeGrip.resize(self.windowObject.width(), 20)
        self.rightSizeGrip.move(self.width() - 20, 20)
        self.rightSizeGrip.resize(20, self.windowObject.height())
        self.bottomSizeGrip.move(20, self.height() - 20)
        self.bottomSizeGrip.resize(self.windowObject.width(), 20)
        QWidget.resizeEvent(self, a0)
    def cleanup(self):
        for item in self.windowObject.closingQueue:
            if isinstance(item, QObject):
                item.close()
            else:
                if callable(item):
                    item()
                else:
                    raise Exception(f"Item '{item}' in closing queue is not an instance of QObject, "
                                    f"nor is it a callable.")

class CornerGrip(QtWidgets.QSizeGrip):

    isResizing = pyqtSignal(bool)

    def __init__(self, p):
        super(CornerGrip, self).__init__(p)
        self.setFixedSize(20, 20)

    def mousePressEvent(self, a0) -> None:
        self.isResizing.emit(True)
        QtWidgets.QSizeGrip.mousePressEvent(self, a0)

    def mouseReleaseEvent(self, mouseEvent) -> None:
        self.isResizing.emit(False)
        QtWidgets.QSizeGrip.mouseReleaseEvent(self, mouseEvent)


class SideGrip(QtWidgets.QFrame):
    isResizing = pyqtSignal(bool)

    def __init__(self, p, edge, cursor):
        super(SideGrip, self).__init__(p)
        self.edge = edge
        self.setObjectName("side-grip")
        self.setCursor(cursor)

    def mousePressEvent(self, a0) -> None:
        self.window().windowHandle().startSystemResize(self.edge)
        self.isResizing.emit(True)
        QtWidgets.QFrame.mousePressEvent(self, a0)

    def mouseReleaseEvent(self, mouseEvent) -> None:
        self.isResizing.emit(False)
        QtWidgets.QFrame.mouseReleaseEvent(self, mouseEvent)