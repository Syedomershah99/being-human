# being-human as an MCP server

Exposes the voiceprint to any MCP client. One file, stdlib only, no SDK and no
`pip install` — it speaks JSON-RPC over stdio directly.

```bash
python3 mcp/server.py
```

Nothing happens when you run it by hand. That's correct: it waits on stdin for a
client to speak first.

## what it exposes

**Tools**

| tool | what it does |
| --- | --- |
| `voice_get` | the voice rules, to load before drafting |
| `voice_score` | score a draft 0-100 for AI tells, with line-level findings |
| `voice_verify` | the impostor test: is this text statistically you? |
| `voice_status` | is a voiceprint built, and is the corpus big enough to trust |
| `voice_learn` | build or refresh from history, a ChatGPT export, or your files |
| `voice_note` | record something measurement can't reach; survives rebuilds |
| `voice_export` | compile for ChatGPT, Cursor, AGENTS.md, or a raw system prompt |

**Resources** — `voiceprint://current` (markdown), `voiceprint://metrics` (json)

`voice_score` and `voice_verify` catch different failures. A draft has to pass
both: clean prose by a different hand clears the first and fails the second.

**Prompts** — `write_in_voice`, `check_draft`

## the design problem, and what it does about it

MCP tools are model-invoked. Nothing makes a model call one.

That's a real problem here, because being-human's payload is instructional: the voice
rules have to be in context *before* drafting, not available on request
afterwards. A server that only answers when asked will sit idle while the model
writes in its default voice and you assume it's working.

Three mitigations, layered, because no single one holds across every client:

1. **The `instructions` field.** Returned during initialize. Clients that
   surface it put a standing directive in the system prompt. Support varies, so
   this is a bonus rather than the mechanism.

2. **Every tool returns the rules.** Call the scorer, get the rules. Check
   status, get the rules. There is no path through this server that hands back a
   score without also handing back the target. This is deliberate duplication —
   a model that called one tool shouldn't need to know to call a second one to
   get the thing that changes its output.

3. **Situation-shaped tool descriptions.** They trigger on "before writing
   anything the user will send under their own name" rather than on a noun.
   Descriptions are the only real lever on model-side invocation.

Even so: in Claude Code the skill is the stronger guarantee, because skills
auto-trigger on description match. Install both there. The MCP server is what
makes the voiceprint portable everywhere else.

## setup

Use the absolute path to `server.py`. Replace `/path/to/being-human` throughout.

**Claude Code**

```bash
claude mcp add being-human -- python3 /path/to/being-human/mcp/server.py
```

**Claude Desktop** — `claude_desktop_config.json`

```json
{
  "mcpServers": {
    "being-human": {
      "command": "python3",
      "args": ["/path/to/being-human/mcp/server.py"]
    }
  }
}
```

**Cursor** — `~/.cursor/mcp.json`, or `.cursor/mcp.json` in a project

```json
{
  "mcpServers": {
    "being-human": {
      "command": "python3",
      "args": ["/path/to/being-human/mcp/server.py"]
    }
  }
}
```

**Codex** — `~/.codex/config.toml`

```toml
[mcp_servers.being-human]
command = "python3"
args = ["/path/to/being-human/mcp/server.py"]
```

**Zed** — `settings.json`

```json
{
  "context_servers": {
    "being-human": {
      "command": { "path": "python3", "args": ["/path/to/being-human/mcp/server.py"] }
    }
  }
}
```

Any other MCP client works the same way: a `command` and `args` pointing at
`server.py`.

## where the voiceprint lives

First match wins:

1. `$BEING_HUMAN_DIR`
2. `./.being-human` in the working directory, if it already exists
3. `~/.being-human`

Set `BEING_HUMAN_DIR` explicitly if you want one voice shared across every client:

```json
{
  "mcpServers": {
    "being-human": {
      "command": "python3",
      "args": ["/path/to/being-human/mcp/server.py"],
      "env": { "BEING_HUMAN_DIR": "/Users/you/.being-human" }
    }
  }
}
```

## publishing to the MCP registry

Verified against the live schema
(`https://static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json`)
rather than remembered, because this moves. The registry is in preview under an
API freeze at v0.1.

Install the publisher:

```bash
brew install mcp-publisher
```

Then, from the repo root:

```bash
mcp-publisher login github
mcp-publisher publish
```

`server.json` is filled in as `io.github.Syedomershah99/being-human`, published
and active. Fork-and-publish means changing that line to your own username.

**The namespace is case-sensitive, and it must match your GitHub login exactly.**
This is worth stating plainly because the obvious inference is wrong. Reverse-DNS
convention is lowercase, the schema pattern `^[a-zA-Z0-9.-]+/...` permits either,
and a large sample of live registry names is entirely lowercase -- so lowercase
looks right. It is not. The token issued by `mcp-publisher login github` grants
`io.github.<YourExactLogin>/*`, and publishing under any other casing fails:

```
403 Forbidden: You do not have permission to publish this server.
You have permission to publish: io.github.Syedomershah99/*
Attempting to publish: io.github.syedomershah99/being-human
```

`validate` passes either way -- it checks the schema, not your grant -- so this
only surfaces at publish time. Use your login's exact casing from the start.
GitHub URLs elsewhere in the file are genuinely case-insensitive.

Only `name`, `description`, and `version` are required. `packages` is optional,
which is why the shipped manifest omits it: this server is a single Python file
run from a clone, not a published artifact.

The tradeoff is real, so it's worth stating. A manifest without `packages` gets
you listed and discoverable, but clients can't one-command install it — people
clone and point at `server.py`. To get `uvx being-human` working you'd publish
to PyPI first (the name is currently free), then add:

```json
"packages": [
  {
    "registryType": "pypi",
    "identifier": "being-human",
    "version": "0.1.0",
    "runtimeHint": "uvx",
    "transport": { "type": "stdio" }
  }
]
```

That needs a `pyproject.toml` and a console entry point, which the repo does not
have yet. Listed-but-clone-to-install is the honest starting state.

Other directories worth submitting to once the GitHub repo is public: Smithery,
mcp.so, Glama, and PulseMCP. Each has its own submission form; none of them were
verifiable in this session, so check their current process rather than trusting
this list.

## privacy

stdio, local, single-user by design.

This is not a hosted service and shouldn't become one. The corpus is your raw
prompt history — running it remotely would mean uploading exactly the thing the
project exists to keep on your machine. Every user runs their own copy against
their own corpus, which is also why "multi-user" here means "many people install
it", not "one server holds many people's writing".

## checking it works

```bash
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"t","version":"1"}}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' \
  | python3 mcp/server.py
```

Two JSON lines back means it's healthy. Diagnostics go to stderr; stdout carries
protocol traffic only.
