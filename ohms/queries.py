"""
queries.py

Some useful sql queries.
"""

from base import session
from objects import QuestionResponse, QuestionGrade, GradingTask


def get_question_responses(id, sunet):
    return session.query(QuestionResponse).\
        filter_by(sunet=sunet).\
        filter_by(question_id=id).\
        order_by(QuestionResponse.time.desc()).all()


def get_question_grades(id, sunet):
    return session.query(QuestionGrade).\
        filter_by(grading_task_id=id).\
        join(GradingTask).\
        filter(GradingTask.grader == sunet).\
        order_by(QuestionGrade.time.desc()).all()
