#!/usr/bin/env python3
import os
import json
import sys
from typing import Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

URL = "https://bloxfruitsvalues.com/api/v1/values?sortBy=position&limit=100&page=1"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/119.0.0.0 Safari/537.36"
)

HEADERS = {
    "Accept": "application/json",
    "Referer": "https://bloxfruitsvalues.com/",
    "Origin": "https://bloxfruitsvalues.com",
    "User-Agent": USER_AGENT,
}

def make_session() -> requests.Session:
    s = requests.Session()
    retry = Retry(
        total=5,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET", "HEAD", "OPTIONS"]),
        raise_on_status=False,
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter(max_retries=retry)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    s.cookies.set("first_visit", "true", domain="bloxfruitsvalues.com", path="/")
    return s

def fetch_values(session: Optional[requests.Session] = None):
    close = False
    if session is None:
        session = make_session()
        close = True
    try:
        resp = session.get(URL, headers=HEADERS, timeout=20)
        if resp.status_code >= 400:
            try:
                msg = json.dumps(resp.json(), indent=2, ensure_ascii=False)
            except Exception:
                msg = (resp.text or "")[:2000]
            raise requests.HTTPError(f"HTTP {resp.status_code} {resp.reason}\n{msg}", response=resp)
        if "application/json" in (resp.headers.get("Content-Type","").lower()):
            return resp.json()
        return {"non_json_preview": (resp.text or "")[:1000]}
    finally:
        if close:
            session.close()

# ---- partition helpers ----

DROP_KEYS = {
    "id","position","image","updatedAt","itemId","createdAt",
    "history","hype","bestUsedFor","value","trend","tier","type",
    "demand","regDemand","permDemand",
}

def normalize_item(item: dict) -> dict:
    """Copy, merge optional metadata, and drop noisy keys."""
    out = dict(item)  # shallow copy so original is untouched
    meta = out.pop("metadata", None)
    if isinstance(meta, dict):
        # don't overwrite existing top-level keys
        for k, v in meta.items():
            out.setdefault(k, v)
    for k in DROP_KEYS:
        out.pop(k, None)
    return out

def partition_items(items: list[dict]) -> dict:
    fruits, gamepasses, extra = [], [], []
    for raw in items:
        item = normalize_item(raw)
        cat = (item.get("category") or "").strip()
        if cat == "Fruits":
            fruits.append(item)
        elif cat == "Gamepasses":
            gamepasses.append(item)
        else:
            extra.append(item)
    return {"fruits": fruits, "gamepasses": gamepasses, "extra": extra}

def get_fruits():
    try:
        data = fetch_values()
        if not isinstance(data, dict) or "items" not in data:
            raise RuntimeError("Unexpected response shape; no 'items' key present.")
        payload = partition_items(data["items"])

        # os.makedirs("storage", exist_ok=True)
        # with open("storage/fruits_bfv.json", "w", encoding="utf-8") as f:
        #     json.dump(payload, f, indent=2, ensure_ascii=False)
        
        return payload

        # Optional: print a quick summary
        # print(json.dumps(
        #     {
        #         "counts": {
        #             "fruits": len(payload["fruits"]),
        #             "gamepasses": len(payload["gamepasses"]),
        #             "extra": len(payload["extra"]),
        #         }
        #     },
        #     indent=2,
        #     ensure_ascii=False,
        # ))

    except requests.HTTPError as e:
        print(f"[HTTP ERROR] {e}", file=sys.stderr); sys.exit(2)
    except requests.RequestException as e:
        print(f"[REQUEST ERROR] {e}", file=sys.stderr); sys.exit(3)
    except Exception as e:
        print(f"[UNEXPECTED ERROR] {e}", file=sys.stderr); sys.exit(1)
