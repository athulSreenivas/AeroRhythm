from .pages import LibraryPage
from .playerpanel import PlayerPanelLayout
from .sidetab import SideTab
from .uilib.window import Window
from PyQt5 import QtWidgets


class MainWindow(Window):
    def __init__(self, p):
        super(MainWindow, self).__init__(p)
        self.titlebar.windowNotch.setTitle("AeroRhytm")
        self.vlay = QtWidgets.QVBoxLayout(self)  # our main layout
        self.upper_hlay = QtWidgets.QHBoxLayout()
        self.sideTab = SideTab(self)

        self.playerPanelLayout = PlayerPanelLayout()
        self.pageContainer = QtWidgets.QStackedWidget(self)

        self.libraryPage = LibraryPage(self, "Library")

        # for idx, button in enumerate(self.sideTab.findChildren(SideTabButton)):
        #     button.setTabIndex(idx)
        #     button.onClicked.connect(self.pageContainer.setCurrentIndex)

        self.upper_hlay.addWidget(self.sideTab)
        self.upper_hlay.addWidget(self.pageContainer)

        self.vlay.addLayout(self.upper_hlay)
        self.vlay.addLayout(self.playerPanelLayout)
        self.raiseBaseWidget()

