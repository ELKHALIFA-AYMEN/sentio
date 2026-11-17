import sys
from pathlib import Path

# The tests run in pytest's "importlib" mode, where test files cannot import each other.
# Make the shared sample events (enrichment_samples.py) importable.
sys.path.insert(0, str(Path(__file__).parent))
