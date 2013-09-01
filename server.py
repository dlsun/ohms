"""
OHMS: Online Homework Management System
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()
engine = create_engine('sqlite:///ohms.db', echo=True)
Session = sessionmaker(bind=engine)
session = Session()

from flask import Flask
app = Flask(__name__)

import homework
import question


@app.route("/")
def hello():
    return "Hello World!"


def init_db():
    question.Base.metadata.create_all(engine)

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
