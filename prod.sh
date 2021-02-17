#!/usr/bin/env bash

export UNSUBBER_CLIENT_ID=$(head -n 1 config.txt)
export UNSUBBER_CLIENT_SECRET=$(head -n 2 config.txt | tail -n 1)

gunicorn -w 4 --threads 12 -b :5000 src.unsubber:app --timeout 60