"""Example script to trigger node suggestions for a material."""

import argparse
import os

import httpx


def main() -> int:
    parser = argparse.ArgumentParser(description="Run node suggestions for a material")
    parser.add_argument("--base-url", default="http://localhost:8000/api/v1")
    parser.add_argument("--material-id", required=True)
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--threshold", type=float, default=0.75)
    parser.add_argument("--semantic-weight", type=float, default=0.6)
    parser.add_argument("--keyword-weight", type=float, default=0.4)
    parser.add_argument("--top-k", type=int, default=20)
    args = parser.parse_args()

    if not os.environ.get("HF_TOKEN"):
        raise SystemExit("HF_TOKEN is required in the environment")

    payload = {
        "project_id": args.project_id,
        "threshold": args.threshold,
        "semantic_weight": args.semantic_weight,
        "keyword_weight": args.keyword_weight,
        "top_k": args.top_k,
    }

    url = f"{args.base_url}/materials/{args.material_id}/suggestions"
    response = httpx.post(url, json=payload, timeout=60)
    response.raise_for_status()
    data = response.json()

    print("Strong suggestions:")
    for item in data.get("strong", []):
        print(" -", item)

    print("\nWeak suggestions:")
    for item in data.get("weak", []):
        print(" -", item)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
