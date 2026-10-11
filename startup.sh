#!/bin/bash

if [ ! -d "static/item_icons" ]; then
    mkdir -p static/item_icons
    python -m zipfile -e item_icons.zip static
fi

gunicorn --bind=0.0.0.0:$PORT app:app
