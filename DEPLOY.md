# Deploying TRACE to Streamlit Community Cloud

This walks you from a local-only POC to a shareable HTTPS URL anyone can open
in a browser — no install, no terminal, no Python. Free tier, ~30 minutes
the first time.

## What you'll end up with

- A private GitHub repo containing the POC code + synthetic dataset
- A live app at `https://<your-app>.streamlit.app` you can share with
  investors and clinicians
- An auto-deploy pipeline: every time you push to GitHub, the live app
  updates within a minute

## One-time prerequisites

- A GitHub account ([github.com/join](https://github.com/join) if you don't
  have one — free)
- Git installed locally. Check with `git --version` in Terminal. If missing,
  run `xcode-select --install` (macOS will prompt you to install command-line
  tools).

That's it. Streamlit Cloud handles the rest.

---

## Step 1 — Confirm the data is in place

The repo already has the synthetic dataset copied into
`data/utah_synthetic/` (I did this for you). Verify:

```bash
cd "/Users/kimberlyvillalta/Library/CloudStorage/GoogleDrive-kimberjam@gmail.com/My Drive/Antibiotic Dashboard/TRACE - Technical/Dashboard/Ingestion Files_Templates/TRACE POC/trace_poc_unified"

ls data/utah_synthetic/
# Should list: README.md, aggregates/, facilities.csv, test_results.csv, zip_county_map.csv
```

The data loader auto-detects this path before falling back to the original
`Claude Mockups/` location, so local + cloud both work with no config.

---

## Step 2 — Initialize Git and make the first commit

```bash
cd "/Users/kimberlyvillalta/Library/CloudStorage/GoogleDrive-kimberjam@gmail.com/My Drive/Antibiotic Dashboard/TRACE - Technical/Dashboard/Ingestion Files_Templates/TRACE POC/trace_poc_unified"

git init
git add .
git status   # quick check — should show all your files staged
git commit -m "Initial commit: TRACE POC unified build"
```

If `git config` complains about your name/email, set them once:

```bash
git config --global user.name "Kimberly Villalta"
git config --global user.email "kimberjam@gmail.com"
```

Then re-run the `git commit` line.

---

## Step 3 — Create a private GitHub repo

In your browser:

1. Go to [github.com/new](https://github.com/new)
2. **Repository name**: `trace-poc` (or whatever you prefer)
3. **Visibility**: **Private** — investors/clinicians will see the *deployed
   app*, not the code, so keep the code private
4. **Do NOT** check "Add a README", "Add .gitignore", or "Choose a license" —
   you already have those locally
5. Click **Create repository**

GitHub will show you a page with instructions for an empty repo. Copy the
two-line "push an existing repository" block, which looks like:

```bash
git remote add origin git@github.com:<your-username>/trace-poc.git
git branch -M main
git push -u origin main
```

Paste those into Terminal (still inside the `trace_poc_unified` folder). The
push will take a couple of minutes since the synthetic dataset is ~57MB.

If GitHub asks you to authenticate, the easiest path is to install the
[GitHub CLI](https://cli.github.com/) (`brew install gh` then `gh auth login`).
Alternatively, use the HTTPS URL form and GitHub Desktop.

---

## Step 4 — Deploy on Streamlit Community Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with
   GitHub. Authorize Streamlit to read your repos.
2. Click **New app** (top right).
3. Fill in:
   - **Repository**: `<your-username>/trace-poc`
   - **Branch**: `main`
   - **Main file path**: `app.py`
   - **App URL** (optional): pick something like `trace-resistance` →
     produces `https://trace-resistance.streamlit.app`
4. Click **Deploy**.

Streamlit will spin up a container, install your `requirements.txt`, and
launch the app. First deploy takes 3–5 minutes (pip installs from a cold
cache). Subsequent deploys are 30–60 seconds.

Watch the build log; if anything errors, paste it back to me.

---

## Step 5 — Lock down access (optional but recommended for pre-launch)

By default the app is public. To restrict it to specific email addresses
during the pilot:

1. From the app's dashboard on share.streamlit.io, click **Settings** →
   **Sharing**
2. Toggle **Only specific people** and add the emails of your investors and
   clinical reviewers
3. Save. Now only those emails can view the app (they'll Google-sign-in
   to verify)

This is free, takes a minute, and means random GitHub crawlers can't find
your demo by accident.

---

## Step 6 — Iteration workflow

For every future change:

```bash
cd "/Users/kimberlyvillalta/Library/CloudStorage/GoogleDrive-kimberjam@gmail.com/My Drive/Antibiotic Dashboard/TRACE - Technical/Dashboard/Ingestion Files_Templates/TRACE POC/trace_poc_unified"

git add .
git commit -m "Describe what you changed"
git push
```

Streamlit Cloud picks up the push within seconds and auto-redeploys within
a minute. Refresh the live URL and your change is there. No downtime, no
manual deploy step.

When you're working with me, I edit the files locally → you run those three
git lines → live app updates. Same loop as before, just with a live URL.

---

## Troubleshooting

**"Repository too large"** — only happens above 100MB per file. Our largest
file (`test_results.csv`) is 56MB, so this should never fire. If it does,
we can switch to Git LFS or move the data to S3.

**"Module not found"** — Streamlit Cloud failed to install a dependency.
Check `requirements.txt` is up to date.

**App boots but data loader fails** — the synthetic data didn't make it
into the repo. Re-run Step 1 to verify `data/utah_synthetic/` is committed.

**App is slow on first load** — Streamlit Cloud spins down inactive apps
after a few days. First request to a cold app takes ~30 seconds to wake.
Once warm, it's fast. If this matters for a demo, hit the URL a couple of
minutes before the meeting.

**Custom domain** (e.g., `trace.alta-health.com`) — Streamlit Community
Cloud doesn't support custom domains on the free tier. If you need one,
either upgrade to Streamlit Cloud Teams or self-host on Render / Railway
/ Fly.io.

---

## Cost

- **Streamlit Community Cloud**: free for public and private apps with
  basic resource limits (1 GB RAM, 1 GB storage). Plenty for this POC.
- **GitHub**: free for unlimited private repos.

Total cost to ship this demo: $0.

If you outgrow the free tier (millions of pageviews, larger data, custom
domain), Streamlit Cloud Teams is around $250/month, or you can move to
self-hosted at ~$5–20/month on Render or Railway.
