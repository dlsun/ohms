#!/usr/bin/python
import sys
sys.path.append("..")

from wsgiref.handlers import CGIHandler
from ohms import app

CGIHandler().run(app)
