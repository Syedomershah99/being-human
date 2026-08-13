#!/usr/bin/env python3
"""
being-human analyze -- turn a corpus into a voiceprint.

Two things happen here.

1. Measurement. Sentence rhythm, punctuation habits, contractions, how you open,
   how you hedge. Boring, deterministic, and the part an LLM can actually follow.

2. Contrast. If a model corpus exists, every word gets a log-odds score: how much
   more likely you are to use it than the model is. The top of that list is your
   idiolect. The bottom is the slop the model has been feeding you all along.

Usage:
  python3 analyze.py --in .being-human/ --name "Your Name"
"""

import argparse
import json
import math
import os
import re
import statistics
import sys
from collections import Counter
from datetime import date

STOPWORDS = set("""
a an and are as at be been but by can could did do does for from had has have he her
him his how i if in into is it its me my no not of on or our out she should so than
that the their them then there these they this to too was we were what when where
which who will with would you your am been being here just also may might must
""".split())

# Stylometry's trick: voice lives in function words, because they're independent
# of subject matter. But raw grammar (the, a, of, is) mostly measures who wrote
# longer sentences. What survives both filters is the stance layer -- hedges,
# intensifiers, connectives, discourse markers. That's where two writers on the
# same topic actually diverge.
STYLE_WORDS = set("""
absolutely actually additionally albeit almost already also alternatively although
always anyway apparently arguably basically besides better both briefly broadly
certainly clearly completely consequently considerably conversely correct crucial
crucially definitely deliberately directly effectively either entirely especially
essentially even eventually exactly explicitly extremely fairly finally frankly
frequently fully fundamentally further furthermore generally genuinely gladly greatly
hence hopefully however ideally immediately importantly incredibly indeed inherently
initially instead interestingly ironically largely likely literally maybe meanwhile
merely mostly moreover much mainly naturally nearly necessarily nevertheless nonetheless
normally notably obviously occasionally often overall particularly perfectly perhaps
personally possibly practically precisely presumably pretty previously primarily
probably properly quickly quite rarely rather readily really regardless relatively
respectively roughly seemingly seriously significantly similarly simply slightly
somehow sometimes somewhat specifically strictly subsequently substantially suddenly
supposedly surely surprisingly technically theoretically thereby therefore thoroughly
thus totally traditionally truly typically ultimately unfortunately unless unlike
usually vaguely various vastly very virtually well whereas whilst wholly widely
honestly kinda sorta gotta gonna wanna anyways yeah yep nope ok okay please just
maybe like sure fine cool weird nice tricky messy solid clean tiny huge whole entire
proper decent rough quick simple straightforward robust seamless comprehensive
""".split())

SHORTHAND = ["kinda", "sorta", "gonna", "wanna", "lemme", "gotta", "tbh", "idk", "imo",
             "imho", "btw", "rn", "afaik", "iirc", "fyi", "asap", "ish", "prob", "def",
             "pls", "plz", "thx", "u", "ur", "ya", "yeah", "yep", "nope", "ok", "okay"]
HEDGES = ["maybe", "perhaps", "probably", "possibly", "might", "kinda", "sort of",
          "i think", "i guess", "i feel like", "not sure", "somewhat", "fairly", "seems"]
INTENSIFIERS = ["very", "really", "super", "extremely", "totally", "absolutely",
                "literally", "actually", "definitely", "way", "so much", "insanely"]
DISCOURSE = ["so", "basically", "honestly", "look", "anyway", "well", "right",
             "like", "obviously", "clearly", "essentially", "frankly"]
DIRECTIVES = ["can you", "could you", "please", "let's", "lets", "i want", "i need",
              "make", "build", "fix", "add", "create", "write", "give me", "show me",
              "check", "run", "update", "remove"]

SENT_SPLIT = re.compile(r"[.!?]+[\s\"')\]]*|\n+")
WORD = re.compile(r"[A-Za-z']+")


# ------------------------------------------------------------------ measuring


def sentences(text):
    return [s.strip() for s in SENT_SPLIT.split(text) if s.strip()]


def words(text):
    return WORD.findall(text.lower())


def rate(count, total, per=1000.0):
    return round((count / float(total)) * per, 2) if total else 0.0


def pct(count, total):
    return round(100.0 * count / float(total), 1) if total else 0.0


def phrase_hits(blob, phrases):
    out = Counter()
    for p in phrases:
        n = len(re.findall(r"\b" + re.escape(p) + r"\b", blob))
        if n:
            out[p] = n
    return out


def measure(samples):
    blob = "\n".join(s["text"] for s in samples)
    low = blob.lower()
    toks = words(blob)
    total = len(toks) or 1

    sent_lens = []
    for s in samples:
        for sent in sentences(s["text"]):
            n = len(words(sent))
            if n:
                sent_lens.append(n)

    # How often do you start a sentence without reaching for shift?
    starts_lower = starts_total = 0
    for s in samples:
        for sent in sentences(s["text"]):
            first = sent.lstrip()[:1]
            if first.isalpha():
                starts_total += 1
                if first.islower():
                    starts_lower += 1

    solo_i_lower = len(re.findall(r"(?<![A-Za-z'])i(?![A-Za-z'])", blob))
    solo_i_upper = len(re.findall(r"(?<![A-Za-z'])I(?![A-Za-z'])", blob))
    i_total = solo_i_lower + solo_i_upper

    m = {
        "samples": len(samples),
        "words": total,
        "words_per_sample": round(total / float(len(samples)), 1) if samples else 0,
        "sentence_len_mean": round(statistics.mean(sent_lens), 1) if sent_lens else 0,
        "sentence_len_median": round(statistics.median(sent_lens), 1) if sent_lens else 0,
        "sentence_len_sd": round(statistics.pstdev(sent_lens), 1) if len(sent_lens) > 1 else 0,
        "sentence_len_max": max(sent_lens) if sent_lens else 0,
        "lowercase_starts_pct": pct(starts_lower, starts_total),
        "lowercase_i_pct": pct(solo_i_lower, i_total),
        "contractions_per_1k": rate(len(re.findall(r"\b\w+'(s|t|re|ve|ll|d|m)\b", low)), total),
        "questions_pct": pct(sum(1 for s in samples if "?" in s["text"]), len(samples)),
        "punct_per_1k": {
            "comma": rate(blob.count(","), total),
            "em_dash": rate(len(re.findall(r"[—–]", blob)), total),
            "semicolon": rate(blob.count(";"), total),
            "colon": rate(blob.count(":"), total),
            "exclaim": rate(blob.count("!"), total),
            "ellipsis": rate(len(re.findall(r"\.\.\.|…", blob)), total),
            "parens": rate(blob.count("("), total),
        },
        "emoji_per_1k": rate(len(re.findall(
            r"[\U0001F300-\U0001FAFF☀-➿]", blob)), total),
        "bullets_pct": pct(sum(1 for s in samples
                               if re.search(r"^\s*[-*•]\s", s["text"], re.M)), len(samples)),
        "shorthand": dict(phrase_hits(low, SHORTHAND).most_common(12)),
        "hedges": dict(phrase_hits(low, HEDGES).most_common(10)),
        "intensifiers": dict(phrase_hits(low, INTENSIFIERS).most_common(10)),
        "discourse": dict(phrase_hits(low, DISCOURSE).most_common(10)),
        "directives": dict(phrase_hits(low, DIRECTIVES).most_common(10)),
    }
    m["hedge_per_1k"] = rate(sum(m["hedges"].values()), total)
    m["shorthand_per_1k"] = rate(sum(m["shorthand"].values()), total)
    return m


def openers(samples, n=12):
    firsts, pairs = Counter(), Counter()
    for s in samples:
        w = words(s["text"])
        if w:
            firsts[w[0]] += 1
        if len(w) >= 2:
            pairs[" ".join(w[:2])] += 1
    return {"first_word": firsts.most_common(n), "first_two": pairs.most_common(n)}


# ------------------------------------------------------------------ contrast


def ctx_key(ctx):
    """
    Collapse a context to a coarse project id.

    Sources label context differently -- a project name from one, a working
    directory from another. Without normalizing, the same project counts twice
    and project jargon passes the spread filter.
    """
    if not ctx:
        return "?"
    parts = [p for p in re.split(r"[/\\_\-\s]+", str(ctx).lower()) if p]
    return "/".join(parts[-2:]) if parts else "?"


def count(samples):
    """Term frequency, plus how many distinct projects each word showed up in."""
    tf = Counter()
    spread = {}
    for s in samples:
        seen = set()
        for w in words(s["text"]):
            tf[w] += 1
            seen.add(w)
        key = ctx_key(s.get("ctx"))
        for w in seen:
            spread.setdefault(w, set()).add(key)
    return tf, spread


def style_vocab(mine, theirs, min_count):
    return set(w for w in STYLE_WORDS if mine[w] + theirs[w] >= min_count)


def content_vocab(mine, theirs, spread, min_count, min_spread=3):
    """
    Content words, minus the ones that only exist inside a single project.

    "fwhm" appearing 200 times in one repo is a topic, not a habit. Requiring a
    word to surface across several separate contexts is what separates the
    vocabulary someone carries with them from the vocabulary a project imposed.
    """
    out = set()
    for w in set(mine) | set(theirs):
        if w in STYLE_WORDS or w in STOPWORDS or len(w) <= 3:
            continue
        if mine[w] + theirs[w] < min_count:
            continue
        if len(spread.get(w, ())) < min_spread:
            continue
        out.add(w)
    return out


def log_odds(mine, theirs, vocab, top=40):
    """
    Monroe et al. log-odds ratio with an uninformative Dirichlet prior.

    Positive z = you say it far more than the model does -> your idiolect.
    Negative z = the model says it far more than you do  -> candidate slop.
    """
    if not vocab:
        return [], []
    n_mine = sum(mine[w] for w in vocab)
    n_theirs = sum(theirs[w] for w in vocab)
    alpha, a0 = 0.5, 0.5 * len(vocab)

    scored = []
    for w in vocab:
        ym, yt = mine[w] + alpha, theirs[w] + alpha
        odds_m = math.log(ym / (n_mine + a0 - ym))
        odds_t = math.log(yt / (n_theirs + a0 - yt))
        var = (1.0 / ym) + (1.0 / yt)
        z = (odds_m - odds_t) / math.sqrt(var)
        scored.append((w, round(z, 2), mine[w], theirs[w]))

    scored.sort(key=lambda r: r[1], reverse=True)
    yours = [r for r in scored if r[1] > 0][:top]
    model = [r for r in reversed(scored) if r[1] < 0][:top]
    return yours, model


def ngrams(samples, n=2, top=25, min_spread=3):
    """
    Recurring phrases, filtered the same way vocabulary is.

    A phrase that only ever appears inside one project is that project's
    terminology. A phrase that follows someone across projects is a verbal habit.
    """
    c = Counter()
    spread = {}
    for s in samples:
        w = words(s["text"])
        key = ctx_key(s.get("ctx"))
        for i in range(len(w) - n + 1):
            gram = w[i:i + n]
            if all(g in STOPWORDS for g in gram):
                continue
            g = " ".join(gram)
            c[g] += 1
            spread.setdefault(g, set()).add(key)
    ranked = [(g, k) for g, k in c.most_common(top * 6)
              if k > 2 and len(spread.get(g, ())) >= min_spread]
    return ranked[:top]


# --------------------------------------------------------------------- rules


def derive_rules(m, registers):
    """Thresholds -> instructions. An LLM can follow these; it can't follow 'be authentic'."""
    do, dont = [], []
    p = m["punct_per_1k"]

    if m["lowercase_i_pct"] >= 60:
        do.append('Write "i" lowercase. They do, %.0f%% of the time.' % m["lowercase_i_pct"])
    elif m["lowercase_i_pct"] <= 15 and m["words"] > 500:
        dont.append('Never write a bare lowercase "i". They always capitalize it.')

    if m["lowercase_starts_pct"] >= 45:
        do.append("Start sentences lowercase. %.0f%% of theirs do. Don't tidy this up."
                  % m["lowercase_starts_pct"])
    elif m["lowercase_starts_pct"] <= 10:
        do.append("Capitalize every sentence. They are consistent about it.")

    # Burstiness is relative. sd=8 is placid around a 40-word mean and violent
    # around a 9-word one, so the ratio is what matters, not the raw deviation.
    burst = m["sentence_len_sd"] / float(m["sentence_len_mean"] or 1)
    if burst >= 0.65:
        do.append("Vary sentence length hard. Theirs average %.0f words but deviate %.0f "
                  "(ratio %.2f), running as long as %d. Put a three-word sentence next to a "
                  "thirty-word one. Uniform rhythm is the loudest tell there is."
                  % (m["sentence_len_mean"], m["sentence_len_sd"], burst, m["sentence_len_max"]))
    elif burst >= 0.4:
        do.append("Some rhythm variation: %.0f-word sentences, deviation %.0f (ratio %.2f). "
                  "Break up any run of three same-length sentences."
                  % (m["sentence_len_mean"], m["sentence_len_sd"], burst))
    else:
        do.append("Sentences stay even, near %.0f words (ratio %.2f). Don't force variation."
                  % (m["sentence_len_mean"], burst))

    if p["em_dash"] < 0.6:
        dont.append("No em dashes. Rate is %.2f per 1k words -- effectively never. "
                    "Use a period, a comma, or parentheses." % p["em_dash"])
    elif p["em_dash"] > 3:
        do.append("Em dashes are theirs, %.1f per 1k. Keep them." % p["em_dash"])

    if p["semicolon"] < 0.3:
        dont.append("No semicolons. They don't use them.")
    if p["exclaim"] < 0.5:
        dont.append("No exclamation marks. Rate is %.2f per 1k." % p["exclaim"])
    elif p["exclaim"] > 4:
        do.append("Exclamation marks are in-voice here (%.1f per 1k)." % p["exclaim"])

    if m["emoji_per_1k"] < 0.2:
        dont.append("No emoji. Zero in the corpus.")
    if m["contractions_per_1k"] >= 12:
        do.append("Use contractions freely (%.0f per 1k). Never expand to \"do not\", \"it is\"."
                  % m["contractions_per_1k"])
    elif m["contractions_per_1k"] <= 4:
        dont.append("Avoid contractions. They write it out.")

    if m["shorthand"]:
        top = ", ".join(list(m["shorthand"].keys())[:6])
        do.append("Their shorthand is fair game: %s." % top)
    if m["hedge_per_1k"] < 2:
        dont.append("Don't hedge. Hedge rate is %.1f per 1k -- they assert." % m["hedge_per_1k"])
    else:
        do.append("Some hedging is in-voice (%.1f per 1k): %s."
                  % (m["hedge_per_1k"], ", ".join(list(m["hedges"].keys())[:4])))

    if m["discourse"]:
        do.append("They open clauses with: %s." % ", ".join(list(m["discourse"].keys())[:5]))
    if m["bullets_pct"] < 15:
        dont.append("Prose, not bullets. Only %.0f%% of their writing uses lists."
                    % m["bullets_pct"])
    elif m["bullets_pct"] > 45:
        do.append("Bullets are natural here (%.0f%% of samples)." % m["bullets_pct"])

    if m["words_per_sample"] < 25:
        do.append("Be short. Their median message is ~%.0f words." % m["words_per_sample"])

    if registers:
        short, long_ = registers.get("quick"), registers.get("considered")
        if short and long_:
            do.append("Two registers exist. Quick: ~%.0f words, %.0f-word sentences. "
                      "Considered: ~%.0f words, %.0f-word sentences. Match the one the "
                      "situation calls for."
                      % (short["words_per_sample"], short["sentence_len_mean"],
                         long_["words_per_sample"], long_["sentence_len_mean"]))

    dont.append("No summary paragraph at the end. No \"in conclusion\". Stop when done.")
    dont.append("No \"I hope this helps\", no \"let me know if\", no offer to continue.")
    return do, dont


# ------------------------------------------------------------------- writing


def fmt_rows(rows, limit):
    return ", ".join("%s" % r[0] for r in rows[:limit])


def render(name, m, ops, grams, style_mine, lexicon, style_slop, registers, do, dont, sources):
    L = []
    A = L.append
    A("# voiceprint: %s" % (name or "unknown"))
    A("")
    A("<!-- generated by being-human on %s. do not hand-edit the measured block; " % date.today())
    A("     re-run `analyze.py` instead. the notes section is yours. -->")
    A("")
    A("Built from %s samples, %s words." % (format(m["samples"], ","), format(m["words"], ",")))
    A("Source: %s" % ", ".join(sources))
    A("")
    A("## how to use this")
    A("")
    A("This is a description of one specific person's writing, measured from their own words.")
    A("When you write **as** them or **for** them, match it. When the rules below conflict with")
    A("your defaults, the rules win. They are evidence; your defaults are habit.")
    A("")
    A("Match voice only. Never match voice at the cost of a true statement.")
    A("")
    A("## do")
    A("")
    for r in do:
        A("- %s" % r)
    A("")
    A("## don't")
    A("")
    for r in dont:
        A("- %s" % r)
    A("")
    A("## measured")
    A("")
    A("| signal | value |")
    A("| --- | --- |")
    A("| words per message | %s |" % m["words_per_sample"])
    A("| sentence length | %s avg, sd %s, longest %s |"
      % (m["sentence_len_mean"], m["sentence_len_sd"], m["sentence_len_max"]))
    A("| lowercase sentence starts | %s%% |" % m["lowercase_starts_pct"])
    A('| lowercase "i" | %s%% |' % m["lowercase_i_pct"])
    A("| contractions | %s per 1k words |" % m["contractions_per_1k"])
    A("| em dash | %s per 1k |" % m["punct_per_1k"]["em_dash"])
    A("| semicolon | %s per 1k |" % m["punct_per_1k"]["semicolon"])
    A("| exclamation | %s per 1k |" % m["punct_per_1k"]["exclaim"])
    A("| ellipsis | %s per 1k |" % m["punct_per_1k"]["ellipsis"])
    A("| emoji | %s per 1k |" % m["emoji_per_1k"])
    A("| hedging | %s per 1k |" % m["hedge_per_1k"])
    A("| uses bullets | %s%% of messages |" % m["bullets_pct"])
    A("| asks a question | %s%% of messages |" % m["questions_pct"])
    A("")

    if ops["first_two"]:
        A("## how they open")
        A("")
        A("Most common first words: %s."
          % ", ".join('"%s"' % w for w, _ in ops["first_word"][:8]))
        A("")
        A("Openings, verbatim from the corpus:")
        A("")
        for phrase, count in ops["first_two"][:10]:
            A('- "%s..." (%dx)' % (phrase, count))
        A("")

    if style_mine or lexicon:
        A("## their words")
        A("")
        A("Ranked by log-odds against the model's own output in the same conversations.")
        A("High score means they reach for it and the model doesn't.")
        A("")
    if style_mine:
        A("**Function words** -- the load-bearing ones. Voice lives here, not in nouns:")
        A("")
        A("`%s`" % "`, `".join(w for w, _, _, _ in style_mine[:26]))
        A("")
    if lexicon:
        A("**Vocabulary** -- content words they carry across projects, not jargon from one:")
        A("")
        A("`%s`" % "`, `".join(w for w, _, _, _ in lexicon[:26]))
        A("")
    if grams:
        A("**Recurring pairs**: %s."
          % ", ".join('"%s"' % g for g, _ in grams[:14]))
        A("")

    if style_slop:
        A("## words to avoid")
        A("")
        A("The model leaned on these in these same conversations. They never did.")
        A("This list is personal -- it is *this* model's slop, measured against *this* person.")
        A("It will not match anyone else's.")
        A("")
        A("`%s`" % "`, `".join(w for w, _, _, _ in style_slop[:26]))
        A("")

    if registers:
        A("## registers")
        A("")
        for key, r in registers.items():
            A("**%s** -- %s messages, ~%.0f words each, %.0f-word sentences, "
              "%.1f contractions/1k."
              % (key, r["samples"], r["words_per_sample"],
                 r["sentence_len_mean"], r["contractions_per_1k"]))
        A("")

    A("## notes")
    A("")
    A("<!-- yours. anything the numbers can't see: who you're writing for, what you")
    A("     refuse to say, running jokes, words you've banned. this survives re-runs. -->")
    A("")
    return "\n".join(L)


def load(path):
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


def main():
    ap = argparse.ArgumentParser(description="Turn a corpus into a voiceprint.")
    ap.add_argument("--in", dest="indir", default=".being-human")
    ap.add_argument("--name", default="")
    ap.add_argument("--out", default=None, help="Voiceprint path (default: <in>/voiceprint.md)")
    ap.add_argument("--min-count", type=int, default=6, help="Min occurrences for contrast")
    ap.add_argument("--min-spread", type=int, default=3,
                    help="A content word must appear across this many contexts to count "
                         "as vocabulary rather than project jargon")
    args = ap.parse_args()

    corpus = load(os.path.join(args.indir, "corpus.jsonl"))
    if not corpus:
        print("No corpus at %s. Run harvest.py first." % args.indir)
        return 1
    model = load(os.path.join(args.indir, "model.jsonl"))

    m = measure(corpus)
    ops = openers(corpus)
    grams = ngrams(corpus)

    quick = [s for s in corpus if s["words"] < 25]
    considered = [s for s in corpus if s["words"] >= 25]
    registers = {}
    if len(quick) >= 20 and len(considered) >= 20:
        registers["quick"] = measure(quick)
        registers["considered"] = measure(considered)

    style_mine, style_slop, lexicon = [], [], []
    if model:
        mine_c, mine_spread = count(corpus)
        theirs_c, _ = count(model)

        style_mine, style_slop = log_odds(
            mine_c, theirs_c, style_vocab(mine_c, theirs_c, args.min_count))
        # Spread is judged on their own usage. Whether the model repeated a term
        # back at them says nothing about whether it's part of their vocabulary.
        lexicon, _ = log_odds(
            mine_c, theirs_c,
            content_vocab(mine_c, theirs_c, mine_spread, args.min_count, args.min_spread))

    sources = ["%d of your messages" % len(corpus)]
    if model:
        sources.append("%d model replies (contrast)" % len(model))

    do, dont = derive_rules(m, registers)
    doc = render(args.name, m, ops, grams, style_mine, lexicon, style_slop,
                 registers, do, dont, sources)

    out = args.out or os.path.join(args.indir, "voiceprint.md")

    # Anything under `## notes` is hand-written. Never clobber it.
    if os.path.exists(out):
        with open(out) as fh:
            prev = fh.read()
        idx = prev.find("## notes")
        if idx != -1:
            kept = prev[idx:].split("\n", 1)
            tail = kept[1].strip() if len(kept) > 1 else ""
            if tail and "<!-- yours." not in tail:
                doc = doc[:doc.find("## notes")] + "## notes\n\n" + tail + "\n"

    with open(out, "w") as fh:
        fh.write(doc)

    payload = {"name": args.name, "generated": str(date.today()), "metrics": m,
               "openers": ops, "bigrams": grams, "registers": registers,
               "style_words": style_mine, "lexicon": lexicon,
               "slop_candidates": style_slop}
    with open(os.path.join(args.indir, "metrics.json"), "w") as fh:
        json.dump(payload, fh, indent=2)

    print("voiceprint  %s" % out)
    print("metrics     %s" % os.path.join(args.indir, "metrics.json"))
    print("")
    print("  %s samples, %s words" % (format(m["samples"], ","), format(m["words"], ",")))
    print("  %s sentences avg (sd %s)" % (m["sentence_len_mean"], m["sentence_len_sd"]))
    print("  lowercase starts %s%%, lowercase i %s%%"
          % (m["lowercase_starts_pct"], m["lowercase_i_pct"]))
    print("  em dash %s/1k, exclaim %s/1k, emoji %s/1k"
          % (m["punct_per_1k"]["em_dash"], m["punct_per_1k"]["exclaim"], m["emoji_per_1k"]))
    if style_mine:
        print("  your style:  %s" % fmt_rows(style_mine, 10))
    if lexicon:
        print("  your words:  %s" % fmt_rows(lexicon, 10))
    if style_slop:
        print("  model slop:  %s" % fmt_rows(style_slop, 10))
    return 0


if __name__ == "__main__":
    sys.exit(main())
