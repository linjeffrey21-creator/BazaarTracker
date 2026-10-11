#!/bin/bash

if [ ! -d "static/item_icons" ]; then
    python -m zipfile -e static/item_icons.zip static
fi

gunicorn --bind=0.0.0.0:$PORT app:app
