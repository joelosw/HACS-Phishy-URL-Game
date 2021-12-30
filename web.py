from flask import *
from set_of_questions import question_set
import random

app = Flask(__name__,static_url_path='/static')

#Default route for serving index template
@app.route('/',methods=['GET'])
def main():
    return render_template("index.html")

#Route for front end to query new question from Joel's question class
@app.route('/question',methods=["GET"])
def fetch_question():
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