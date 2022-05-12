APP=concierge
LOCAL_APP=welcome-${APP}
VERSION_TAG=$(shell git branch --show-current)-$(shell git rev-parse --short HEAD)
CONCIERGE_ECR_URI=$(shell AWS_PROFILE=${AWS_PROFILE} AWS_REGION=${AWS_REGION} aws ecr describe-repositories --repository-names ml/${APP} | jq -r ".repositories[0].repositoryUri"):${VERSION_TAG}
AWS_PROFILE=welco
AWS_REGION=us-east-1
ECR_URI=257779808675.dkr.ecr.us-east-1.amazonaws.com/

.PHONY : githook
githook: clean_dependencies dependencies application

OS := $(shell uname -s | tr A-Z a-z)
linux_python = /usr/bin/python3
linux_pip = /usr/local/bin/pip3

.PHONY : clean_dependencies
clean_dependencies :
ifeq ($(OS), darwin)
	pip uninstall -y rsyslog_cee
	pip uninstall -y bandolier
endif
ifeq ($(OS), linux)
	$(linux_pip) uninstall -y rsyslog_cee
	$(linux_pip) uninstall -y bandolier
endif

.PHONY : dependencies
dependencies :
ifeq ($(OS), darwin)
	pip install -r requirements.txt
endif
ifeq ($(OS), linux)
	$(linux_pip) install -r requirements.txt --user
endif

.PHONY : application
application :
ifeq ($(OS), darwin)
	pip install .
endif
ifeq ($(OS), linux)
	$(linux_pip) install . --user
endif

.PHONY : dev_application
dev_application :
ifeq ($(OS), darwin)
	pip install -e ./
endif
ifeq ($(OS), linux)
	$(linux_pip) install -e ./  --user
endif

.PHONY : dev
dev: clean_dependencies dependencies dev_application

.PHONY : package
package :
ifeq ($(OS), darwin)
	python setup.py sdist bdist_wheel
endif
ifeq ($(OS), linux)
	$(linux_python) setup.py sdist bdist_wheel
endif

.PHONY : clean
clean :
ifeq ($(OS), darwin)
	pip uninstall -y rsyslog_cee
	pip uninstall -y bandolier
	pip uninstall -y concierge
endif
ifeq  ($(OS), linux)
	$(linux_pip) uninstall -y rsyslog_cee
	$(linux_pip) uninstall -y bandolier
	$(linux_pip) uninstall -y concierge
endif

.PHONY : docker_python
docker_python:
	./docker_build_python3.8.sh


.PHONY : docker_concierge_requirements
docker_concierge_requirements: docker_python
	./docker_build_requirements.sh

.PHONY : docker_build
docker_build:
	./docker_build.sh
	docker tag concierge $(CONCIERGE_ECR_URI)

.PHONY : up # assumes we have stored our built container
up: docker_build
	ECR_URI=$(ECR_URI) \
	docker compose up --remove-orphans

.PHONY : docker_login_1	
# Need to login to ecr in order to allow docker cli to push images to it.  Just run this
docker_login_1:
	# Notice the backticks, this is running the command returned by the aws command
	`AWS_PROFILE=$(AWS_PROFILE) aws ecr get-login --region $(AWS_REGION) --no-include-email`

.PHONY : docker_login
# aws cli v2
docker_login: 
	AWS_PROFILE=$(AWS_PROFILE) aws ecr get-login-password --region $(AWS_REGION) | docker login --username AWS --password-stdin $(ECR_URI)

.PHONY : docker_publish
# pushes the containers with the ECR URI tag to ECR
docker_publish: docker_build docker_login
	docker tag concierge $(CONCIERGE_ECR_URI)
	docker push $(CONCIERGE_ECR_URI)

.PHONY : os
os :
	@echo $(OS)

.PHONY: con-bash
con-bash:
	docker exec -it concierge /bin/bash