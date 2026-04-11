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
bot = Bot(token=os.environ["NERIMITY_TOKEN"], prefix="/")


@bot.on("ready")
async def on_ready(me):
    print(f"Logged in as {me.username}#{me.tag}")


@bot.command("ping", description="Replies with Pong!")
async def ping(ctx):
    await ctx.reply("Pong!")


@bot.command_private("help", description="Show available commands")
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

_ENV_TEMPLATE = (
    "# Get your token at: https://nerimity.com/app/settings/developer/applications\n"
    "# Create an application → add a Bot → copy the token\n"
    "NERIMITY_TOKEN=your_token_here\n"
)

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

    lint_p = sub.add_parser("lint", help="Check bot code for common mistakes")
    lint_p.add_argument("paths", nargs="*", default=["."], help="Files or directories to lint")

    dev_p = sub.add_parser("dev", help="Run bot in development mode (debug + watch + pretty logs)")
    dev_p.add_argument("file", nargs="?", default="bot.py", help="Bot file to run (default: bot.py)")

    test_p = sub.add_parser("test", help="Run bot tests (pytest wrapper)")
    test_p.add_argument("paths", nargs="*", default=["tests/"], help="Test paths (default: tests/)")
    test_p.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    deploy_p = sub.add_parser("deploy", help="Deploy bot to a hosting provider")
    deploy_p.add_argument("target", nargs="?", default="railway",
                          choices=["railway", "fly", "render"],
                          help="Hosting provider (default: railway)")

    args = parser.parse_args()

    if args.command == "create":
        create_project(args.name)
    elif args.command == "version":
        from nerimity_sdk import __version__
        print(f"nerimity-sdk {__version__}")
    elif args.command == "lint":
        from nerimity_sdk.cli.lint import run_lint
        run_lint(args.paths)
    elif args.command == "dev":
        from nerimity_sdk.cli.dev import run
        run(args.file)
    elif args.command == "test":
        _run_tests(args.paths, args.verbose)
    elif args.command == "deploy":
        _run_deploy(args.target)
    else:
        parser.print_help()


def _run_tests(paths: list[str], verbose: bool) -> None:
    import subprocess, sys
    cmd = [sys.executable, "-m", "pytest"] + paths
    if verbose:
        cmd.append("-v")
    result = subprocess.run(cmd)
    sys.exit(result.returncode)


def _run_deploy(target: str) -> None:
    import subprocess, sys, os

    if target == "railway":
        if not os.path.exists("railway.toml"):
            _write_railway_config()
            print("✓ Created railway.toml")
        print("Deploying to Railway...")
        result = subprocess.run(["railway", "up"])
        if result.returncode != 0:
            print("Install Railway CLI: https://docs.railway.app/develop/cli")
            sys.exit(result.returncode)

    elif target == "fly":
        if not os.path.exists("fly.toml"):
            _write_fly_config()
            print("✓ Created fly.toml")
        print("Deploying to Fly.io...")
        result = subprocess.run(["flyctl", "deploy"])
        if result.returncode != 0:
            print("Install flyctl: https://fly.io/docs/hands-on/install-flyctl/")
            sys.exit(result.returncode)

    elif target == "render":
        if not os.path.exists("render.yaml"):
            _write_render_config()
            print("✓ Created render.yaml")
        print("render.yaml created. Push to GitHub and connect at https://render.com")


def _write_railway_config() -> None:
    with open("railway.toml", "w") as f:
        f.write('[build]\nbuilder = "nixpacks"\n\n[deploy]\nstartCommand = "python bot.py"\nrestartPolicyType = "always"\n')


def _write_fly_config() -> None:
    app_name = os.path.basename(os.getcwd()).lower().replace("_", "-")
    with open("fly.toml", "w") as f:
        f.write(f'app = "{app_name}"\nprimary_region = "iad"\n\n[build]\n\n[[services]]\ninternal_port = 8080\nprotocol = "tcp"\n')


def _write_render_config() -> None:
    with open("render.yaml", "w") as f:
        f.write('services:\n  - type: worker\n    name: nerimity-bot\n    env: python\n    buildCommand: pip install -r requirements.txt\n    startCommand: python bot.py\n')
