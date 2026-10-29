"""The conversation loop: ask the AI, run the tools it asks for, repeat."""

import json
import platform

MAX_ROUNDS = 8  # tool rounds per question, so a confused model cannot loop forever

SYSTEM_PROMPT = """You are Stevie, the assistant built into KrelboyneOS (KOS), a Debian 13 based distro for developers and security learners.
You run on the user's own computer ({host}) and can use tools to look at and change it.

Rules:
- You know nothing about this computer except what tools tell you. Use a tool before saying anything about its files, packages, services or hardware.
- Prefer the specific tools; use run_command only when nothing else fits.
- Tools that change the system ask the user first. If they decline, accept it and suggest what they could do instead.
- KOS Doctor (kos_doctor_check) is the first place to look when something seems wrong: it covers updates, sound, the clock (time sync), broken packages, disk space and more, and its check ids can be fixed with kos_doctor_fix.
- Judge what you read, do not just repeat it: a battery holding under 80% of its original charge is worn; a disk over 90% full needs attention.
- Say only what a tool showed. "Installed" does not mean "running".
- Be brief and direct. Explain enough to understand, without beginner-level padding.
"""


class Agent:
    def __init__(self, provider, tools, confirm):
        """confirm(tool, args) -> bool is asked before any tool that changes the system."""
        self.provider = provider
        self.tools = {t.name: t for t in tools}
        self.confirm = confirm
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT.format(host=platform.node())}]

    def ask(self, text, on_tool=None):
        """Answer one user message, running tools as needed. Returns the reply text."""
        self.messages.append({"role": "user", "content": text})
        schemas = [t.schema() for t in self.tools.values()]
        for _ in range(MAX_ROUNDS):
            reply = self.provider.chat(self.messages, schemas)
            calls = reply.get("tool_calls") or []
            self.messages.append({"role": "assistant", "content": reply.get("content") or "",
                                  **({"tool_calls": calls} if calls else {})})
            if not calls:
                return (reply.get("content") or "").strip()
            for call in calls:
                result = self.call_tool(call, on_tool)
                self.messages.append({"role": "tool", "tool_call_id": call.get("id", ""),
                                      "name": call["function"]["name"], "content": result})
        return "I went round in circles with the tools and stopped. Try asking more specifically."

    def call_tool(self, call, on_tool):
        name = call["function"]["name"]
        tool = self.tools.get(name)
        if not tool:
            return f"There is no tool called {name}."
        raw = call["function"].get("arguments") or "{}"
        try:
            args = json.loads(raw) if isinstance(raw, str) else dict(raw)
        except json.JSONDecodeError:
            return f"The arguments were not valid JSON: {raw}"
        allowed = {k: v for k, v in args.items() if k in tool.params}
        missing = [k for k in tool.required if k not in allowed]
        if missing:
            return f"Missing required argument(s): {', '.join(missing)}"
        if tool.changes and not self.confirm(tool, allowed):
            return "The user said no, so nothing was done."
        if on_tool:
            on_tool(tool, allowed)
        try:
            return tool.run(**allowed)
        except Exception as e:  # a broken tool should not end the conversation
            return f"The tool failed: {type(e).__name__}: {e}"
