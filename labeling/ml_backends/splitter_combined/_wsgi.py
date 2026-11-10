import argparse
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from label_studio_ml.api import init_app
from model import SplitterCombined
if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--host", default="127.0.0.1"); parser.add_argument("--port", type=int, default=9097)
    args = parser.parse_args(); init_app(model_class=SplitterCombined).run(host=args.host, port=args.port, debug=False)
else:
    app = init_app(model_class=SplitterCombined)
