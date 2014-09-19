target = "test"

# this customizes the page header
title = "OHMS"
instructor = "Dennis Sun and Naftali Harris"

# specify the directories that you use for your course
base_url = "https://www.stanford.edu/class/stats60"
cgi = "cgi-bin/test/index.cgi"
static = "static_test"

# specify the directory on AFS
base_dir = "/afs/ir/class/stats60"

# specify the USERNAME, PASSWORD, AND DATABASE for the production MySQL database
db = 'mysql://USERNAME:PASSWORD@mysql-user-master.stanford.edu/DATABASE?charset=utf8'

# specify the IDs of the course administrators (e.g., instructors, TAs)
admins = ['dlsun', 'naftali']
