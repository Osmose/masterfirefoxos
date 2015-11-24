#!/bin/bash
#
# Fetches the latest strings from the database and codebase and
# updates the locale repository.
#
# Needs DEIS_USER, DEIS_PASSWORD, DEIS_CONTROLLER, DEIS_APP and
# LOCALE_REPOSITORY environment variables.
#
# To set them go to Job -> Configure -> Build Environment -> Inject
# passwords and Inject env variables
#

set -ex

TDIR=`mktemp -d`
virtualenv $TDIR
. $TDIR/bin/activate
pip install fig

rm -rf locale db-changes.diff run-output
git clone $LOCALE_REPOSITORY locale

deis login $DEIS_CONTROLLER --username $DEIS_USERNAME --password $DEIS_PASSWORD
deis run -a $DEIS_APP -- "./manage.py runscript db_strings && echo CUTHERE && git diff locale | gzip -9 | uuencode -" > run-output
awk '{if (nowprint) {print;}}/CUTHERE/ {nowprint = 1}' run-output | uudecode | gunzip > db-changes.diff
fig --project-name jenkins${JOB_NAME}${BUILD_NUMBER} run -T web git apply db-changes.diff
fig --project-name jenkins${JOB_NAME}${BUILD_NUMBER} run -T web ./manage.py runscript extract
fig --project-name jenkins${JOB_NAME}${BUILD_NUMBER} run -T web ./manage.py runscript merge
fig --project-name jenkins${JOB_NAME}${BUILD_NUMBER} run -T web chmod a+wx -R locale

cd locale
git add .
git commit -m "Update strings."
git push origin master
