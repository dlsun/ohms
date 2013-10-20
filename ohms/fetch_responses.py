from base import session
from objects import *
import sys

treatments = {
    0: [1,1,1,0,0,1,1,0,0],
    1: [1,0,0,1,1,0,0,1,1],
    2: [1,1,1,0,0,0,0,1,1],
    3: [1,0,0,1,1,1,1,0,0]
}

def print_responses(hw_number, q_number):

    homework = session.query(Homework).filter_by(name="Homework %d" % hw_number).one()
    questions = session.query(Question).filter_by(hw_id=homework.id).order_by(Question.id).all()

    question = questions[q_number-1]
    groups = []
    for i in range(4):
        if treatments[i][hw_number-1]==0:
            groups.append(i)
    
    responses = session.query(QuestionResponse).\
        filter_by(question_id=question.id).join(User).\
        filter((User.group == groups[0]) | (User.group == groups[1])).all()

    for response in responses:
        print response.id
        print response.item_responses[0].response.encode('utf-8')
        print '\n'


if __name__ == '__main__':
    print_responses(int(sys.argv[1]), int(sys.argv[2]))
    while True:
        id = raw_input('Enter ID of response you would like to make a sample response: ')
        response = session.query(QuestionResponse).get(id)
        response.sample = 1
        score = raw_input('Now enter its score: ')
        response.score = score
        session.commit()
        print 'Update successful!'

