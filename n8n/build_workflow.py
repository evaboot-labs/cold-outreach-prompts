"""Builds n8n/cold-outreach-prompts.json. Run: python3 n8n/build_workflow.py

A form takes one prompt and one lead's facts. Claude writes the message with the same prompt, limits and
rules as prompts.py run; the same checks as prompts.py check run on it; the last page shows both. The
prompts and OFFER.md are copied into the workflow when you build it, so edit them first.
"""
import glob
import json
import re
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ANTHROPIC_CRED = {"anthropicApi": {"id": "", "name": "Anthropic"}}
MODEL = "claude-sonnet-5-5"
FORM = "One lead, one prompt"
LEAD_FIELDS = [("First name", "first_name"), ("Job title", "title"), ("Company", "company"),
               ("Industry", "industry"), ("Company size", "company_size"), ("Months in role", "months_in_role"),
               ("Company growth in 1 year (%)", "company_growth_1y_pct"), ("Headline", "headline"),
               ("Company description", "company_description")]

PROMPTS = []
for path in sorted(glob.glob(str(ROOT / "prompts/*.md"))):
    head, body = open(path).read().split("---\n")[1:3]
    meta = dict(re.findall(r"^([a-z_]+):\s*(.+)$", head, re.M))
    meta["text"] = body.strip()
    PROMPTS.append(meta)
OFFER = dict(re.findall(r"^([a-z_]+):\s*(.+)$", open(ROOT / "OFFER.md").read(), re.M))
OFFER.pop("status", None)
RULES = re.search(r'RULES = """(.*?)"""', open(ROOT / "prompts.py").read(), re.S).group(1)
BANNED = json.loads("[" + re.search(r"BANNED = \[(.*?)\]", open(ROOT / "prompts.py").read(), re.S).group(1)
                    .replace("\n", " ") + "]")

nodes, connections = [], {}


def node(name, type_, version, params, pos, creds=None, **extra):
    n = {"parameters": params, "id": str(uuid.uuid4()), "name": name, "type": type_,
         "typeVersion": version, "position": pos, **extra}
    if creds:
        n["credentials"] = creds
    nodes.append(n)


def link(a, b, kind="main"):
    connections.setdefault(a, {}).setdefault(kind, [[]])[0].append({"node": b, "type": kind, "index": 0})


BUILD_JS = r"""
// Same as prompts.py run: the prompt, its hard limits, the offer and the rules.
const PROMPTS = %s, OFFER = %s, RULES = %s, FIELDS = %s;
const f = $('%s').first().json;
const p = PROMPTS.find(x => x.name === f['Prompt']);
const lead = {};
for (const [label, key] of FIELDS) if (String(f[label] ?? '').trim()) lead[key] = String(f[label]).trim();
const limits = `Hard limits: at most ${p.max_words} words` + (p.max_chars ? ` and ${p.max_chars} characters` : '') + `, at most ${p.max_questions} question mark(s). Count before you answer.`;
return [{ json: { prompt: p, lead, system: `${p.text}\n\n${limits}\n\nThe offer:\n${JSON.stringify(OFFER, null, 1)}\n\n${RULES}`, user: JSON.stringify(lead) } }];
""" % (json.dumps(PROMPTS), json.dumps(OFFER), json.dumps(RULES), json.dumps(LEAD_FIELDS), FORM)

CHECK_JS = r"""
// Same as prompts.py check.
const BANNED = %s;
const { prompt: p, lead } = $('Build the prompt').first().json;
const out = $json.output || {};
const text = String(out.text || ''), used = out.facts_used || [];
const norm = s => String(s).toLowerCase().replace(/[^a-z0-9%%]+/g, ' ').trim();
const data = norm(Object.values(lead).join(' ')), offer = norm(%s);
const problems = [];
const words = text.split(/\s+/).filter(Boolean).length;
if (words > +p.max_words) problems.push(`${words} words, max ${p.max_words}`);
if (p.max_chars && text.length > +p.max_chars) problems.push(`${text.length} characters, max ${p.max_chars}`);
const q = (text.match(/\?/g) || []).length;
if (q > +p.max_questions) problems.push(`${q} questions, max ${p.max_questions}`);
for (const b of BANNED) if (new RegExp('(?<![a-z])' + b.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '(?![a-z])').test(text.toLowerCase())) problems.push('banned phrase: ' + b);
if (/\b(he|she|him|her|his|hers)\b/i.test(text)) problems.push('guesses a gender');
if (used.length < +(p.min_facts ?? 1)) problems.push("uses no fact from the lead's data");
for (let fact of used) { fact = String(fact).replace(/^\W*[a-z_0-9]+\W*:\s*/, '').replace(/^"|"$/g, '');
  if (norm(fact) && !data.includes(norm(fact)) && !offer.includes(norm(fact))) problems.push('claims a fact that is not in the data: ' + fact.slice(0, 60)); }
for (const num of text.match(/\d[\d,.]*%%?/g) || []) { const n = norm(num).replace(/ /g, '').replace(/%%$/, '');
  if (n && !data.replace(/ /g, '').includes(n) && !offer.replace(/ /g, '').includes(n)) problems.push('number not in the data or the offer: ' + num); }
return [{ json: { prompt: p.name, text, facts_used: used.join(' | '), check: problems.length ? 'FAIL: ' + problems.join('; ') : 'OK' } }];
""" % (json.dumps(BANNED), json.dumps(" ".join(OFFER.values())))

node(FORM, "n8n-nodes-base.formTrigger", 2.2, {
    "formTitle": "Cold outreach prompt, tested",
    "formDescription": "Pick a prompt and paste what you know about one lead, from an Evaboot export or the profile. Claude writes it; the check says if it used only these facts.",
    "formFields": {"values": [
        {"fieldLabel": "Prompt", "fieldType": "dropdown", "requiredField": True,
         "fieldOptions": {"values": [{"option": p["name"]} for p in PROMPTS]}}] + [
        {"fieldLabel": label, "fieldType": "textarea" if key in ("headline", "company_description") else "text",
         "requiredField": key in ("first_name", "title", "company")} for label, key in LEAD_FIELDS]},
    "responseMode": "lastNode", "options": {},
}, [0, 0], webhookId=str(uuid.uuid4()))
node("Build the prompt", "n8n-nodes-base.code", 2, {"jsCode": BUILD_JS}, [220, 0])
node("Write the message", "@n8n/n8n-nodes-langchain.agent", 2.2, {
    "promptType": "define", "hasOutputParser": True, "text": "={{ $json.user }}",
    "options": {"systemMessage": "={{ $json.system }}", "maxIterations": 3},
}, [440, 0], retryOnFail=True, maxTries=3, waitBetweenTries=2000)
node("Claude", "@n8n/n8n-nodes-langchain.lmChatAnthropic", 1.3, {
    "model": {"__rl": True, "mode": "list", "value": MODEL, "cachedResultName": MODEL},
    "options": {"maxTokensToSample": 2000},
}, [400, 220], ANTHROPIC_CRED)
node("Message", "@n8n/n8n-nodes-langchain.outputParserStructured", 1.3, {
    "schemaType": "manual",
    "inputSchema": json.dumps({"type": "object", "required": ["text", "facts_used"], "properties": {
        "text": {"type": "string"}, "facts_used": {"type": "array", "items": {"type": "string"}}}}, indent=2),
}, [560, 220])
node("Check the message", "n8n-nodes-base.code", 2, {"jsCode": CHECK_JS}, [720, 0])
node("Show the message", "n8n-nodes-base.form", 2.3, {
    "operation": "completion", "completionTitle": "={{ $json.prompt }}",
    "completionMessage": "={{ $json.text }}\n\nFacts used: {{ $json.facts_used }}\n\nCheck: {{ $json.check }}",
    "options": {},
}, [940, 0])

for a, b in [(FORM, "Build the prompt"), ("Build the prompt", "Write the message"),
             ("Write the message", "Check the message"), ("Check the message", "Show the message")]:
    link(a, b)
link("Claude", "Write the message", "ai_languageModel")
link("Message", "Write the message", "ai_outputParser")

workflow = {"name": "Cold outreach prompts, tested (Claude)", "nodes": nodes, "connections": connections,
            "settings": {"executionOrder": "v1"}, "pinData": {}}
out = Path(__file__).with_name("cold-outreach-prompts.json")
out.write_text(json.dumps(workflow, indent=2, ensure_ascii=False) + "\n")
print(out, len(nodes), "nodes")
