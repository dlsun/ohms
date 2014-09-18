target = "prod"

# this customizes the page header
title = "OHMS"
instructor = "Dennis Sun and Naftali Harris"

# specify the directories that you use for your course
base_url = "http://www.stanford.edu/class/stats60"
cgi = "cgi-bin/index.cgi"
static = "static"

# specify the USERNAME, PASSWORD, AND DATABASE for the production MySQL database
db = 'mysql://USERNAME:PASSWORD@mysql-user-master.stanford.edu/DATABASE?charset=utf8'

# specify the IDs of the course administrators (e.g., instructors, TAs)
admins = ['dlsun', 'naftali']
