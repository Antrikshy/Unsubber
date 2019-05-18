#!/usr/bin/env bash

export FLASK_APP=src/unsubber.py
export FLASK_ENV=development
export UNSUBBER_CLIENT_ID=$(head -n 1 config.txt)
export UNSUBBER_CLIENT_SECRET=$(head -n 2 config.txt | tail -n 1)

flask run