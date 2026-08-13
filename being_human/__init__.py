"""
being-human -- learn a writing voice from your own prompt history.

The modules here are also runnable directly:

    python3 -m being_human.harvest   --source claude-history --out .being-human/
    python3 -m being_human.analyze   --in .being-human/
    python3 -m being_human.slopscore draft.md --in .being-human/
    python3 -m being_human.verify    draft.md --in .being-human/
    python3 -m being_human.export    --target chatgpt
    python3 -m being_human.server                      # the MCP server

or through the `being-human` console script, which wraps all of the above.
"""

__version__ = "0.1.0"
