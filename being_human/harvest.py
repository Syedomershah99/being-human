#!/usr/bin/env python3
"""
being-human harvest -- build a corpus of your own writing.

You already wrote thousands of words in your own voice. They're sitting in your
prompt history. This pulls them out, strips the noise, redacts the secrets, and
writes a clean corpus you can analyze.

Sources:
  claude-history    ~/.claude/history.jsonl        cleanest -- raw typed prompts
  claude-projects   ~/.claude/projects/**/*.jsonl  also yields model text for contrast
  chatgpt           a conversations.json from your ChatGPT data export
  files             any directory or glob of .md/.txt you wrote yourself
  stdin             paste it in

Everything runs locally. Nothing leaves the machine.

Usage:
  python3 harvest.py --source claude-history --out .being-human/
  python3 harvest.py --source claude-projects --out .being-human/ --contrast
  python3 harvest.py --source files --path ~/writing --out .being-human/
"""

import argparse
import glob
import hashlib
import json
import os
import re
import sys

# ---------------------------------------------------------------- redaction

REDACTIONS = [
    (re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]{2,}\b"), "<email>"),
    (re.compile(r"\b(?:sk-|sk-ant-|ghp_|gho_|github_pat_|xox[baprs]-|AKIA|AIza)"
                r"[A-Za-z0-9_\-]{10,}"), "<secret>"),
    (re.compile(r"\bBearer\s+[A-Za-z0-9._\-]{12,}"), "Bearer <secret>"),
    (re.compile(r"\b\+?\d{1,2}[-.\s]?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}\b"), "<phone>"),
    (re.compile(r"/Users/[^/\s]+"), "/Users/<me>"),
    (re.compile(r"/home/[^/\s]+"), "/home/<me>"),
    (re.compile(r"\b[0-9a-f]{32,}\b"), "<hash>"),
]


def redact(text):
    for pattern, repl in REDACTIONS:
        text = pattern.sub(repl, text)
    return text


# ------------------------------------------------------------------ cleanup

# Harness scaffolding that gets glued onto user turns. Not written by a human.
_TAGS = (r"ide_opened_file|ide_selection|system-reminder|command-name|command-message|"
         r"command-args|local-command-stdout|local-command-stderr|user-prompt-submit-hook|"
         r"attachment|thinking|task-notification|task-id|status|summary|result|"
         r"function_results|tool_use_error")
PAIRED_TAGS = re.compile(r"<(" + _TAGS + r")>.*?</\1>", re.S)
STRAY_TAGS = re.compile(r"^\s*</?(" + _TAGS + r")\b.*$", re.M)

# "[Pasted text #1 +11 lines] resolve this error..." -- the marker is noise but
# the sentence after it is the actual prompt. Drop the marker, keep the human.
PASTE_MARKER = re.compile(r"\[(Pasted text|Image|Screenshot|File)[^\]]*\]", re.I)

# Terminal pastes. Deliberately narrow: a full user@host:path$ prompt, an env
# assignment, or a line that opens with a command. Anything looser starts eating
# prose that merely contains a dollar sign or an address.
SHELL_PROMPT = re.compile(r"^\s*\(?[\w.\-]*\)?\s*[\w.\-]+@[\w.\-]+:\S*\s*[$#].*$", re.M)
ENV_ASSIGN = re.compile(r"^\s*(export\s+)?[A-Z_][A-Z0-9_]{2,}=.*$", re.M)
SHELL_CMD = re.compile(
    r"^\s*(sudo |cd |ls |cat |grep |sed |awk |chmod |chown |mkdir |rm |cp |mv |scp |ssh |"
    r"git |pip |pip3 |conda |npm |npx |yarn |python |python3 |sbatch |squeue |srun |module "
    r"|source |bash |sh |make |docker |kubectl |curl |wget )\S*.*$", re.M)
FENCED_CODE = re.compile(r"```.*?```", re.S)
URL = re.compile(r"https?://\S+|www\.\S+")
# Mixed letter+digit tokens: R53121, a1b2c3, v2beta. Identifiers, not vocabulary.
IDLIKE = re.compile(r"\b(?=\w*\d)(?=\w*[A-Za-z])\w{4,}\b")
INLINE_PATH_BLOB = re.compile(r"^\s*[\w./~-]+\.(py|js|ts|tsx|json|csv|yaml|yml|txt|md):\d+.*$", re.M)
CAUGHT_OUTPUT = re.compile(r"^\s*(Traceback \(most recent call last\)|\s{4,}File \").*$", re.M)

# Turns that are pure control, not voice.
CONTROL_ONLY = re.compile(
    r"^\s*(/[\w:-]+|y|n|yes|no|ok|okay|k|continue|go|go ahead|proceed|next|stop|"
    r"thanks|thank you|ty|cool|nice|perfect|great|done|sure|yep|yeah|nope)\s*[.!]*\s*$",
    re.I,
)


def clean(text):
    """Strip harness noise and pasted code so what's left is what the human typed."""
    if not text:
        return ""
    text = PAIRED_TAGS.sub(" ", text)
    text = STRAY_TAGS.sub("", text)
    text = FENCED_CODE.sub(" ", text)
    text = URL.sub(" ", text)
    text = PASTE_MARKER.sub(" ", text)
    text = SHELL_PROMPT.sub("", text)
    text = ENV_ASSIGN.sub("", text)
    text = SHELL_CMD.sub("", text)
    text = INLINE_PATH_BLOB.sub("", text)
    text = CAUGHT_OUTPUT.sub("", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def word_count(text):
    return len(re.findall(r"[A-Za-z']+", text))


def keep(text, min_words, max_words):
    if not text:
        return False
    if CONTROL_ONLY.match(text):
        return False
    n = word_count(text)
    # Too short is noise. Too long is almost always a paste, not prose.
    if not (min_words <= n <= max_words):
        return False
    # Dense with identifiers -> a pasted listing, log, or config. Not a voice sample.
    if len(IDLIKE.findall(text)) > max(2, 0.12 * n):
        return False
    # Mostly symbols -> a table or dump that survived the other filters.
    letters = sum(1 for c in text if c.isalpha() or c.isspace())
    return letters / float(len(text)) >= 0.72


# ------------------------------------------------------------------ sources


def from_claude_history(path):
    """~/.claude/history.jsonl -- one record per prompt, `display` is verbatim."""
    if not os.path.exists(path):
        return
    with open(path, "r", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            text = rec.get("display") or ""
            if text:
                yield {"text": text, "ts": rec.get("timestamp"), "ctx": rec.get("project")}


def _blocks_to_text(content):
    """Message content is a string or a list of blocks. Only text blocks are voice."""
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    parts = []
    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "text" and block.get("text"):
            parts.append(block["text"])
    return "\n".join(parts)


def from_claude_projects(root, role="user"):
    """Session transcripts. role='assistant' gives the contrast corpus."""
    pattern = os.path.join(root, "**", "*.jsonl")
    for path in glob.iglob(pattern, recursive=True):
        try:
            fh = open(path, "r", errors="replace")
        except IOError:
            continue
        with fh:
            for line in fh:
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue
                if rec.get("type") != role:
                    continue
                if rec.get("isSidechain") or rec.get("isMeta"):
                    continue  # subagent traffic, not you
                if role == "user" and rec.get("userType") not in (None, "external"):
                    continue  # tool-generated turns
                msg = rec.get("message") or {}
                text = _blocks_to_text(msg.get("content"))
                if text:
                    yield {"text": text, "ts": rec.get("timestamp"),
                           "ctx": rec.get("cwd") or rec.get("gitBranch")}


def from_chatgpt(path, role="user"):
    """conversations.json from a ChatGPT data export."""
    with open(path, "r", errors="replace") as fh:
        data = json.load(fh)
    convos = data if isinstance(data, list) else data.get("conversations", [])
    for convo in convos:
        title = convo.get("title")
        for node in (convo.get("mapping") or {}).values():
            msg = (node or {}).get("message")
            if not msg:
                continue
            if ((msg.get("author") or {}).get("role")) != role:
                continue
            parts = ((msg.get("content") or {}).get("parts")) or []
            text = "\n".join(p for p in parts if isinstance(p, str))
            if text:
                yield {"text": text, "ts": msg.get("create_time"), "ctx": title}


def from_files(path_spec):
    """Your own prose: blog drafts, notes, emails you exported. One doc per file."""
    paths = []
    if os.path.isdir(path_spec):
        for ext in ("md", "txt", "markdown"):
            paths.extend(glob.glob(os.path.join(path_spec, "**", "*." + ext), recursive=True))
    else:
        paths = glob.glob(os.path.expanduser(path_spec), recursive=True)
    for path in sorted(paths):
        try:
            with open(path, "r", errors="replace") as fh:
                text = fh.read()
        except IOError:
            continue
        if text.strip():
            yield {"text": text, "ts": None, "ctx": os.path.basename(path)}


def from_stdin():
    text = sys.stdin.read()
    if text.strip():
        yield {"text": text, "ts": None, "ctx": "stdin"}


# -------------------------------------------------------------------- write


def collect(records, min_words, max_words, do_redact, seen):
    out = []
    for rec in records:
        text = clean(rec.get("text", ""))
        if not keep(text, min_words, max_words):
            continue
        if do_redact:
            text = redact(text)
        digest = hashlib.sha1(re.sub(r"\W+", "", text.lower()).encode("utf-8")).hexdigest()
        if digest in seen:
            continue
        seen.add(digest)
        out.append({"text": text, "words": word_count(text),
                    "ts": rec.get("ts"), "ctx": rec.get("ctx")})
    return out


def write_jsonl(path, rows):
    directory = os.path.dirname(path)
    if directory and not os.path.isdir(directory):
        os.makedirs(directory)
    with open(path, "w") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def main():
    ap = argparse.ArgumentParser(description="Harvest your own writing into a corpus.")
    ap.add_argument("--source", required=True,
                    choices=["claude-history", "claude-projects", "chatgpt", "files", "stdin"])
    ap.add_argument("--path", help="File, dir, or glob (required for chatgpt/files)")
    ap.add_argument("--out", default=".being-human", help="Output directory (default: .being-human)")
    ap.add_argument("--append", action="store_true", help="Add to an existing corpus")
    ap.add_argument("--contrast", action="store_true",
                    help="Also collect the model's replies, to learn what you DON'T sound like")
    ap.add_argument("--min-words", type=int, default=4)
    ap.add_argument("--max-words", type=int, default=500)
    ap.add_argument("--no-redact", action="store_true", help="Skip secret redaction (not advised)")
    args = ap.parse_args()

    home = os.path.expanduser("~")
    corpus_path = os.path.join(args.out, "corpus.jsonl")
    model_path = os.path.join(args.out, "model.jsonl")

    seen = set()
    existing = []
    if args.append and os.path.exists(corpus_path):
        with open(corpus_path) as fh:
            for line in fh:
                try:
                    row = json.loads(line)
                except ValueError:
                    continue
                existing.append(row)
                seen.add(hashlib.sha1(
                    re.sub(r"\W+", "", row["text"].lower()).encode("utf-8")).hexdigest())

    if args.source == "claude-history":
        src = from_claude_history(os.path.join(home, ".claude", "history.jsonl"))
    elif args.source == "claude-projects":
        src = from_claude_projects(os.path.join(home, ".claude", "projects"))
    elif args.source == "chatgpt":
        if not args.path:
            ap.error("--path is required for chatgpt")
        src = from_chatgpt(os.path.expanduser(args.path))
    elif args.source == "files":
        if not args.path:
            ap.error("--path is required for files")
        src = from_files(os.path.expanduser(args.path))
    else:
        src = from_stdin()

    rows = collect(src, args.min_words, args.max_words, not args.no_redact, seen)
    all_rows = existing + rows
    write_jsonl(corpus_path, all_rows)

    total_words = sum(r["words"] for r in all_rows)
    print("corpus  %s" % corpus_path)
    print("  +%d new samples (%d total, %s words)" % (len(rows), len(all_rows), format(total_words, ",")))

    if args.contrast:
        if args.source == "claude-projects":
            msrc = from_claude_projects(os.path.join(home, ".claude", "projects"), role="assistant")
        elif args.source == "chatgpt":
            msrc = from_chatgpt(os.path.expanduser(args.path), role="assistant")
        else:
            msrc = iter([])
            print("  (contrast needs claude-projects or chatgpt -- skipped)")
        mrows = collect(msrc, args.min_words, 800, not args.no_redact, set())
        if mrows:
            write_jsonl(model_path, mrows)
            print("contrast %s" % model_path)
            print("  %d model samples (%s words)"
                  % (len(mrows), format(sum(r["words"] for r in mrows), ",")))

    if not all_rows:
        print("\nNothing found. Try a different --source, or lower --min-words.")
        return 1
    print("\nNext:  python3 scripts/analyze.py --in %s" % args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
