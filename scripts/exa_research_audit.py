"""Explicit Exa retrieval for manuscript audits; credentials never enter artifacts."""

import argparse
import json
import os
import ssl
import certifi
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
OBJECTIVE = "Audit Scout manuscript and circle-packing benchmarks. Rank original papers, author repositories and official problem pages first; exclude unsupported secondary claims. Retrieve methods, baseline limitations and dated numerical bounds."


def key():
    if os.environ.get("EXA_API_KEY"):
        return os.environ["EXA_API_KEY"]
    value = dotenv_values(ROOT / ".env.research.local").get("EXA_API_KEY")
    if not value:
        raise RuntimeError("EXA_API_KEY is missing")
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query")
    parser.add_argument("--urls", nargs="+")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if bool(args.query) == bool(args.urls):
        parser.error("Choose query or URLs")
    if args.output.exists():
        parser.error("Output exists; refusing duplicate call")
    endpoint = "search" if args.query else "contents"
    payload = (
        dict(
            query=args.query,
            objective=OBJECTIVE,
            type="auto",
            contents={"highlights": True},
        )
        if args.query
        else dict(urls=args.urls, text=True)
    )
    request = Request(
        "https://api.exa.ai/" + endpoint,
        data=json.dumps(payload).encode(),
        headers={"x-api-key": key(), "Content-Type": "application/json"},
    )
    with urlopen(
        request, timeout=90, context=ssl.create_default_context(cafile=certifi.where())
    ) as response:
        result = json.load(response)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(
            dict(
                retrieved_utc=datetime.now(timezone.utc).isoformat(),
                endpoint=endpoint,
                request=payload,
                response=result,
            ),
            indent=2,
        )
    )
    print(
        json.dumps(
            dict(
                saved=str(args.output),
                results=len(result.get("results", [])),
                cost=result.get("costDollars"),
                statuses=result.get("statuses"),
            )
        )
    )


if __name__ == "__main__":
    main()
