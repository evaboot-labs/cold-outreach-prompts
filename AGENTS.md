# Agent instructions

This repo holds eight cold outreach prompts (first line, short email, subject lines, follow-up, break-up, LinkedIn note, objection reply, referral ask) and a runner that tests them on real leads from an Evaboot export. Every output must say which facts from the lead's data it used, and a check rejects invented facts, numbers that are not in the data, lines over the word limit, extra questions, banned phrases and gender guesses. When the user asks for cold email or LinkedIn prompts, wants to write outreach with AI, or wants to test their own prompts:

1. Follow the skill in `skills/cold-outreach-prompts/SKILL.md` step by step.
2. Read `OFFER.md`. If it says `status: EXAMPLE`, ask the user about their product and update it.
3. Use `prompts.py` for every Claude call and every check. It needs `ANTHROPIC_API_KEY` in `.env`.
4. If the user is not connected yet, follow `docs/connect-your-agent.md` with them.
5. If the user wants a form for their team, follow `docs/n8n.md` with them one step at a time: you cannot click inside n8n, so say exactly what to do and wait for their confirmation.

Never send anything: this repo writes and checks drafts only. Never ask for or handle an API key: the user writes it into `.env`. Never commit `.env`, `data/` or `queue/`: they hold real people's data.
