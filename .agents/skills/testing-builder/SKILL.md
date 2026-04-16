# Testing Bot Zombie Builder

## Overview
The Bot Zombie builder (`docs/builder.html`) is a visual node-based bot creator for Nerimity bots. It has a login screen that requires runner API credentials.

## Devin Secrets Needed
None required for local testing — auth can be bypassed.

## Local Setup

1. **Build the mkdocs site:**
   ```bash
   cd /home/ubuntu/repos/Bot-Zombie
   pip install mkdocs mkdocs-material
   mkdocs build
   ```

2. **Serve the built site:**
   ```bash
   python3 -m http.server 8081 --directory /home/ubuntu/repos/Bot-Zombie/site
   ```

3. **Open in Chrome:**
   - Navigate to `http://localhost:8081/builder.html`

## Bypassing Authentication

The builder has a login screen that calls the runner API. For local testing, bypass it:

```python
from playwright.sync_api import sync_playwright
p = sync_playwright().start()
browser = p.chromium.connect_over_cdp('http://localhost:29229')
page = browser.contexts[0].pages[0]
page.evaluate('_enterBuilder()')
p.stop()
```

This calls `_enterBuilder()` which hides the login overlay and shows the builder canvas.

## Testing Builder Features

### Creating Nodes Programmatically
Drag-and-drop from the palette works via computer use, but for precise operations use Playwright:

```javascript
// Create a node
createNode('trigger_command', 400, 400, {});

// Wire two nodes
addWire(fromNodeId, 'exec', toNodeId, 'exec');

// Select a node
const node = nodes.find(n => n.type === 'action_reply');
selectNode(node);

// Duplicate selected node
duplicateSelected();

// Clear canvas (bypasses confirm dialog)
window.confirm = () => true;
clearCanvas();
```

### Key Variables and Functions
- `nodes` — array of all nodes on canvas
- `wires` — array of all wire connections
- `NODE_DEFS` — node type definitions (check `NODE_DEFS.comment`, etc.)
- `generateCode()` — generates bot JavaScript code
- `zoom`, `panX`, `panY` — canvas transform state
- `selectedNode` — currently selected node
- `filterPalette(query)` — filter palette by search text
- `showToast(message, type)` — show toast notification
- `updateStatusBar()` — refresh status bar counts
- `zoomToFit()` / `centerCanvas()` — canvas view controls
- `exportGraphJSON()` / `importGraphJSON(input)` — JSON export/import

### Node Categories
- **Triggers**: trigger_command, trigger_message, trigger_ready, trigger_join, trigger_leave
- **Actions**: action_reply, action_send, action_dm, action_role, action_kick, action_ban, action_unban, action_nick, action_react, action_delete, action_embed, action_webhook
- **Logic**: logic_if, logic_switch, logic_delay, logic_loop, logic_random, logic_try_catch
- **Utility**: util_log, util_var, util_fetch, util_json_parse, util_regex, util_math, util_timestamp, util_format
- **Annotations**: comment (yellow dashed node, skipped in code gen)

## Testing mkdocs Navigation

To verify the nav structure, navigate to an inner page:
```python
page.goto('http://localhost:8081/guide/installation/')
nav_text = page.evaluate('document.querySelector(".md-sidebar--primary .md-nav")?.innerText')
```

Expected: "LEGACY DOCS" section containing Guides and API Reference sub-sections.

## Known Issues
- **Ctrl+D shortcut**: Conflicts with Chrome's "Add Bookmark" when focus is on an input field. The `duplicateSelected()` function works correctly when called programmatically or when canvas has focus.
- **clearCanvas()**: May trigger a confirm dialog. Override `window.confirm` before calling.
- **Multiple builder copies**: `docs/builder.html`, `runner/builder.html`, and `docs/index.html` must stay in sync.
- **mkdocs dev server**: May return 404 for builder.html. Test against the built static site (`mkdocs build` then serve `site/` directory) instead.
