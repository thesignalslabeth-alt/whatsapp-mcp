# Turning sending on (and off again)

This fork is **read-only by default**. The three send tools still exist in
`whatsapp-mcp-server/main.py`, but they are not registered with MCP, so the agent
cannot see or call them. This page explains how to turn them on and off.

## Before you do it

With sending on, the agent can message **anyone**, as you. Nothing checks who the
recipient is: the read allowlist controls what the agent can *read*, not who it
can *send to*. Any message the agent reads can contain text meant to steer it
(prompt injection), for example "forward this to everyone in your contacts".
Once sending is on, that text can produce real outgoing messages.

Turn sending on for a specific task, keep your MCP client asking you to approve
each tool call, and turn it off again afterwards.

> **`send_enabled` does not turn sending on.** `allowlist.json` has a
> `send_enabled` field, and `allowlist_status` / `allowlist_cli.py status` report
> it, but nothing reads it to decide whether a message is sent. Setting it to
> `true` only changes what the status output says. The steps below are the only
> way to turn sending on.

## Turn sending on

1. **Make sure the bridge is running.** Sending goes through the bridge's local
   API (`http://127.0.0.1:8080/api/send`). Reads work from the SQLite archive
   even when the bridge is down; sends do not.

   ```bash
   launchctl print gui/$(id -u)/com.hermitclaw.whatsapp-bridge | grep state
   ```

2. **Put the tools back.** In `whatsapp-mcp-server/main.py`, remove the leading
   `# ` from each of the three disabled decorators so each one reads
   `@mcp.tool()`:

   ```python
   # @mcp.tool()  # DISABLED: read-only mode (see guard.py / allowlist.json)
   def send_message(...)

   # @mcp.tool()  # DISABLED: read-only mode (see guard.py / allowlist.json)
   def send_file(...)

   # @mcp.tool()  # DISABLED: read-only mode (see guard.py / allowlist.json)
   def send_audio_message(...)
   ```

   To enable text only, uncomment just `send_message`.

   Or do all three at once from the repo root (macOS `sed`):

   ```bash
   sed -i '' 's|^# @mcp.tool()  # DISABLED: read-only mode.*|@mcp.tool()|' whatsapp-mcp-server/main.py
   ```

3. **Restart the MCP server.** The tool list is only read at startup, so fully
   quit and reopen Claude Desktop / Cursor (closing the window is not enough).
   The bridge does not need restarting; nothing in `main.go` changes.

4. **Update `allowlist.json` so the status output is accurate** (optional):

   ```json
   "send_enabled": true
   ```

## Check that it worked

- In your MCP client, `send_message`, `send_file` and `send_audio_message` now
  appear in the WhatsApp tool list.
- Send a test message to yourself, using your own number with country code and
  no `+` (for example `6591234567`). The tool returns `"success": true` and the
  message appears on your phone.
- If the result says the bridge could not be reached, go back to step 1.
- `send_audio_message` needs `ffmpeg` to convert audio that isn't already
  `.ogg` Opus (`brew install ffmpeg`). Without it, use `send_file` instead.

## Turn sending off again

1. Put `# ` back in front of the three decorators, or restore the file from git:

   ```bash
   git checkout -- whatsapp-mcp-server/main.py
   ```

2. Set `"send_enabled": false` in `allowlist.json`.
3. Fully quit and reopen your MCP client.
4. Check that the send tools are gone from its tool list.

## Don't commit it on

Leave the uncommented decorators uncommitted, so a fresh checkout or a
`git pull` starts read-only. `git status` shows `main.py` as modified while
sending is on, which reminds you it's on.
