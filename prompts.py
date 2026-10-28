"""Cold outreach prompts, tested on real leads: every output checked against the lead's own data.

    python3 prompts.py facts data/export.json --n 10 > queue/leads.json
        one row per person with a safe email, from an Evaboot export
    python3 prompts.py run <prompt-id|all> queue/leads.json
        runs the prompt (prompts/*.md) on every lead with Claude; writes queue/out-<id>.json
    python3 prompts.py check queue/out-<id>.json
        every output: facts it claims are in the lead's data, length, questions, banned phrases
    python3 prompts.py score
        one line per prompt: outputs, passed, average words, most common failure

Needs ANTHROPIC_API_KEY in the environment or in .env for `run` only. Python 3.9+, no packages.
"""
import argparse
import glob
import json
import os
import re
import sys
import urllib.error
import urllib.request
from collections import Counter

MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5-5")
FIELDS = {"First Name": "first_name", "Current Job": "title", "Company Name": "company",
          "Company Industry": "industry", "Company Employee Range": "company_size",
          "Months in Position": "months_in_role", "Company Employee Growth 1 Year (%)": "company_growth_1y_pct",
          "Profile Headline": "headline", "Company Description": "company_description", "Location": "location"}
BANNED = ["hope this email finds you", "hope you're well", "just following up", "following up on", "bumping this",
          "circle back", "touch base", "quick question", "game-changer", "game changer", "revolutionize",
          "revolutionise", "synergy", "leverage", "cutting-edge", "best-in-class", "i wanted to reach out",
          "free", "guarantee", "100%", "act now", "limited time"]
GENDERED = re.compile(r"\b(he|she|him|her|his|hers)\b", re.I)
RULES = """Use ONLY the facts in the lead JSON and the offer. Never invent a number, a news item, a customer, a tool they use or anything you cannot see in the data. Never guess anyone's gender: use the first name, "you" or the role. Write in plain English, no emoji.

Return ONLY a JSON object: {"text": "<the message>", "facts_used": ["<the value of each fact from the lead JSON you used, copied exactly, without its key>"]}"""


def env(name):
    if os.environ.get(name):
        return os.environ[name]
    if os.path.exists(".env"):
        m = re.search(rf"^{name}=(.*)$", open(".env").read(), re.M)
        if m and m.group(1).strip():
            return m.group(1).strip().strip("'\"")
    sys.exit(f"{name} is missing: add it to .env")


def offer():
    return dict(re.findall(r"^([a-z_]+):\s*(.+)$", open("OFFER.md").read(), re.M))


def prompt(pid):
    for path in sorted(glob.glob("prompts/*.md")):
        head, body = open(path).read().split("---\n")[1:3]
        meta = dict(re.findall(r"^([a-z_]+):\s*(.+)$", head, re.M))
        if meta["id"] == pid:
            meta["text"] = body.strip()
            return meta
    sys.exit(f"no prompt with id {pid}: see prompts/")


def all_ids():
    return [prompt_meta for prompt_meta in (dict(re.findall(r"^([a-z_]+):\s*(.+)$", open(p).read().split("---\n")[1], re.M))["id"]
                                            for p in sorted(glob.glob("prompts/*.md")))]


def facts(path, n):
    out = []
    for p in json.load(open(path)).get("prospects") or []:
        if (p.get("Email Status") or "").lower() != "safe":
            continue
        lead = {k2: " ".join(str(p.get(k) or "").split())[:300] for k, k2 in FIELDS.items()}
        lead["id"] = p.get("Linkedin URL Unique ID") or ""
        out.append(lead)
        if len(out) >= n:
            break
    print(f"{len(out)} leads with a safe email", file=sys.stderr)
    return out


def claude(system, user):
    body = {"model": MODEL, "max_tokens": 2000, "system": system, "messages": [{"role": "user", "content": user}]}
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=json.dumps(body).encode(),
                                 headers={"x-api-key": env("ANTHROPIC_API_KEY"), "anthropic-version": "2023-06-01",
                                          "content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            d = json.loads(r.read())
    except urllib.error.HTTPError as e:
        sys.exit(f"Claude call failed ({e.code}): {e.read()[:200]}")
    text = "".join(c.get("text", "") for c in d["content"] if c["type"] == "text")
    start = text.find("{")
    try:
        return json.JSONDecoder().raw_decode(text[start:])[0] if start >= 0 else {"text": text, "facts_used": []}
    except json.JSONDecodeError:
        return {"text": text, "facts_used": []}


def run(pid, leads_path):
    ids = all_ids() if pid == "all" else [pid]
    leads, o = json.load(open(leads_path)), offer()
    for i in ids:
        p = prompt(i)
        limits = f"Hard limits: at most {p['max_words']} words" + (f" and {p['max_chars']} characters" if "max_chars" in p else "") \
            + f", at most {p['max_questions']} question mark(s). Count before you answer."
        system = f"{p['text']}\n\n{limits}\n\nThe offer:\n{json.dumps(o, indent=1)}\n\n{RULES}"
        out = []
        for lead in leads:
            facts_only = {k: v for k, v in lead.items() if k != "id" and v}
            r = claude(system, json.dumps(facts_only, ensure_ascii=False))
            out.append({"lead": lead, "prompt": i, "text": r.get("text", ""), "facts_used": r.get("facts_used", [])})
        json.dump(out, open(f"queue/out-{i}.json", "w"), indent=1, ensure_ascii=False)
        print(f"{i}: {len(out)} outputs -> queue/out-{i}.json", file=sys.stderr)


def norm(s):
    return re.sub(r"[^a-z0-9%]+", " ", str(s).lower()).strip()


def problems_for(item):
    p, lead, text = prompt(item["prompt"]), item["lead"], item["text"]
    data = norm(" ".join(str(v) for k, v in lead.items() if k != "id"))
    offer_text = norm(" ".join(offer().values()))
    out = []
    words = len(text.split())
    if words > int(p["max_words"]):
        out.append(f"{words} words, max {p['max_words']}")
    if "max_chars" in p and len(text) > int(p["max_chars"]):
        out.append(f"{len(text)} characters, max {p['max_chars']}")
    if text.count("?") > int(p["max_questions"]):
        out.append(f"{text.count('?')} questions, max {p['max_questions']}")
    low = text.lower()
    for b in BANNED:
        if re.search(rf"(?<![a-z]){re.escape(b)}(?![a-z])", low):
            out.append(f"banned phrase: {b}")
    if GENDERED.search(text):
        out.append("guesses a gender")
    used = item.get("facts_used") or []
    if len(used) < int(p.get("min_facts", 1)):
        out.append("uses no fact from the lead's data")
    for f in used:
        f = re.sub(r'^\W*[a-z_0-9]+\W*:\s*', "", str(f)).strip(' "')  # "title": "VP Sales" -> VP Sales
        if norm(f) and norm(f) not in data and norm(f) not in offer_text:
            out.append(f"claims a fact that is not in the data: {str(f)[:60]}")
    for num in re.findall(r"\d[\d,.]*%?", text):
        n = norm(num).replace(" ", "").rstrip("%")  # growth is stored as "15", written as "15%"
        if n and n not in data.replace(" ", "") and n not in offer_text.replace(" ", ""):
            out.append(f"number not in the data or the offer: {num}")
    return out


def check(path):
    items, failed = json.load(open(path)), 0
    for it in items:
        probs = problems_for(it)
        if probs:
            failed += 1
            print(f"FAIL {it['lead'].get('company')}: " + "; ".join(probs))
    print(f"{len(items) - failed} of {len(items)} passed")
    return failed


def score():
    rows = []
    for path in sorted(glob.glob("queue/out-*.json")):
        items = json.load(open(path))
        fails = [p for it in items for p in problems_for(it)]
        passed = sum(not problems_for(it) for it in items)
        avg = round(sum(len(it["text"].split()) for it in items) / len(items)) if items else 0
        top = Counter(re.sub(r":.*|\d+ ", "", f).strip() for f in fails).most_common(1)
        rows.append((items[0]["prompt"] if items else path, len(items), passed, avg, top[0][0] if top else "-"))
    print(f"{'prompt':18}{'outputs':>8}{'passed':>8}{'words':>7}  most common failure")
    for r in rows:
        print(f"{r[0]:18}{r[1]:>8}{r[2]:>8}{r[3]:>7}  {r[4]}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("facts")
    f.add_argument("export")
    f.add_argument("--n", type=int, default=10)
    r = sub.add_parser("run")
    r.add_argument("prompt")
    r.add_argument("leads")
    sub.add_parser("check").add_argument("out")
    sub.add_parser("score")
    a = ap.parse_args()
    if a.cmd == "facts":
        json.dump(facts(a.export, a.n), sys.stdout, indent=1, ensure_ascii=False); print()
    elif a.cmd == "run":
        run(a.prompt, a.leads)
    elif a.cmd == "check":
        sys.exit(1 if check(a.out) else 0)
    else:
        score()


if __name__ == "__main__":
    main()
