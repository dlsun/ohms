# Makefile for deploys

all: local-deploy

local-deploy:
	cp options/local_options.py ohms/options.py

test-deploy: static-test-deploy ohms-test-deploy
	@echo "running on: http://www.stanford.edu/class/stats60/cgi-bin/test/index_test.cgi/"

prod-deploy: static-prod-deploy ohms-prod-deploy
	@echo "running on: http://www.stanford.edu/class/stats60/cgi-bin/index.cgi/"

static-test-deploy:
	rsync -avz static/ corn.stanford.edu:/afs/ir.stanford.edu/class/stats60/WWW/static_test

ohms-test-deploy:
	cp options/test_options.py ohms/options.py
	rsync -avz --delete-excluded ohms/ corn.stanford.edu:/afs/ir.stanford.edu/class/stats60/ohms_test/

static-prod-deploy:
	rsync -avz static/ corn.stanford.edu:/afs/ir.stanford.edu/class/stats60/WWW/static

ohms-prod-deploy:
	cp options/prod_options.py ohms/options.py
	rsync -avz --delete-excluded ohms/ corn.stanford.edu:/afs/ir.stanford.edu/class/stats60/ohms/
