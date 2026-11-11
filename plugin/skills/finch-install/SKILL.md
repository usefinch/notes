---
name: finch-install
description: Set up Finch in a project so its owner can edit the live site in the browser — signs in with Google (and creates the Finch API key), detects the framework, creates the Finch project, injects the script with live editing on, adds the source plugin for React+Vite, writes the .finch config, pre-approves the Finch tools, makes sure the project is in git, and deploys Ample apps with `ample up`. Use when the user says "install Finch", "set up Finch", "add Finch to this site" or runs /finch-install.
allowed-tools: mcp__plugin_finch_finch__* Read Edit Write Grep Glob Bash(ls *) Bash(python3 *finch_auth.py*) Bash(cat ~/.finch-session.json) Bash(git rev-parse *) Bash(git init *) Bash(git status *) Bash(git log *) Bash(git add *) Bash(git commit *) Bash(git rm --cached *) Bash(ample up) Bash(date *) Bash(python3 -c "import uuid; print(uuid.uuid4())") Bash(npm install -D vite-plugin-finch) Bash(pnpm add -D vite-plugin-finch) Bash(yarn add -D vite-plugin-finch) Bash(bun add -d vite-plugin-finch)
---

The user wants to install Finch in their project.

**Usage:** `/finch-install [project-name]`

- `[project-name]`: optional. If omitted, derive from directory name or ask.

## Credentials (hardcoded — no file needed)

```
SUPABASE_URL=https://djrzptnmlkvafrtxismf.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRqcnpwdG5tbGt2YWZydHhpc21mIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzU3MzMyMzksImV4cCI6MjA5MTMwOTIzOX0.7vAL8UYx_CjSC8eFAo8mfs0YrFF5GCRR40TQhxYhVFY
SESSION_FILE=~/.finch-session.json
MCP_ENDPOINT=https://djrzptnmlkvafrtxismf.supabase.co/functions/v1/finch-mcp
```

Use these directly. Do not look for any `.env` file.

---

## Step 1 — Sign in to Finch

Run the sign-in script that ships with this skill:

```bash
python3 "${CLAUDE_SKILL_DIR}/finch_auth.py"
```

It reuses the saved session (`~/.finch-session.json`) or refreshes it, and only opens the browser for Google sign-in on finchnotes.co when neither works — tell the user to finish signing in there; the script waits up to 5 minutes. It also creates the Finch API key the plugin's connection needs and saves it to `~/.finch/credentials`, so nobody has to run `npx finch login`. (`npx finch` is not our package on npm — never suggest it.)

It prints one line of JSON: `email`, `user_id`, `name` (from Google) and `apiKey` (`existing`, `created`, or `replaced` when the saved key had expired or been disconnected). The raw API key is never printed — don't read or print `~/.finch/credentials` either.

- Keep `user_id` for Step 5 and the owner's first name (first word of `name`, or the part of `email` before `@`, capitalised) for Step 6.
- For Step 5 you also need the access token: read `access_token` from `~/.finch-session.json`.
- If the script exits with an error, show it and stop.
- If `apiKey` is `created` or `replaced`, the plugin's **finch** connection was started before the key existed: tell the user at the end to reconnect **finch** from `/mcp` (or start a new session) before running `/finch-apply`.

---

## Step 2 — Detect framework

Run the following checks in order, stopping at the first match:

1. `ls astro.config.js astro.config.mjs astro.config.ts 2>/dev/null` → **Astro**
2. `ls nuxt.config.js nuxt.config.ts 2>/dev/null` → **Nuxt**
3. `ls next.config.js next.config.mjs next.config.ts 2>/dev/null` → **Next.js**
   - Then check: `ls src/app/layout.tsx src/app/layout.jsx app/layout.tsx app/layout.jsx 2>/dev/null`
     - Found → **Next.js App Router**
   - Else check: `ls src/pages/_app.tsx src/pages/_app.jsx pages/_app.tsx pages/_app.jsx 2>/dev/null`
     - Found → **Next.js Pages Router**
   - Else → **Next.js (unknown router)** — ask the user which they use.
4. Check `package.json` for `"vite"` in devDependencies or dependencies → **React+Vite** (also works for plain Vite, Vue+Vite, Svelte+Vite)
5. `find . -maxdepth 2 -name "*.html" ! -path "*/node_modules/*" ! -path "*/.git/*" 2>/dev/null | head -5` — if HTML files found → **Plain HTML**
6. Else → **Unknown** — ask the user to describe their setup and pick the closest match.

---

## Step 3 — Project name

If a name wasn't supplied as an argument and you can't derive a clear one, ask:
> What should this project be called in the Finch dashboard?

Derive from the current directory name as the default suggestion.

**Then one more question — is this a live production site?** Ask it with `AskUserQuestion`:
> Should Finch show to everyone who visits, or only to people you send a review link?
> 1. Everyone — a prototype, staging or preview site (default)
> 2. Only with a review link — a live production site; visitors never see Finch

Remember the answer as **show**: `always` for 1, `link` for 2. Ask nothing else — reviewers sign in with Google to suggest changes, and there are no access settings yet.

---

## Step 4 — Check for existing config

Check if a `.finch` **file** exists at the current directory (or a parent, walking upward — stop at the git root or the home folder):

```bash
ls -p .finch 2>/dev/null
```

Only a regular file counts. `~/.finch/` in the home folder is a **folder** (Step 1 keeps the API key there), not a project config — if the only match is that folder (`ls -p` shows a trailing `/`), treat it as not found.

- **Found:** read it and extract `projectId` as the existing `prototypeId`. Skip project creation — the project already exists. Skip to step 6 (injection).
- **Not found:** continue to step 5.

---

## Step 5 — Generate prototypeId and create project in Supabase

**Generate a UUID:**
```bash
python3 -c "import uuid; print(uuid.uuid4())"
```
Use this as `prototypeId`. Do NOT slugify the project name — human-readable slugs are guessable.

**Detect base URL** (needed for project creation):

Run these in order, stopping at the first confident result:

0. **Ample app** (`ample.toml` at the root): don't ask — leave `base_url` out for now. Step 10 runs `ample up`, which prints the live URL, and sets it on the project then.
a. Read `package.json` → `homepage` field — use if non-empty.
b. Check `.vercel/project.json` exists → run `vercel ls --json 2>/dev/null`, parse `url` from first entry, prepend `https://`.
c. Scan `.env`, `.env.local`, `.env.production` for `VITE_APP_URL`, `NEXT_PUBLIC_URL`, `PUBLIC_URL`, `SITE_URL`, `APP_URL`, `BASE_URL` — use first value starting with `http`.
d. Check `vite.config.js`/`vite.config.ts` for `server.port`, `next.config.js` for port, or `package.json` scripts for `--port NNNN` → candidate `http://localhost:{port}`.
e. If no confident result: ask the user:
   > What URL will reviewers open this prototype at? (e.g. https://my-app.vercel.app — leave blank to set later)

**Create the project:**

```bash
curl -s -X POST \
  '{SUPABASE_URL}/rest/v1/projects' \
  -H 'apikey: {SUPABASE_ANON_KEY}' \
  -H 'Authorization: Bearer {access_token}' \
  -H 'Content-Type: application/json' \
  -H 'Prefer: return=representation' \
  -d '{
    "name": "{projectName}",
    "prototype_id": "{prototypeId}",
    "base_url": "{base_url_or_null}",
    "owner_id": "{user_id}"
  }'
```

If `base_url` is null/blank, omit the field entirely from the JSON. Check the response for errors (non-2xx or `{ "code": ... }` in body).

---

## Step 6 — Inject the Finch script

The config+script block to inject is always:

```html
<script>
  window.__FINCH_CONFIG__ = {
    supabaseUrl: 'https://djrzptnmlkvafrtxismf.supabase.co',
    supabaseAnonKey: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRqcnpwdG5tbGt2YWZydHhpc21mIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzU3MzMyMzksImV4cCI6MjA5MTMwOTIzOX0.7vAL8UYx_CjSC8eFAo8mfs0YrFF5GCRR40TQhxYhVFY',
    prototypeId: '{prototypeId}',
    dashboardUrl: 'https://finchnotes.co',
    mode: 'live',
    live: {live},
  }
</script>
<script src="https://finchnotes.co/finch.js"></script>
```

**If show is `link`** (Step 3), add `show: 'link',` on its own line right after `mode: 'live',` — in whichever framework's snippet below you use. Finch then stays hidden (no download, nothing on the page) until someone opens the site with `?finch` on the end of the URL; the owner is remembered on their device after that, and **Hide Finch on this site** in the panel's account menu puts it away again. Leave the line out for `always`.

`mode: 'live'` turns on editing on the page: the owner sees **Edit this page** (and the Edit / Changes / History pill on the right edge) and can change copy, colours, spacing and layout, then press **Apply changes**; everyone else can suggest changes and leave notes. Replace `{live}` with:

- **Plain HTML:** `{ owner: '{ownerName}' }`
- **Every other framework:** `{ owner: '{ownerName}', liveReload: false }` — their dev servers reload the page themselves, and swapping in fetched HTML would break a built app.

`{ownerName}` is the owner's first name from Step 1 — reviewers see "Send to {ownerName}". Escape any `'` in it.

**Already injected** (the file has `finchnotes.co/finch.js`)? Don't add a second copy — but if its config has no `mode`, add the `mode` and `live` lines to it, so re-running the skill on an older install turns editing on.

Inject it according to the detected framework:

### Plain HTML

For each `.html` file found in step 2:
- Check if it already contains `finchnotes.co/finch.js` → skip (already injected).
- Otherwise: insert the block immediately before `</body>` using the Edit tool.

Do this for all HTML files found — typically there is one `index.html`.

### React+Vite (also Vue+Vite, Svelte+Vite, plain Vite)

Check if `index.html` exists at the project root. If yes, inject before `</body>` (same as plain HTML above).

If no root `index.html` exists, check `src/index.html`. If found, inject there.

If neither exists, report that the user should manually add the snippet to their HTML entry point and print it for them to copy.

### Next.js App Router

Find the root layout file — try in order:
1. `src/app/layout.tsx`
2. `src/app/layout.jsx`
3. `app/layout.tsx`
4. `app/layout.jsx`

Read the file. Check if Finch is already present (`finchnotes.co/finch.js`) → skip if so.

Add `import Script from 'next/script'` to the imports if not already present.

Inside the returned JSX, find the `<body ...>` tag and insert inside it (after any className/other props, before the first child or `{children}`):

```tsx
<Script id="finch-config" strategy="beforeInteractive">{`
  window.__FINCH_CONFIG__ = {
    supabaseUrl: 'https://djrzptnmlkvafrtxismf.supabase.co',
    supabaseAnonKey: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRqcnpwdG5tbGt2YWZydHhpc21mIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzU3MzMyMzksImV4cCI6MjA5MTMwOTIzOX0.7vAL8UYx_CjSC8eFAo8mfs0YrFF5GCRR40TQhxYhVFY',
    prototypeId: '{prototypeId}',
    dashboardUrl: 'https://finchnotes.co',
    mode: 'live',
    live: {live},
  }
`}</Script>
<Script src="https://finchnotes.co/finch.js" strategy="afterInteractive" />
```

If editing the layout would be risky (file is complex or the pattern is unclear), print the snippet and tell the user where to add it rather than making a potentially broken edit.

### Next.js Pages Router

Find the app file — try in order:
1. `src/pages/_app.tsx`
2. `src/pages/_app.jsx`
3. `pages/_app.tsx`
4. `pages/_app.jsx`

Read the file. Check if Finch is already present → skip if so.

Add `import Script from 'next/script'` to imports if not present.

In the returned JSX, add after the opening fragment or wrapping element (before `<Component {...pageProps} />`):

```tsx
<Script id="finch-config" strategy="beforeInteractive">{`
  window.__FINCH_CONFIG__ = {
    supabaseUrl: 'https://djrzptnmlkvafrtxismf.supabase.co',
    supabaseAnonKey: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRqcnpwdG5tbGt2YWZydHhpc21mIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzU3MzMyMzksImV4cCI6MjA5MTMwOTIzOX0.7vAL8UYx_CjSC8eFAo8mfs0YrFF5GCRR40TQhxYhVFY',
    prototypeId: '{prototypeId}',
    dashboardUrl: 'https://finchnotes.co',
    mode: 'live',
    live: {live},
  }
`}</Script>
<Script src="https://finchnotes.co/finch.js" strategy="afterInteractive" />
```

### Nuxt

Find `nuxt.config.ts` or `nuxt.config.js`. Read it.

Check if Finch is already present → skip if so.

Add or extend the `app.head.script` array inside the config:

```ts
app: {
  head: {
    script: [
      {
        innerHTML: `window.__FINCH_CONFIG__ = { supabaseUrl: 'https://djrzptnmlkvafrtxismf.supabase.co', supabaseAnonKey: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRqcnpwdG5tbGt2YWZydHhpc21mIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzU3MzMyMzksImV4cCI6MjA5MTMwOTIzOX0.7vAL8UYx_CjSC8eFAo8mfs0YrFF5GCRR40TQhxYhVFY', prototypeId: '{prototypeId}', dashboardUrl: 'https://finchnotes.co', mode: 'live', live: {live} }`,
        tagPosition: 'bodyClose',
      },
      {
        src: 'https://finchnotes.co/finch.js',
        tagPosition: 'bodyClose',
      },
    ],
  },
},
```

If an `app.head.script` array already exists, append to it rather than replacing it. If the `app` or `app.head` key doesn't exist, add the whole structure. Preserve the existing config style (TypeScript `defineNuxtConfig` wrapper, etc.).

If editing the config would be risky, print the snippet and tell the user where to add it.

### Astro

Find the layout file — try in order:
1. `src/layouts/Layout.astro`
2. `src/layouts/BaseLayout.astro`
3. `src/pages/index.astro`

Read the file. Check if Finch is already present → skip if so.

Insert before `</body>`:

```html
<script>
  window.__FINCH_CONFIG__ = {
    supabaseUrl: 'https://djrzptnmlkvafrtxismf.supabase.co',
    supabaseAnonKey: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRqcnpwdG5tbGt2YWZydHhpc21mIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzU3MzMyMzksImV4cCI6MjA5MTMwOTIzOX0.7vAL8UYx_CjSC8eFAo8mfs0YrFF5GCRR40TQhxYhVFY',
    prototypeId: '{prototypeId}',
    dashboardUrl: 'https://finchnotes.co',
    mode: 'live',
    live: {live},
  }
</script>
<script src="https://finchnotes.co/finch.js" is:inline></script>
```

Note: Astro processes `<script>` tags specially. Use `is:inline` on the src script to prevent Astro from bundling it.

If no layout file is found, inject into each `.astro` page file in `src/pages/` that has a `</body>` tag.

### Unknown framework

Print the config+script block and tell the user to add it just before `</body>` in their HTML entry point (or equivalent). Do not attempt to edit any files.

---

## Step 6b — Add the source plugin (React+Vite only)

**Not published yet — skip this step entirely for now.** `vite-plugin-finch` isn't on npm, so installing it fails with a 404 and a scary-looking error. Don't run the install. In the report, say one line: "Source stamps (exact file:line for edits) come with a Vite plugin that isn't released yet — Finch works without it." Remove this paragraph once the package is on npm.

`vite-plugin-finch` stamps every element with its source `file:line` and the page with the build's git commit, so Finch visual edits and comments point Claude at the exact line. Only do this when `package.json` lists `@vitejs/plugin-react` or `@vitejs/plugin-react-swc`. Skip it for every other framework (plain HTML needs nothing — the file is the source; Vue, Svelte and Next.js aren't supported yet) and say so in the report.

1. Check the Vite config (`vite.config.js` / `.ts` / `.mjs`). If it already imports `vite-plugin-finch`, skip this step.
2. Install it as a dev dependency with the project's package manager (lockfile tells you: `pnpm-lock.yaml` → `pnpm add -D`, `yarn.lock` → `yarn add -D`, `bun.lockb` → `bun add -d`, otherwise `npm install -D`):
   ```bash
   npm install -D vite-plugin-finch
   ```
   If the install fails (e.g. the package can't be found), skip the rest of this step and report it — the overlay works without the plugin, just less precisely.
3. Edit the Vite config: add `import finch from 'vite-plugin-finch'` with the other imports, and add `finch()` to the `plugins` array **before** the React plugin:
   ```js
   plugins: [finch(), react()],
   ```

The plugin reads the commit from `VERCEL_GIT_COMMIT_SHA` / `CF_PAGES_COMMIT_SHA` / `GITHUB_SHA` / `RENDER_GIT_COMMIT` / `COMMIT_REF`, falling back to `git rev-parse HEAD` — no configuration needed on common hosts.

---

## Step 7 — Write .finch config

Write a `.finch` file at the current working directory (project root):

```json
{
  "projectId": "{prototypeId}",
  "projectName": "{projectName}"
}
```

If `.finch` already existed (step 4 found it), skip this step — don't overwrite.

---

## Step 8 — Pre-approve the Finch tools

This skill ships in the **Finch plugin**, which already connects Claude Code to the hosted Finch MCP server in every project — so **don't write a `.mcp.json`** (a second `finch` server would duplicate the tools and need its own reconnect). If the project already has a `finch` entry in `.mcp.json` from an older install, leave it but mention it can be removed.

Add a project permission so the Finch tools never prompt in this repo. Read `.claude/settings.json` if it exists and merge — keep everything already there — so that `permissions.allow` contains:

```json
{
  "permissions": {
    "allow": ["mcp__plugin_finch_finch__*"],
    "ask": [
      "Edit(/package.json)", "Edit(/package-lock.json)", "Edit(/pnpm-lock.yaml)", "Edit(/yarn.lock)",
      "Edit(/.finch)", "Edit(/.github/**)", "Edit(**/.env*)",
      "Edit(/vercel.json)", "Edit(/netlify.toml)", "Edit(/ample.toml)",
      "Edit(**/next.config.*)", "Edit(**/vite.config.*)", "Edit(**/nuxt.config.*)", "Edit(**/astro.config.*)",
      "Edit(**/svelte.config.*)", "Edit(**/webpack.config.*)", "Edit(**/postcss.config.*)", "Edit(**/babel.config.*)"
    ]
  }
}
```

The `ask` rules are the safety net for `/finch-apply`: ordinary changes to pages, styles and copy still go through with no prompt, but a change to the package file, build or deploy config, environment files or CI stops and asks the owner first. Reviewers' text can't talk Claude out of this, because Claude Code enforces it, not the model. Merge them into any existing `ask` list; don't remove rules the project already has. (Git and `.claude/` are protected by Claude Code already.)

Write it with the Write/Edit tools (create `.claude/` if needed). Claude Code shows these rules in its trust prompt the next time the folder is opened; that one approval covers every Finch tool call from then on.

**API key check:** Step 1 already made sure `~/.finch/credentials` has a key. If it reported `apiKey: created` or `replaced`, the user must reconnect **finch** from `/mcp` (or open a new session) before `/finch-apply` will see the Finch tools — say so in the report.

---

## Step 9 — Make sure the project is in git

`/finch-apply` puts every change on its own branch and commit, so the project needs git.

```bash
git rev-parse --is-inside-work-tree
```

**Not a git repo** (the command fails):
1. If there's no `.gitignore`, write one that suits the framework — at least `node_modules/`, `.env*` (but not `.env.example`), build output (`.next/`, `dist/`, `.nuxt/`, `.output/`, `.astro/`), `.vercel`, `.DS_Store`. If one exists, make sure `.env*` is in it.
2. Run each of these on its own:
   ```bash
   git init -b main
   ```
   ```bash
   git add -A
   ```
   ```bash
   git commit -m "First commit, with Finch"
   ```
3. Before committing, run `git status --porcelain` and check no secrets are staged (`.env` files, keys, `credentials`). If any are, unstage them with `git rm --cached <file>`, add them to `.gitignore`, then commit.

**Already a git repo:** commit only the files this skill changed, naming them, so the user's other work isn't swept in:
```bash
git add <files>
```
```bash
git commit -m "Add Finch" -- <files>
```
(The files: the one the script went into, `.finch`, `.claude/settings.json`, and the Vite config / `package.json` / lockfile if Step 6b ran.) If the user has a commit-message convention visible in `git log --oneline -5`, follow it.

No remote is needed — Ample deploys from the folder, and `/finch-apply` merges locally.

---

## Step 10 — Put Finch on the live site

The overlay only shows up where the new script is deployed.

- **`ample.toml` at the root** (an Ample app): run `ample up` in the foreground and wait for it — it prints the live URL. If the project has no `base_url` yet, set it on the Finch project now:
  ```bash
  curl -s -X PATCH '{SUPABASE_URL}/rest/v1/projects?prototype_id=eq.{prototypeId}' -H 'apikey: {SUPABASE_ANON_KEY}' -H 'Authorization: Bearer {access_token}' -H 'Content-Type: application/json' -d '{"base_url": "{liveUrl}"}'
  ```
  If `ample up` fails, show the error and carry on to the report — setup is done, only the deploy needs another try.
- **Anything else:** don't deploy. Tell the user to deploy the way they usually do (Vercel / Netlify / `git push`), and that `/finch-apply` will ask once how the site deploys and remember it.

---

## Step 11 — Report results

Print a clear summary:

```
Signed in as sam@example.com ✓
Framework: Next.js App Router

Project: "My App" (a3f9b2c1-4d5e-6f7a-8b9c-0d1e2f3a4b5c) — created ✓
Live editing: on — you're the owner ("Sam")

Script injected into: src/app/layout.tsx ✓
Config written: .finch ✓
Finch tools pre-approved: .claude/settings.json ✓
Git: new repo, first commit made ✓
Deployed: https://my-app.ample.run ✓

Next steps:
  1. Open https://my-app.ample.run and click Edit on the right edge.
  2. Change anything — text, colours, spacing, layout. It previews as you go.
  3. Click Apply changes, then come back here and run /finch-apply.
     Claude makes the changes, deploys, and the page reloads into the live site.
```

If show is `link`, add a line `Shows: only with a review link (visitors never see Finch)` to the summary, and make next step 1 "Open https://my-app.ample.run/?finch and click Edit on the right edge — the ?finch is what shows Finch; send that same link to anyone you want feedback from (or copy it from finchnotes.co/app)."

If Step 1 created the API key, add before the next steps: "Reconnect **finch** from `/mcp` (or open a new session) so `/finch-apply` can see your Finch tools." If the site wasn't deployed (no `ample.toml`), step 1 becomes "Deploy the site the way you usually do, then open it…".

If anything failed (e.g. project creation errored, no HTML file found), report the error clearly and note which steps succeeded and which need manual attention. A partial setup is better than a hard stop.

---

## Notes

- Use `curl` via Bash for Supabase API calls — not the Supabase SDK.
- Use the Read and Edit tools for file modifications; Write for new files.
- If `.finch` already exists (re-running the skill), skip project creation and config writing; only re-inject the script tag if missing, add `mode: 'live'` if it's missing, and still run Steps 9–10.
- The API key is never written into the project. The plugin's Finch connection reads it from `~/.finch/credentials` (saved by Step 1) each time it connects, falling back to a `FINCH_API_KEY` environment variable. Don't tell users to export it in their shell — the desktop app doesn't load shell profiles.
