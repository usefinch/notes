---
name: finch-uninstall
description: Take Finch off a project — removes the Finch script and config that /finch-install added (script tag, .finch, the Finch permissions in .claude/settings.json, vite-plugin-finch), commits, redeploys Ample apps, and optionally deletes the site from Finch and disconnects this computer. Use when the user says "uninstall Finch", "remove Finch", "take Finch off this site" or runs /finch-uninstall.
allowed-tools: Read Edit Write Grep Glob AskUserQuestion Bash(ls *) Bash(python3 *finch_uninstall.py*) Bash(rm .finch) Bash(git rm .finch) Bash(git rev-parse *) Bash(git ls-files *) Bash(git status *) Bash(git log *) Bash(git add *) Bash(git commit *) Bash(ample up) Bash(npm uninstall vite-plugin-finch) Bash(pnpm remove vite-plugin-finch) Bash(yarn remove vite-plugin-finch) Bash(bun remove vite-plugin-finch)
---

The user wants Finch off this project. Undo what `/finch-install` did, and only that: leave the rest of the project exactly as it was.

Running this skill is the go-ahead to edit the project's files, commit and (for Ample apps) redeploy. Deleting the site from Finch and disconnecting this computer each need the user's yes in Step 2: deleting the site can't be undone.

Run each shell command on its own, in the forms shown — no `&&`, `cd`, `-C` or pipes.

## Step 1 — Find what Finch added

1. Read `.finch` at the project root if it's there (a regular **file** — `~/.finch/` in the home folder is a folder and doesn't count). Keep `projectId` (the prototype id) and `projectName`.
2. Grep the project for `finchnotes.co/finch.js`, `__FINCH_CONFIG__` and `vite-plugin-finch`, skipping `node_modules`, `.git` and build output (`dist`, `.next`, `.nuxt`, `.output`, `.astro`, `.vercel`). Also check `.env*.local` files for a Finch overlay override (a variable whose value points at `finch.js` or `finch-live.js`).
3. If there's no `.finch`, take `prototypeId` from the injected config.

Nothing found at all → tell the user Finch isn't installed in this project, and skip to Step 2 asking only the "disconnect this computer" question.

## Step 2 — Ask what else to remove

Ask with one `AskUserQuestion` call holding both questions (leave out the first if there's no `prototypeId`):

1. **Delete "{projectName}" from Finch too?** (header "Finch site")
   - "Keep it" — the site and its suggestions stay in finchnotes.co/app; reinstalling picks them back up. (first)
   - "Delete it" — removes the site with all its suggestions, notes and apply history. Can't be undone.
2. **Disconnect this computer from Finch?** (header "Computer")
   - "Stay connected" — Finch keeps working in your other projects on this computer. (first)
   - "Disconnect" — revokes this computer's Finch key and signs it out. Do this if you're done with Finch here.

## Step 3 — Remove the script

For each file Step 1 found, remove exactly the block `/finch-install` injected and nothing around it:

- **Plain HTML / Vite `index.html` / Astro:** the `<script>` holding `window.__FINCH_CONFIG__ = {…}` and the `<script src="https://finchnotes.co/finch.js" …></script>` after it.
- **Next.js (App or Pages Router):** the `<Script id="finch-config" …>{`…`}</Script>` and `<Script src="https://finchnotes.co/finch.js" … />`. Then remove `import Script from 'next/script'` **only** if no other `<Script` is left in the file.
- **Nuxt:** the two `app.head.script` entries (the `innerHTML` one with `__FINCH_CONFIG__` and the `src: 'https://finchnotes.co/finch.js'` one). If that leaves `script: []`, and then `head: {}` and `app: {}` empty, remove the empty keys too — but keep anything else that was there.
- **`.env*.local` overrides** from Step 1: remove just that line.

Leave the indentation and blank lines around the removed block the way they'd be if it had never been added. If a file looks hand-edited in a way that makes the block unclear, show the user the lines and ask before cutting.

## Step 4 — Remove the source plugin (if present)

If a Vite config imports `vite-plugin-finch`: remove the `import finch from 'vite-plugin-finch'` line and `finch()` from `plugins`, then uninstall it with the project's package manager (`pnpm-lock.yaml` → `pnpm remove`, `yarn.lock` → `yarn remove`, `bun.lockb` → `bun remove`, otherwise `npm uninstall`):

```bash
npm uninstall vite-plugin-finch
```

Editing `package.json`, the lockfile or the Vite config may ask the user for permission (the ask rules `/finch-install` added) — that's expected; Step 6 removes those rules.

## Step 5 — Remove `.finch`

If it's tracked by git (`git ls-files .finch` prints it):

```bash
git rm .finch
```

Otherwise:

```bash
rm .finch
```

## Step 6 — Remove the Finch permissions

Read `.claude/settings.json` (skip if it doesn't exist). Remove:

- `mcp__plugin_finch_finch__*` from `permissions.allow`
- these entries from `permissions.ask`, which `/finch-install` added for `/finch-apply`:
  `Edit(/package.json)`, `Edit(/package-lock.json)`, `Edit(/pnpm-lock.yaml)`, `Edit(/yarn.lock)`, `Edit(/.finch)`, `Edit(/.github/**)`, `Edit(**/.env*)`, `Edit(/vercel.json)`, `Edit(/netlify.toml)`, `Edit(/ample.toml)`, `Edit(**/next.config.*)`, `Edit(**/vite.config.*)`, `Edit(**/nuxt.config.*)`, `Edit(**/astro.config.*)`, `Edit(**/svelte.config.*)`, `Edit(**/webpack.config.*)`, `Edit(**/postcss.config.*)`, `Edit(**/babel.config.*)`

Keep every other entry. Drop `ask` / `allow` / `permissions` only if they end up empty; if the whole file ends up empty, leave it as `{}` rather than deleting it (it may be tracked).

If `.mcp.json` has a `finch` server (older installs), remove that entry; if it was the only one, leave `{"mcpServers": {}}`.

## Step 7 — Commit

If the project is a git repo (`git rev-parse --is-inside-work-tree`), commit only the files this skill changed, naming them:

```bash
git add <files>
```
```bash
git commit -m "Remove Finch" -- <files>
```

(`<files>` includes `.finch` when Step 5 used `git rm`.) Follow the project's commit-message style if `git log --oneline -5` shows one. Don't push.

## Step 8 — Take it off the live site

- **`ample.toml` at the root:** run `ample up` in the foreground and wait for it. If it fails, show the error and carry on.
- **Anything else:** don't deploy. Tell the user Finch stays on the live site until they deploy the way they usually do (Vercel / Netlify / `git push`).

## Step 9 — Finch account (only what the user chose in Step 2)

Run once, with only the flags they said yes to:

```bash
python3 "${CLAUDE_SKILL_DIR}/finch_uninstall.py" --delete-project {prototypeId} --disconnect
```

It signs in like `/finch-install` (the browser opens only if the saved session has expired — tell the user to finish signing in there). It prints one line of JSON:

- `project.status`: `deleted` · `not_found` (already gone, or owned by another Finch account — say so) · `failed` (show `error`)
- `computer.status`: `disconnected` · `already_revoked` (removed from the dashboard earlier; local files cleaned up anyway) · `no_key` · `failed` (show `error`)

Don't run it at all if the user chose neither.

## Step 10 — Report

```
Finch removed from this project ✓

Script removed from: src/app/layout.tsx ✓
Removed: .finch, Finch permissions in .claude/settings.json ✓
Committed: "Remove Finch" ✓
Deployed: https://my-app.ample.run ✓          (or: Deploy the site to take Finch off the live page)
Finch site "My App": kept in finchnotes.co/app   (or: deleted ✓)
This computer: still connected                  (or: disconnected ✓)
```

Then, only if the computer was disconnected, add: "To remove the Finch plugin from Claude Code as well, run `/plugin uninstall finch@finch`." If anything failed, say which steps worked and which need a manual look.
