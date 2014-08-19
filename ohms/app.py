"""
OHMS: Online Homework Management System
"""

from flask import Flask, request, render_template, make_response
import json
from utils import NewEncoder, convert_to_last_name
from datetime import datetime
import elementtree.ElementTree as ET
from collections import defaultdict

from objects import session, Question, User
from queries import get_user, get_homework, get_question, \
    get_question_response, get_last_question_response, \
    get_peer_review_questions, get_peer_tasks_for_student, \
    get_peer_tasks_for_grader, get_self_tasks_for_student, \
    get_grading_task, add_grade, get_grade
import options
from pdt import pdt_now
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

    to_do = defaultdict(int)
    peer_review_questions = get_peer_review_questions()
    for prq in peer_review_questions:
        prq.set_metadata()
        response = get_last_question_response(prq.question_id, user.stuid)
        # if deadline has passed...
        if response and prq.homework.due_date < pdt_now():
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
                           current_time=pdt_now(),
                           to_do=to_do)


@app.route("/hw", methods=['GET'])
def hw():
    user = validate_user()
    hw_id = request.args.get("id")
    hw = get_homework(hw_id)
    if user.type != "admin" and hw.start_date and hw.start_date > pdt_now():
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


def calculate_grade(user, hw):

    # total up the points
    score, points = 0, 0
    for q in hw.questions:
        points += q.points
        if q.type == "question":
            response = get_last_question_response(q.id, user.stuid)
            if response and response.score:
                score += response.score
        elif q.type == "Peer Review":
            q.set_metadata()
            tasks = get_peer_tasks_for_grader(q.question_id, user.stuid)
            tasks.extend(get_self_tasks_for_student(q.question_id, user.stuid))
            for task in tasks:
                if task.comments is not None:
                    score += 1. * q.points / len(tasks)

    # fill in grades
    grade = get_grade(user.stuid, hw.name)
    if not grade:
        add_grade(user.stuid, hw.name, hw.due_date, score, points)
    else:
        grade.time = hw.due_date
        grade.score = score
        grade.points = points

    return grade


@app.route("/grades")
def grades():
    user = validate_user()

    homeworks = [hw for hw in get_homework() if hw.due_date <= pdt_now()]
    grades = []

    for hw in homeworks:
        grades.append(calculate_grade(user, hw))
    session.commit()
    
    # fetch grades from gradebook
    return render_template("grades.html", grades=grades, 
                           options=options, user=user)

# ADMIN FUNCTIONS
@app.route("/admin")
def admin():
    admin = validate_admin()

    homeworks = [hw for hw in get_homework() if hw.due_date <= pdt_now()]
    students = session.query(User).filter_by(type="student").all()
    students.sort(key=lambda user: convert_to_last_name(user.name))

    gradebook = []
    for student in students:
        grades = []
        for hw in homeworks:
            grades.append(calculate_grade(student, hw))
        gradebook.append((student, grades))
    session.commit()

    assignments = [g.assignment for g in gradebook[0][1]] if gradebook else []

    guests = session.query(User).filter_by(type="guest").all()
    admins = session.query(User).filter_by(type="admin").all()

    return render_template("admin/index.html", students=students, guests=guests, admins=admins,  
                           assignments=assignments, gradebook=gradebook, options=options)

@app.route("/change_user_type", methods=['POST'])
def change_user_type():
    admin = validate_admin()

    stuid = request.form['user']
    user_type = request.form['type']

    session.query(User).filter_by(stuid=stuid).update({
        "type": user_type
    })
    session.commit()

    return "Successfully changed user %s to %s." % (stuid, user_type)

@app.route("/update_question", methods=['POST'])
def update_question():
    admin = validate_admin()
    
    q_id = request.form['q_id']
    xml_new = request.form['xml']
    try:
        node = ET.fromstring(xml_new)
    except Exception as e:
        raise Exception(str(e))
    node.attrib['id'] = q_id
    question = Question.from_xml(node)
    return json.dumps({
        "xml": question.xml,
        "html": question.to_html(),
    })
        
@app.route("/update_response", methods=['POST'])
def update_response():
    admin = validate_admin()

    response_id = request.form["response_id"]
    response = get_question_response(response_id)
    score = request.form["score"]
    response.score = float(score) if score else None
    response.comments = request.form["comments"]
    session.commit()
    return ""
    
@app.route("/view_responses")
def view_responses():
    admin = validate_admin()

    q_id = request.args.get('q')
    users = session.query(User).all()
    responses = []
    for u in users:
        response = get_last_question_response(q_id, u.stuid)
        if response:
            responses.append(response)
    return render_template("admin/view_responses.html", responses=responses, options=options)

@app.route("/change_user", methods=['POST'])
def change_user():
    admin = validate_admin()
    student = request.form['user']

    try:
        session.query(User).get(student)
    except:
        raise Exception("No user exists with the given ID.")

    session.query(User).filter_by(stuid=admin.stuid).update({
        "proxy": student
    })
    session.commit()

    return "Successfully changed user to %s" % admin.proxy

@app.route("/add_homework", methods=['POST'])
def add_homework():
    admin = validate_admin()

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
    admin = validate_admin()

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

