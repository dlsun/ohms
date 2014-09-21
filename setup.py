import os, re, subprocess

# the root directory for the course
root = "../.."

# run a command and print
def run_command(cmd):
    print cmd
    os.system(cmd)

# do not allow regular users to view this direcotry
run_command("fs sa . system:anyuser none")

# figure out name of CGI user (usually of the form class-stats60-1142.cgi), set its permissions
out = subprocess.check_output(["fs", "la", root])
cgi_user = re.findall('class.*\.cgi', out)[0]
run_command('fs sa -dir `find %s -type d -not -path "*/.backup*" -print` -acl %s rlidwk' % (root, cgi_user))

# replace the options file in ohms/ with the appropriate options file
run_command("cp -r options/options.py ohms/options.py")

# copy ohms to root, do not allow any user to see it
run_command("cp -r ohms %s/" % root)
run_command("fs sa %s/ohms system:anyuser none" % root)

# copy static files to WWW/static
run_command("cp -r static %s/WWW/" % root)

# copy CGI file to cgi-bin/
run_command("cp cgi-bin/index.cgi %s/cgi-bin/" % root)
run_command("chmod 700 %s/cgi-bin/index.cgi" % root)

# set .htaccess file appropriately
try:
    from options import htaccess
    if htaccess:
        run_command("cp %s %s/cgi-bin/.htaccess" % (htaccess, root))
    else:
        run_command("cp cgi-bin/.htaccess %s/cgi-bin/.htaccess" % root)

# initialize empty database
print "Now initializing the database..."
from ohms.objects import Base
from ohms.base import engine
Base.metadata.create_all(engine)

