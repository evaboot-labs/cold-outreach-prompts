# Run one prompt on one lead in n8n

[`n8n/cold-outreach-prompts.json`](../n8n/cold-outreach-prompts.json) is a form your team can use without a terminal: pick a prompt, paste what you know about one lead, and get the message with its check.

## What runs

1. **One lead, one prompt** (form): the prompt and nine lead fields. First name, job title and company are required.
2. **Build the prompt**: the same prompt text, hard limits, offer and rules as `prompts.py run`.
3. **Write the message** (Claude): the text and the facts it used.
4. **Check the message**: the same rules as `prompts.py check`.
5. **Show the message**: the text, the facts used and the check, on the last page of the form.

## Set it up

1. **Edit `prompts/` and `OFFER.md` first**, then run `python3 n8n/build_workflow.py`: the prompts and the offer are copied into the workflow JSON.
2. **Import** the JSON in n8n: *Workflows > Import from file*.
3. **Add the Anthropic credential** on the Claude node.
4. **Publish** the workflow and open the form: the first node shows its production URL.

## Good to know

- The form keeps nothing: each submission is one message, and nothing is sent to the lead.
- Paste facts exactly as they appear in the profile or the Evaboot export. The check looks for each fact the model used in what you pasted.

Back to the [README](../README.md).
