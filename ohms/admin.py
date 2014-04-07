"""
OHMS: Online Homework Management System
"""

import os
from flask import Flask, request, render_template, make_response
import json
from utils import NewEncoder
from datetime import datetime
import random

from base import session
from objects import User, Homework, Question, QuestionResponse, GradingTask, LongAnswerItem
from queries import get_user
from send_email import send_all
import options
from auth import auth_stuid, auth_student_name

import smtplib

if options.target == "local":
    app = Flask(__name__, static_url_path="/static", static_folder="../static")
    stuid = "test"
    user = User(stuid=stuid,
                name="Test User",
                type="admin")
else:
    app = Flask(__name__)
    app.debug = (options.target != "prod")

    @app.errorhandler(Exception)
    def handle_exceptions(error):
        return make_response(error.message, 403)

    stuid = auth_stuid()
    if not stuid:
        raise Exception("You are no longer logged in. Please refresh the page.")
    try:
        user = get_user(stuid)
    except:
        user = User(stuid=stuid,
                    name=auth_student_name(),
                    type="student")
        session.add(user)
        session.commit()

@app.route("/")
def index():
    return render_template("admin/index.html", options=options, user=user)


@app.route("/reminder_email/<int:hw_id>", methods=['POST'])
def reminder_email(hw_id):

    homework = session.query(Homework).get(hw_id)

    # get users who haven't completed peer grading
    users = set()
    for question in homework.questions:
        tasks = session.query(GradingTask).join(QuestionResponse).\
                filter(QuestionResponse.question_id == question.id).all()
        for task in tasks:
            grades = session.query(QuestionGrade).filter_by(grading_task_id=task.id).all()
            if not grades:
                users.add(task.grader)

    # send e-mails
    users = [session.query(User).get(u) for u in users]
    message = '''Dear %s,\n\n''' + request.form['message'].replace("%", "%%") + '''

Best,
Stats 60 Staff
'''
    send_all(users, request.form['subject'], message)
    
    admins = session.query(User).filter_by(type="admin").all()
    send_all(admins, "%s Peer Assessment Reminder Sent" % homework.name,
"""Hey %s (and other staff),

A reminder e-mail was just sent to the following users to remind them to complete their 
peer assessments.\n\n""" + "\n".join(u.stuid for u in users) + """

Sincerely,
OHMS

P.S. This is an automatically generated message ;-)""")

    return "Sent reminder to %d recipients. You should have received an e-mail." % len(users)
    
@app.errorhandler(Exception)
def handle_exceptions(error):
    return make_response(error.message, 403)

# For local development--this does not run in prod or test
if __name__ == "__main__":
    app.run(debug=True)
