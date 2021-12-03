"""
Main file that runs the game.
First, it loads a set of questions,
    afterwards it starts the game with those questions.
"""
from PyQt5.QtWidgets import QApplication
from set_of_questions import question_set
from app import App
import signal
import sys
import logging
logging.basicConfig(encoding='utf-8', level=logging.DEBUG)


app = QApplication(sys.argv)
signal.signal(signal.SIGINT, signal.SIG_DFL)
ex = App(question_set)
sys.exit(app.exec_())
