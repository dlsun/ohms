"""
grading_assignments.py
"""

import sys
import random

from base import session
from objects import GradingTask
from queries import get_recent_question_responses


def make_grading_assignments(q_id, reps=3):
    """Assigns students to grade each other, regardless of treatment group"""
    responses = get_recent_question_responses(q_id)
    random.shuffle(responses)

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
