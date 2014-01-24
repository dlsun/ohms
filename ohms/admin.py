"""
OHMS: Online Homework Management System
"""

import os
from flask import Flask, request, render_template, make_response
import json
from utils import NewEncoder
from datetime import datetime, timedelta

from base import session
from objects import User, Homework, Question, QuestionResponse, QuestionGrade, GradingTask, LongAnswerItem
from queries import get_user, get_question_responses, get_question_grades, get_grading_tasks_for_response
from assign_grading_tasks import make_grading_assignments
from send_email import send_all
import options

import smtplib


# Configuration based on deploy target
app = Flask(__name__)
app.debug = (options.target != "prod")
sunet = os.environ.get("WEBAUTH_USER")
if not sunet:
    raise Exception("You are no longer logged in. Please refresh the page.")
try:
    user = get_user(sunet)
    assert(user.type == "admin")
except:
    raise Exception("You are not authorized to view this page.")


@app.route("/")
def index():
    return render_template("admin/index.html", options=options, user=user)


@app.route("/assign_tasks/<int:hw_id>", methods=['POST'])
def assign_tasks(hw_id):

    homework = session.query(Homework).get(hw_id)

    groups = [int(i) for i in request.form.getlist("group")]
    users = session.query(User).filter(User.group.in_(groups)).all()

    due_date = datetime.strptime(request.form["due_date"],
                                 "%m/%d/%Y %H:%M:%S")

    for q in homework.questions:

        # only if this is a peer graded question
        if isinstance(q.items[0], LongAnswerItem):

            # get the responses from the relevant users
            responses = []
            for user in users:
                submits = get_question_responses(q.id, user.sunet)
                if submits: responses.append(submits[-1])

            # assign grading tasks to those users
            make_grading_assignments(q.id, [user.sunet for users in users], due_date)

            # update the comments to include a link to peer comments
            for r in responses:
                r.comments = "Click <a href='rate?id=%d' target='_blank'>here</a> to view comments from your peers." % r.id

            session.commit()

            # Send email notifications
            send_all(users, "Peer Grading for %s is Ready" % homework.name,
r"""Dear %s,

You've been assigned to peer grade this week. Peer grading is due at {due_date}. 

You will be able to view peer comments on your answers as they come in, but 
your score will not be available until {due_date}. Don't forget to 
rate the peer comments!

Best,
STATS 60 Staff""".format(due_date=request.form["due_date"]))

            admins = session.query(User).filter_by(type="admin").all()
            send_all(admins, "Peer Grading for %s is Ready" % homework.name,
r"""Hey %s (and other staff),

Just letting you know that peer grading was released this week, due at {due_date}.

Sincerely,

OHMS

P.S. This is an automatically generated message ;-)
""". format(due_date=request.form["due_date"]))

    return r'''Successfully assigned %d students. You should have received an 
e-mail as confirmation.''' % len(responses)


@app.route("/reminder_email/<int:hw_id>", methods=['POST'])
def reminder_email(hw_id):

    homework = session.query(Homework).get(hw_id)
    users = []

    for question in homework.questions:
        tasks = session.query(GradingTask).join(QuestionResponse).\
                filter(QuestionResponse.question_id == question.id).all()
        for task in tasks:
            grades = session.query(QuestionGrade).filter_by(grading_task_id=task.id).all()
            if not grades and (task.grader not in recipients):
                users.append(session.query(User).get(task.grader))

        message = '''Dear %s,\n\n''' + request.form['message'] + '''\n
Best,
Stats 60 Staff
'''
        send_all(users, request.form['subject'], message)

        admins = session.query(User).filter_by(type="admin").all()
        send_all(admins, "Peer Grading Reminder Sent" % homework.name,
"""Hey %s (and other staff),

A reminder e-mail was just sent to the following users to remind them to complete their 
peer grading.\n\n""" + "\n".join(u.sunet for u in users) + """

Sincerely,
OHMS

P.S. This is an automatically generated message ;-)""")

    return "Sent reminder to %d recipients. You should have received an e-mail." % len(users)


@app.route("/view_responses", methods=['POST', 'GET'])
def view_responses():

    q_id = request.args.get('q')
    groups = request.form.getlist('group')

    users = session.query(User).filter(User.group.in_(groups)).all()

    import random
    random.seed(q_id)
    random.shuffle(users)

    user_responses = []
    for u in users:
        responses = session.query(QuestionResponse).\
                   filter_by(sunet = u.sunet).\
                   filter_by(question_id = q_id).\
                   all()
        if responses:
            user_responses.append( (u, responses[-1]) )
        
    return render_template("admin/view_responses.html", user_responses=user_responses, options=options, user=user, groups=groups)

    
@app.route("/update_response/<int:response_id>", methods=['POST'])
def update_response(response_id):
    from objects import QuestionResponse
    response = session.query(QuestionResponse).get(response_id)
    score = request.form['score']
    response.score = int(score) if score else None
    response.comments = request.form['comments']
    session.commit()
    return r'''
Successfully updated response %d! 
<script type="text/javascript">window.close();</script>
''' % response.id


@app.route("/rate", methods=['GET'])
def view_peer_comments():

    out = {}
    question_response_id = request.args.get("id")

    grading_tasks = get_grading_tasks_for_response(question_response_id)
    question_grades = []
    
    for task in grading_tasks:
        submissions = get_question_grades(task.id)
        if submissions:
            question_grades.append(submissions[-1])

    return render_template("admin/view_comments.html",
                           question_grades=question_grades,
                           options=options)


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


@app.errorhandler(Exception)
def handle_exceptions(error):
    return make_response(error.message, 403)
