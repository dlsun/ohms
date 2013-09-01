"""
question.py

Objects representing homework questions.
"""

from sqlalchemy import Column, Integer, String, ForeignKey
from server import Base


class Question(Base):
    __tablename__ = 'questions'

    id = Column(Integer, primary_key=True)
    hw_id = Column(Integer, ForeignKey('hws.id'))
    questiontype = Column(String)
    points = Column(Integer)

    def score(self, answer):
        pass


class MultipleChoiceQuestion(Question):
    pass


class MultipleChoiceOption(Base):
    __tablename__ = 'mc_options'

    id = Column(Integer, primary_key=True)
    question_id = Column(Integer, ForeignKey('questions.id'))
    order = Column(Integer)
    text = Column(String)
    correct = Column(Integer)


class ShortAnswerQuestion(Question):
    pass


class LongAnswerQuestion(Question):
    pass
