import os
import sys

# Ensure engine/ is on the path for all tests, so individual test files
# don't need their own sys.path manipulation.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
