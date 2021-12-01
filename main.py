"""
Main file that runs the game.
First, it loads a set of questions,
    afterwards it starts the game with those questions.
"""
from set_of_questions import question_set
from app import App
import sys
from PyQt5.QtWidgets import QApplication


app = QApplication(sys.argv)
ex = App(question_set)
sys.exit(app.exec_())
