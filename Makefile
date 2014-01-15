# Makefile for deploys

all: local-deploy

local-deploy:
	cp options/local_options.py ohms/options.py

test-deploy: static-test-deploy ohms-test-deploy
	@echo "running on: http://www.stanford.edu/class/psych10/cgi-bin/test/index.cgi/"

prod-deploy: static-prod-deploy ohms-prod-deploy
	@echo "running on: http://www.stanford.edu/class/psych10/cgi-bin/index.cgi/"

static-test-deploy:
	rsync -avz static/ corn.stanford.edu:/afs/ir.stanford.edu/class/psych10/WWW/static_test

ohms-test-deploy:
	cp options/test_options.py ohms/options.py
	rsync -avz --delete-excluded ohms/ corn.stanford.edu:/afs/ir.stanford.edu/class/psych10/ohms_test/

static-prod-deploy:
	rsync -avz static/ corn.stanford.edu:/afs/ir.stanford.edu/class/psych10/WWW/static

ohms-prod-deploy:
	scp corn.stanford.edu:~/psych10/ohms/templates/office_hours.html ohms/templates/
	cp options/prod_options.py ohms/options.py
	rsync -avz --delete-excluded ohms/ corn.stanford.edu:/afs/ir.stanford.edu/class/psych10/ohms/
