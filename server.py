"""
OHMS: Online Homework Management System
"""

from flask import Flask, request, render_template
from sqlalchemy.orm.query import Query
import json
from datetime import datetime

from base import session
from objects import Homework, Question, Item, QuestionResponse, ItemResponse
app = Flask(__name__, static_url_path="")

sunet = "dlsun"


# special JSON encoder to handle dates and Response objects
class NewEncoder(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj, datetime):
            return datetime.strftime(obj, "%m/%d/%Y %H:%M:%S")
        elif isinstance(obj, QuestionResponse):
            d = {}
            for column in obj.__table__.columns:
                d[column.name] = getattr(obj, column.name)
            d['item_responses'] = obj.item_responses
            return d
        elif isinstance(obj, ItemResponse):
            d = {}
            for column in obj.__table__.columns:
                d[column.name] = getattr(obj, column.name)
            return d
        return json.JSONEncoder.default(self, obj)


@app.route("/")
def index():
    hws = session.query(Homework).all()
    return render_template("index.html", homeworks=hws)


@app.route("/view", methods=['GET'])
def view():
    hw_id = request.args.get("id")
    questions = session.query(Question).filter_by(hw_id=hw_id).all()
    return render_template("view.html", questions=questions)


def get_responses(q_id):
    responses = session.query(QuestionResponse).\
        filter_by(sunet=sunet).\
        filter_by(question_id=q_id).\
        order_by(QuestionResponse.time.desc()).all()
    return responses


@app.route("/load", methods=['GET'])
def load():
    q_id = request.args.get("q_id")
    responses = get_responses(q_id)
    if responses:
        return json.dumps({"last_submission": responses[0]}, cls=NewEncoder)
    else:
        return json.dumps({})


@app.route("/submit", methods=['POST'])
def submit():
    q_id = request.args.get("q_id")
    question = session.query(Question).filter_by(id=q_id).one()

    past_responses = get_responses(q_id)
    items = session.query(Item).filter_by(question_id=q_id).all()
    responses = request.form.getlist('responses')

    score, comments = question.check(responses)

    question_response = QuestionResponse(
        sunet=sunet,
        question_id=q_id,
        time=datetime.now(),
        score=score,
        comments=comments
    )

    for item, response in zip(items, responses):
        ir = ItemResponse(item_id=item.id, response=response)
        question_response.item_responses.append(ir)

    # add response to the database
    session.add(question_response)
    session.commit()
    # add response to what to return to the user
    return json.dumps({"last_submission": question_response}, cls=NewEncoder)


if __name__ == "__main__":
    app.run(debug=True)
