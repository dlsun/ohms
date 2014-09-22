target = "prod"

# this customizes the page header
title = "Stats 60"
instructor = "Guenther Walther"

# specify the URLs for your course
base_url = "https://web.stanford.edu/class/stats60"
cgi = "cgi-bin/index.cgi"
static = "static"

# specify the directory on AFS
base_dir = "/afs/ir/class/stats60"

# specify htaccess file -- this controls who can access OHMS
# by default, it allows access to anybody with a Stanford login
htaccess = ""
# however, you can also use the file in WWW/restricted/, which limits access to students enrolled in the course
# htaccess = "%s/WWW/restricted/.htaccess" % base_dir

# grab the username, password, and database name from db_info file (this works as of Autumn 2014)
def get_db():
    f = open("%s/db_private/db_info" % base_dir, "r")
    info = f.read().strip().split('\n')
    username = info[0].split(': ')[1]
    password = info[1].split(': ')[1]
    server = info[2].split(': ')[1]
    db_name = info[3].split(': ')[1]
    # NB. The alternative is to simply hard code this URL into this file
    return "mysql://%s:%s@%s/%s?charset=utf8" % (username, password, server, db_name)

# specify the IDs of the course administrators (e.g., instructors, TAs)
admins = ['dlsun', 'naftali']
