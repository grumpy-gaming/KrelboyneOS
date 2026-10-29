"""The stevie command: one question, or a chat when run on its own."""

import argparse
import sys
import threading
import time

from stevie import __version__, config
from stevie.agent import Agent
from stevie.providers import OpenAICompatible, ProviderError
from stevie.tools import TOOLS


class Spinner:
    """Shows 'Stevie is thinking... 12s' while waiting on the AI, so a slow model does not look frozen."""

    def __init__(self):
        self.enabled = sys.stderr.isatty()
        self.lock = threading.Lock()
        self.running = False
        self.thread = None

    def start(self):
        if self.enabled and not self.running:
            self.running = True
            self.began = time.monotonic()
            self.thread = threading.Thread(target=self.spin, daemon=True)
            self.thread.start()

    def stop(self):
        if self.running:
            self.running = False
            self.thread.join()
            self.clear()

    def spin(self):
        while self.running:
            with self.lock:
                if self.running:
                    sys.stderr.write(f"\r  Stevie is thinking... {time.monotonic() - self.began:.0f}s ")
                    sys.stderr.flush()
            time.sleep(0.5)

    def clear(self):
        sys.stderr.write("\r\033[K")
        sys.stderr.flush()

    def print(self, text):
        with self.lock:
            if self.running:
                self.clear()
            print(text, file=sys.stderr)


SPINNER = Spinner()


def confirm(tool, args):
    """Ask before a tool changes anything. Without a terminal to ask in, the answer is no."""
    if not sys.stdin.isatty():
        SPINNER.print(f"Stevie wanted to {tool.describe(args)}, but there is no terminal to ask you in, so it did not.")
        return False
    SPINNER.stop()
    try:
        answer = input(f"\nStevie wants to {tool.describe(args)}\nGo ahead? [y/N] ")
    except EOFError:
        answer = ""
    SPINNER.start()
    return answer.strip().lower() in ("y", "yes")


def show_tool(tool, args):
    if not tool.changes:
        detail = ", ".join(f"{k}={v}" for k, v in args.items())
        SPINNER.print(f"  (checking: {tool.name}{' ' + detail if detail else ''})")


def main(argv=None):
    parser = argparse.ArgumentParser(prog="stevie", description="Stevie, the KrelboyneOS assistant.")
    parser.add_argument("question", nargs="*", help="ask one question; leave out to chat")
    parser.add_argument("--provider", help=f"AI provider: {', '.join(config.PROVIDERS)}")
    parser.add_argument("--model", help="model name for that provider")
    parser.add_argument("--tools", action="store_true", help="list what Stevie can do, then exit")
    parser.add_argument("--version", action="version", version=f"stevie {__version__}")
    args = parser.parse_args(argv)

    if args.tools:
        for t in TOOLS:
            print(f"{t.name:20} {'asks first  ' if t.changes else 'read-only   '}{t.description}")
        return 0

    try:
        cfg = config.load(args.provider, args.model)
    except config.ConfigError as e:
        print(f"stevie: {e}", file=sys.stderr)
        return 1
    agent = Agent(OpenAICompatible(cfg), TOOLS, confirm)

    if args.question:
        return answer(agent, " ".join(args.question))

    print(f"Stevie here ({cfg.provider}, {cfg.model}). Ask away; 'exit' or Ctrl+D to leave.")
    while True:
        try:
            text = input("\nyou> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if text.lower() in ("exit", "quit", "bye"):
            return 0
        if text:
            answer(agent, text)


def answer(agent, text):
    SPINNER.start()
    try:
        reply = agent.ask(text, on_tool=show_tool)
    except ProviderError as e:
        SPINNER.stop()
        print(f"stevie: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        SPINNER.stop()
        print("\n(stopped)")
        return 130
    SPINNER.stop()
    print(f"\nStevie: {reply}")
    return 0
