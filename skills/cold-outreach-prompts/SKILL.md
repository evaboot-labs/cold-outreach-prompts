---
name: cold-outreach-prompts
description: Write and test cold outreach with AI - eight prompts (first line, short cold email, subject lines, follow-up, break-up email, LinkedIn connection note, objection reply, referral ask) run on real leads from an Evaboot (Sales Navigator) export, every output checked for invented facts, numbers not in the data, length, questions, banned phrases and gender guesses, then scored per prompt. Use when the user wants AI prompts for cold email or LinkedIn outreach, wants to write outreach with Claude or ChatGPT, or wants to test and improve their own prompts.
---

# Cold outreach prompts, tested

This skill runs inside a clone of https://github.com/evaboot-labs/cold-outreach-prompts: it uses the repo's `prompts.py`, `prompts/`, `OFFER.md` and `docs/`. If `prompts.py` is not in the working directory, clone the repo and work from there.

`prompts.py` calls Claude and runs every check. You pick the prompts, read the results and improve the prompts.

## Rules

- **Draft only.** Nothing in this repo sends a message. The user copies what passes into their own tool.
- **Facts from the data only.** Every output lists the facts it used; `prompts.py check` rejects any it cannot find in the lead's data.
- **Change one thing at a time.** When a prompt fails, edit that prompt file, run it again on the same leads, and compare the scores.
- Never ask for or paste a key. The user writes `ANTHROPIC_API_KEY` into `.env` (`docs/connect-your-agent.md`).

## Step 1: the offer and the leads

1. Read `OFFER.md`. If it says `status: EXAMPLE`, ask what they sell, to whom, the problem, one proof and the call to action. Rewrite it and set `status: yours`.
2. Get an Evaboot export as `data/export.json`: with the Evaboot MCP server (`.mcp.json`), export a Sales Navigator search with `export_sn_search_or_list` (1 credit per lead), or ask the user for an export JSON.
3. `python3 prompts.py facts data/export.json --n 10 > queue/leads.json` keeps 10 people with a safe email.

## Step 2: run and check

```bash
python3 prompts.py run all queue/leads.json
python3 prompts.py score
```

`run` writes `queue/out-<prompt>.json` for each prompt. `score` prints one line per prompt: outputs, passed, average words and the most common failure. Show the user the score and three passing outputs of the prompt they care about.

## Step 3: fix what fails

For each prompt under 8 of 10:

1. Read the failures: `python3 prompts.py check queue/out-<prompt>.json`.
2. Edit `prompts/<n>-<prompt>.md`: one change, for example a sharper instruction or a lower limit.
3. Run that prompt again and compare.

To give the team a form that runs one prompt on one lead, set up the n8n version (`docs/n8n.md`).
