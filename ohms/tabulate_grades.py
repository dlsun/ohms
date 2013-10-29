from base import session
from queries import get_recent_question_responses
from objects import *
import numpy as np
import sys

def tabulate_grades(q_id):

    responses = get_recent_question_responses(q_id)

    for r in responses:
        grading_tasks = session.query(GradingTask).\
            filter_by(question_response_id=r.id).all()
        question_grades = []
        for task in grading_tasks:
            submissions = session.query(QuestionGrade).\
                filter_by(grading_task_id=task.id).\
                order_by(QuestionGrade.time).all()
            if submissions:
                submission = question_grades.append(submissions[-1])
        scores = [grade.score for grade in question_grades]
        print r.sunet, scores

        if r.score is None:
            r.score = np.median(scores)
            r.comments = "Click <a href='rate?id=%d' target='_blank'>here</a> to view comments." % r.id
    
    session.commit()

if __name__ == "__main__":
    tabulate_grades(sys.argv[1])
