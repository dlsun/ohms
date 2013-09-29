"""
queries.py

Some useful sql queries.
"""

import sqlalchemy

from base import session
from objects import QuestionResponse, QuestionGrade, GradingTask, User


def get_question_responses(id, sunet):
    return session.query(QuestionResponse).\
        filter_by(sunet=sunet).\
        filter_by(question_id=id).\
        order_by(QuestionResponse.time).all()


def get_question_grades(id, sunet):
    return session.query(QuestionGrade).\
        filter_by(grading_task_id=id).\
        join(GradingTask).\
        filter(GradingTask.grader == sunet).\
        order_by(QuestionGrade.time).all()


def get_user(sunet):
    return session.query(User).filter_by(sunet=sunet).one()


def exists_user(sunet):
    try:
        user = get_user(sunet)
        return True
    except sqlalchemy.orm.exc.NoResultFound:
        return False
