"""
OHMS: Online Homework Management System
"""

import os
from flask import Flask, request, render_template, make_response
import json
from utils import NewEncoder
from datetime import datetime, timedelta

from base import session
from objects import Question, QuestionResponse, User
from queries import get_user, get_homework, get_question, \
    get_question_response, get_last_question_response, \
    get_peer_review_questions, \
    get_peer_tasks_for_student, get_grading_task
import options
from collections import defaultdict

# Configuration based on deploy target
if options.target == "local":
    app = Flask(__name__, static_url_path="/static", static_folder="../static")
    sunet = "jsmith"
    os.environ["WEBAUTH_USER"] = sunet
    user = User(sunet=sunet, name="John Smith", type="admin")

else:
    app = Flask(__name__)
    app.debug = (options.target != "prod")

    sunet = os.environ.get("WEBAUTH_USER")
    if not sunet:
        raise Exception("You are no longer logged in. Please refresh the page.")
    try:
        user = get_user(sunet)
    except:
        user = User(sunet=sunet,
                    name=os.environ.get("WEBAUTH_LDAP_DISPLAYNAME"),
                    type="student")
        session.add(user)
        session.commit()

    @app.errorhandler(Exception)
    def handle_exceptions(error):
        return make_response(error.message, 403)

# allow admins to view other users' account
if user.type == "admin" and user.proxy:
    print user.proxy
    sunet = user.proxy
    user = get_user(sunet)

@app.route("/")
def index():
    hws = get_homework()
    
    # to-do list for peer reviews
    to_do = defaultdict(int)
    peer_review_questions = get_peer_review_questions()
    for prq in peer_review_questions:
        prq.set_metadata()
        response = get_last_question_response(prq.question_id, sunet)
        # if deadline has passed...
        if prq.homework.due_date < datetime.now():
            # compute updated score for student
            tasks = get_peer_tasks_for_student(prq.question_id, sunet)
            scores = [t.score for t in tasks if t.score is not None]
            new_score = sorted(scores)[len(scores) // 2] if scores else None
            if response.score != new_score:
                response.score = new_score
                response.comments = "Click <a href='rate?id=%d'>here</a> to view comments" % prq.question_id
                session.commit()
            # check that student has rated all the peer reviews
            for task in tasks:
                if task.score is not None and task.rating is None:
                    to_do[response.question.homework] += 1

    return render_template("index.html", homeworks=hws,
                           user=user,
                           options=options,
                           current_time=datetime.now(),
                           to_do=to_do)


@app.route("/hw", methods=['GET'])
def hw():
    hw_id = request.args.get("id")
    hw = get_homework(hw_id)
    if user.type != "admin" and hw.start_date and hw.start_date > datetime.now():
        raise Exception("This homework has not yet been released.")
    else:
        return render_template("hw.html",
                               homework=hw,
                               user=user,
                               options=options)


@app.route("/rate", methods=['GET'])
def rate():
    question_id = request.args.get("id")
    tasks = get_peer_tasks_for_student(question_id, sunet)
    tasks = [t for t in tasks if t.score is not None]
    return render_template("rate.html",
                           grading_tasks=tasks,
                           options=options)

@app.route("/rate_submit", methods=['POST'])
def rate_submit():
    task = get_grading_task(request.form.get('task_id'))
    task.rating = int(request.form.get('rating'))
    session.commit()
    return ""


@app.route("/load", methods=['GET'])
def load():
    q_id = request.args.get("q_id")
    question = get_question(q_id)
    return json.dumps(question.load_response(sunet), cls=NewEncoder)


@app.route("/submit", methods=['POST'])
def submit():
    q_id = request.args.get("q_id")
    question = get_question(q_id)
    responses = request.form.getlist('responses')
    return json.dumps(question.submit_response(sunet, responses),
                      cls=NewEncoder)


if user.type == "admin":

    @app.route("/update_question", methods=['POST'])
    def update_question():
        q_id = request.form['q_id']
        xml_new = request.form['xml']
        import elementtree.ElementTree as ET
        question = Question.from_xml(ET.fromstring(xml_new))
        return json.dumps({
            "xml": question.xml,
            "html": question.to_html(),
        })
        
    @app.route("/update_response", methods=['POST'])
    def update_response():
        response_id = request.form["response_id"]
        response = get_question_response(response_id)
        score = request.form["score"]
        response.score = float(score) if score else None
        response.comments = request.form["comments"]
        session.commit()
        return ""

    @app.route("/view_responses")
    def view_responses():
        q_id = request.args.get('q')
        users = session.query(User).all()
        responses = []
        for u in users:
            response = get_last_question_response(q_id, u.sunet)
            if response:
                responses.append((u, response))
        return render_template("admin/view_responses.html", user_responses=responses, options=options, user=user)

    @app.route("/change_user/<string:student>")
    def change_user(student):
        session.query(User).filter_by(sunet=sunet).update({
            "proxy": student
            })

# For local development--this does not run in prod or test
if __name__ == "__main__":
    app.run(debug=True)
