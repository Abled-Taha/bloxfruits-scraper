import re
import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Any, Tuple

URL_VALUES = "https://fruityblox.com/blox-fruits-value-list/"

CARD_SELECTOR = "div.p-4.border.border-secondary.rounded-lg"  # keep hover/bg/transition/cursor optional

VALUE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*([kmbKMB])\b")
# common keywords to help classification (tweak as needed)
GAMEPASS_KEYS = {"gamepass", "pass"}
SPECIAL_KEYS = {"special", "exclusive", "limited", "event", "holiday"}

SUFFIX_MULTIPLIERS = {
    "k": 1_000,
    "m": 1_000_000,
    "b": 1_000_000_000,
}

def fetch_soup(url: str) -> BeautifulSoup:
    resp = requests.get(url, timeout=20)
    resp.raise_for_status()
    return BeautifulSoup(resp.content, "html.parser")

def normalize_whitespace(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()

def parse_values(text: str) -> List[Dict[str, Any]]:
    """Find value tokens like 50k, 1.2m, 3b and return both raw + numeric."""
    values = []
    for num, suffix in VALUE_RE.findall(text):
        raw = f"{num}{suffix}"
        n = float(num) * SUFFIX_MULTIPLIERS[suffix.lower()]
        # prefer ints for whole numbers
        n = int(n) if n.is_integer() else n
        values.append({"raw": raw, "numeric": n})
    return values

def guess_name(card_text: str) -> str:
    """
    Try to guess the item name from the first line or bold header-ish chunk.
    Fallback: take the first 4 words that look like a title.
    """
    # Split by lines and pick the first non-empty
    lines = [normalize_whitespace(x) for x in card_text.splitlines()]
    lines = [ln for ln in lines if ln]
    if not lines:
        return "Unknown"

    # Prefer a line that does NOT start with a value token
    for ln in lines:
        if not VALUE_RE.search(ln):
            # Remove generic words like 'fruit'/'gamepass' at the end
            ln_clean = re.sub(r"\b(fruit|gamepass|special)\b", "", ln, flags=re.I).strip(" -–:|")
            if ln_clean:
                return ln_clean
    # fallback
    words = lines[0].split()
    return " ".join(words[:4]) if words else "Unknown"

def classify(card_text: str) -> str:
    t = card_text.lower()
    if any(k in t for k in GAMEPASS_KEYS):
        return "gamepasses"
    if any(k in t for k in SPECIAL_KEYS):
        return "special"
    # default bucket
    return "fruits"

def extract_cards(soup: BeautifulSoup) -> List[Tuple[str, str, List[Dict[str, Any]]]]:
    cards = soup.select(CARD_SELECTOR)
    results = []
    for c in cards:
        text = normalize_whitespace(c.get_text(separator="\n"))
        name = guess_name(text)
        values = parse_values(text)
        category = classify(text)
        results.append((category, name, values))
    return results

def get_fruits() -> Dict[str, Any]:
    """
    Scrape values and return:
    {
      "fruits":   [{"name": ..., "values": [{"raw": "50k", "numeric": 50000}, ...]}, ...],
      "gamepasses": [...]
    }
    """
    soup = fetch_soup(URL_VALUES)
    buckets = {"fruits": [], "gamepasses": []}

    for category, name, values in extract_cards(soup):
        item = {"name": name, "values": values}
        # ensure the bucket exists even if classify returns something unexpected
        buckets.setdefault(category, [])
        buckets[category].append(item)

    buckets["fruits"].pop(len(buckets["fruits"]) - 1)  # remove last (ads)
    buckets["gamepasses"].pop(0)
    return buckets
