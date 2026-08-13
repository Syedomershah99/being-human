#!/usr/bin/env python3
"""
being-human MCP server -- the voiceprint, exposed to any MCP client.

Speaks JSON-RPC 2.0 over stdio directly rather than importing the MCP SDK. That
keeps the whole project installable with nothing but a python3 binary, which
matters more here than SDK ergonomics: the people who most want this are the
ones who won't set up a virtualenv to try it.

The design problem this server has to solve:

    MCP tools are model-invoked. Nothing forces a model to call one. But
    being-human's payload is INSTRUCTIONAL -- the voice rules have to be in context
    *before* drafting, not available on request afterwards. A server that only
    answers when asked will sit unused while the model writes in its default
    voice and the user assumes the tool is working.

Three mitigations, layered, because no single one is reliable across clients:

  1. `instructions` in the initialize response. Clients that surface it put a
     standing directive in the system prompt. Support varies; treat as a bonus.
  2. Every tool that returns anything also returns the voice rules. Call the
     scorer, get the rules. Check status, get the rules. There is no path
     through this server that leaves the model holding a score but no voice.
  3. Tool descriptions written to trigger on the situation ("before writing
     anything the user will send under their own name") rather than on the
     noun. Descriptions are the only lever on model-side invocation.

Everything runs locally. No network. The corpus never leaves the machine.

Run:
  python3 mcp/server.py

Register (Claude Code):
  claude mcp add being-human -- python3 /absolute/path/to/being-human/mcp/server.py
"""

import json
import os
import subprocess
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SCRIPTS = os.path.join(ROOT, "scripts")

# Newest first. We echo back whatever the client asks for if we know it.
SUPPORTED_PROTOCOLS = ["2025-06-18", "2025-03-26", "2024-11-05"]

SERVER_INSTRUCTIONS = """\
This server holds a measured description of how THIS USER writes, derived from \
their own past writing.

Before you draft any prose the user will send or publish under their own name -- \
posts, emails, replies, bios, docs, commit messages, cover letters -- call \
`voice_get` first and follow the rules it returns. They were measured from the \
user's actual writing, so where they conflict with your defaults, they win.

After drafting, call BOTH `voice_score` (catches AI tells) and `voice_verify` \
(catches text that is clean but reads as a different person). They measure \
different failures and a draft has to pass both. Revise and re-run before showing \
the user. Do not skip this: generated prose reads fluent to the model that generated \
it, which is exactly why an external check is needed.

This governs voice only. Never bend a fact, invent an anecdote, or add a number \
you do not have in order to fit the style.\
"""


def voice_dir():
    env = os.environ.get("BEING_HUMAN_DIR")
    if env:
        return os.path.expanduser(env)
    local = os.path.join(os.getcwd(), ".being-human")
    if os.path.isdir(local):
        return local
    return os.path.join(os.path.expanduser("~"), ".being-human")


def log(msg):
    """stderr only. Anything on stdout corrupts the JSON-RPC stream."""
    sys.stderr.write("[being-human] %s\n" % msg)
    sys.stderr.flush()


def run(args, timeout=180):
    try:
        proc = subprocess.run(
            [sys.executable] + args, capture_output=True, text=True,
            timeout=timeout, cwd=ROOT)
        return proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired:
        return 1, "", "timed out after %ss" % timeout
    except Exception as exc:
        return 1, "", str(exc)


def read_voiceprint():
    path = os.path.join(voice_dir(), "voiceprint.md")
    try:
        with open(path) as fh:
            return fh.read()
    except IOError:
        return None


def read_metrics():
    path = os.path.join(voice_dir(), "metrics.json")
    try:
        with open(path) as fh:
            return json.load(fh)
    except (IOError, ValueError):
        return None


def rules_block():
    """
    The instructional payload, appended to every successful tool result.

    This is deliberate duplication. A model that called one tool should not have
    to know to call a second one to get the thing that actually changes its
    output.
    """
    code, out, _ = run([os.path.join(SCRIPTS, "export.py"),
                        "--in", voice_dir(), "--target", "system"])
    if code == 0 and out.strip():
        return out.strip()
    vp = read_voiceprint()
    if vp:
        return vp
    return None


def with_rules(body):
    rules = rules_block()
    if not rules:
        return body + (
            "\n\n---\nNo voiceprint exists yet. Call `voice_learn` to build one "
            "from the user's own writing, or ask them to paste a few things they "
            "have written.")
    return body + "\n\n--- the user's measured voice, follow this ---\n\n" + rules


# ----------------------------------------------------------------- the tools

TOOLS = [
    {
        "name": "voice_get",
        "description": (
            "Get the user's measured writing voice as explicit rules. CALL THIS BEFORE "
            "writing any prose the user will send or publish under their own name -- a "
            "post, email, reply, bio, doc, commit message, cover letter, or anything "
            "else in their name. The rules are measured from their own past writing "
            "(sentence rhythm, casing, punctuation rates, vocabulary, words to avoid), "
            "so they override your defaults. Cheap and fast; call it rather than "
            "guessing what the user sounds like."
        ),
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "voice_score",
        "description": (
            "Score a draft 0-100 for AI tells and get line-level findings. CALL THIS ON "
            "EVERY DRAFT before showing it to the user. Checks a curated slop lexicon "
            "plus structural signals -- sentence-length uniformity, paragraph shape, "
            "bullet symmetry, punctuation rates -- against THIS user's own measured "
            "baseline rather than universal rules. Above 85 reads human, below 50 is "
            "slop. Also returns the voice rules, so one call gives you both the "
            "critique and the target."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "The draft text to score."},
                "path": {"type": "string",
                         "description": "Path to a file to score, instead of text."},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "voice_verify",
        "description": (
            "The impostor test: statistically, is this text a plausible sample of THIS "
            "user? Returns an authorship percentile against a null resampled from their "
            "own writing at the same length. Under 75 means indistinguishable from them; "
            "over 97 means it reads as someone else. This is a different question from "
            "voice_score -- that one catches AI tells, this one catches 'fluent, clean, "
            "and not you'. Run BOTH on any draft before showing it; a draft has to pass "
            "each. Also names the specific words that pushed it out of range."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "The draft text to test."},
                "path": {"type": "string", "description": "Path to a file, instead of text."},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "voice_status",
        "description": (
            "Check whether a voiceprint exists and how solid it is: sample count, word "
            "count, when it was built, and whether the corpus is large enough for the "
            "measurements to be stable. Use this when you are not sure the user has set "
            "being-human up yet."
        ),
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "voice_learn",
        "description": (
            "Build or refresh the voiceprint from the user's own writing. Sources: "
            "'claude-history' and 'claude-projects' (local Claude Code history), "
            "'chatgpt' (a conversations.json from a ChatGPT data export, needs path), "
            "'files' (a folder of the user's own writing, needs path). Takes a few "
            "seconds. Run this once at setup, or again to fold in newer writing."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "enum": ["claude-history", "claude-projects", "chatgpt", "files"],
                    "description": "Where to harvest from.",
                },
                "path": {"type": "string",
                         "description": "Required for 'chatgpt' and 'files'."},
                "name": {"type": "string", "description": "The user's name, for labelling."},
                "append": {"type": "boolean",
                           "description": "Add to the existing corpus instead of replacing."},
            },
            "required": ["source"],
            "additionalProperties": False,
        },
    },
    {
        "name": "voice_note",
        "description": (
            "Record something about the user's voice that measurement cannot reach -- a "
            "phrase they have banned, who they are usually writing for, a correction "
            "they just made to your draft, a running joke. Use this whenever the user "
            "says 'I wouldn't say that', 'too formal', or rewrites something you wrote. "
            "Notes persist across every rebuild of the voiceprint and tend to matter "
            "more than the statistics."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "note": {"type": "string",
                         "description": "The rule or observation, in one or two sentences."},
            },
            "required": ["note"],
            "additionalProperties": False,
        },
    },
    {
        "name": "voice_export",
        "description": (
            "Compile the voiceprint into a format another tool reads: 'chatgpt' (custom "
            "instructions box, ~1500 chars), 'agents' (AGENTS.md), 'cursor' "
            "(.cursorrules), 'claude' (CLAUDE.md), 'system' (raw system prompt), or "
            "'json'. Use when the user wants their voice set up in a different "
            "assistant."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "enum": ["chatgpt", "claude", "agents", "cursor", "system", "json"],
                },
            },
            "required": ["target"],
            "additionalProperties": False,
        },
    },
]


def tool_voice_get(_args):
    vp = read_voiceprint()
    if not vp:
        return ("No voiceprint yet. Call `voice_learn` with source 'claude-history' "
                "to build one from the user's own prompt history, or ask them to "
                "paste a few things they have written.")
    return with_rules("The user's voiceprint, in full:\n\n" + vp)


def tool_voice_status(_args):
    directory = voice_dir()
    mx = read_metrics()
    corpus = os.path.join(directory, "corpus.jsonl")
    n_lines = 0
    if os.path.exists(corpus):
        try:
            with open(corpus) as fh:
                n_lines = sum(1 for _ in fh)
        except IOError:
            pass

    if not mx:
        return ("No voiceprint built yet.\n"
                "  directory: %s\n"
                "  corpus samples: %d\n\n"
                "Call `voice_learn` to build one." % (directory, n_lines))

    m = mx.get("metrics", {})
    words = m.get("words", 0)
    stable = "yes" if words >= 3000 else "NO -- under 3,000 words, treat rhythm figures as noisy"
    lines = [
        "Voiceprint is built.",
        "  directory:      %s" % directory,
        "  built:          %s" % mx.get("generated", "unknown"),
        "  samples:        %s (corpus now holds %d)" % (format(m.get("samples", 0), ","), n_lines),
        "  words:          %s" % format(words, ","),
        "  measurements stable: %s" % stable,
        "  personal slop list:  %s" % ("yes" if mx.get("slop_candidates") else
                                       "no -- re-harvest with --contrast to build it"),
    ]
    return with_rules("\n".join(lines))


def tool_voice_score(args):
    text, path = args.get("text"), args.get("path")
    if not text and not path:
        return "Give me either `text` or `path`."

    tmp = None
    if not path:
        tmp = os.path.join(voice_dir(), ".score-tmp.md")
        directory = os.path.dirname(tmp)
        if not os.path.isdir(directory):
            os.makedirs(directory)
        with open(tmp, "w") as fh:
            fh.write(text)
        path = tmp

    code, out, err = run([os.path.join(SCRIPTS, "slopscore.py"), path,
                          "--in", voice_dir(), "--json"])
    if tmp and os.path.exists(tmp):
        try:
            os.remove(tmp)
        except OSError:
            pass

    if code not in (0, 1) or not out.strip():
        return "Scoring failed: %s" % (err.strip() or "no output")

    try:
        data = json.loads(out)
    except ValueError:
        return "Scoring returned unparseable output:\n%s" % out[:800]

    lines = ["%d/100  --  %s" % (data["score"], data["verdict"]),
             "%d words, %d tells" % (data["words"], len(data["findings"]))]
    if not data.get("personalized"):
        lines.append("(generic thresholds -- no voiceprint loaded, so punctuation "
                     "checks are not calibrated to this user)")
    lines.append("")
    for f in data["findings"][:30]:
        where = ("line %d" % f["line"]) if f["line"] else "whole draft"
        lines.append("  [%s] %s -- %s" % (where, f["label"], f["fix"]))
    if len(data["findings"]) > 30:
        lines.append("  ... and %d more" % (len(data["findings"]) - 30))
    if data["score"] < 85:
        lines.append("")
        lines.append("Revise and score again before showing the user. Fix the writing, "
                     "not the score -- swapping flagged words for unflagged synonyms "
                     "raises the number without making the text any more theirs.")
    return with_rules("\n".join(lines))


def tool_voice_learn(args):
    source = args["source"]
    path = args.get("path")
    if source in ("chatgpt", "files") and not path:
        return "Source '%s' needs a `path`." % source

    directory = voice_dir()
    harvest = [os.path.join(SCRIPTS, "harvest.py"), "--source", source, "--out", directory]
    if path:
        harvest += ["--path", os.path.expanduser(path)]
    if args.get("append"):
        harvest.append("--append")
    if source in ("claude-projects", "chatgpt"):
        harvest.append("--contrast")

    code, out, err = run(harvest)
    if code != 0:
        return "Harvest failed: %s" % (err.strip() or out.strip() or "unknown error")

    analyze = [os.path.join(SCRIPTS, "analyze.py"), "--in", directory]
    if args.get("name"):
        analyze += ["--name", args["name"]]
    code2, out2, err2 = run(analyze)
    if code2 != 0:
        return "Harvest worked but analysis failed: %s" % (err2.strip() or out2.strip())

    return with_rules("Voiceprint rebuilt.\n\n%s\n%s" % (out.strip(), out2.strip()))


def tool_voice_note(args):
    note = (args.get("note") or "").strip()
    if not note:
        return "Empty note."
    path = os.path.join(voice_dir(), "voiceprint.md")
    if not os.path.exists(path):
        return "No voiceprint yet. Call `voice_learn` first."
    try:
        with open(path) as fh:
            doc = fh.read()
        if "## notes" not in doc:
            doc = doc.rstrip() + "\n\n## notes\n"
        doc = doc.rstrip() + "\n- " + note + "\n"
        with open(path, "w") as fh:
            fh.write(doc)
    except IOError as exc:
        return "Could not write the note: %s" % exc
    return "Noted. This survives every rebuild of the voiceprint."


def tool_voice_export(args):
    code, out, err = run([os.path.join(SCRIPTS, "export.py"),
                          "--in", voice_dir(), "--target", args["target"]])
    if code != 0:
        return "Export failed: %s" % (err.strip() or "unknown error")
    return out


def tool_voice_verify(args):
    text, path = args.get("text"), args.get("path")
    if not text and not path:
        return "Give me either `text` or `path`."
    tmp = None
    if not path:
        tmp = os.path.join(voice_dir(), ".verify-tmp.md")
        directory = os.path.dirname(tmp)
        if not os.path.isdir(directory):
            os.makedirs(directory)
        with open(tmp, "w") as fh:
            fh.write(text)
        path = tmp

    code, out, err = run([os.path.join(SCRIPTS, "verify.py"), path,
                          "--in", voice_dir(), "--json"])
    if tmp and os.path.exists(tmp):
        try:
            os.remove(tmp)
        except OSError:
            pass
    if code != 0 or not out.strip():
        return "Verification failed: %s" % (err.strip() or "no output")
    try:
        d = json.loads(out)
    except ValueError:
        return "Verification returned unparseable output:\n%s" % out[:600]

    lines = ["authorship: %.0fth percentile -- %s" % (d["percentile"], d["verdict"]),
             "delta %.2f against %d same-length samples of the user "
             "(their median %.2f, p97 %.2f)"
             % (d["delta"], d["null_size"], d["null_median"], d["null_p97"])]
    if d["words"] < 40:
        lines.append("(very short text -- treat this loosely)")
    if d.get("drivers"):
        lines.append("")
        lines.append("words that pushed it out of range:")
        for x in d["drivers"]:
            lines.append("  %-12s %+.1f sd %s   draft %.1f/1k, them %.1f/1k"
                         % (x["word"], x["z"], x["direction"],
                            x["draft_per_1k"], x["you_per_1k"]))
    if d["percentile"] > 90:
        lines.append("")
        lines.append("This reads as a different hand. Rework it toward their habits and "
                     "test again. Note this measures authorship, not tells -- run "
                     "voice_score too.")
    return with_rules("\n".join(lines))


HANDLERS = {
    "voice_get": tool_voice_get,
    "voice_score": tool_voice_score,
    "voice_verify": tool_voice_verify,
    "voice_status": tool_voice_status,
    "voice_learn": tool_voice_learn,
    "voice_note": tool_voice_note,
    "voice_export": tool_voice_export,
}

RESOURCES = [
    {
        "uri": "voiceprint://current",
        "name": "voiceprint",
        "title": "The user's measured writing voice",
        "description": ("Sentence rhythm, casing, punctuation rates, vocabulary, and "
                        "words to avoid, measured from the user's own writing. Attach "
                        "this before drafting anything in their name."),
        "mimeType": "text/markdown",
    },
    {
        "uri": "voiceprint://metrics",
        "name": "metrics",
        "title": "Raw voiceprint measurements",
        "description": "Full statistics: per-register figures, log-odds tables, openers.",
        "mimeType": "application/json",
    },
]

PROMPTS = [
    {
        "name": "write_in_voice",
        "title": "Write in my voice",
        "description": "Draft something in the user's measured voice, then verify it.",
        "arguments": [{"name": "task", "description": "What to write.", "required": True}],
    },
    {
        "name": "check_draft",
        "title": "Check this draft",
        "description": "Score a draft for AI tells against the user's baseline and fix it.",
        "arguments": [{"name": "draft", "description": "The text to check.", "required": True}],
    },
]


def build_prompt(name, args):
    args = args or {}
    if name == "write_in_voice":
        text = (
            "Write this in my voice: %s\n\n"
            "First call `voice_get` and read the rules. Match the rhythm figure "
            "deliberately -- uniform sentence length is the strongest tell and the "
            "easiest to miss. Then call `voice_score` on your draft and revise until "
            "it clears 85. Show me the draft and the score together.\n\n"
            "Match the voice, never a fact. If the voice wants a specific detail you "
            "do not have, ask me for it rather than inventing one."
        ) % args.get("task", "")
    elif name == "check_draft":
        text = (
            "Score this draft with `voice_score`, then walk me through it:\n\n%s\n\n"
            "Lead with the structural findings -- rhythm, paragraph shape, bullet "
            "symmetry -- before the word-level ones. A draft can have zero flagged "
            "phrases and still read as generated because every sentence is the same "
            "length. Then offer to fix it."
        ) % args.get("draft", "")
    else:
        return None
    return {"messages": [{"role": "user", "content": {"type": "text", "text": text}}]}


# ----------------------------------------------------------------- transport


def result(rid, payload):
    return {"jsonrpc": "2.0", "id": rid, "result": payload}


def error(rid, code, message):
    return {"jsonrpc": "2.0", "id": rid, "error": {"code": code, "message": message}}


def handle(msg):
    """Returns a response dict, or None for notifications."""
    method = msg.get("method")
    rid = msg.get("id")
    params = msg.get("params") or {}
    is_notification = rid is None

    if method == "initialize":
        wanted = params.get("protocolVersion")
        version = wanted if wanted in SUPPORTED_PROTOCOLS else SUPPORTED_PROTOCOLS[0]
        return result(rid, {
            "protocolVersion": version,
            "capabilities": {
                "tools": {"listChanged": False},
                "resources": {"listChanged": False, "subscribe": False},
                "prompts": {"listChanged": False},
            },
            "serverInfo": {"name": "being-human", "version": "0.1.0",
                           "title": "being-human -- write in the user's own voice"},
            "instructions": SERVER_INSTRUCTIONS,
        })

    if is_notification:
        return None  # initialized, cancelled, progress: nothing to answer

    if method == "ping":
        return result(rid, {})

    if method == "tools/list":
        return result(rid, {"tools": TOOLS})

    if method == "tools/call":
        name = params.get("name")
        handler = HANDLERS.get(name)
        if not handler:
            return error(rid, -32602, "Unknown tool: %s" % name)
        try:
            text = handler(params.get("arguments") or {})
            return result(rid, {"content": [{"type": "text", "text": text}]})
        except Exception as exc:
            log("tool %s failed:\n%s" % (name, traceback.format_exc()))
            # Tool failures are reported in-band so the model can recover,
            # rather than as protocol errors that abort the call.
            return result(rid, {
                "content": [{"type": "text", "text": "%s failed: %s" % (name, exc)}],
                "isError": True,
            })

    if method == "resources/list":
        return result(rid, {"resources": RESOURCES})

    if method == "resources/templates/list":
        return result(rid, {"resourceTemplates": []})

    if method == "resources/read":
        uri = params.get("uri")
        if uri == "voiceprint://current":
            vp = read_voiceprint()
            if vp is None:
                return error(rid, -32002, "No voiceprint yet. Run the voice_learn tool.")
            return result(rid, {"contents": [
                {"uri": uri, "mimeType": "text/markdown", "text": vp}]})
        if uri == "voiceprint://metrics":
            mx = read_metrics()
            if mx is None:
                return error(rid, -32002, "No metrics yet. Run the voice_learn tool.")
            return result(rid, {"contents": [
                {"uri": uri, "mimeType": "application/json",
                 "text": json.dumps(mx, indent=2)}]})
        return error(rid, -32002, "Unknown resource: %s" % uri)

    if method == "prompts/list":
        return result(rid, {"prompts": PROMPTS})

    if method == "prompts/get":
        built = build_prompt(params.get("name"), params.get("arguments"))
        if built is None:
            return error(rid, -32602, "Unknown prompt: %s" % params.get("name"))
        return result(rid, built)

    return error(rid, -32601, "Method not found: %s" % method)


def main():
    log("ready (voice dir: %s)" % voice_dir())
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except ValueError:
            sys.stdout.write(json.dumps(
                {"jsonrpc": "2.0", "id": None,
                 "error": {"code": -32700, "message": "Parse error"}}) + "\n")
            sys.stdout.flush()
            continue

        try:
            response = handle(msg)
        except Exception:
            log("handler crashed:\n%s" % traceback.format_exc())
            response = error(msg.get("id"), -32603, "Internal error")

        if response is not None:
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(0)
