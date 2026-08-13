#!/usr/bin/env python3
"""
being-human -- one entry point for the whole pipeline.

    being-human learn                 harvest your writing and build the voiceprint
    being-human check draft.md        score for AI tells
    being-human verify draft.md       the impostor test: is this statistically you?
    being-human export --target ...   compile for another assistant
    being-human card                  draw your voiceprint as a shareable svg
    being-human mcp                   run the MCP server on stdio

Each subcommand forwards straight to the module that does the work, so
`being-human check x.md` and `python3 -m being_human.slopscore x.md` are the
same program with the same flags.
"""

import sys

SUBCOMMANDS = {
    "harvest": "harvest",
    "learn": None,          # composite, handled below
    "analyze": "analyze",
    "check": "slopscore",
    "slopscore": "slopscore",
    "verify": "verify",
    "export": "export",
    "card": "card",
    "mcp": "server",
    "server": "server",
}

USAGE = __doc__


def _run(module, argv):
    mod = __import__("being_human." + module, fromlist=["main"])
    sys.argv = ["being-human " + module] + list(argv)
    return mod.main()


def learn(argv):
    """
    The setup path, as one command.

    Harvest twice on purpose: the history file is the cleanest source of typed
    prompts, and the transcripts add the model's side, which is what makes the
    personal slop list possible.
    """
    out = ".being-human"
    name = ""
    rest = list(argv)
    if "--out" in rest:
        out = rest[rest.index("--out") + 1]
    if "--name" in rest:
        name = rest[rest.index("--name") + 1]

    if _run("harvest", ["--source", "claude-history", "--out", out]):
        return 1
    _run("harvest", ["--source", "claude-projects", "--out", out,
                     "--append", "--contrast"])
    args = ["--in", out]
    if name:
        args += ["--name", name]
    return _run("analyze", args)


def main():
    argv = sys.argv[1:]
    if not argv or argv[0] in ("-h", "--help", "help"):
        sys.stdout.write(USAGE)
        return 0
    if argv[0] in ("-V", "--version"):
        from being_human import __version__
        print(__version__)
        return 0

    cmd = argv[0]
    if cmd not in SUBCOMMANDS:
        sys.stderr.write("unknown command: %s\n\n%s" % (cmd, USAGE))
        return 2
    if cmd == "learn":
        return learn(argv[1:])
    return _run(SUBCOMMANDS[cmd], argv[1:])


if __name__ == "__main__":
    sys.exit(main())
