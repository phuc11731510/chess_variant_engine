#!/bin/bash
# run.sh GIA: chuyen thang sang engine gia.
exec python3 "$(dirname "$0")/fake_engine.py" "$@"
