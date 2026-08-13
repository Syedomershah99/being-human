#!/usr/bin/env python3
"""
being-human card -- draw your voiceprint as a shareable SVG.

    being-human card --in .being-human/ --out voiceprint.svg
    being-human card --in .being-human/ --compare draft.md --out rhythm.svg

The voiceprint is a table of numbers, which is the right shape for a model to
follow and the wrong shape for a human to look at. This draws the same
measurements as a picture: a rhythm strip where every bar is one real sentence
you wrote, your casing and punctuation rates, and the words the model uses with
you that you never use.

On --compare, the same strip is drawn for your corpus and for whatever you
point it at, which is useful for eyeballing a draft against yourself.

Do not expect a dramatic picture. Measured over 4,000 sentences of one real
corpus, the author sat at a rhythm ratio of 0.91 and the model that answered
him at 0.78: a genuine difference, and a small one. The popular claim that
generated text draws as an obvious picket fence did not survive contact with
this data. That gap is exactly why the tool reports a number instead of asking
you to look at a chart -- 0.91 against 0.78 is decidable, and two strips side
by side are not.

Only aggregates are drawn. No sentence text ever reaches the SVG, so a card is
safe to post publicly even though the corpus behind it is not.

Stdlib only.
"""

import argparse
import json
import os
import random
import re
import sys

BG = "#0d1117"
BORDER = "#30363d"
INK = "#e6edf3"
MUTED = "#8b949e"
ACCENT = "#58a6ff"
GOOD = "#3fb950"
BAD = "#f85149"

WORD = re.compile(r"[A-Za-z']+")
SENT = re.compile(r"[.!?]+|\n+")
FENCE = re.compile(r"^[ \t]*```.*?^[ \t]*```", re.M | re.S)


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def sentence_lengths(text):
    return [len(WORD.findall(s)) for s in SENT.split(text) if WORD.findall(s)]


def corpus_lengths(path, limit=120, seed=11):
    lens = []
    if not os.path.exists(path):
        return lens
    with open(path) as fh:
        for line in fh:
            try:
                row = json.loads(line)
            except ValueError:
                continue
            lens.extend(sentence_lengths(row.get("text", "")))
    if len(lens) > limit:
        start = random.Random(seed).randrange(0, len(lens) - limit)
        lens = lens[start:start + limit]
    return lens


def rhythm(a, lens, x0, y_base, width, color, maxh=46, bw=4, gap=2, delay=0.0):
    """One bar per sentence. Height is word count, scaled to the tallest."""
    if not lens:
        return
    top = max(lens) or 1
    for i, n in enumerate(lens):
        x = x0 + i * (bw + gap)
        if x > x0 + width:
            break
        h = max(2, (n / float(top)) * maxh)
        y = y_base - h
        # Base state is the finished bar, so a renderer that ignores SMIL still
        # draws the card. The animation only supplies the entrance.
        a('<rect x="%d" y="%.1f" width="%d" height="%.1f" rx="1" fill="%s" opacity="0.9">'
          '<animate attributeName="height" from="0" to="%.1f" dur="0.45s" begin="%.3fs" fill="freeze"/>'
          '<animate attributeName="y" from="%d" to="%.1f" dur="0.45s" begin="%.3fs" fill="freeze"/>'
          '</rect>'
          % (x, y, bw, h, color, h, delay + 0.004 * i, y_base, y, delay + 0.004 * i))


def voiceprint_card(metrics_path, corpus_path, name=""):
    with open(metrics_path) as fh:
        m = json.load(fh)
    met = m["metrics"]
    p = met["punct_per_1k"]
    mean = met["sentence_len_mean"] or 1
    burst = met["sentence_len_sd"] / float(mean)
    avoid = [w for w, _, _, _ in m.get("slop_candidates", [])][:7]
    lens = corpus_lengths(corpus_path)

    W, H = 840, 286
    o = []
    a = o.append
    a('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" '
      'font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif">'
      % (W, H, W, H))
    a('<rect width="%d" height="%d" rx="12" fill="%s" stroke="%s"/>' % (W, H, BG, BORDER))
    a('<text x="32" y="42" fill="%s" font-size="15" font-weight="600">voiceprint%s</text>'
      % (INK, (" — " + esc(name)) if name else ""))
    a('<text x="32" y="62" fill="%s" font-size="12">measured from %s of my own words</text>'
      % (MUTED, format(met["words"], ",")))
    a('<text x="%d" y="42" fill="%s" font-size="11.5" text-anchor="end">being-human</text>'
      % (W - 32, ACCENT))

    a('<text x="32" y="92" fill="%s" font-size="11.5">sentence rhythm — every bar is one real sentence</text>' % MUTED)
    rhythm(a, lens, 32, 148, W - 72, ACCENT)
    a('<text x="32" y="168" fill="%s" font-size="11">%.0f words average, deviating %.0f. ratio %.2f.</text>'
      % (MUTED, mean, met["sentence_len_sd"], burst))

    facts = [('lowercase "i"', "%.0f%%" % met["lowercase_i_pct"]),
             ("em dash", "%.1f/1k" % p["em_dash"]),
             ("exclamation", "%.2f/1k" % p["exclaim"]),
             ("hedging", "%.1f/1k" % met.get("hedge_per_1k", 0))]
    x = 32
    for k, v in facts:
        a('<text x="%d" y="200" fill="%s" font-size="19" font-weight="600">%s</text>' % (x, INK, v))
        a('<text x="%d" y="216" fill="%s" font-size="11">%s</text>' % (x, MUTED, k))
        x += 132

    if avoid:
        a('<text x="32" y="250" fill="%s" font-size="11">'
          'words this model uses with me that i never do</text>' % MUTED)
        cx = W - 32
        for w in reversed(avoid):
            wid = 9 + len(w) * 6.6
            cx -= wid + 6
            a('<rect x="%.1f" y="256" width="%.1f" height="20" rx="10" fill="#21262d" '
              'stroke="%s" stroke-opacity="0.4"/>' % (cx, wid, BAD))
            a('<text x="%.1f" y="270" fill="%s" font-size="11" text-anchor="middle">%s</text>'
              % (cx + wid / 2, BAD, esc(w)))
    a('</svg>')
    return "\n".join(o)


def compare_card(panels):
    """
    Three rhythm strips stacked, so the difference is visible rather than argued.

    panels: list of (label, sublabel, lengths, color)
    """
    W = 840
    rowh = 96
    H = 58 + rowh * len(panels)
    o = []
    a = o.append
    a('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" '
      'font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif">'
      % (W, H, W, H))
    a('<rect width="%d" height="%d" rx="12" fill="%s" stroke="%s"/>' % (W, H, BG, BORDER))
    a('<text x="32" y="38" fill="%s" font-size="15" font-weight="600">sentence rhythm</text>' % INK)
    a('<text x="%d" y="38" fill="%s" font-size="11.5" text-anchor="end">being-human</text>'
      % (W - 32, ACCENT))

    y = 62
    for i, (label, sub, lens, color) in enumerate(panels):
        a('<text x="32" y="%d" fill="%s" font-size="12" font-weight="600">%s</text>'
          % (y + 12, INK, esc(label)))
        a('<text x="%d" y="%d" fill="%s" font-size="11" text-anchor="end">%s</text>'
          % (W - 32, y + 12, MUTED, esc(sub)))
        rhythm(a, lens, 32, y + 72, W - 72, color, maxh=44, delay=0.25 * i)
        if i < len(panels) - 1:
            a('<line x1="32" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-opacity="0.5"/>'
              % (y + rowh - 12, W - 32, y + rowh - 12, BORDER))
        y += rowh
    a('</svg>')
    return "\n".join(o)


def main():
    ap = argparse.ArgumentParser(description="Draw your voiceprint as an SVG.")
    ap.add_argument("--in", dest="indir", default=".being-human")
    ap.add_argument("--out", default="voiceprint.svg")
    ap.add_argument("--name", default="")
    ap.add_argument("--compare", nargs="*", metavar="FILE",
                    help="Draw a rhythm comparison of your corpus against these files")
    args = ap.parse_args()

    metrics = os.path.join(args.indir, "metrics.json")
    corpus = os.path.join(args.indir, "corpus.jsonl")
    if not os.path.exists(metrics):
        print("No metrics.json in %s. Run `being-human learn` first." % args.indir,
              file=sys.stderr)
        return 2

    if args.compare is not None:
        panels = [("your writing", "from your own corpus",
                   corpus_lengths(corpus, limit=110), GOOD)]
        # The honest contrast is the model's own replies in the same
        # conversations, not a strawman someone typed to look uniform.
        model = os.path.join(args.indir, "model.jsonl")
        if not args.compare and os.path.exists(model):
            panels.append(("the model, same conversations", "from model.jsonl",
                           corpus_lengths(model, limit=110, seed=5), BAD))
        for path in args.compare:
            with open(path) as fh:
                text = FENCE.sub(" ", fh.read())
            lens = sentence_lengths(text)[:110]
            panels.append((os.path.basename(path), "%d sentences" % len(lens), lens, BAD))
        svg = compare_card(panels)
    else:
        svg = voiceprint_card(metrics, corpus, args.name)

    with open(args.out, "w") as fh:
        fh.write(svg)
    print("wrote %s (%d bytes)" % (args.out, len(svg)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
