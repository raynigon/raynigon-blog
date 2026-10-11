# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Jekyll static site (the source for https://www.raynigon.de), a personal tech blog. No application code, no test suite — the only "build" is a Jekyll static-site generation.

## Commands

- `make setup` — install Jekyll/Bundler and project gems (`gem install bundler jekyll && bundle install`)
- `make serve` — build and serve locally with live-reload (`bundle exec jekyll serve`)
- `make build` — one-off build to `./_site` (`bundle exec jekyll build`)
- `make clean` — remove generated output and caches (`bundle exec jekyll clean`)

There is no linter, formatter, or test suite configured for the Jekyll site. The only CI check is that the site builds (see Deployment below).

## Architecture

- **Theme lives in a separate repo.** `_config.yml` sets `remote_theme: raynigon/mere-blog-theme`, fetched via the `jekyll-remote-theme` plugin. This repo intentionally has **no `_layouts/`, `_includes/`, `_sass/`, or `_plugins/` directories** — all layout markup, includes, and styling come from that external theme repo. Visual/structural changes (page layout, CSS, nav) require editing `raynigon/mere-blog-theme`, not this repo.
- **Content collections**: standard Jekyll `_posts/` (flat directory, no per-year/category subfolders) plus two custom collections declared in `_config.yml`: `authors` (`_authors/`) and `imprint` (output pages). `authors.md` and `posts.md` are listing pages for those.
- **Post convention**: filenames are `YYYY-MM-DD-slug.md`. Front matter consistently includes `layout: post`, `title`, `author`, `date`, `categories`, `tags`, `header_image`, `image`, `description`, and a `twitter.username` block. Follow the existing front-matter shape exactly when adding a post — the remote theme depends on these fields (e.g. `header_image`/`image` for hero/card art, `description`/`twitter` for SEO/social tags via `jekyll-seo-tag`).
- **Post images**: stored under `img/posts/` as `<slug>-header.png` and `<slug>-card.png`, with an optional `img/posts/<slug>/` subfolder for additional inline images referenced from the post body.
- **Legal/legacy pages**: `imprint.md` is the real, Jekyll-rendered imprint content; `impressum.html` is a static meta-refresh redirect stub preserving the old German URL (`/impressum.html` → `/imprint/`). Don't merge or remove one assuming it duplicates the other.
- **`assets/`** holds static files (`robots.txt`, `.htaccess`) that are copied verbatim into `_site/` at deploy time (not processed by Jekyll) — see the CD workflow.
- **`tools/latex-to-md/main.py`** is a standalone, unrelated Python CLI (not part of the Jekyll build) that converts a `.tex` file into a draft blog post, turning LaTeX equations into SVG images. Invoked directly with Python/click, not through `make`.

## Deployment

`.github/workflows/cd.yml` runs on every push to `master`: `bundle exec jekyll build`, then copies `assets/*` (including `.htaccess`) into `_site/`, then FTP-uploads `_site/` to a shared webspace host using `WEBSPACE_HOST`/`WEBSPACE_USER`/`WEBSPACE_PASSWORD` secrets. There is no staging environment or PR preview — anything pushed to `master` deploys live. CI uses Ruby 2.6.3 explicitly (`ruby/setup-ruby`); match that if debugging CI-only build failures that don't reproduce locally.

## Known data issue

`_posts/2023-10-20-migrate-terrabytes-with-es.md` has `date: 2123-10-20` in its front matter — almost certainly a typo for `2023`. Be aware of this if working on date-based sorting/pagination/feed logic; don't silently "fix" it without flagging it, since it may be intentional (e.g. a future-dated draft).

## Never write blog post prose

Writing the actual prose of a blog post — the sentences and paragraphs that make up a post's content — is a task reserved for the human author. Do not draft, author, or generate new prose for `_posts/` content, under any framing (a "quick draft", "placeholder text," "just an example," etc.).

What **is** allowed when asked to help with a post: restructuring existing human-written text (reordering sections, splitting/merging paragraphs), rephrasing or copy-editing sentences the human already wrote, fixing grammar/typos, adjusting front matter, formatting (headings, lists, code blocks, links), and generating an initial structural skeleton — section headlines only, based on topics/outline the user provides — with no body prose underneath them. The human always writes the prose that fills in each section.

If asked to write new prose content for a post, decline and explain that post authorship is human-only, then offer to help with structuring/editing instead.
