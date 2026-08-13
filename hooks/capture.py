#!/usr/bin/env python3
"""
being-human capture -- a UserPromptSubmit hook that quietly grows the corpus.

Every prompt you type is a labeled sample of how you write. This appends each
one, so the voiceprint sharpens as you work instead of only when you remember to
rebuild it.

Design constraints, in order:

1. Never block. This runs on every prompt submission. Any failure -- unreadable
   corpus, full disk, malformed input -- exits 0 silently. A voice tool has no
   business standing between you and your prompt.
2. Never print. Stdout from a UserPromptSubmit hook is injected into the model's
   context. Anything chatty here would end up in every conversation.
3. Never leave a truncated corpus. Appends are atomic-ish: one line, one write,
   flushed.

Corpus location, first match wins:
  $BEING_HUMAN_DIR
  ./.being-human            (if it already exists -- per-project voice)
  ~/.being-human            (default)

Re-run analyze.py to fold new samples into the voiceprint. Capture only collects.
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))

MIN_WORDS = 4
MAX_WORDS = 500


def corpus_dir():
    env = os.environ.get("BEING_HUMAN_DIR")
    if env:
        return os.path.expanduser(env)
    local = os.path.join(os.getcwd(), ".being-human")
    if os.path.isdir(local):
        return local
    return os.path.join(os.path.expanduser("~"), ".being-human")


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0

    prompt = payload.get("prompt") or ""
    if not prompt.strip():
        return 0

    # Slash commands are control, not voice.
    if prompt.lstrip().startswith("/"):
        return 0

    try:
        from harvest import clean, keep, redact, word_count
    except Exception:
        return 0

    try:
        text = clean(prompt)
        if not keep(text, MIN_WORDS, MAX_WORDS):
            return 0
        text = redact(text)

        directory = corpus_dir()
        if not os.path.isdir(directory):
            os.makedirs(directory)

        row = {
            "text": text,
            "words": word_count(text),
            "ts": payload.get("timestamp"),
            "ctx": payload.get("cwd") or os.getcwd(),
            "via": "hook",
        }
        with open(os.path.join(directory, "corpus.jsonl"), "a") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            fh.flush()
    except Exception:
        return 0

    return 0


if __name__ == "__main__":
    # Belt and braces: the hook must never fail loudly, whatever happens above.
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
