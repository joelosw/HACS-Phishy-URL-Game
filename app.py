import argparse
import json
import os
import sys
import time
import urllib.request
import random
from collections import defaultdict
from itertools import zip_longest
from queue import Empty, Queue
from threading import Thread
from typing import Dict, List, Optional, Tuple, Set
from question_class import Question
import numpy as np
from PIL import Image, ImageDraw, ImageQt
from PyQt5 import QtCore
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QIcon, QKeySequence, QPixmap, QFont
from PyQt5.QtWidgets import (
    QApplication,
    QBoxLayout,
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QShortcut,
    QVBoxLayout,
    QWidget,
    QProgressBar
)


class App(QMainWindow):
    question_set: Set[Question]
    interaction_layout: QBoxLayout
    label_layout: QBoxLayout
    combine_layout: QBoxLayout
    correct_url: bool = None
    score: int = 0
    question_start_time: float = 0
    timer = QTimer()
    time_remaining: float = 0

    def __init__(
        self,
        question_set: Set[Question],

    ):
        super().__init__()
        self.question_set = question_set
        self._init()

    def _init(self):
        self.title = "URL Game"
        self.left_padding = 10
        self.top_padding = 10
        self.width = 512
        self.height = 400
        self.current_key = ""
        self.label_qt_obj = {}
        self.result_data = {}
        self.score = 0

        self.setWindowTitle(self.title)
        self.setGeometry(self.left_padding, self.top_padding,
                         self.width, self.height)
        self.global_layout = QHBoxLayout()
        self.interaction_layout = QVBoxLayout()
        self.button_layout = QHBoxLayout()
        self.button_true = QPushButton("Correct")
        self.button_true.setMinimumHeight(50)
        self.button_true.setStyleSheet("background-color: {}".format('green'))
        self.button_true.clicked.connect(self.correct_clicked)
        self.button_false = QPushButton("FALSE")
        self.button_false.setMinimumHeight(50)
        self.button_false.setStyleSheet("background-color: {}".format('red'))
        self.button_false.clicked.connect(self.false_clicked)
        self.widget_image = QLabel(self)
        self.widget_image.setAlignment(QtCore.Qt.AlignCenter)
        self.widget_url = QLabel(self)
        self.score_board = QLabel(self)
        self.widget_url.setFont(QFont('Arial', 35))
        self.interaction_layout.addWidget(self.widget_image)
        self.interaction_layout.addWidget(self.widget_url)
        self.widget_url.setFont(QFont('Arial', 35))
        self.widget_url.setAlignment(QtCore.Qt.AlignCenter)
        self.button_layout.addWidget(self.button_true, 5)
        self.button_layout.addWidget(self.button_false, 1)
        self.interaction_layout.addLayout(self.button_layout)

        self.time_bar = QProgressBar(self)
        self.time_bar.setMaximum(1000)
        self.time_bar.setValue(1000)
        self.time_bar.setStyleSheet("QProgressBar::chunk "
                                    "{"
                                    "background-color: green;"
                                    "}")
        self.time_bar.setTextVisible(True)
        self.time_bar.setAlignment(QtCore.Qt.AlignCenter)
        self.interaction_layout.addWidget(self.time_bar)

        self.timer.timeout.connect(self.set_time_bar_status)
        self.timer.start(50)

        self.window = QWidget()  # Main Widget

        self.global_layout.addLayout(self.interaction_layout)
        self.global_layout.addWidget(self.score_board)
        self.window.setLayout(self.global_layout)
        self.setCentralWidget(self.window)
        self.show()
        self.load_next_screen()

    def set_time_bar_status(self):
        self.time_remaining = 10 - (time.time() - self.question_start_time)
        if self.time_remaining <= 0:
            self.score -= 10
            self.score_board.setStyleSheet('background-color: red')
            self.load_next_screen()
        self.time_bar.setValue(self.time_remaining*100)
        self.time_bar.setFormat(f'{round(self.time_remaining, 1)} s')

    def load_next_screen(self):
        self.score_board.setText('Points: \n {}'.format(self.score))
        self.next_random_question()

    def correct_clicked(self):
        """
        Define what happens if the button "correct" was clicked
        """
        if self.correct_url:
            self.score += (round(self.time_remaining) * 2)
            self.score_board.setStyleSheet('background-color: green')
        else:
            self.score -= 10
            self.score_board.setStyleSheet('background-color: red')
        self.load_next_screen()

    def false_clicked(self):
        """
        Define what happens if the button "FALSE" was clicked
        """
        if self.correct_url:
            self.score -= 10
            self.score_board.setStyleSheet('background-color: red')
        else:
            self.score += (round(self.time_remaining) * 2)
            self.score_board.setStyleSheet('background-color: green')
        self.load_next_screen()

    def next_random_question(self):
        """
        Randomly decide whether the next question should be a valid url or a phishy url
        """
        self.setWindowTitle(f'Score: {self.score}')
        if random.randint(0, 1) > 0.5:
            self.set_new_question_correct()
        else:
            self.set_new_question_phyishy()
        self.question_start_time = time.time()

    def set_new_question_correct(self):
        self.correct_url = True
        q = random.choice(list(self.question_set))
        qim = ImageQt.ImageQt(q.logo_file)
        pix = QPixmap.fromImage(qim).scaledToHeight(128)
        self.widget_image.setPixmap(pix)
        self.widget_url.setText(q.random_correct_url)
        self.widget_image.repaint()
        self.widget_url.repaint()

    def set_new_question_phyishy(self):
        self.correct_url = False
        q = random.choice(list(self.question_set))
        qim = ImageQt.ImageQt(q.logo_file)
        pix = QPixmap.fromImage(qim).scaledToHeight(128)
        self.widget_image.setPixmap(pix)
        self.widget_url.setText(q.random_false_url)
        self.widget_image.repaint()
        self.widget_url.repaint()
