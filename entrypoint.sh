#!/bin/sh
export FLASK_APP=app:create_app
export FLASK_RUN_HOST=0.0.0.0
export FLASK_ENV=production
flask run
