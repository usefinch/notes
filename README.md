# Finch for Claude Code

Edit your live site in the browser, then let Claude make the changes in your code.

[Finch](https://finchnotes.co) puts an **Edit** button on your deployed site. Change text, colours, spacing and layout right on the page, or just type what you want different. Press **Apply changes**, run `/finch-apply` in Claude Code, and Claude makes each change on a branch, merges it, deploys, and your page reloads into the live version. People you share the site with can suggest changes too; you approve the ones you want.

## Install

In Claude Code:

```
/plugin marketplace add finchnotes/finch
```

```
/plugin install finch@finch
```

Then start a new session in your project.

## Use

1. **`/finch-install`** in your project. It signs you in with Google (once), creates your Finch project, adds the Finch script with editing turned on, sets up git if needed, and redeploys if it's an [Ample](https://ample.computer) app.
2. **Open your live site** and click **Edit** on the right edge. Make changes, or type what you'd change.
3. **Click Apply changes**, then run **`/finch-apply`** in Claude Code. Claude applies everything, deploys, and the page reloads into the live site.

## What's in here

- `plugin/skills/finch-install` — sets Finch up in a project
- `plugin/skills/finch-apply` — applies the changes queued from the Apply button
- `plugin/.mcp.json` — connects Claude Code to the hosted Finch server, using the key `/finch-install` saves to `~/.finch/credentials`

Questions or problems: [finchnotes.co](https://finchnotes.co)
