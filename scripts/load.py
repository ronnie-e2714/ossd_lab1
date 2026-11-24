"""Concurrent real inference requests; exits nonzero if all requests fail."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import time
import urllib.request


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--url", default="http://127.0.0.1:8080/predict")
    p.add_argument("--seconds", type=int, default=180)
    p.add_argument("--concurrency", type=int, default=50)
    args = p.parse_args()
    payload = json.dumps({"instances": [[5.1, 3.5, 1.4, 0.2]]}).encode()
    deadline = time.monotonic() + args.seconds

    def worker(_):
        success = errors = 0
        while time.monotonic() < deadline:
            try:
                req = urllib.request.Request(args.url, data=payload,
                    headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=10) as response:
                    if json.load(response) != {"predictions": [0]}:
                        raise ValueError("Unexpected prediction")
                success += 1
            except Exception:
                errors += 1
        return success, errors

    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        counts = list(pool.map(worker, range(args.concurrency)))
    success, errors = map(sum, zip(*counts))
    print(json.dumps(dict(success=success, errors=errors)))
    if not success:
        raise SystemExit("No successful predictions")


if __name__ == "__main__":
    main()
