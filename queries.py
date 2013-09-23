"""
queries.py

Some useful sql queries.
"""

from base import session
from objects import QuestionResponse, QuestionGrade, GradingTask


def get_responses(id, sunet):
    if id.startswith("g"):
        responses = session.query(QuestionGrade).\
            filter_by(grading_task_id=id[1:]).\
            join(GradingTask).\
            filter(GradingTask.grader == sunet).\
            order_by(QuestionGrade.time.desc()).all()
    else:
        responses = session.query(QuestionResponse).\
            filter_by(sunet=sunet).\
            filter_by(question_id=id).\
            order_by(QuestionResponse.time.desc()).all()
    return responses


def get_sample_responses(question_id):
    return session.query(QuestionResponses).\
        filter_by(sunet="Sample Sam").\
        filter_by(question_id=question_id).all()

def get_grading_task(id):
    id = id[1:] if id.startswith("g") else id
    return session.query(GradingTask).get(id)
