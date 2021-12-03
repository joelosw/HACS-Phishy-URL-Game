import os
import sys
import time
import random
import logging
from typing import Dict, List, Optional, Tuple, Set
from question_class import Question
import numpy as np
from PIL import Image, ImageDraw, ImageQt
from PyQt5 import QtCore
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QPixmap, QFont
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import (
    QBoxLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
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
        self.width = 900
        self.height = 400
        self.current_key = ""
        self.label_qt_obj = {}
        self.result_data = {}
        self.score = 0

        self.setWindowTitle(self.title)
        self.setGeometry(self.left_padding, self.top_padding,
                         self.width, self.height)
        self.global_layout = QVBoxLayout()
        self.interaction_layout = QHBoxLayout()
        self.question_layout = QVBoxLayout()
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
        self.score_board.setSizePolicy(
            QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Expanding)
        self.score_board.setStyleSheet("")
        self.widget_url.setFont(QFont('Arial', 35))
        self.question_layout.addWidget(self.widget_image)
        self.question_layout.addWidget(self.widget_url)
        self.widget_url.setFont(QFont('Arial', 35))
        self.widget_url.setAlignment(QtCore.Qt.AlignCenter)
        self.button_layout.addWidget(self.button_true, 5)
        self.button_layout.addWidget(self.button_false, 1)

        self.time_bar = QProgressBar(self)
        self.time_bar.setMaximum(1000)
        self.time_bar.setValue(1000)
        self.time_bar.setStyleSheet("QProgressBar::chunk "
                                    "{"
                                    "background-color: green;"
                                    "}")
        self.time_bar.setTextVisible(True)
        self.time_bar.setAlignment(QtCore.Qt.AlignCenter)

        self.timer.timeout.connect(self.set_time_bar_status)
        self.timer.start(50)

        self.window = QWidget()  # Main Widget
        # self.window.setFixedSize(self.width, self.height)
        self.interaction_layout.addLayout(self.question_layout)
        self.interaction_layout.addWidget(self.score_board)
        self.global_layout.addLayout(self.interaction_layout)
        self.global_layout.addLayout(self.button_layout)
        self.global_layout.addWidget(self.time_bar)
        self.window.setLayout(self.global_layout)
        self.setCentralWidget(self.window)
        self.show()
        self.load_next_screen()

    def set_score_style(self, color: str):
        self.score_board.setStyleSheet(
            'border: 2px solid black; background-color: {}'.format(color))

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
            self.score += (round(self.time_remaining) * 1)
            self.set_score_style("green")
        else:
            self.score -= 10
            self.set_score_style("red")

        self.load_next_screen()

    def false_clicked(self):
        """
        Define what happens if the button "FALSE" was clicked
        """
        if self.correct_url:
            self.score -= 10
            self.set_score_style("red")
        else:
            self.score += (round(self.time_remaining) * 1)
            self.set_score_style("green")
        self.load_next_screen()

    def next_random_question(self):
        """
        Randomly decide whether the next question should be a valid url or a phishy url
        """
        self.setWindowTitle(f'Score: {self.score}')
        if random.randint(0, 1) > 0.5:
            self.set_new_question_correct()
            logging.info('Loading Correct Question')
        else:
            self.set_new_question_phyishy()
            logging.info('Loading Phishy Question')
        self.question_start_time = time.time()

    def set_url(self, url: str):
        self.widget_url.setText(url)

    def set_new_question_correct(self):
        self.correct_url = True
        q = random.choice(list(self.question_set))
        qim = ImageQt.ImageQt(q.logo_file)
        pix = QPixmap.fromImage(qim).scaledToWidth(256)
        self.widget_image.setPixmap(pix)
        self.set_url(q.random_correct_url())
        self.widget_image.repaint()
        self.widget_url.repaint()

    def set_new_question_phyishy(self):
        self.correct_url = False
        q = random.choice(list(self.question_set))
        qim = ImageQt.ImageQt(q.logo_file)
        pix = QPixmap.fromImage(qim).scaledToWidth(256)
        self.widget_image.setPixmap(pix)
        self.set_url(q.random_false_url())
        self.widget_image.repaint()
        self.widget_url.repaint()
