import os, sys

def update_options():
    os.system("cp options/options.py ohms/options.py")
    from ohms.options import base_dir
    return base_dir

def static_deploy():
    base_dir = update_options()
    os.system("rsync -avz static/ corn.stanford.edu:%s/WWW/static" % base_dir)
    print "Successfully deployed static files into production!"

def code_deploy():
    base_dir = update_options()
    os.system("rsync -avz ohms/ corn.stanford.edu:%s/ohms" % base_dir)
    print "Successfully deployed code files into production!"

if len(sys.argv) < 2:
    print '''The command is: python deploy.py (local/prod) (code/static/both) 
depending on where you want to deploy the system, and whether you want to copy just 
the Python code, the static Javascript and CSS files, or both.'''
elif sys.argv[1] == "local":
    os.system("cp options/local_options.py ohms/options.py")
else:
    if len(sys.argv) < 3 or sys.argv[2] == "both":
        code_deploy()
        static_deploy()
    elif sys.argv[2] == "static":
        static_deploy()
    elif sys.argv[2] == "code":
        code_deploy()


