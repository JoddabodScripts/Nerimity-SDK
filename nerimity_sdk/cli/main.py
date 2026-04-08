"""CLI entry point: nerimity create <project-name>"""
from __future__ import annotations
import argparse
import os
import sys
import textwrap


_BOT_TEMPLATE = '''\
import os
from dotenv import load_dotenv
from nerimity_sdk import Bot

load_dotenv()
bot = Bot(token=os.environ["NERIMITY_TOKEN"], prefix="!")


@bot.on("ready")
async def on_ready(me):
    print(f"Logged in as {me.username}#{me.tag}")


@bot.command("ping", description="Replies with Pong!")
async def ping(ctx):
    await ctx.reply("Pong!")


@bot.command("help", description="Show available commands")
async def help_cmd(ctx):
    await ctx.reply(bot.router.help_text())


@bot.on_command_error
async def on_error(ctx, error):
    await ctx.reply(f"❌ {error}")


if __name__ == "__main__":
    bot.run()
'''

_PLUGIN_TEMPLATE = '''\
"""Example plugin — drop this in your plugins/ folder."""
from nerimity_sdk.plugins.manager import PluginBase, listener


class GreeterPlugin(PluginBase):
    name = "greeter"
    description = "Greets new members"

    @listener("server:member_joined")
    async def on_join(self, data):
        print(f"New member joined: {data}")

    async def on_ready(self):
        print(f"[{self.name}] Ready!")


async def setup(bot):
    await bot.plugins.load(GreeterPlugin())
'''

_GITIGNORE = "__pycache__/\n*.pyc\n.env\n"

_ENV_TEMPLATE = "NERIMITY_TOKEN=your_token_here\n"

_README = textwrap.dedent("""\
    # {name}

    A Nerimity bot built with [nerimity-sdk](https://github.com/your-repo).

    ## Setup

    ```bash
    pip install nerimity-sdk
    cp .env.example .env   # fill in your token
    python bot.py
    ```
""")


def create_project(name: str) -> None:
    base = os.path.join(os.getcwd(), name)
    if os.path.exists(base):
        print(f"Error: directory '{name}' already exists.", file=sys.stderr)
        sys.exit(1)

    dirs = [base, os.path.join(base, "plugins")]
    for d in dirs:
        os.makedirs(d, exist_ok=True)

    files = {
        "bot.py": _BOT_TEMPLATE,
        "plugins/greeter.py": _PLUGIN_TEMPLATE,
        ".gitignore": _GITIGNORE,
        ".env.example": _ENV_TEMPLATE,
        "README.md": _README.format(name=name),
    }
    for rel, content in files.items():
        path = os.path.join(base, rel)
        with open(path, "w") as f:
            f.write(content)

    print(f"✓ Created project '{name}'")
    print(f"  cd {name}")
    print(f"  pip install nerimity-sdk")
    print(f"  cp .env.example .env   # then add your token")
    print(f"  python bot.py")


def cli() -> None:
    parser = argparse.ArgumentParser(prog="nerimity", description="Nerimity SDK CLI")
    sub = parser.add_subparsers(dest="command")

    create_p = sub.add_parser("create", help="Scaffold a new bot project")
    create_p.add_argument("name", help="Project directory name")

    sub.add_parser("version", help="Show SDK version")

    args = parser.parse_args()

    if args.command == "create":
        create_project(args.name)
    elif args.command == "version":
        from nerimity_sdk import __version__
        print(f"nerimity-sdk {__version__}")
    else:
        parser.print_help()
