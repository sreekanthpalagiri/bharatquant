#!/bin/bash

# Unset any DATABASE_URL from shell environment
unset DATABASE_URL

# Activate the tester environment
source ~/.pyenv/versions/tester/bin/activate 2>/dev/null || pyenv activate tester 2>/dev/null || true

# Run the Flask app
python -m web.app
