"""
queries.py

Some useful sql queries.
"""

from base import session
from objects import QuestionResponse


def get_responses(q_id, sunet="dlsun"):
    responses = session.query(QuestionResponse).\
        filter_by(sunet=sunet).\
        filter_by(question_id=q_id).\
        order_by(QuestionResponse.time.desc()).all()
    return responses
