#!/usr/bin/env bash

export UNSUBBER_CLIENT_ID=$(head -n 1 config.txt)
export UNSUBBER_CLIENT_SECRET=$(head -n 2 config.txt | tail -n 1)

gunicorn -w 4 -b 127.0.0.1:5000 src.unsubber:app