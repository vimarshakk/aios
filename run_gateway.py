import os
import sys

# Add virtualenv site-packages first
venv_site = os.path.abspath(".venv/lib/python3.12/site-packages")
if os.path.exists(venv_site):
    sys.path.insert(0, venv_site)

# Find all packages and services src directories
for parent in ["packages", "services"]:
    if os.path.exists(parent):
        for name in os.listdir(parent):
            src_dir = os.path.join(parent, name, "src")
            if os.path.exists(src_dir):
                sys.path.append(os.path.abspath(src_dir))

# Now import uvicorn and app
import uvicorn
from aios.gateway.main import app
uvicorn.run(app, host="127.0.0.1", port=8085)
