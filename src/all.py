import json, re
from collections import OrderedDict, Counter
from statistics import mean

import requests
from .stock_scraper import get_stock_all
from .fruits_scraper_fruity import get_fruits as get_fruits_fruity
from .fruits_scraper_bfv import get_fruits as get_fruits_bfv

data_fruity = get_fruits_fruity()
data_fruity_fruits = data_fruity["fruits"]; data_fruity_fruits.pop(len(data_fruity["fruits"]) - 1)
data_fruity_gamepasses = data_fruity["gamepasses"]

data_bfv = get_fruits_bfv()
data_bfv_fruits = data_bfv["fruits"]
data_bfv_gamepasses = data_bfv["gamepasses"]
data_bfv_limiteds = data_bfv["extra"]
# Split BFV "extra" into skins & specials
data_bfv_skins = data_bfv_limiteds.copy(); data_bfv_skins[:] = [s for s in data_bfv_skins if "Dragon Token" not in s["name"]]
data_bfv_specials = data_bfv_limiteds.copy(); data_bfv_specials[:] = [s for s in data_bfv_specials if "Dragon Token" in s["name"]]

result = {
  "stock": "",
  "fruits": "",
  "gamepasses": "",
  "specials": "",
}

# -------------------- small helpers --------------------

def normalize_name(name: str) -> str:
    return re.sub(r'[^a-z]+', '', (name or '').lower())

def words(name: str):
    return re.findall(r'[a-z]+', (name or '').lower())

def normalize_name_words(name: str) -> str:
    return ''.join(sorted(words(name)))

def choose_better_name(a: str, b: str) -> str:
    if len(b) > len(a):
        return b
    if len(b) == len(a) and sum(ch.isupper() for ch in b) > sum(ch.isupper() for ch in a):
        return b
    return a

def avg_int(values):
    return int(round(mean(values))) if values else 0

def most_frequent_nonempty(values):
    vals = [v for v in values if v]
    if not vals:
        return ""
    c = Counter(vals); mx = max(c.values())
    winners = {v for v, n in c.items() if n == mx}
    for v in vals:
        if v in winners:
            return v
    return vals[0]

def to_int_loose(x):
    if x is None: return 0
    if isinstance(x, bool): return int(x)
    if isinstance(x, (int, float)): return int(round(x))
    if isinstance(x, str):
        s = x.strip().replace(',', '')
        try: return int(float(s))
        except: return 0
    return 0

# -------------------- gamepasses merge --------------------

def merge_gamepasses_with_averages(gamepasses):
    merged = OrderedDict()

    for g in gamepasses:
        name = g.get("name")
        if not name:
            continue

        key = normalize_name(name)
        reg_value_candidate = g.get("regValueNumeric", g.get("regValue"))
        robux_price_candidate = g.get("robuxPrice")

        if key not in merged:
            merged[key] = {
                "_names": [name],
                "_regValues": [v for v in [reg_value_candidate] if isinstance(v, (int, float)) and v is not None],
                "_robuxPrices": [v for v in [robux_price_candidate] if isinstance(v, (int, float)) and v is not None],
                "_trends": [g.get("regTrend", "")],
                "_tradeables": [bool(g.get("tradeable", False))],
            }
            continue

        it = merged[key]
        it["_names"].append(name)
        if isinstance(reg_value_candidate, (int, float)) and reg_value_candidate is not None:
            it["_regValues"].append(reg_value_candidate)
        if isinstance(robux_price_candidate, (int, float)) and robux_price_candidate is not None:
            it["_robuxPrices"].append(robux_price_candidate)
        it["_trends"].append(g.get("regTrend", ""))
        it["_tradeables"].append(bool(g.get("tradeable", False)))

    out = []
    for key, it in merged.items():
        final_name = it["_names"][0]
        for cand in it["_names"][1:]:
            final_name = choose_better_name(final_name, cand)

        final = {
            "name": final_name,
            "regTrend": most_frequent_nonempty(it["_trends"]),
            "regValue": avg_int(it["_regValues"]),
            "tradeable": any(it["_tradeables"]),
            "robuxPrice": avg_int(it["_robuxPrices"]),
        }
        out.append(final)

    return out

# -------------------- fruits merge --------------------

def merge_fruits_with_averages(fruits_bfv, fruits_fruity, fruits_info, bfv_skins):
    # simple alias map (extend as needed)
    alias = {
        normalize_name_words("Lightning"): normalize_name_words("Rumble"),
        # normalize_name_words("Door"): normalize_name_words("Portal"),
    }

    # Build master fruit name list for resolver
    fruit_names = []
    for src in (fruits_bfv, fruits_info):
        for it in src:
            n = it.get("name")
            if not n: continue
            fruit_names.append(n)
    fruit_names = sorted(set(fruit_names), key=lambda n: -len(n))
    fruit_key_map = {normalize_name_words(n): alias.get(normalize_name_words(n), normalize_name_words(n)) for n in fruit_names}

    # Index info by canonical key
    info_index = {}
    for it in fruits_info:
        n = it.get("name")
        if not n: continue
        k = alias.get(normalize_name_words(n), normalize_name_words(n))
        info_index[k] = it

    merged = OrderedDict()

    def ensure_bucket(fkey, display_name):
        if fkey not in merged:
            merged[fkey] = {
                "_names": [display_name],
                "_regValues": [], "_permValues": [], "_robuxPrices": [],
                "_tradeables": [],
                "_rarity_first": None, "_regTrend_first": None, "_beliPrice_first": None,
                "_fruitType_first": None, "_permTrend_first": None,
                "_awakening_first": None, "_awakening_total_fallback": 0,
                "_upgrading": [],
                "_skins_map": {},          # skey -> per-skin aggregator
                "_bfv_skin_keys": set(),   # for mismatch report
                "_info_skin_keys": set(),
                "_info_type": None,
            }
        else:
            merged[fkey]["_names"].append(display_name)

    # ---------- PASS 0: BFV SKINS FILE ----------

    def resolve_skin_affiliation(sname: str, fruit_names):
        """Try to split a BFV-skins entry into (fruit_display_name, skin_display_name)."""
        if not sname:
            return None, None
        raw_words = sname.split()
        w = words(sname)

        # try longest fruit name first
        fruits = [(fname, words(fname)) for fname in fruit_names]
        fruits.sort(key=lambda x: -len(x[1]))

        # suffix / prefix match
        for fname, fw in fruits:
            if len(fw) <= len(w) and w[-len(fw):] == fw:
                skin_part = raw_words[:-len(fw)]
                return fname, (" ".join(skin_part).strip() or sname)
            if len(fw) <= len(w) and w[:len(fw)] == fw:
                skin_part = raw_words[len(fw):]
                return fname, (" ".join(skin_part).strip() or sname)

        # ordered subsequence anywhere
        def find_subseq_positions(big, small):
            i = 0; pos = []
            for token in big:
                if i < len(small) and token == small[i]:
                    pos.append(True); i += 1
                else:
                    pos.append(False)
            return (i == len(small)), pos

        for fname, fw in fruits:
            ok, pos = find_subseq_positions(w, fw)
            if not ok: continue
            # remove first-occurring fruit tokens
            rem = []
            j = 0
            for tok, keep in zip(raw_words, pos):
                if keep:
                    j += 1  # skip
                else:
                    rem.append(tok)
            skin_disp = " ".join(rem).strip() or sname
            return fname, skin_disp

        return None, None

    # quick reverse map: skin name (info) -> fruit fkey
    info_skin_to_fruit = {}
    for f_it in fruits_info:
        fkey = alias.get(normalize_name_words(f_it.get("name", "")), normalize_name_words(f_it.get("name", "")))
        for s in (f_it.get("skins") or []):
            sname = s.get("name")
            if not sname: continue
            info_skin_to_fruit[normalize_name_words(sname)] = fkey

    # Track which BFV skin names we actually resolved (either directly or via info fallback)
    resolved_bfv_skin_names = set()

    for s in (bfv_skins or []):
        s_disp = s.get("name")
        if not s_disp: continue

        fruit_disp, skin_disp = resolve_skin_affiliation(s_disp, fruit_names)
        fkey = None

        if not fruit_disp:
            # fallback using info skins like "Parrot", "Eclipse"
            inferred_fkey = info_skin_to_fruit.get(normalize_name_words(s_disp))
            if inferred_fkey:
                fkey = inferred_fkey
                # pick a representative display for that key (prefer exact in fruit_names)
                fruit_disp = next((n for n in fruit_names if alias.get(normalize_name_words(n), normalize_name_words(n)) == fkey), None) or "Unknown"
                skin_disp = s_disp
                resolved_bfv_skin_names.add(s_disp)
            else:
                # cannot resolve at all; leave for report later
                continue
        else:
            fkey = alias.get(normalize_name_words(fruit_disp), normalize_name_words(fruit_disp))
            resolved_bfv_skin_names.add(s_disp)

        ensure_bucket(fkey, fruit_disp)
        b = merged[fkey]

        skey = normalize_name_words(skin_disp)
        agg = b["_skins_map"].setdefault(skey, {
            "_names": [skin_disp],
            "_rarity_first": None,
            "_obtainment": None,
            "_image": None,
            "_ingame_image": None,
            "_regValues": [], "_regTrends": [],
            "_robuxPrices": [], "_tradeables": [],
        })
        if skin_disp not in agg["_names"]:
            agg["_names"].append(skin_disp)

        # collect numeric/trend/tradeable from BFV skins file
        if (v := s.get("regValue")) is not None:     agg["_regValues"].append(to_int_loose(v))
        if (v := s.get("robuxPrice")) is not None:   agg["_robuxPrices"].append(to_int_loose(v))
        if "tradeable" in s:                          agg["_tradeables"].append(bool(s["tradeable"]))
        if (v := s.get("regTrend")):                  agg["_regTrends"].append(v)

        b["_bfv_skin_keys"].add(skey)

    # build unresolved list correctly (mirror fallback, not raw resolver-only)
    unresolved_bfv_skins = []
    for s in (bfv_skins or []):
        s_disp = s.get("name")
        if not s_disp: continue
        if s_disp in resolved_bfv_skin_names:
            continue
        fruit_disp, skin_disp = resolve_skin_affiliation(s_disp, fruit_names)
        if fruit_disp is None:
            # also check info fallback one more time
            if info_skin_to_fruit.get(normalize_name_words(s_disp)) is None:
                unresolved_bfv_skins.append(s_disp)

    # ---------- PASS 1: BFV FRUITS ----------
    for g in fruits_bfv:
        name = g.get("name")
        if not name: continue
        fkey = alias.get(normalize_name_words(name), normalize_name_words(name))
        ensure_bucket(fkey, name)
        b = merged[fkey]

        for fld, bucket in [("regValue","_regValues"), ("permValue","_permValues"), ("robuxPrice","_robuxPrices")]:
            v = g.get(fld)
            if v is not None: b[bucket].append(to_int_loose(v))
        b["_tradeables"].append(bool(g.get("tradeable", False)))

        if b["_rarity_first"] is None and g.get("rarity"): b["_rarity_first"] = g["rarity"]
        if b["_regTrend_first"] is None and g.get("regTrend"): b["_regTrend_first"] = g["regTrend"]
        if b["_beliPrice_first"] is None and g.get("beliPrice") is not None: b["_beliPrice_first"] = to_int_loose(g["beliPrice"])
        if b["_fruitType_first"] is None and g.get("fruitType"): b["_fruitType_first"] = g["fruitType"]
        if b["_permTrend_first"] is None and g.get("permTrend"): b["_permTrend_first"] = g["permTrend"]

        ap = g.get("awakeningPrice")
        if b["_awakening_first"] is None and isinstance(ap, dict):
            b["_awakening_first"] = {k: to_int_loose(ap.get(k)) for k in ("z","x","c","v","f")}

        # embedded BFV skins under fruit (if any)
        for s in (g.get("skins") or []):
            if not isinstance(s, dict): continue
            sname = s.get("name"); 
            if not sname: continue
            skey = normalize_name_words(sname)
            agg = b["_skins_map"].setdefault(skey, {
                "_names": [sname],
                "_rarity_first": None,
                "_obtainment": None,
                "_image": None,
                "_ingame_image": None,
                "_regValues": [], "_regTrends": [],
                "_robuxPrices": [], "_tradeables": [],
            })
            if sname not in agg["_names"]: agg["_names"].append(sname)
            if agg["_rarity_first"] is None and s.get("rarity"): agg["_rarity_first"] = s["rarity"]
            if agg["_obtainment"] is None and s.get("obtainment"): agg["_obtainment"] = s["obtainment"]
            if agg["_image"] is None and "image" in s: agg["_image"] = s.get("image")
            if agg["_ingame_image"] is None and "ingame_image" in s: agg["_ingame_image"] = s.get("ingame_image")
            if (v := s.get("regValue")) is not None:   agg["_regValues"].append(to_int_loose(v))
            if (v := s.get("robuxPrice")) is not None: agg["_robuxPrices"].append(to_int_loose(v))
            if "tradeable" in s:                        agg["_tradeables"].append(bool(s["tradeable"]))
            if (v := s.get("regTrend")):                agg["_regTrends"].append(v)
            b["_bfv_skin_keys"].add(skey)

    # ---------- PASS 2: FRUITY (numerics) ----------
    for g in fruits_fruity:
        name = g.get("name")
        if not name: continue
        fkey = alias.get(normalize_name_words(name), normalize_name_words(name))
        ensure_bucket(fkey, name)
        b = merged[fkey]
        if (v := g.get("regValueNumeric")) is not None: b["_regValues"].append(to_int_loose(v))
        if (v := g.get("permValueNumeric")) is not None: b["_permValues"].append(to_int_loose(v))
        if (v := g.get("robuxPrice")) is not None:       b["_robuxPrices"].append(to_int_loose(v))

    # ---------- PASS 3: INFO (type & enrich) ----------
    for fkey, b in merged.items():
        inf = info_index.get(fkey)
        if not inf: continue
        b["_info_type"] = inf.get("type") or b["_info_type"]
        if (v := inf.get("robux_price")) is not None: b["_robuxPrices"].append(to_int_loose(v))
        if b["_beliPrice_first"] is None and (v := inf.get("price")) is not None: b["_beliPrice_first"] = to_int_loose(v)
        if b["_rarity_first"] is None and inf.get("rarity"): b["_rarity_first"] = inf["rarity"]
        b["_upgrading"] = inf.get("upgrading", []) or []
        if (v := inf.get("awakening")) and to_int_loose(v) > 0: b["_awakening_total_fallback"] = to_int_loose(v)

        info_skins = inf.get("skins") or []
        for s in info_skins:
            if not isinstance(s, dict): continue
            sname = s.get("name"); 
            if not sname: continue
            skey = normalize_name_words(sname)
            b["_info_skin_keys"].add(skey)
            agg = b["_skins_map"].setdefault(skey, {
                "_names": [sname],
                "_rarity_first": None,
                "_obtainment": None,
                "_image": None,
                "_ingame_image": None,
                "_regValues": [], "_regTrends": [],
                "_robuxPrices": [], "_tradeables": [],
            })
            if sname not in agg["_names"]: agg["_names"].append(sname)
            # enrich (chromatic intentionally ignored)
            if agg["_rarity_first"] is None and s.get("rarity"):       agg["_rarity_first"] = s["rarity"]
            if agg["_obtainment"] is None and s.get("obtainment"):     agg["_obtainment"] = s["obtainment"]
            if agg["_image"] is None and "image" in s:                  agg["_image"] = s.get("image")
            if agg["_ingame_image"] is None and "ingame_image" in s:    agg["_ingame_image"] = s.get("ingame_image")
            # optional numerics in info skins
            if (v := s.get("regValue")) is not None:   agg["_regValues"].append(to_int_loose(v))
            if (v := s.get("robuxPrice")) is not None: agg["_robuxPrices"].append(to_int_loose(v))
            if "tradeable" in s:                        agg["_tradeables"].append(bool(s["tradeable"]))
            if (v := s.get("regTrend")):                agg["_regTrends"].append(v)
            # infer from obtainment text
            obt = (s.get("obtainment") or "")
            if "trading" in obt.lower(): agg["_tradeables"].append(True)
            m = re.search(r'(\d+)\s*robux', obt, flags=re.I)
            if m:
                try: agg["_robuxPrices"].append(int(m.group(1)))
                except: pass

    # --- Special handling: move Dragon skins to East/West and remove Dragon entirely ---
    dragon_key = normalize_name_words("Dragon")
    east_key   = normalize_name_words("East Dragon")
    west_key   = normalize_name_words("West Dragon")

    if dragon_key in merged:
        d = merged[dragon_key]

        # helper to merge one skin aggregator into a target bucket
        def _merge_skin_agg_into_bucket(target_bucket, skey, agg):
            tskins = target_bucket["_skins_map"]
            tagg = tskins.setdefault(skey, {
                "_names": [],
                "_rarity_first": None,
                "_obtainment": None,
                "_image": None,
                "_ingame_image": None,
                "_regValues": [], "_regTrends": [],
                "_robuxPrices": [], "_tradeables": [],
            })
            for nm in (agg.get("_names") or []):
                if nm not in tagg["_names"]:
                    tagg["_names"].append(nm)
            if tagg["_rarity_first"] is None and agg.get("_rarity_first"):
                tagg["_rarity_first"] = agg["_rarity_first"]
            if tagg["_obtainment"] is None and agg.get("_obtainment"):
                tagg["_obtainment"] = agg["_obtainment"]
            if tagg["_image"] is None and ("_image" in agg):
                tagg["_image"] = agg.get("_image")
            if tagg["_ingame_image"] is None and ("_ingame_image" in agg):
                tagg["_ingame_image"] = agg.get("_ingame_image")
            tagg["_regValues"].extend(agg.get("_regValues") or [])
            tagg["_regTrends"].extend(agg.get("_regTrends") or [])
            tagg["_robuxPrices"].extend(agg.get("_robuxPrices") or [])
            tagg["_tradeables"].extend(agg.get("_tradeables") or [])
            # mark as present in both to avoid unmatched-only_in_info after copying
            target_bucket["_info_skin_keys"].add(skey)
            target_bucket["_bfv_skin_keys"].add(skey)

        # ensure East/West buckets exist
        ensure_bucket(east_key, "East Dragon")
        ensure_bucket(west_key, "West Dragon")

        # copy every Dragon skin to both East and West
        for skey, agg in (d.get("_skins_map") or {}).items():
            _merge_skin_agg_into_bucket(merged[east_key], skey, agg)
            _merge_skin_agg_into_bucket(merged[west_key], skey, agg)

        # drop Dragon fruit entirely
        del merged[dragon_key]

    # --- Dragon family bridging (unify skin-key sets across Dragon/East/West) ---
    fam_norm = [normalize_name_words(n) for n in ["Dragon", "East Dragon", "West Dragon"]]
    fam_keys = [k for k in merged.keys() if normalize_name_words(merged[k]["_names"][0]) in fam_norm]
    if fam_keys:
        union_info = set(); union_bfv = set()
        for fk in fam_keys:
            union_info |= merged[fk]["_info_skin_keys"]
            union_bfv  |= merged[fk]["_bfv_skin_keys"]
        for fk in fam_keys:
            merged[fk]["_info_skin_keys"] |= union_info
            merged[fk]["_bfv_skin_keys"]  |= union_bfv

    # ---------- FINALIZE + REPORT ----------
    out, unmatched_report = [], []

    for fkey, b in merged.items():
        display_name = b["_names"][0]
        for cand in b["_names"][1:]:
            display_name = choose_better_name(display_name, cand)

        aw = b["_awakening_first"] or {"z":0,"x":0,"c":0,"v":0,"f":0}
        total = sum(aw.values()) or b["_awakening_total_fallback"]
        awakening = dict(aw); awakening["total"] = total

        fruit_reg_value = avg_int(b["_regValues"])
        fruit_reg_trend = b["_regTrend_first"] or ""
        fruit_robux = avg_int(b["_robuxPrices"])

        skins = []
        for skey, agg in b["_skins_map"].items():
            sname = agg["_names"][0]
            for cand in agg["_names"][1:]:
                sname = choose_better_name(sname, cand)

            obtained = agg["_obtainment"] or ""
            skin_reg_value = avg_int(agg["_regValues"]) or fruit_reg_value
            skin_reg_trend = most_frequent_nonempty(agg["_regTrends"]) or fruit_reg_trend
            skin_tradeable = any(agg["_tradeables"]) or ("trading" in obtained.lower())
            skin_robux = avg_int(agg["_robuxPrices"])
            if skin_robux == 0:
                m = re.search(r'(\d+)\s*robux', obtained, flags=re.I)
                if m:
                    try: skin_robux = int(m.group(1))
                    except: pass
            if skin_robux == 0:
                skin_robux = fruit_robux

            skins.append({
                "name": sname,
                "rarity": agg["_rarity_first"] or "",
                "image": agg["_image"] if agg["_image"] is not None else "",
                "ingame_image": agg["_ingame_image"] if agg["_ingame_image"] is not None else "",
                "obtainment": obtained,
                "regTrend": skin_reg_trend,
                "regValue": skin_reg_value,
                "tradeable": skin_tradeable,
                "robuxPrice": skin_robux,
            })

        # unmatched (ignore anything that exists in final output)
        def _pretty_from_key(k: str) -> str:
            toks = re.findall(r'[a-z]+', k)
            return " ".join(t.title() for t in toks) if toks else k

        def _skin_name_or_key(bkt, k):
            agg = bkt["_skins_map"].get(k)
            if agg and agg.get("_names"):
                return agg["_names"][0]
            return _pretty_from_key(k)

        present_keys = set(b["_skins_map"].keys())
        only_bfv  = sorted(_skin_name_or_key(b, k) for k in (b["_bfv_skin_keys"] - (b["_info_skin_keys"] | present_keys)))
        only_info = sorted(_skin_name_or_key(b, k) for k in (b["_info_skin_keys"] - (b["_bfv_skin_keys"] | present_keys)))

        if only_bfv or only_info:
            unmatched_report.append(f"- {display_name}: only_in_bfv={only_bfv or []}, only_in_info={only_info or []}")

        # NOTE: presence mismatch report (useful for data fixes)
        only_bfv  = sorted(_skin_name_or_key(b, k) for k in (b["_bfv_skin_keys"] - b["_info_skin_keys"]))
        only_info = sorted(_skin_name_or_key(b, k) for k in (b["_info_skin_keys"] - b["_bfv_skin_keys"]))
        if only_bfv or only_info:
            unmatched_report.append(f"- {display_name}: only_in_bfv={only_bfv or []}, only_in_info={only_info or []}")

        out.append({
            "name": display_name,
            "regValue": fruit_reg_value,
            "permValue": avg_int(b["_permValues"]),
            "rarity": b["_rarity_first"] or "",
            "regTrend": fruit_reg_trend,
            "beliPrice": b["_beliPrice_first"] or 0,
            "fruitType": b["_info_type"] or b["_fruitType_first"] or "",
            "permTrend": b["_permTrend_first"] or "",
            "tradeable": any(b["_tradeables"]),
            "robuxPrice": fruit_robux,
            "image": "",
            "awakening": awakening,
            "upgrading": b["_upgrading"],
            "skins": skins,
        })

    if unmatched_report:
        print("UNMATCHED SKINS (by fruit):")
        for line in unmatched_report:
            print(line)
    if any(True for _ in unresolved_bfv_skins):
        print("STILL_UNRESOLVED_BFV_SKINS:")
        for nm in sorted(set(unresolved_bfv_skins)):
            print(" -", nm)

    return out

# -------------------- caching --------------------

def ready_cache():
  with open("storage/data_fruity_fruits.json", "w", encoding="utf-8") as f:
    for fruit in data_fruity_fruits:
      fruit["regValueNumeric"] = fruit["values"][0]["numeric"]
      fruit["permValueNumeric"] = fruit["values"][1]["numeric"]
      fruit["regValueRaw"] = fruit["values"][0]["raw"]
      fruit["permValueRaw"] = fruit["values"][1]["raw"]
      fruit.pop("values")
    json.dump(data_fruity_fruits, f, indent=2, ensure_ascii=False)
    
  with open("storage/data_fruity_gamepasses.json", "w", encoding="utf-8") as f:
    for gamepass in data_fruity_gamepasses:
      gamepass["regValueNumeric"] = gamepass["values"][0]["numeric"]
      gamepass["regValueRaw"] = gamepass["values"][0]["raw"]
      gamepass.pop("values")
    json.dump(data_fruity_gamepasses, f, indent=2, ensure_ascii=False)
    
  with open("storage/data_bfv_fruits.json", "w", encoding="utf-8") as f:
    for fruit in data_bfv_fruits:
      fruit.pop("category")
    json.dump(data_bfv_fruits, f, indent=2, ensure_ascii=False)
    
  with open("storage/data_bfv_gamepasses.json", "w", encoding="utf-8") as f:
    for gamepass in data_bfv_gamepasses:
      gamepass.pop("category")
      gamepass.pop("rarity")
      gamepass.pop("beliPrice")
      gamepass.pop("fruitType")
      gamepass.pop("permTrend")
      gamepass.pop("permValue")
    json.dump(data_bfv_gamepasses, f, indent=2, ensure_ascii=False)
    
  with open("storage/data_bfv_skins.json", "w", encoding="utf-8") as f:
    for skin in data_bfv_skins:
      skin.pop("category")
      skin.pop("rarity")
      skin.pop("beliPrice")
      skin.pop("fruitType")
      skin.pop("permTrend")
      skin.pop("permValue")
    json.dump(data_bfv_skins, f, indent=2, ensure_ascii=False)
    
  with open("storage/data_bfv_specials.json", "w", encoding="utf-8") as f:
    for special in data_bfv_specials:
      special.pop("category")
      special.pop("rarity")
      special.pop("beliPrice")
      special.pop("fruitType")
      special.pop("permTrend")
      special.pop("permValue")
      special.pop("robuxPrice")
    json.dump(data_bfv_specials, f, indent=2, ensure_ascii=False)

# -------------------- main entry --------------------

def get_all():
  # refresh endpoints to update cache
  requests.get("http://localhost:5000/fruits").json()
  requests.get("http://localhost:5000/stock").json()
  requests.get("http://localhost:5000/info").json()
  ready_cache()
  with open("storage/all.json", "w", encoding="utf-8") as f_all, \
     open("storage/data_fruity_gamepasses.json", "r", encoding="utf-8") as f_fruity_gp, \
     open("storage/data_bfv_gamepasses.json", "r", encoding="utf-8") as f_bfv_gp, \
     open("storage/data_fruity_fruits.json", "r", encoding="utf-8") as f_fruity_fr, \
     open("storage/data_bfv_fruits.json", "r", encoding="utf-8") as f_bfv_fr, \
     open("storage/info.json", "r", encoding="utf-8") as f_info, \
     open("storage/data_bfv_skins.json", "r", encoding="utf-8") as f_bfv_skins:

    gamepasses_from_fruity = json.load(f_fruity_gp)
    gamepasses_from_bfv = json.load(f_bfv_gp)
    fruits_from_fruity = json.load(f_fruity_fr)
    fruits_from_bfv = json.load(f_bfv_fr)
    info_fruits = json.load(f_info)
    bfv_skins = json.load(f_bfv_skins)

    result["stock"] = get_stock_all()
    result["specials"] = data_bfv_specials
    result["gamepasses"] = merge_gamepasses_with_averages(gamepasses_from_fruity + gamepasses_from_bfv)
    result["fruits"] = merge_fruits_with_averages(fruits_from_bfv, fruits_from_fruity, info_fruits, bfv_skins)

    json.dump(result, f_all, indent=2, ensure_ascii=False)
    return result
