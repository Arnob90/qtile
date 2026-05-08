#!/bin/sh
WLR_BACKENDS=wayland PYTHONPATH=. ./venv/bin/python -m libqtile.scripts.main start -b wayland -c ./dev_config.py
