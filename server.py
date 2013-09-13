"""
OHMS: Online Homework Management System
"""

from flask import Flask, render_template
from sqlalchemy.orm.query import Query

from base import session
from objects import Question
app = Flask(__name__,static_url_path="")

@app.route("/")
def hello():
    return "Hello World!"

@app.route("/hw/<id>")
def view(id):
    questions = session.query(Question).filter_by(hw_id=id).all()
    return render_template("view.html",questions=questions)

if __name__ == "__main__":
    app.run(debug=True)
