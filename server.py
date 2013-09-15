"""
OHMS: Online Homework Management System
"""

from flask import Flask, request, render_template
from sqlalchemy.orm.query import Query
import json
from datetime import datetime

from base import session
from objects import Question, Item, Response
app = Flask(__name__, static_url_path="")

sunet = "dlsun"


# special JSON encoder to handle dates and Response objects
class NewEncoder(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj, datetime):
            return str(obj)
        elif isinstance(obj, Response):
            d = {}
            for column in obj.__table__.columns:
                d[column.name] = getattr(obj, column.name)
            return d
        return json.JSONEncoder.default(self, obj)


@app.route("/")
def hello():
    return "Hello World!"


@app.route("/view", methods=['GET'])
def view():
    hw_id = request.args.get("id")
    questions = session.query(Question).filter_by(hw_id=hw_id).all()
    return render_template("view.html", questions=questions)


def get_responses(q_id):
    responses = session.query(Response).\
        filter_by(sunet=sunet).\
        join(Item).join(Question).\
        filter(Question.id == q_id).\
        order_by(Response.time.desc()).all()
    return responses


@app.route("/load", methods=['GET'])
def load():
    q_id = request.args.get("q_id")
    n_items = session.query(Item).join(Question).\
        filter(Question.id == q_id).count()
    responses = get_responses(q_id)
    if responses:
        return json.dumps({
                "last_submission": responses[:n_items],
                }, cls=NewEncoder)
    else:
        return json.dumps({"last_submission": []})


@app.route("/submit", methods=['POST'])
def submit():
    q_id = request.args.get("q_id")
    responses = get_responses(q_id)
    items = session.query(Item).filter_by(question_id=q_id).all()
    new_responses = [Response(
            sunet=sunet,
            item_id=item.id,
            time=datetime.now(),
            response=request.form.getlist('responses')[i],
            score=10
        ) for i, item in enumerate(items)]
    # add response to the database
    session.add_all(new_responses)
    session.commit()
    # add response to what to return to the user
    return json.dumps({
            "last_submission": new_responses,
            }, cls=NewEncoder)


if __name__ == "__main__":
    app.run(debug=True)
