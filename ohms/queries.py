"""
queries.py

Some useful sql queries.
"""

from datetime import datetime
from collections import defaultdict

from base import session
from objects import QuestionResponse, GradingTask, User
from objects import Homework, Question, PeerReview


def get_homework(hw_id=None):
    if hw_id is None:
        return session.query(Homework).order_by(Homework.due_date).all()
    else:
        return session.query(Homework).get(hw_id)

def get_question(question_id):
    return session.query(Question).get(question_id)

def get_peer_review_questions():
    return session.query(PeerReview).all()


def get_question_response(question_response_id):
    return session.query(QuestionResponse).get(question_response_id)

def get_question_responses(question_id, sunet):
    return session.query(QuestionResponse).\
        filter_by(sunet=sunet).\
        filter_by(question_id=question_id).\
        order_by(QuestionResponse.time).all()

def get_last_question_response(question_id, sunet):
    qrs = session.query(QuestionResponse).\
        filter_by(sunet=sunet).\
        filter_by(question_id=question_id).\
        order_by(QuestionResponse.time).all()
    return qrs[-1] if qrs else None

def grading_permissions_query(question_id, sunet):
    return session.query(GradingTask.permission).\
        filter_by(sunet=sunet).\
        filter_by(question_id=question_id)

def get_grading_permissions(question_id, sunet):
    return grading_permissions_query(question_id, sunet).all()

def set_grading_permissions(question_id, sunet, permissions):
    grading_permissions_query(question_id, sunet).update({"permissions": permissions})
    session.commit()

def get_grading_task(grading_task_id):
    return session.query(GradingTask).get(grading_task_id)

def get_grading_tasks_for_grader(question_id, sunet):
    return session.query(GradingTask).\
        filter_by(grader=sunet).join(QuestionResponse).\
        filter(QuestionResponse.question_id == question_id).\
        order_by(GradingTask.id).all()

def get_grading_tasks_for_student(question_id, sunet):
    return session.query(GradingTask).\
        filter_by(student=sunet).join(QuestionResponse).\
        filter(QuestionResponse.question_id == question_id).\
        order_by(GradingTask.id).all()

def get_sample_responses(question_id):
    return session.query(QuestionResponse).filter_by(sample=1).\
        filter_by(question_id=question_id).\
        order_by(QuestionResponse.id).all()

def get_user(sunet):
    return session.query(User).filter_by(sunet=sunet).one()



