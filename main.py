"""
Main file that runs the game.
First, it loads a set of questions,
    afterwards it starts the game with those questions.
"""
import sys, signal
from app import App
from set_of_questions import question_set
from PyQt5.QtWidgets import QApplication


app = QApplication(sys.argv)
signal.signal(signal.SIGINT, signal.SIG_DFL)
ex = App(question_set)
sys.exit(app.exec_())
