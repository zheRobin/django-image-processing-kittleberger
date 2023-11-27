#!/bin/bash

source /var/app/venv/*/bin/activate
cd /var/app/current

source /etc/profile.d/sh.local
python manage.py makemigrations --noinput
python manage.py migrate --noinput