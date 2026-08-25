# so pytest can import backtester / strategies without installing the package
import sys
from pathlib import Path

# put backend/ on sys.path - tests live one level deeper
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
