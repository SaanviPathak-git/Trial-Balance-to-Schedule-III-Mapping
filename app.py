"""
app.py
Root entrypoint for Streamlit Cloud deployment:
    streamlit run app.py
Delegates execution to app/streamlit_app.py.
"""

import os
import sys
import runpy

# Ensure repository root is on sys.path
root_dir = os.path.dirname(os.path.abspath(__file__))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

target_script = os.path.join(root_dir, "app", "streamlit_app.py")
runpy.run_path(target_script, run_name="__main__")
