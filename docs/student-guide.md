# Student Guide

Welcome to **Intro to AI Red Teaming Through an AI Image Generation CTF**. Everything you need runs
in your browser. This page is your handout.

## The big idea

You're attacking an **AI image-generation application** — not just a model. The interesting bugs
live in the *app around the model*: the hidden prompt, the templates, the guardrails, the image
metadata, the tools the AI is allowed to use. Your job is to find and exploit those, then understand
how you'd *fix* them.

## Getting in

1. Open the workshop URL (on the board / your handout) in Chrome, Firefox, or Edge.
2. Enter your **access code** → you're in. No password, no signup.
3. Solve **Level 0** (free) to confirm everything works: generate any image and submit the flag
   shown in the footer.

## Flags

- Format: `bsides{lowercase_words_with_underscores}`.
- Submit on each challenge's page. Correct = points; wrong = no penalty (but don't brute force —
  you'll get rate-limited).
- Flags can be hidden in: the AI's text reply, an image's **metadata**, a watermark, an error
  message, or a tool's output. Look everywhere an app produces output.

## Your most important tool: browser DevTools

Most of this CTF is about *what the app sends to the model* and *what it sends back*.

- **Open DevTools:** `F12` (or right-click → Inspect) → **Network** tab.
- Click **Generate**, then click the `/api/generate` request.
- **Headers / Payload:** see the *full* request body — every field the app sends (not just the
  prompt box!).
- **Response:** read the JSON — text replies, URLs, hints about metadata.
- **Copy as fetch / Copy as cURL:** replay and *edit* a request. The app gives you a
  **"Copy as request"** button to make this easy.

> Tip: the prompt box is rarely the only input. Open the **Advanced** drawer and read the Network
> payload — there may be fields nobody filters.

## Inspecting image metadata

Some flags hide in the image file itself (PNG text chunks / EXIF):
- Use the built-in **Inspect Metadata** tool (upload or click an image you generated), **or**
- Download the image and run `exiftool image.png`, **or** open it in any metadata viewer.

## Hints

Each challenge has **3 hint tiers**. Taking a hint costs points but they're always available — a
solve with hints beats no solve. If you're stuck for a while, the app may *offer* the next hint;
it's your choice.

## Scoring

`points = base − hints taken − small late-solve decay + first-blood bonus`. First person to solve a
level gets a bonus. Level 8 has a **writeup bonus** — submit a short disclosure (root cause / how you
exploited it / how you'd fix it).

## Rules of engagement

- ✅ Attack the **target application** (prompts, fields, metadata, tools, conversation).
- ❌ Don't attack the **platform** (scoreboard, auth, other people's sessions) — that's not the game.
- ❌ No denial-of-service / flooding. Rate limits will stop you anyway.
- 🔒 The image model's **safety filter is out of scope** — no flag ever requires generating harmful,
  explicit, or illegal content. Don't try; it won't help.
- 🤝 Be excellent to your neighbors. Share *approaches* at checkpoints, not full answers mid-block.

## The loop that solves everything

1. **Recon** — generate normally; read the request and response in DevTools and the image metadata.
2. **Hypothesize** — "the app probably does X with my input / hides Y here."
3. **Test** — craft one change and try it.
4. **Read carefully** — the flag or the next clue is usually right there in some output channel.
5. **Name it** — which OWASP LLM risk is this? How would you fix it? (You'll need this for debriefs
   and the Level 8 writeup.)

## Responsible disclosure template (for Level 8 + real life)

```
Title:        <short, component-focused — e.g. "Unfiltered negative_prompt enables policy bypass">
Component:    <where in the app — orchestration / template / tool / metadata>
Severity:     <impact-based>
Root cause:   <the underlying design flaw, not "the AI is dumb">
Reproduction: <numbered steps, exact inputs>
Impact:       <what an attacker gains>
Mitigation:   <the specific control that fixes it, and any trade-offs>
```

## Where to go next

OWASP Top 10 for LLM Applications (2025), the mitigation catalog in this repo
([03 §14](03-architecture.md#14-security-controls-catalog-what-we-teach-as-the-fixes)), and the
challenge writeups in [02-ctf-design.md](02-ctf-design.md) after the event.

Have fun. Break the app, then learn how you'd ship it safely.
