from flask import *
from set_of_questions import question_set
import random

app = Flask(__name__,static_url_path='/static')

@app.route('/',methods=['GET'])
def main():
    return render_template("index.html")

@app.route('/answer',methods=['GET'])
def check_answer():
    answer=request.args.get("value")
    if answer == correctAnswer:
        return "1"
    else:
        return "0"

@app.route('/question',methods=["GET"])
def fetch_question():
    #I will have to integrate Joels question classes form question sets
    q = random.choice(list(question_set))
    logoPath = "static/"+q.logo_path
    if random.randint(0, 1) > 0.5:
        urlString = q.random_false_url()
        correctAnswer="0"
    else:
        urlString = q.random_correct_url()
        correctAnswer="1"
    return jsonify(
        logo=logoPath,
        url=urlString,
        answer=correctAnswer
    )

app.run()