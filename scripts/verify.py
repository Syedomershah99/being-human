#!/usr/bin/env python3
"""
being-human verify -- the impostor test.

Every voice tool asserts a profile and then asks you to eyeball whether the
output sounds right. That is not a measurement, and eyeballing is the one
judgment guaranteed to fail here: a draft reads fine to whoever just read the
instructions that produced it.

This answers a falsifiable question instead:

    Among things this person actually wrote, at this length, how unusual is
    this text?

The distance is Burrows's Delta, the standard authorship-attribution measure:
express a document as the relative frequencies of the most frequent words in the
corpus, z-score them against the author, and take the mean absolute z.

The subtlety is the reference distribution, and getting it wrong inverts the
result. Delta has no absolute scale and is strongly length-dependent -- a short
document leaves most feature words at zero, and absent words sit near the mean,
so their near-zero |z| drags the average down. Worse, when the corpus is short
messages of uneven length, the per-word variance is inflated by that unevenness,
every |z| shrinks, and bland average-English prose ends up *closer* to the
centroid than the author's own writing. Scored naively, slop wins.

So the null is built by resampling: for a draft of N words, draw many N-word
chunks from the author's own corpus, compute the mean and standard deviation
across those chunks, and score every chunk and the draft against that. Length is
matched by construction, variance is estimated at the right scale, and the
result is a percentile with a plain meaning:

    "delta 1.31, 62nd percentile" = more typical of you than a third of your
                                    own writing at this length
    "delta 2.44, 99th percentile" = out of 400 same-length samples of you, only
                                    four were ever this far from your centre

The idea of judging a draft against the author's natural range rather than
against perfection is borrowed, with credit, from writer-persona's
"self-similarity ceiling". The difference here is that this is arithmetic: no
model judges it, it costs nothing, and it returns the same answer every time.

Usage:
  python3 verify.py draft.md --in .being-human/
  cat draft.md | python3 verify.py - --in .being-human/
  python3 verify.py --calibrate --in .being-human/
"""

import argparse
import json
import math
import os
import random
import re
import sys
from collections import Counter

WORD = re.compile(r"[A-Za-z']+")
EPS = 1e-9
MIN_CHUNK = 40


def words(text):
    return WORD.findall(text.lower())


def load_corpus(path):
    rows = []
    if not os.path.exists(path):
        return rows
    with open(path) as fh:
        for line in fh:
            try:
                rows.append(json.loads(line))
            except ValueError:
                continue
    return rows


def vec_from_tokens(toks, index):
    """Relative frequency of each feature word. `index` maps word -> slot."""
    v = [0.0] * len(index)
    n = len(toks) or 1
    for t in toks:
        slot = index.get(t)
        if slot is not None:
            v[slot] += 1.0
    return [x / n for x in v]


def mean_sd(vectors):
    k = len(vectors[0])
    n = float(len(vectors))
    mean = [0.0] * k
    for v in vectors:
        for i in range(k):
            mean[i] += v[i]
    mean = [x / n for x in mean]
    sd = [0.0] * k
    for v in vectors:
        for i in range(k):
            d = v[i] - mean[i]
            sd[i] += d * d
    sd = [math.sqrt(x / n) if x / n > EPS else EPS for x in sd]
    return mean, sd


def delta_of(vec, mean, sd):
    zs = [(vec[i] - mean[i]) / sd[i] for i in range(len(vec))]
    return sum(abs(z) for z in zs) / float(len(zs)), zs


def percentile_of(value, sorted_values):
    lo, hi = 0, len(sorted_values)
    while lo < hi:
        mid = (lo + hi) // 2
        if sorted_values[mid] < value:
            lo = mid + 1
        else:
            hi = mid
    return 100.0 * lo / float(len(sorted_values))


def quantile(sorted_values, q):
    if not sorted_values:
        return 0.0
    idx = min(len(sorted_values) - 1, max(0, int(round(q * (len(sorted_values) - 1)))))
    return sorted_values[idx]


def verdict(pct):
    if pct <= 75:
        return "indistinguishable from your writing"
    if pct <= 90:
        return "within your range"
    if pct <= 97:
        return "unusual for you"
    return "outside your range -- this does not read as you"


class Model(object):
    """
    A resampling null built from one author's tokens.

    Holds the corpus as a flat token stream. Every comparison chunk is a window
    into that stream, drawn the same way for the null and for the draft under
    test, which is what keeps the percentile honest.

    Note what this measures: authorship, not quality. It answers "is this the
    same hand?" using function-word distribution, which is topic-independent and
    hard to fake deliberately. It will happily pass fluent generic prose whose
    grammar resembles yours. Pair it with slopscore.py, which catches the
    opposite failure -- text full of AI tells that is nonetheless grammatically
    unremarkable. A draft has to clear both.
    """

    def __init__(self, streams, feats, n_chunks, seed):
        self.streams = streams           # list of token lists, one per sample
        self.flat = [t for s in streams for t in s]
        self.feats = feats
        self.index = dict((w, i) for i, w in enumerate(feats))
        self.n_chunks = n_chunks
        self.seed = seed
        self.n_words = len(self.flat)
        self.n_samples = len(streams)
        self._cache = {}

    def _chunks(self, size, count):
        """
        Windows drawn uniformly from the concatenated token stream.

        An earlier version preferred windows inside a single sample, which
        quietly biased the null: chunks from one message are more internally
        consistent than any real draft, so the null sat too tight and the
        author's own held-out writing scored around the 65th percentile instead
        of the 50th. Drawing every chunk the same way -- and the same way a real
        draft is scored -- puts the median back where it belongs.
        """
        rng = random.Random(self.seed ^ (size * 2654435761))
        flat, n = self.flat, len(self.flat)
        span = max(1, n - size)
        return [flat[i:i + size] for i in (rng.randrange(0, span) for _ in range(count))]

    def null(self, size):
        """(mean, sd, sorted deltas) for chunks of `size` words. Cached."""
        size = max(MIN_CHUNK, min(size, max(MIN_CHUNK, self.n_words // 4)))
        if size in self._cache:
            return self._cache[size]
        chunks = self._chunks(size, self.n_chunks)
        vecs = [vec_from_tokens(c, self.index) for c in chunks]
        mean, sd = mean_sd(vecs)
        deltas = sorted(delta_of(v, mean, sd)[0] for v in vecs)
        self._cache[size] = (mean, sd, deltas, size)
        return self._cache[size]

    def score(self, text):
        n = len(words(text))
        mean, sd, deltas, used = self.null(n)
        vec = vec_from_tokens(words(text), self.index)
        d, zs = delta_of(vec, mean, sd)
        pct = percentile_of(d, deltas)
        ranked = sorted(range(len(zs)), key=lambda i: -abs(zs[i]))[:12]
        return {
            "delta": round(d, 3),
            "percentile": round(pct, 1),
            "verdict": verdict(pct),
            "words": n,
            "matched_at": used,
            "null_size": len(deltas),
            "null_median": round(quantile(deltas, 0.50), 3),
            "null_p97": round(quantile(deltas, 0.97), 3),
            "drivers": [
                {
                    "word": self.feats[i],
                    "z": round(zs[i], 2),
                    "direction": "over" if zs[i] > 0 else "under",
                    "draft_per_1k": round(vec[i] * 1000, 2),
                    "you_per_1k": round(mean[i] * 1000, 2),
                }
                for i in ranked if abs(zs[i]) >= 1.5
            ][:8],
        }


def build_model(indir, features, n_chunks, seed, min_words):
    rows = load_corpus(os.path.join(indir, "corpus.jsonl"))
    if not rows:
        return None, "No corpus at %s. Run harvest.py first." % indir

    streams = []
    total = Counter()
    for r in rows:
        toks = words(r.get("text", ""))
        if len(toks) >= min_words:
            streams.append(toks)
            total.update(toks)
    n_words = sum(len(s) for s in streams)
    if n_words < 4000:
        return None, ("Only %s words of usable corpus (need ~4,000+). The null is "
                      "resampled from your own writing, so it needs enough writing "
                      "to resample." % format(n_words, ","))

    feats = [w for w, _ in total.most_common(features)]
    return Model(streams, feats, n_chunks, seed), None


def main():
    ap = argparse.ArgumentParser(description="Is this text a plausible sample of you?")
    ap.add_argument("file", nargs="?", help="File to test, or - for stdin")
    ap.add_argument("--in", dest="indir", default=".being-human")
    ap.add_argument("--calibrate", action="store_true",
                    help="Show the null distribution at several lengths and exit")
    ap.add_argument("--features", type=int, default=60,
                    help="Most-frequent words used as the style vector")
    ap.add_argument("--chunks", type=int, default=400,
                    help="Size of the resampled null")
    ap.add_argument("--seed", type=int, default=17,
                    help="Fixed so the same draft always scores the same")
    ap.add_argument("--min-words", type=int, default=8,
                    help="Ignore corpus samples shorter than this")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    model, err = build_model(args.indir, args.features, args.chunks,
                             args.seed, args.min_words)
    if err:
        print(err, file=sys.stderr)
        return 2

    if args.calibrate or not args.file:
        rows = []
        for size in (100, 200, 400, 800):
            if size > model.n_words // 4:
                continue
            _, _, deltas, used = model.null(size)
            rows.append({"length": used, "median": round(quantile(deltas, 0.50), 3),
                         "p75": round(quantile(deltas, 0.75), 3),
                         "p90": round(quantile(deltas, 0.90), 3),
                         "p97": round(quantile(deltas, 0.97), 3)})
        if args.json:
            print(json.dumps({"corpus_words": model.n_words,
                              "samples": model.n_samples, "bands": rows}, indent=2))
        else:
            print("")
            print("  null distributions resampled from your own writing")
            print("  %s words across %d samples, %d features, %d chunks each"
                  % (format(model.n_words, ","), model.n_samples,
                     args.features, args.chunks))
            print("")
            print("  %-8s %8s %8s %8s %8s" % ("length", "median", "p75", "p90", "p97"))
            for r in rows:
                print("  %-8s %8.2f %8.2f %8.2f %8.2f"
                      % (r["length"], r["median"], r["p75"], r["p90"], r["p97"]))
            print("")
            print("  a draft scoring above the p97 column for its length is one your")
            print("  own writing almost never reaches.")
            print("")
        return 0

    text = sys.stdin.read() if args.file == "-" else open(args.file).read()
    result = model.score(text)

    if args.json:
        print(json.dumps(result, indent=2))
        return 0

    print("")
    print("  delta %.2f   %dth percentile   %s"
          % (result["delta"], int(result["percentile"]), result["verdict"]))
    print("  %d words, against %d same-length samples of you (median %.2f, p97 %.2f)"
          % (result["words"], result["null_size"],
             result["null_median"], result["null_p97"]))
    if result["words"] < MIN_CHUNK:
        print("  (very short -- treat this loosely)")
    print("")
    if result["drivers"]:
        print("  what pushed it out:")
        for d in result["drivers"]:
            print("    %-12s %+5.1f sd  %-5s  draft %6.1f/1k   you %6.1f/1k"
                  % (d["word"], d["z"], d["direction"],
                     d["draft_per_1k"], d["you_per_1k"]))
        print("")
    else:
        print("  no feature word is more than 1.5 sd out of line.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
