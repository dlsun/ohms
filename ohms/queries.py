"""
queries.py

Some useful sql queries.
"""

from datetime import datetime
from collections import defaultdict

from base import session
from objects import QuestionResponse, QuestionGrade, GradingTask, GradingPermission, User
from objects import Homework, Question


def get_homework(hw_id=None):
    if hw_id is None:
        return session.query(Homework).order_by(Homework.due_date).all()
    else:
        return session.query(Homework).get(hw_id)


def get_last_homework():
    """Gets the homework that finished most recently"""
    now = datetime.now()
    homeworks = session.query(Homework).all()
    finished_hws = [hw for hw in homeworks if hw.due_date <= now]
    return max(homeworks, key=lambda hw: hw.due_date)


def get_question(question_id):
    return session.query(Question).get(question_id)


def get_question_response(question_response_id):
    return session.query(QuestionResponse).get(question_response_id)

def get_question_responses(question_id, sunet):
    return session.query(QuestionResponse).\
        filter_by(sunet=sunet).\
        filter_by(question_id=question_id).\
        order_by(QuestionResponse.time).all()
        

def get_recent_question_responses(q_id):
    """Returns each student's most recent response to a question"""
    responses = session.query(QuestionResponse).\
        filter_by(question_id=q_id).\
        join(User).\
        filter(User.type == "student").all()

    student_responses = defaultdict(list)
    for r in responses:
        student_responses[r.sunet].append(r)

    return [max(rs, key=lambda r: r.time) for rs in student_responses.values()]


def grading_permissions_query(question_id, sunet):
    return session.query(GradingPermission).\
        filter_by(sunet=sunet).\
        filter_by(question_id=question_id)

def get_grading_permissions(question_id, sunet):
    return grading_permissions_query(question_id, sunet).one()

def set_grading_permissions(question_id, sunet, permissions):
    grading_permissions_query(question_id, sunet).update({"permissions": permissions})
    session.commit()


def get_grading_task(grading_task_id):
    return session.query(GradingTask).get(grading_task_id)

def get_grading_tasks_for_grader(question_id, sunet):
    return session.query(GradingTask).\
        filter_by(grader=sunet).join(QuestionResponse).\
        filter(QuestionResponse.question_id == question_id).all()

def get_grading_tasks_for_response(question_response_id):
    return session.query(GradingTask).\
        filter_by(question_response_id=question_response_id).all()


def get_sample_responses(question_id):
    return session.query(QuestionResponse).filter_by(sample=1).\
        filter_by(question_id=question_id).\
        order_by(QuestionResponse.id).all()


def question_grade_query(grading_task_id):
    return session.query(QuestionGrade).\
        filter_by(grading_task_id=grading_task_id).\
        order_by(QuestionGrade.time)

def get_question_grade(question_grade_id):
    return session.query(QuestionGrade).get(question_grade_id)

def get_question_grades(grading_task_id, sunet):
    return question_grade_query(grading_task_id).\
        join(GradingTask).filter(GradingTask.grader == sunet).all()


def get_user(sunet):
    return session.query(User).filter_by(sunet=sunet).one()


def get_long_answer_qs(hw_id):
    """Returns questions that are composed of a single long answer"""
    questions = session.query(Question).\
        join(Homework).\
        filter_by(id=hw_id).all()

    return [q for q in questions if len(q.items) == 1 and
            q.items[0].type == "Long Answer"]


