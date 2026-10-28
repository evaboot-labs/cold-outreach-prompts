# Connect your agent by hand

The prompt in the README does all of this for you. These are the same steps, for when you want to do them yourself.

1. **Get the repo:**
   ```bash
   git clone https://github.com/evaboot-labs/cold-outreach-prompts.git
   cd cold-outreach-prompts
   ```
2. **Add your Anthropic key** from [console.anthropic.com](https://console.anthropic.com/). Then:
   ```bash
   cp .env.example .env          # paste the key
   ```
   To use another Claude model, set `CLAUDE_MODEL` in your shell.
3. **Get your leads.** Create your [Evaboot account](https://dash.evaboot.com/accounts/signup/?last_click_origin=cold-outreach-prompts-repo), export a Sales Navigator search, and save the export JSON as `data/export.json`. The repo's `.mcp.json` connects the Evaboot MCP server (`https://mcp.evaboot.com/mcp`, it reads `EVABOOT_API_KEY`), so your agent can do it for you.
4. **Write your offer** in [`OFFER.md`](../OFFER.md), or let your agent ask you.
5. **Check** (Python 3.9+, no packages to install): `python3 prompts.py -h` lists the commands.

Then ask your agent: **"Test the cold outreach prompts on my Evaboot export."**

Back to the [README](../README.md).
