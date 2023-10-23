import threading
from os.path import expanduser, join
import cv2
from PyQt5.QtCore import QThreadPool
from typing import Union
from .avlc import AudioPlayer, AudioPlayerEvent, AvlcMedia, ms2min
from app.ui.mainwindow import MainWindow
from .scanner import LibraryScanner
from .serializer import serialize_library
from .ui.widgets import TrackItem
import mediapipe as mp
import time


def count_fingers2(results):
    fingerCount = 0
    for hand_landmarks in results.multi_hand_landmarks:
        # Get hand index to check label (left or right)
        handIndex = results.multi_hand_landmarks.index(hand_landmarks)
        handLabel = results.multi_handedness[handIndex].classification[0].label

        # Set variable to keep landmarks positions (x and y)
        handLandmarks = []

        # Fill list with x and y positions of each landmark
        for landmarks in hand_landmarks.landmark:
            handLandmarks.append([landmarks.x, landmarks.y])

        # Test conditions for each finger: Count is increased if finger is
        #   considered raised.
        # Thumb: TIP x position must be greater or lower than IP x position,
        #   deppeding on hand label.

        if handLabel == "Left" and handLandmarks[4][0] > handLandmarks[3][0]:
            fingerCount = fingerCount + 1
        elif handLabel == "Right" and handLandmarks[4][0] < handLandmarks[3][0]:
            fingerCount = fingerCount + 1

        # Other fingers: TIP y position must be lower than PIP y position,
        #   as image origin is in the upper left corner.

        if handLandmarks[8][1] < handLandmarks[6][1]:  # Index finger
            fingerCount = fingerCount + 1
        if handLandmarks[12][1] < handLandmarks[10][1]:  # Middle finger
            fingerCount = fingerCount + 1
        if handLandmarks[16][1] < handLandmarks[14][1]:  # Ring finger
            fingerCount = fingerCount + 1
        if handLandmarks[20][1] < handLandmarks[18][1]:  # Pinky
            fingerCount = fingerCount + 1

    return fingerCount

class VideoThread(threading.Thread):

    def __init__(self, parent):
        super(VideoThread, self).__init__()
        self.parent = parent
        self.running = True

    def run(self):
        cap = cv2.VideoCapture(0)
        drawing = mp.solutions.drawing_utils
        hands = mp.solutions.hands
        hand_obj = hands.Hands(max_num_hands=1)
        start_init = False
        prev = -1
        while True:
            end_time = time.time()
            _, frm = cap.read()
            res = hand_obj.process(cv2.cvtColor(frm, cv2.COLOR_BGR2RGB))
            if res.multi_hand_landmarks:

                # hand_keyPoints=res.multi_hand_landmarks[0]

                cnt=count_fingers2(res)

                if not (prev == cnt):
                    if not (start_init):
                        start_time = time.time()
                        start_init = True

                    elif (end_time - start_time) > 0.2:
                        if (cnt == 1):
                            self.parent.on_next()

                        elif (cnt == 2):
                            self.parent.on_previous()

                        elif (cnt == 3):
                            self.parent.on_fast_forward()

                        elif (cnt == 4):
                            self.parent.on_rewind()

                        elif (cnt == 5):
                            self.parent.on_play_pause()

                        prev = cnt
                        start_init = False

                # drawing.draw_landmarks(frm, hand_keyPoints, hands.HAND_CONNECTIONS)

            # frm = cv2.flip(frm, 1)
            # cv2.putText(frm, str(cnt), (50, 450), cv2.FONT_HERSHEY_SIMPLEX, 3, (255, 0, 0), 10)
            # cv2.imshow("window", frm)
        cv2.destroyAllWindows()
        cap.release()



class Application(MainWindow):

    def __init__(self, p):
        super(Application, self).__init__(p)
        self.threadPool = QThreadPool(self)
        self.video_thread = VideoThread(self)
        self.threadPool.setMaxThreadCount(1000)
        self.audioPlayer: Union[AudioPlayer, None] = None
        self.closingQueue.append(self.serialize)
        self.init_player()
        self.scan_library()
        self.video_thread.start()

    def init_player(self):
        self.audioPlayer = AudioPlayer()
        self.audioPlayer.set_volume(100)
        self.audioPlayer.connect_event(AudioPlayerEvent.PositionChanged, self.on_pos_changed)
        self.audioPlayer.connect_event(AudioPlayerEvent.TrackEndReached, self.on_track_changed)

        self.playerPanelLayout.seekbarFrame.seekbar.seek.connect(self.audioPlayer.set_position)
        self.playerPanelLayout.playerControllerFrame.playPause.clicked.connect(self.on_play_pause)
        self.playerPanelLayout.playerControllerFrame.nextButton.clicked.connect(self.on_next)
        self.playerPanelLayout.playerControllerFrame.previousButton.clicked.connect(self.on_previous)
        self.playerPanelLayout.playerControllerFrame.fastForward.clicked.connect(self.on_fast_forward)
        self.playerPanelLayout.playerControllerFrame.rewind.clicked.connect(self.on_rewind)

        self.playerPanelLayout.playbackControllerFrame.volumeButton.onValueChanged.connect(self.audioPlayer.set_volume)
        # self.playerPanelLayout.playbackControllerFrame.equalizerButton.clicked.connect(self.open_equalizer)
        self.playerPanelLayout.playbackControllerFrame.playbackModeButton.onStateChanged.connect(
            self.playback_mode_changed
        )
    def on_play_pause(self):
        self.audioPlayer.pause()
        if self.audioPlayer.isPaused:
            self.playerPanelLayout.playerControllerFrame.playPause.changeIcon("res/icons/play.svg")
        else:
            self.playerPanelLayout.playerControllerFrame.playPause.changeIcon("res/icons/pause.svg")

    def on_next(self):
        self.audioPlayer.next()
        self.on_track_changed()

    def on_previous(self):
        self.audioPlayer.previous()
        self.on_track_changed()

    def on_fast_forward(self):
        self.audioPlayer.set_position(self.audioPlayer.get_position() + 5000)

    def on_rewind(self):
        self.audioPlayer.set_position(self.audioPlayer.get_position() - 5000)

    def playback_mode_changed(self, mode):
        self.audioPlayer.set_playback_mode(mode)

    def library_add_track(self, media: AvlcMedia):
        track = TrackItem(self, media)
        track.onPlay.connect(self.quick_play)
        self.libraryPage.trackContainer.addItem(track)

    def scan_library(self):
        self.libraryPage.closeEmptyPrompt()
        libraryScanner = LibraryScanner(self.audioPlayer, join(expanduser("~"), "Music"))
        libraryScanner.signal.scanned.connect(self.library_add_track)
        self.threadPool.start(libraryScanner)


    def on_pos_changed(self):
        if not self.isUpdating:
            self.playerPanelLayout.seekbarFrame.seekbar.updatePosition(self.audioPlayer.get_position())
            self.playerPanelLayout.timeFrame.time.setText(
                f"{ms2min(self.audioPlayer.get_position())}/{ms2min(self.audioPlayer.get_length())}"
            )

    def on_track_changed(self):
        media: AvlcMedia = self.audioPlayer.mediaList[self.audioPlayer.currentIndex]
        self.update_player_info(media.art, media.title, media.artist, media.duration)

    # double-click on a track item to quick play
    def quick_play(self, media: AvlcMedia):
        self.audioPlayer.play(self.audioPlayer.mediaList.index(media))
        self.update_player_info(media.art, media.title, media.artist, media.duration)
        self.playerPanelLayout.playerControllerFrame.playPause.changeIcon("res/icons/pause.svg")

    def update_player_info(self, cover, title, artist, duration):
        self.playerPanelLayout.playerInfoFrame.setCoverArt(cover)
        self.playerPanelLayout.playerInfoFrame.setTitle(title)
        self.playerPanelLayout.playerInfoFrame.setArtist(artist)
        self.playerPanelLayout.seekbarFrame.seekbar.setRange(0, duration)

    def serialize(self):
        serialize_library(self.audioPlayer.mediaList, "conf/library.json")



