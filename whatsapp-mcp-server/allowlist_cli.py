#!/usr/bin/env python3
"""Manage the WhatsApp MCP read allowlist.

Deliberately a command you run, not an MCP tool. The agent can propose chats to
allow; granting access stays a human action, so no amount of injected text in a
message can widen what the agent is permitted to read.

    ./allowlist_cli.py status
    ./allowlist_cli.py search "family"
    ./allowlist_cli.py add 6591234567@s.whatsapp.net
    ./allowlist_cli.py remove 6591234567@s.whatsapp.net
"""

import json
import sys

import guard
import whatsapp


def _save(cfg):
    with open(guard.CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)


def _load_raw():
    try:
        with open(guard.CONFIG_PATH) as f:
            return json.load(f)
    except FileNotFoundError:
        return {"read_allowlist": [], "send_enabled": False}


def cmd_status():
    st = whatsapp.allowlist_status()
    print(f"config:       {st['config_path']}")
    print(f"status:       {st['status']}")
    print(f"readable:     {st['allowed_chats']} chats")
    print(f"quarantined:  {st['quarantined_chats']} chats")
    print(f"sending:      {'ENABLED' if st['send_enabled'] else 'disabled'}")
    if st["allowed_jids"]:
        print("\nallowed:")
        for jid in st["allowed_jids"]:
            print(f"  {jid}")


def cmd_search(query):
    rows = whatsapp.find_chat(query, limit=25)
    if not rows:
        print("no matches")
        return
    print(f"{'':3}{'kind':7}{'msgs':>7}  {'last':10}  name")
    print("-" * 70)
    for r in rows:
        mark = "[x]" if r["allowed"] else "[ ]"
        last = str(r["last_message_time"] or "")[:10]
        print(f"{mark}{r['kind']:7}{r['message_count']:>7}  {last:10}  {r['name'][:30]}")
        print(f"       {r['jid']}")


def cmd_add(jid):
    cfg = _load_raw()
    if jid in cfg["read_allowlist"]:
        print(f"already allowed: {jid}")
        return
    cfg["read_allowlist"].append(jid)
    _save(cfg)
    print(f"allowed: {jid}")
    print("restart Claude Code for the change to take effect")


def cmd_remove(jid):
    cfg = _load_raw()
    if jid not in cfg["read_allowlist"]:
        print(f"not in allowlist: {jid}")
        return
    cfg["read_allowlist"].remove(jid)
    _save(cfg)
    print(f"removed: {jid}")
    print("restart Claude Code for the change to take effect")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    cmd, args = sys.argv[1], sys.argv[2:]
    if cmd == "status":
        cmd_status()
    elif cmd == "search" and args:
        cmd_search(args[0])
    elif cmd == "add" and args:
        cmd_add(args[0])
    elif cmd == "remove" and args:
        cmd_remove(args[0])
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
