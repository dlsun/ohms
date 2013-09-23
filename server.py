"""
OHMS: Online Homework Management System
"""

from flask import Flask, request, render_template
from sqlalchemy.orm.query import Query
import json
from datetime import datetime

from base import session
from objects import Homework, Question, Item, QuestionResponse, ItemResponse
from objects import GradingTask, QuestionGrade, GradingPermission
from queries import get_responses
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
        elif isinstance(obj, QuestionGrade):
            d = {}
            for column in obj.__table__.columns:
                d[column.name] = getattr(obj, column.name)
            d['item_responses'] = [
                {"response": obj.score},
                {"response": obj.comments}
                ]
            return d
        return json.JSONEncoder.default(self, obj)


@app.route("/")
def index():
    hws = session.query(Homework).all()
    return render_template("index.html", homeworks=hws)


@app.route("/hw", methods=['GET'])
def hw():
    hw_id = request.args.get("id")
    homework = session.query(Homework).filter_by(id=hw_id).one()
    return render_template("hw.html", homework=homework)


@app.route("/grade", methods=['GET'])
def grade():
    hw_id = request.args.get("id")
    permissions = session.query(GradingPermission).\
        filter_by(sunet=sunet).join(Question).\
        filter(Question.hw_id == hw_id).all()
    questions = []
    for permission in permissions:
        question = permission.question
        if permission.permissions:
            tasks = session.query(GradingTask).\
                filter_by(grader=sunet).join(QuestionResponse).\
                filter(QuestionResponse.question_id == 
                          question.id).all()
        else:
            tasks = None
        questions.append({
                "question": question, 
                "permission": permission.permissions,
                "tasks": tasks})
    return render_template("grade.html", questions=questions)


@app.route("/load", methods=['GET'])
def load():
    q_id = request.args.get("q_id")
    responses = get_responses(q_id, sunet)
    if responses:
        return json.dumps({"last_submission": responses[0]}, cls=NewEncoder)
    else:
        return json.dumps({})


@app.route("/submit", methods=['POST'])
def submit():
    q_id = request.args.get("q_id")
    responses = request.form.getlist('responses')

    if q_id.startswith("g"):

        question_grade = QuestionGrade(
            grading_task_id=q_id[1:],
            time=datetime.now(),
            score=float(responses[0]),
            comments=responses[1]
            )
        session.add(question_grade)
        session.commit()

        return json.dumps({})

    question = session.query(Question).filter_by(id=q_id).one()

    past_responses = get_responses(q_id, sunet)
    items = session.query(Item).filter_by(question_id=q_id).all()

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
