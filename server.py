"""
OHMS: Online Homework Management System
"""

from base import Base, session, engine
from flask import Flask
app = Flask(__name__)
import objects


@app.route("/")
def hello():
    return "Hello World!"


def init_db():
    Base.metadata.create_all(engine)
    h = objects.Homework()
    h.from_xml('hws/example.xml')
    session.add(h)
    session.commit()

if __name__ == "__main__":
    init_db()
    app.run(debug=False)
