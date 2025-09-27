import re
import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Any

URL_VALUES = "https://fruityblox.com/blox-fruits-value-list/"

VALUES_CARD_SELECTOR = "div.p-4.border.border-secondary.rounded-lg"
VALUE_RE = re.compile(r"\b(\d+(?:\.\d+)?)\s*([kmbKMB])\b")

SUFFIX_MULTIPLIERS = {"k": 1_000, "m": 1_000_000, "b": 1_000_000_000}

def fetch_soup(url: str) -> BeautifulSoup:
    resp = requests.get(url, timeout=20)
    resp.raise_for_status()
    return BeautifulSoup(resp.content, "html.parser")

def normalize_whitespace(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()

def parse_values(text: str) -> List[Dict[str, Any]]:
    values = []
    for num, suffix in VALUE_RE.findall(text):
        raw = f"{num}{suffix}"
        n = float(num) * SUFFIX_MULTIPLIERS[suffix.lower()]
        n = int(n) if n.is_integer() else n
        values.append({"raw": raw, "numeric": n})
    return values

def guess_name(card_text: str) -> str:
    # pick first non-empty line; DON'T strip words like 'fruit'
    lines = [normalize_whitespace(x) for x in card_text.splitlines()]
    lines = [ln for ln in lines if ln]
    if not lines:
        return "Unknown"
    # Prefer a line that isn't only values
    for ln in lines:
        if not VALUE_RE.search(ln) or not ln.strip().lower() in {m[0] for m in VALUE_RE.findall(ln)}:
            return ln.strip(" -–:|")
    return lines[0].strip(" -–:|")

def classify(card_text: str) -> str:
    t = card_text.lower()
    if "gamepass" in t or "pass" in t:
        return "gamepasses"
    if any(k in t for k in ("special", "exclusive", "limited", "event", "holiday")):
        return "special"
    return "fruits"

def extract_value_cards(soup: BeautifulSoup):
    cards = soup.select(VALUES_CARD_SELECTOR)
    results = []
    for c in cards:
        text = normalize_whitespace(c.get_text(separator="\n"))
        name = guess_name(text)
        values = parse_values(text)
        category = classify(text)
        results.append((category, name, values))
    return results

# === NEW: name cleaner per your requirements ===
TOKEN_REPEAT_RE = re.compile(r"\b(token)\b(?:\s+\1\b)+", flags=re.I)
VALUE_TOKEN_RE = re.compile(r"\b\d+(?:\.\d+)?\s*[kmbKMB]\b")
GAMEPASS_WORD_RE = re.compile(r"\bgamepass(?:es)?\b", flags=re.I)
FRUIT_WORD_RE = re.compile(r"\bfruit\b", flags=re.I)
TRAILING_ZERO_RE = re.compile(r"[\s\-–:|]*\b0\b$", flags=re.I)

def clean_name(name: str, category: str) -> str:
    # 1) remove value tokens like '860m', '2.3b'
    name = VALUE_TOKEN_RE.sub("", name)
    # 2) collapse repeated 'token'
    name = TOKEN_REPEAT_RE.sub(r"\1", name)
    # 3) strip the word 'gamepass' from gamepass items
    if category == "gamepasses":
        name = GAMEPASS_WORD_RE.sub("", name)
    # 4) strip the word 'fruit' from fruit items
    if category == "fruits":
        name = FRUIT_WORD_RE.sub("", name)
    # 5) NEW: remove trailing standalone '0'
    name = TRAILING_ZERO_RE.sub("", name)

    # tidy punctuation/spaces
    name = re.sub(r"\s+", " ", name).strip(" -–:| \t")
    if not name:
        name = "Unknown"
    return name

def looks_like_header(item_name: str) -> bool:
    t = item_name.lower()
    return (
        "blox fruits values" in t
        or "select an item" in t
        or "all categories" in t
    )

def get_fruits() -> Dict[str, Any]:
    soup = fetch_soup(URL_VALUES)
    buckets = {"fruits": [], "gamepasses": [], "special": [], "skins": []}

    for category, name, values in extract_value_cards(soup):
        name = clean_name(name, category)
        item = {"name": name, "values": values}

        # Skip obvious header/junk cards
        if looks_like_header(name):
            continue
        # Drop items with no values (these are usually UI/helper cards)
        if not values:
            continue
        # We still collect to buckets, but only return fruits/gamepasses
        buckets.setdefault(category, []).append(item)

    result = {
        "fruits": buckets.get("fruits", []),
        "gamepasses": buckets.get("gamepasses", []),
    }

    # Extra safety: ensure no lingering header entries
    result["fruits"] = [f for f in result["fruits"] if not looks_like_header(f["name"])]
    result["gamepasses"] = [g for g in result["gamepasses"] if not looks_like_header(g["name"])]
    return result