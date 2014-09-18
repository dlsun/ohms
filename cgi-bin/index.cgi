#!/usr/bin/python
import sys
sys.path.append("..")

from wsgiref.handlers import CGIHandler
from ohms.app import app

CGIHandler().run(app)
