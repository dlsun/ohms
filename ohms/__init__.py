"""
OHMS: Online Homework Management System
"""

from flask import Flask, request, render_template, make_response
import json
from utils import NewEncoder
from datetime import datetime

from objects import session, Question, User
from queries import get_user, get_homework, get_question, \
    get_question_response, get_last_question_response, \
    get_peer_review_questions, get_peer_tasks_for_student, \
    get_grading_task, get_grades_for_student, add_grade, get_grade
import options
from auth import validate_user, validate_admin

# Configuration based on deploy target
if options.target == "local":
    app = Flask(__name__, static_url_path="/static", static_folder="../static")
else:
    app = Flask(__name__)
    app.debug = (options.target != "prod")

    @app.errorhandler(Exception)
    def handle_exceptions(error):
        return make_response(error.message, 403)


@app.route("/")
def index():
    user = validate_user()
    hws = get_homework()
    
    # to-do list for peer reviews
    from collections import defaultdict
    to_do = defaultdict(int)
    peer_review_questions = get_peer_review_questions()
    for prq in peer_review_questions:
        prq.set_metadata()
        response = get_last_question_response(prq.question_id, user.stuid)
        # if deadline has passed...
        if prq.homework.due_date < datetime.now():
            # compute updated score for student
            tasks = get_peer_tasks_for_student(prq.question_id, user.stuid)
            scores = [t.score for t in tasks if t.score is not None]
            new_score = sorted(scores)[len(scores) // 2] if scores else None
            if response.score != new_score:
                response.score = new_score
                response.comments = "Click <a href='rate?id=%d' target='_blank'>here</a> to view comments." % prq.question_id
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
    user = validate_user()
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
    user = validate_user()
    question_id = request.args.get("id")
    tasks = get_peer_tasks_for_student(question_id, user.stuid)
    tasks = [t for t in tasks if t.score is not None]
    return render_template("rate.html",
                           grading_tasks=tasks,
                           options=options)

@app.route("/rate_submit", methods=['POST'])
def rate_submit():
    user = validate_user()
    task = get_grading_task(request.form.get('task_id'))
    task.rating = int(request.form.get('rating'))
    session.commit()
    return ""


@app.route("/load", methods=['GET'])
def load():
    user = validate_user()
    q_id = request.args.get("q_id")
    question = get_question(q_id)
    return json.dumps(question.load_response(user.stuid), cls=NewEncoder)


@app.route("/submit", methods=['POST'])
def submit():
    user = validate_user()
    q_id = request.args.get("q_id")
    question = get_question(q_id)
    responses = request.form.getlist('responses')
    return json.dumps(question.submit_response(user.stuid, responses),
                      cls=NewEncoder)


@app.route("/grades")
def grades():
    user = validate_user()

    # update grades
    homeworks = get_homework()
    for hw in homeworks:
        if hw.due_date > datetime.now():
            continue
        score, points = 0, 0
        complete = True
        for q in hw.questions:
            points += q.points
            response = get_last_question_response(q.id, user.stuid)
            if response:
                try:
                    score += response.score
                except:
                    complete = False
                    break # skip hws with scoreless responses
        if complete:
            grade = get_grade(user.stuid, hw.name)
            if not grade:
                add_grade(user.stuid, hw.name, hw.due_date, score, points)
            else:
                grade.time = hw.due_date
                grade.score = score
                grade.points = points
                session.commit()
    
    # fetch grades from gradebook
    return render_template("grades.html", grades=get_grades_for_student(user.stuid), 
                           options=options, user=user)


# ADMIN FUNCTIONS
@app.route("/admin")
def admin():
    user = validate_admin()

    return render_template("admin/index.html", options=options)

@app.route("/update_question", methods=['POST'])
def update_question():
    user = validate_admin()
    
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
    user = validate_admin()

    response_id = request.form["response_id"]
    response = get_question_response(response_id)
    score = request.form["score"]
    response.score = float(score) if score else None
    response.comments = request.form["comments"]
    session.commit()
    return ""
    
@app.route("/view_responses")
def view_responses():
    user = validate_admin()

    q_id = request.args.get('q')
    users = session.query(User).all()
    responses = []
    for u in users:
        response = get_last_question_response(q_id, u.stuid)
        if response:
            responses.append(response)
    return render_template("admin/view_responses.html", responses=responses, options=options, user=user)

@app.route("/change_user", methods=['POST'])
def change_user():
    user = validate_admin()
    student = request.form['user']

    try:
        session.query(User).get(student)
    except:
        raise Exception("No user exists with the given ID.")

    session.query(User).filter_by(stuid=user.stuid).update({
        "proxy": student
    })
    session.commit()

    return "Successfully changed user to %s" % user.proxy

@app.route("/add_homework", methods=['POST'])
def add_homework():
    user = validate_admin()

    name = request.form['name']
    start_date = datetime.strptime(request.form['start_date'],
                                   "%m/%d/%Y %H:%M:%S")
    due_date = datetime.strptime(request.form['due_date'],
                                 "%m/%d/%Y %H:%M:%S")

    from objects import Homework
    homework = Homework(name=name,
                        start_date=start_date,
                        due_date=due_date)
    session.add(homework)
    session.commit()

    return "%s added successfully!" % name

@app.route("/add_question", methods=['POST'])
def add_question():
    user = validate_admin()

    print request.form['hw_id']

    import elementtree.ElementTree as ET
    xml = request.form['xml']
    node = ET.fromstring(xml)

    # remove any ID tags
    for e in node.iter():
        if "id" in e.attrib: e.attrib.pop("id")

    question = Question.from_xml(node)
    question.homework = get_homework(request.form['hw_id'])

    session.commit()

    return "Question added successfully!"

