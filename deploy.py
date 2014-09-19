import os, sys

def update_options(type):
    os.system("cp options/%s_options.py ohms/options.py" % type)
    from ohms.options import base_dir
    suffix = "" if type == "prod" else "_test"
    return base_dir, suffix

def static_deploy(type):
    out = update_options(type)
    os.system("rsync -avz static/ corn.stanford.edu:%s/WWW/static%s" % out)
    print "Successfully deployed static files to %s!" % type

def code_deploy(type):
    out = update_options(type)
    os.system("rsync -avz ohms/ corn.stanford.edu:%s/ohms%s" % out)
    print "Successfully deployed code files to %s!" % type

if len(sys.argv) < 2:
    print '''The command is: python deploy.py (local/test/prod) (code/static/both) 
depending on where you want to deploy the system, and whether you want to copy just 
the Python code, the static Javascript and CSS files, or both.'''
elif sys.argv[1] == "local":
    os.system("cp options/local_options.py ohms/options.py")
else:
    if len(sys.argv) < 3 or sys.argv[2] == "both":
        code_deploy(sys.argv[1])
        static_deploy(sys.argv[1])
    elif sys.argv[2] == "static":
        static_deploy(sys.argv[1])
    elif sys.argv[2] == "code":
        code_deploy(sys.argv[1])


