"""
OHMS: Online Homework Management System
"""

import os
from flask import Flask, request, render_template, make_response
import json
from utils import NewEncoder
from datetime import datetime, timedelta

from base import session
from objects import User, Homework, Question, QuestionResponse, GradingPermission
from queries import get_user
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
    raise Exception("You are not authorized to view thie page.")

treatments = {
    0: [1,1,1,0,0,1,1,0,0],
    1: [1,0,0,1,1,0,0,1,1],
    2: [1,1,1,0,0,0,0,1,1],
    3: [1,0,0,1,1,1,1,0,0]
    }


@app.route("/")
def index():
    return render_template("admin/index.html", options=options, user=user)


@app.route("/assign_tasks/<int:hw_id>", methods=['POST'])
def assign_tasks(hw_id):
    return "Not yet implemented."


@app.route("/tabulate_grades/<int:hw_id>", methods=['POST'])
def tabulate_grades(hw_id):
    return "Not yet implemented."


@app.route("/reminder_email/<int:hw_id>", methods=['POST'])
def reminder_email(hw_id):

    smtpObj = smtplib.SMTP('localhost')
    sender = 'stats60-aut1314-staff@lists.stanford.edu'
    recipients = []

    homework = session.query(Homework).get(hw_id)

    for question in homework.questions:
        entries = session.query(GradingPermission).filter_by(question_id=question.id).filter_by(permissions=0).all()
        for entry in entries:
            name = session.query(User).get(entry.sunet).name
            email = "%s@stanford.edu" % entry.sunet
            if email not in recipients:
                message = r'''From: Stats 60 Staff <stats60-aut1314-staff@lists.stanford.edu>
To: %s <%s>
Subject: %s Peer Grading Incomplete

Dear %s,

You are receiving this e-mail because you were assigned to peer grading 
for %s and have not yet completed it. This is a reminder that 
peer grading is due Tuesday at 5 P.M. Since peer grading counts the same 
amount as the homework toward your course grade, please ensure that you 
finish the peer grading before this deadline.

Best,
Stats 60 Staff
''' % (name, email, homework.name, name, homework.name)
                smtpObj.sendmail(sender, [email], message)                
                recipients.append(email)

    return "Successfully sent email to:<br/>" + "<br/>".join(recipients)


@app.route("/view_responses/<int:q_id>", methods=['POST'])
def view_responses(q_id):

    user_responses = session.query(QuestionResponse, User).filter(QuestionResponse.sunet == User.sunet).\
        filter(QuestionResponse.question_id == q_id).all()

    #homework = session.query(Homework).filter_by(name="Homework %d" % hw).one()
    #questions = homework.questions

    #question = questions[q-1]
    #groups = []
    #for i in range(4):
    #    if treatments[i][hw-1]==0:
    #        groups.append(i)
    #
    #responses = session.query(QuestionResponse).\
    #    filter_by(question_id=question.id).join(User).\
    #    filter((User.group == groups[0]) | (User.group == groups[1])).all()

    #responses = session.query(QuestionResponse).filter_by(question_id=question.id).all()

    return render_template("admin/view_responses.html", user_responses=user_responses, options=options, user=user)

    
@app.route("/update_response/<int:response_id>", methods=['POST'])
def update_response(response_id):
    from objects import QuestionResponse
    response = session.query(QuestionResponse).get(response_id)
    response.sample = 1
    response.score = int(request.form['score'])
    response.comments = request.form['comments']
    session.commit()
    return 'Successfully updated response %d' % response.id


@app.errorhandler(Exception)
def handle_exceptions(error):
    return make_response(error.message, 403)
