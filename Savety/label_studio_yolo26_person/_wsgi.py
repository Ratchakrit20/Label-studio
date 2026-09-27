"""Development WSGI entry point used by `label-studio-ml start`."""

import argparse

from label_studio_ml.api import init_app

from model import YOLO26PersonSegmentation


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9090)
    parser.add_argument("--basic-auth-user", default=None)
    parser.add_argument("--basic-auth-pass", default=None)
    args = parser.parse_args()

    app = init_app(
        model_class=YOLO26PersonSegmentation,
        basic_auth_user=args.basic_auth_user,
        basic_auth_pass=args.basic_auth_pass,
    )
    app.run(host=args.host, port=args.port, debug=False)
else:
    app = init_app(model_class=YOLO26PersonSegmentation)
