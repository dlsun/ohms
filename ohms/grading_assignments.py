"""
grading_assignments.py
"""

import sys
import random

from base import session
from objects import GradingTask, GradingPermission
from queries import get_recent_question_responses
from datetime import datetime


def make_grading_assignments(q_id):
    """Assigns students to grade each other, regardless of treatment group"""
    responses = get_recent_question_responses(q_id)
    random.shuffle(responses)

    # Create grading permissions
    for r in responses:
        gp = GradingPermission(sunet=r.sunet, question_id=q_id,
                               permissions=0,
                               due_date=datetime(2013, 10, 1, 5, 0, 0))
        session.add(gp)

    # This scheme guarantees that no pair of students is ever assigned to grade
    # together more than once.
    n = len(responses)
    for i, response in enumerate(responses):
        for offset in [1, 3, 6]:
            to_grade = responses[(i + offset) % n]
            gt = GradingTask(grader=response.sunet, question_response=to_grade)
            session.add(gt)

    session.commit()


if __name__ == "__main__":
    make_grading_assignments(sys.argv[1])
