#!/usr/bin/env python3
"""
being-human export -- compile a voiceprint into whatever your tool actually reads.

A voiceprint is just measured facts about how someone writes. Every assistant
wants those facts in a different container, and some of the containers are tiny
(ChatGPT's custom-instructions box is ~1500 characters). So this emits a
priority-ordered version that fills the budget it's given and stops.

Targets:
  chatgpt   paste into Settings > Personalization > Custom instructions
  claude    a block for CLAUDE.md
  agents    a block for AGENTS.md (Cursor, Codex, Copilot, Zed, Aider...)
  cursor    .cursorrules
  system    a raw system prompt, for API calls
  json      machine-readable, for building your own thing

Usage:
  python3 export.py --in .being-human/ --target chatgpt
  python3 export.py --in .being-human/ --target agents --out AGENTS.md
"""

import argparse
import json
import os
import sys

BUDGETS = {"chatgpt": 1500, "cursor": 6000, "claude": 6000,
           "agents": 6000, "system": 6000, "json": 0}


def load(path):
    try:
        with open(path) as fh:
            return json.load(fh)
    except (IOError, ValueError):
        return None


def lines_by_priority(mx):
    """
    Every rule this person's writing supports, most distinctive first.

    Order matters more than completeness. A 1500-character budget should spend
    itself on the habits that make someone identifiable, not on the ones any
    competent writer already follows.
    """
    m = mx["metrics"]
    p = m["punct_per_1k"]
    mean = m["sentence_len_mean"] or 1
    burst = m["sentence_len_sd"] / float(mean)
    out = []

    if m["lowercase_i_pct"] >= 60:
        out.append('write "i" in lowercase.')
    if m["lowercase_starts_pct"] >= 45:
        out.append("start sentences in lowercase. don't correct this.")
    elif m["lowercase_starts_pct"] <= 10:
        out.append("Capitalize sentences consistently.")

    if burst >= 0.65:
        out.append("vary sentence length hard: ~%d words on average but swing wide, "
                   "from three words to thirty. never a run of same-length sentences."
                   % round(mean))
    else:
        out.append("keep sentences near %d words. steady rhythm." % round(mean))

    out.append("no em dashes." if p["em_dash"] < 0.6 else "em dashes are fine.")
    if p["exclaim"] < 0.5:
        out.append("no exclamation marks.")
    if m["emoji_per_1k"] < 0.2:
        out.append("no emoji, ever.")
    if p["semicolon"] < 0.3:
        out.append("no semicolons.")

    if m["contractions_per_1k"] >= 12:
        out.append("use contractions.")
    elif m["contractions_per_1k"] <= 4:
        out.append("avoid contractions.")

    if m["bullets_pct"] < 15:
        out.append("write prose, not bullet lists.")
    elif m["bullets_pct"] > 45:
        out.append("bullets are natural here.")

    if m.get("hedge_per_1k", 0) < 2:
        out.append("assert. don't hedge, qualify, or soften.")
    if m["words_per_sample"] < 30:
        out.append("be brief. say it and stop.")

    sh = list(m.get("shorthand", {}).keys())[:5]
    if sh:
        out.append("{poss} shorthand is in-voice: %s." % ", ".join(sh))
    dm = list(m.get("discourse", {}).keys())[:5]
    if dm:
        out.append("{subj} open clauses with: %s." % ", ".join(dm))

    slop = [w for w, _, _, _ in mx.get("slop_candidates", [])][:14]
    if slop:
        out.append("never use: %s." % ", ".join(slop))

    out.append('no "i hope this helps", no "let me know if", no closing summary, '
               "no offer to continue. stop when the point is made.")
    out.append("match the voice, never at the cost of a true statement.")
    return out


def fit(header, rules, budget, person):
    """
    Fill the budget in priority order and stop.

    Person differs by target: instructions you paste into your own settings read
    as "my", instructions describing a user to an agent read as "their".
    """
    subj, poss = ("i", "my") if person == "first" else ("they", "their")
    body = header
    for rule in rules:
        rule = rule.replace("{subj}", subj).replace("{poss}", poss)
        candidate = body + "- " + rule + "\n"
        if budget and len(candidate) > budget:
            break
        body = candidate
    return body


def render(target, mx, budget):
    name = mx.get("name") or "the user"
    rules = lines_by_priority(mx)
    person = "first" if target in ("chatgpt", "cursor") else "third"

    if target == "chatgpt":
        header = ("Write the way I write. Measured from my own writing:\n")
        return fit(header, rules, budget, person)

    if target == "cursor":
        header = ("# voice\n"
                  "When writing prose for me -- commit messages, docs, comments, replies --\n"
                  "match my writing, measured from my own words:\n\n")
        return fit(header, rules, budget, person)

    if target in ("claude", "agents"):
        header = ("## Voice\n\n"
                  "When you write prose *as* me or *for* me, match the habits below. They\n"
                  "were measured from %s of my own words, so where they conflict with your\n"
                  "defaults, they win.\n\n" % format(mx["metrics"]["words"], ","))
        body = fit(header, rules, budget, person)
        return body + ("\nThis governs voice only. Never bend a fact to fit a style.\n"
                       "\n<!-- generated by being-human from %s samples. regenerate with:\n"
                       "     python3 scripts/export.py --target %s -->\n"
                       % (mx["metrics"]["samples"], target))

    if target == "system":
        header = ("You are writing as %s. Match these measured habits exactly:\n\n" % name)
        body = fit(header, rules, budget, person)
        return body + ("\nThese describe voice only. Never alter a fact to fit the voice.\n"
                       "If you cannot say something truthfully in this voice, say it plainly "
                       "instead.\n")

    rules = [r.replace("{subj}", "they").replace("{poss}", "their") for r in rules]
    return json.dumps({"name": name, "rules": rules,
                       "metrics": mx["metrics"]}, indent=2)


def main():
    ap = argparse.ArgumentParser(description="Compile a voiceprint for another tool.")
    ap.add_argument("--in", dest="indir", default=".being-human")
    ap.add_argument("--target", required=True,
                    choices=["chatgpt", "claude", "agents", "cursor", "system", "json"])
    ap.add_argument("--out", help="Write to a file instead of stdout")
    ap.add_argument("--budget", type=int, help="Character budget (overrides the default)")
    ap.add_argument("--append", action="store_true", help="Append to --out instead of replacing")
    args = ap.parse_args()

    mx = load(os.path.join(args.indir, "metrics.json"))
    if not mx:
        print("No metrics.json in %s. Run analyze.py first." % args.indir, file=sys.stderr)
        return 1

    budget = args.budget if args.budget is not None else BUDGETS[args.target]
    text = render(args.target, mx, budget)

    if args.out:
        with open(args.out, "a" if args.append else "w") as fh:
            if args.append:
                fh.write("\n")
            fh.write(text)
        print("wrote %s (%d chars%s)"
              % (args.out, len(text), ", budget %d" % budget if budget else ""))
    else:
        sys.stdout.write(text)
        if budget:
            print("\n---\n%d / %d characters" % (len(text), budget), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
