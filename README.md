# Finch for Claude Code

Finch lets people suggest edits right on your live website; you approve them, and Claude Code puts them live.

[Finch](https://finchnotes.co) puts an **Edit** button on your deployed site. Change text, colours, spacing and layout right on the page, or just type what you want different. Press **Apply changes**, run `/finch-apply` in Claude Code, and Claude makes each change on a branch, merges it, deploys, and your page reloads into the live version. People you share the site with can suggest changes too; you approve the ones you want.

## Install

You need Claude Code, which comes with a paid Claude plan (Pro or higher). Paste this into Claude Code (works in the desktop app and the terminal):

```
Install the Finch plugin from github.com/usefinch/notes, then help me set it up on my site.
```

Or, in the Claude Code terminal:

```
/plugin install finch --marketplace usefinch/notes
```

On Claude Code older than 2.1.292, run `/plugin marketplace add usefinch/notes` and then `/plugin install finch@finch`. Start a new session in your project afterwards.

## Use

1. **`/finch-install`** in your project. It signs you in with Google (once), creates your Finch site, adds the Finch script with editing turned on, sets up git if needed, and redeploys if it's an [Ample](https://ample.computer) app. It works with plain HTML, React with Vite, Next.js, Nuxt and Astro, including sites that live only on Ample.
2. **Open your live site** and click **Edit** on the right edge. Make changes, or type what you'd change. Share the review link so others can suggest changes.
3. **Click Apply changes**, then run **`/finch-apply`** in Claude Code. Claude applies everything on a new branch (one commit per change), merges, deploys, and the page reloads into the live site.

To take Finch off a project, run **`/finch-uninstall`**. It removes the script and config, and asks whether to delete the site from Finch and disconnect your computer too.

## What's in here

- `plugin/skills/finch-install`: sets Finch up in a project
- `plugin/skills/finch-apply`: applies the changes queued from the Apply button
- `plugin/skills/finch-uninstall`: takes Finch off a project
- `plugin/.mcp.json`: connects Claude Code to the hosted Finch server, using the key `/finch-install` saves to `~/.finch/credentials` on your computer

## Your data

Finch keeps your sign-in, your sites, and the notes and changes people leave on them. Your code stays on your computer and in your own git repository; Finch never receives it. See the [privacy policy](https://finchnotes.co/privacy) and [terms](https://finchnotes.co/terms).

## Help

Questions or problems: [finchnotes.co/support](https://finchnotes.co/support) or hello@finchnotes.co.
