# Bot Zombie

A no-code bot creator for [Nerimity](https://nerimity.com). Build and deploy bots visually -- no coding required.

---

## Open the Builder

**[Launch Bot Builder](builder.html)** -- the visual drag-and-drop bot editor.

---

## How it works

1. **Get a token** -- go to [nerimity.com/app/settings/developer/applications](https://nerimity.com/app/settings/developer/applications), create an app, add a Bot, and copy the token.
2. **Open the builder** -- paste your token and start dragging nodes onto the canvas.
3. **Wire nodes together** -- connect triggers (like "On Message") to actions (like "Send Reply") to define your bot's behavior.
4. **Deploy** -- hit the Deploy button and your bot goes live instantly.

---

## Builder features

| Feature | Description |
|---|---|
| Node palette | Drag triggers, actions, conditions, and logic nodes onto the canvas |
| Visual wiring | Connect node ports to build your bot's flow |
| Inspector panel | Configure selected nodes with custom values |
| Templates | Start from pre-built templates (greeter, echo, mod bot, etc.) |
| Live preview | Test your bot's behavior before deploying |
| Code view | See the generated JavaScript code, or edit it directly |
| Embed editor | Build rich embeds with a visual editor |
| Bot dashboard | Manage multiple bots, view logs, start/stop |
| Keyboard shortcuts | Ctrl+Z undo, Ctrl+S save, Delete to remove nodes |
| Import/Export | Save and load bot configurations as JSON |

---

## Runner

The backend server that powers Bot Zombie:

- **Auth** -- register/login with username and password (PBKDF2-hashed)
- **Deploy** -- deploy generated bot code with one click
- **Bot lifecycle** -- auto-restart crashed bots, view logs, stop bots
- **Security** -- CORS lockdown, isolated child process environments, input validation

### Self-hosting

See the [README](https://github.com/JoddabodScripts/Bot-Zombie#self-hosting) for self-hosting instructions.

---

## Legacy SDK docs

The original Python SDK documentation is still available in the sidebar for reference:

- [Installation](guide/installation.md)
- [Quick Start](guide/quickstart.md)
- [API Reference](api/bot.md)
- [Example Bot](example.md)

---

Built by [@Kansane:TETO on Nerimity](https://nerimity.com/app/profile/1750075711936438273) | [JoddabodScripts on GitHub](https://github.com/JoddabodScripts)
