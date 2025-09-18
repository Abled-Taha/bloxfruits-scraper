import json
import re
from dataclasses import dataclass, asdict
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union

from bs4 import BeautifulSoup
import requests

# -----------------------------
# Utilities
# -----------------------------

URL_STOCK = "https://fruityblox.com/stock/"

def fetch_soup() -> BeautifulSoup:
    resp = requests.get(URL_STOCK, timeout=20)
    resp.raise_for_status()
    return BeautifulSoup(resp.content, "html.parser")

@dataclass
class StockItem:
    name: str
    dealer: str            # "Normal" | "Mirage"
    image: Optional[str]
    money_price: Optional[int]    # in-game money (numeric, not shortened)
    robux_price: Optional[int]    # robux (numeric)
    money_price_str: Optional[str]
    robux_price_str: Optional[str]
    slug: Optional[str]
    category: Optional[str]       # "fruit" | "gamepass" | "token" | etc.

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

_SHORT_SUFFIXES = (
    (1_000_000_000, "b"),
    (1_000_000, "m"),
    (1_000, "k"),
)

def _short(n: Optional[Union[int, float]]) -> Optional[str]:
    if n is None:
        return None
    try:
        n = float(n)
    except (TypeError, ValueError):
        return None
    for base, suf in _SHORT_SUFFIXES:
        if n >= base:
            v = n / base
            # Strip trailing .0 (e.g. 1.0k -> 1k)
            s = f"{v:.1f}".rstrip("0").rstrip(".")
            return f"{s}{suf}"
    # <= 999
    if n.is_integer():
        return str(int(n))
    return str(n)

# -----------------------------
# Core extractors
# -----------------------------

_JSON_START_RE = re.compile(r'\{"currentStock"\s*:\s*\{', re.DOTALL)

def _extract_data_blob(raw_html: str) -> Optional[Dict[str, Any]]:
    """
    Find the JSON object that starts with {"currentStock": {...}, "itemMap": {...}}
    inside the Next.js flight data script and parse it.
    """
    m = _JSON_START_RE.search(raw_html)
    if not m:
        return None

    start = m.start()
    # Brace-match to find the end of the JSON object
    depth = 0
    end = None
    for i, ch in enumerate(raw_html[start:], start=start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end is None:
        return None

    blob = raw_html[start:end]
    try:
        data = json.loads(blob)
    except json.JSONDecodeError:
        # Sometimes there can be stray chars; try a mild cleanup
        blob = blob.replace("\n", " ").replace("\t", " ")
        data = json.loads(blob)
    return data

def _parse_cards_fallback(soup: BeautifulSoup) -> List[StockItem]:
    """
    Fallback if the JSON blob can't be parsed.
    Reads visible stock cards to assemble minimal info.
    """
    items: List[StockItem] = []
    for card in soup.select("div.p-4.border.border-secondary.rounded-lg"):
        name_el = card.select_one("h3")
        dealer_el = card.select_one("span.text-xs.text-gray-400")
        img_el = card.select_one("img")
        money_el, robux_el = None, None

        # The price spans appear in the right column; take two spans if present
        spans = card.select("div.flex.flex-col.items-end span.text-sm")
        if spans:
            # money like "$650k"
            money_el = spans[0].get_text(strip=True)
            # robux like "R1.1k"
            robux_el = spans[1].get_text(strip=True) if len(spans) > 1 else None

        name = (name_el.get_text(strip=True) if name_el else "Unknown")
        dealer_raw = (dealer_el.get_text(strip=True) if dealer_el else "")
        dealer = "Mirage" if "Mirage" in dealer_raw else "Normal" if "Normal" in dealer_raw else "All"

        image = img_el.get("src") if img_el else None

        # best-effort: keep money/robux strings from UI; numeric unknown
        def norm_money(s: Optional[str]) -> Optional[str]:
            if not s:
                return None
            return s.replace("$", "").strip()

        def norm_robux(s: Optional[str]) -> Optional[str]:
            if not s:
                return None
            return s.replace("R", "").strip()

        items.append(
            StockItem(
                name=name,
                dealer=dealer,
                image=image,
                money_price=None,
                robux_price=None,
                money_price_str=norm_money(money_el),
                robux_price_str=norm_robux(robux_el),
                slug=None,
                category=None,
            )
        )
    return items

def _build_items_from_state(state: Dict[str, Any]) -> Tuple[List[str], List[str], Dict[str, Dict[str, Any]]]:
    """
    Return (normal_names, mirage_names, item_map)
    """
    current = state.get("currentStock", {})
    item_map = state.get("itemMap", {})
    normal = list(current.get("normal", []))
    mirage = list(current.get("mirage", []))
    return normal, mirage, item_map

def _item_to_stock(name: str, dealer: str, item_map: Dict[str, Any]) -> StockItem:
    rec = item_map.get(name, {}) or {}
    img = rec.get("image")
    money = rec.get("money_price")
    robux = rec.get("robux_price")
    return StockItem(
        name=name,
        dealer=dealer,
        image=img,
        money_price=money if isinstance(money, (int, float)) else None,
        robux_price=robux if isinstance(robux, (int, float)) else None,
        money_price_str=_short(money) if isinstance(money, (int, float)) else None,
        robux_price_str=_short(robux) if isinstance(robux, (int, float)) else None,
        slug=rec.get("slug"),
        category=rec.get("category"),
    )

# -----------------------------
# Public API
# -----------------------------

def parse_stock_from_soup(soup: Union[str, BeautifulSoup]) -> Dict[str, Any]:
    """
    Extract the stock data object from the stock page soup/raw html.

    Returns:
        {
          "normal": ["Spring","Smoke","Light", ...],
          "mirage": ["Smoke","Light","Love", ...],
          "itemMap": { "<name>": { image, money_price, robux_price, slug, category, ... }, ... }
        }
    """
    raw_html = str(soup) if not isinstance(soup, str) else soup
    state = _extract_data_blob(raw_html)
    if not state:
        # No JSON state found; synthesize minimal structure
        bs = BeautifulSoup(raw_html, "html.parser")
        items = _parse_cards_fallback(bs)
        # Group by dealer for a best-effort structure
        normal = [it.name for it in items if it.dealer == "Normal"]
        mirage = [it.name for it in items if it.dealer == "Mirage"]
        item_map: Dict[str, Any] = {}
        for it in items:
            item_map[it.name] = {
                "image": it.image,
                "money_price": None,
                "robux_price": None,
                "slug": None,
                "category": None,
            }
        return {"normal": normal, "mirage": mirage, "itemMap": item_map}
    # Happy path: convert the Next.js state into our compact structure
    normal, mirage, item_map = _build_items_from_state(state)
    return {"normal": normal, "mirage": mirage, "itemMap": item_map}

def get_stock_normal(soup: Union[str, BeautifulSoup]) -> List[Dict[str, Any]]:
    """
    Return a list of Normal dealer stock items as dictionaries.
    Each dict has: name, dealer, image, money_price, robux_price, money_price_str, robux_price_str, slug, category
    """
    state = parse_stock_from_soup(soup)
    item_map = state.get("itemMap", {})
    out: List[Dict[str, Any]] = []
    for name in state.get("normal", []):
        out.append(_item_to_stock(name, "Normal", item_map).to_dict())
    return out

def get_stock_mirage(soup: Union[str, BeautifulSoup]) -> List[Dict[str, Any]]:
    """
    Return a list of Mirage dealer stock items as dictionaries.
    """
    state = parse_stock_from_soup(soup)
    item_map = state.get("itemMap", {})
    out: List[Dict[str, Any]] = []
    for name in state.get("mirage", []):
        out.append(_item_to_stock(name, "Mirage", item_map).to_dict())
    return out

def get_stock_all() -> Dict[str, List[Dict[str, str]]]:
    """
    Return stock in the format:
    {
      "normal": [ { "name": "<item>" }, ... ],
      "mirage": [ { "name": "<item>" }, ... ]
    }
    """
    soup = fetch_soup()
    state = parse_stock_from_soup(soup)

    normal_items = []
    mirage_items = []

    for name in state.get("normal", []):
        normal_items.append({"name": name})

    for name in state.get("mirage", []):
        mirage_items.append({"name": name})

    return {"normal": normal_items, "mirage": mirage_items}

# Optional: tiny helper to pull only names (handy for quick checks)
def get_stock_names(soup: Union[str, BeautifulSoup]) -> Dict[str, List[str]]:
    """
    Return just the names for each dealer.
    """
    state = parse_stock_from_soup(soup)
    return {"normal": state.get("normal", []), "mirage": state.get("mirage", [])}
