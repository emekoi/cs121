#!/usr/bin/bash

python3 -m venv .venv
. .venv/bin/activate
pip3 install -r requirements.txt

DATABASE_NAME=emekafinalprojectdb bash run.sh setup
DATABASE_NAME=emekafinalprojectdb python app.py
