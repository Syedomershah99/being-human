#!/usr/bin/env python3
"""
being-human score -- find the AI tells in a piece of text.

Runs two passes.

Lexical: the curated tell list in data/slop-lexicon.json. Words and constructions
that models reach for and people mostly don't.

Structural: the things a word list can't catch. Sentences that are all the same
length. Every paragraph one line long. Triads everywhere. This pass is where most
of the real signal is -- slop survives find-and-replace, but it can't survive rhythm.

If a voiceprint exists, thresholds come from *your* measured habits instead of
generic defaults. Your em dash rate is whatever you actually do, not zero.

Usage:
  python3 slopscore.py draft.md
  python3 slopscore.py --in .being-human/ draft.md        # personalized
  cat draft.md | python3 slopscore.py -
  python3 slopscore.py draft.md --json --fail-under 70
"""

import argparse
import json
import os
import re
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_LEXICON = os.path.join(HERE, "..", "data", "slop-lexicon.json")

SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")
WORD = re.compile(r"[A-Za-z']+")

FENCE = re.compile(r"^[ \t]*```.*?^[ \t]*```", re.M | re.S)
INLINE_CODE = re.compile(r"`[^`\n]+`")


def mask_code(text):
    """
    Blank out code spans while preserving every byte offset and line break.

    Quoting slop is not writing slop. A doc that demonstrates a bad phrase, or a
    changelog listing banned words, would otherwise score worse than the thing
    it's warning you about. Replacing with spaces rather than deleting keeps
    reported line numbers pointing at the right place.
    """
    def blank(match):
        return re.sub(r"[^\n]", " ", match.group(0))
    return INLINE_CODE.sub(blank, FENCE.sub(blank, text))


def sentences(text):
    out = []
    for block in text.split("\n"):
        block = block.strip()
        if not block or block.startswith(("#", ">", "|", "```")):
            continue
        for s in SENT_SPLIT.split(block):
            s = s.strip(" -*•\t")
            if len(WORD.findall(s)) >= 3:
                out.append(s)
    return out


def line_of(text, index):
    return text.count("\n", 0, index) + 1


def load_json(path):
    try:
        with open(path) as fh:
            return json.load(fh)
    except (IOError, ValueError):
        return None


class Finding(object):
    def __init__(self, line, kind, label, weight, fix, excerpt=""):
        self.line, self.kind, self.label = line, kind, label
        self.weight, self.fix, self.excerpt = weight, fix, excerpt

    def as_dict(self):
        return {"line": self.line, "kind": self.kind, "label": self.label,
                "weight": self.weight, "fix": self.fix, "excerpt": self.excerpt}


# ------------------------------------------------------------------- lexical


def scan_lexicon(text, lexicon):
    found = []
    for entry in lexicon.get("phrases", []):
        rx = re.compile(entry["pattern"], re.I | re.M)
        for match in rx.finditer(text):
            found.append(Finding(
                line_of(text, match.start()), "phrase",
                match.group(0).strip(), entry.get("weight", 3),
                entry.get("fix", ""), excerpt=match.group(0).strip()))
    for entry in lexicon.get("structures", []):
        if not entry.get("pattern"):
            continue
        rx = re.compile(entry["pattern"], re.I | re.M)
        hits = list(rx.finditer(text))
        if entry["id"] == "triad" and len(hits) < 2:
            continue  # one list of three is a list; four is a habit
        if entry["id"] == "em-dash":
            continue  # handled against your own baseline below
        for match in hits:
            found.append(Finding(
                line_of(text, match.start()), "structure",
                entry.get("label", entry["id"]), entry.get("weight", 3),
                entry.get("fix", ""), excerpt=match.group(0).strip()[:60]))
    return found


# ---------------------------------------------------------------- structural


def scan_structure(text, base):
    """
    `base` holds your measured habits when a voiceprint is loaded, generic
    defaults otherwise. Every threshold here is a comparison against you.
    """
    found = []
    sents = sentences(text)
    lens = [len(WORD.findall(s)) for s in sents]
    total_words = sum(lens) or 1

    if len(lens) >= 5:
        mean = statistics.mean(lens)
        sd = statistics.pstdev(lens)
        burst = sd / (mean or 1)
        target = base["burstiness"]
        # Below ~0.45 the prose is metronomic. Also flag anything well under the
        # writer's own natural variation, even if it clears the absolute floor.
        if burst < 0.45 or burst < target * 0.6:
            found.append(Finding(
                0, "rhythm",
                "sentences are too uniform (ratio %.2f, yours is %.2f)" % (burst, target),
                5,
                "break one sentence in half and let another run long. this is the "
                "single strongest tell in the file."))

    paras = [p for p in re.split(r"\n\s*\n", text) if p.strip() and not p.strip().startswith("#")]
    if len(paras) >= 5:
        singles = sum(1 for p in paras if len(sentences(p)) <= 1)
        if singles / float(len(paras)) > 0.7:
            found.append(Finding(
                0, "rhythm",
                "%d of %d paragraphs are a single line" % (singles, len(paras)), 4,
                "the linkedin-broetry cadence. merge some into real paragraphs."))

    def rate(n):
        return (n / float(total_words)) * 1000

    em = rate(len(re.findall(r"[—–]", text)))
    if em > max(1.5, base["em_dash"] * 2.5):
        found.append(Finding(
            0, "punctuation", "em dashes at %.1f per 1k (yours: %.1f)" % (em, base["em_dash"]),
            3, "swap most for a period or a comma."))

    ex = rate(text.count("!"))
    if ex > max(1.5, base["exclaim"] * 3):
        found.append(Finding(
            0, "punctuation", "exclamation marks at %.1f per 1k (yours: %.1f)"
            % (ex, base["exclaim"]), 3, "cut them. the sentence should carry it."))

    emoji = rate(len(re.findall(r"[\U0001F300-\U0001FAFF☀-➿]", text)))
    if emoji > max(0.5, base["emoji"] * 3):
        found.append(Finding(
            0, "punctuation", "emoji at %.1f per 1k (yours: %.1f)" % (emoji, base["emoji"]),
            4, "remove them, especially as bullet markers."))

    bullets = re.findall(r"^\s*[-*•]\s+(.{4,})$", text, re.M)
    if len(bullets) >= 4:
        blens = [len(WORD.findall(b)) for b in bullets]
        if statistics.pstdev(blens) / (statistics.mean(blens) or 1) < 0.22:
            found.append(Finding(
                0, "rhythm", "every bullet is the same length", 3,
                "real lists are ragged. let one be two words and one be a sentence."))
        firsts = [WORD.findall(b)[0].lower() for b in bullets if WORD.findall(b)]
        if len(firsts) >= 4 and len(set(firsts)) == 1:
            found.append(Finding(
                0, "rhythm", "every bullet opens with the same word", 3,
                "vary the openings."))

    # Two hedges stacked before a claim is a model habit, not a human one.
    for match in re.finditer(
            r"\b(i think|it seems|arguably|perhaps|possibly|it (?:may|might|could) be)\b"
            r"[^.!?]{0,30}\b(somewhat|fairly|rather|quite|relatively|generally)\b",
            text, re.I):
        found.append(Finding(
            line_of(text, match.start()), "structure", "stacked hedges", 3,
            "one hedge or none.", excerpt=match.group(0)[:60]))

    return found


# -------------------------------------------------------------------- report


def baseline(metrics):
    """Generic defaults, overridden by your measured habits when available."""
    base = {"burstiness": 0.75, "em_dash": 0.5, "exclaim": 0.5, "emoji": 0.2}
    if not metrics:
        return base, False
    m = metrics.get("metrics", {})
    p = m.get("punct_per_1k", {})
    mean = m.get("sentence_len_mean") or 0
    sd = m.get("sentence_len_sd") or 0
    if mean:
        base["burstiness"] = round(sd / float(mean), 2)
    for key, src in (("em_dash", "em_dash"), ("exclaim", "exclaim")):
        if src in p:
            base[key] = p[src]
    if "emoji_per_1k" in m:
        base["emoji"] = m["emoji_per_1k"]
    return base, True


def score_of(findings, words):
    penalty = sum(f.weight for f in findings)
    # Normalized per 250 words so a long piece isn't punished for being long,
    # and a two-line post isn't let off for being short.
    scaled = penalty * (250.0 / max(words, 120))
    return int(max(0, min(100, round(100 - scaled * 1.6))))


def verdict(score):
    if score >= 85:
        return "reads human"
    if score >= 70:
        return "mostly yours, a few tells"
    if score >= 50:
        return "recognisably generated"
    return "slop"


def main():
    ap = argparse.ArgumentParser(description="Score text for AI tells.")
    ap.add_argument("file", help="File to score, or - for stdin")
    ap.add_argument("--in", dest="indir", default=".being-human",
                    help="Voiceprint dir, for personalized thresholds")
    ap.add_argument("--lexicon", default=DEFAULT_LEXICON)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--quiet", action="store_true", help="Score only")
    ap.add_argument("--fail-under", type=int, default=0,
                    help="Exit 1 if the score falls below this")
    args = ap.parse_args()

    raw = sys.stdin.read() if args.file == "-" else open(args.file).read()
    text = mask_code(raw)
    lexicon = load_json(args.lexicon)
    if not lexicon:
        print("Can't read lexicon at %s" % args.lexicon)
        return 2
    metrics = load_json(os.path.join(args.indir, "metrics.json"))
    base, personalized = baseline(metrics)

    findings = scan_lexicon(text, lexicon) + scan_structure(text, base)
    findings.sort(key=lambda f: (-f.weight, f.line))
    words = len(WORD.findall(text))
    score = score_of(findings, words)

    if args.json:
        print(json.dumps({"score": score, "verdict": verdict(score),
                          "words": words, "personalized": personalized,
                          "baseline": base,
                          "findings": [f.as_dict() for f in findings]}, indent=2))
    elif args.quiet:
        print(score)
    else:
        print("")
        print("  %d/100   %s" % (score, verdict(score)))
        print("  %d words, %d tells%s"
              % (words, len(findings),
                 "" if personalized else "  (generic thresholds -- no voiceprint loaded)"))
        print("")
        if findings:
            cap = 58
            width = min(cap, max(len(f.label) for f in findings[:24]))
            for f in findings[:24]:
                where = ("L%d" % f.line) if f.line else "--"
                label = f.label if len(f.label) <= cap else f.label[:cap - 1] + "…"
                print("  %-5s %-*s  %s" % (where, width, label, f.fix))
            if len(findings) > 24:
                print("  ... and %d more" % (len(findings) - 24))
            print("")
        else:
            print("  nothing flagged.\n")

    if args.fail_under and score < args.fail_under:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
