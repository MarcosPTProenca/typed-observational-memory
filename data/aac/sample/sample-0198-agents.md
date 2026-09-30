# Repository Guidelines

## Project Structure & Module Organization
- `content/` holds bilingual topics; keep `_index.de.md` and `_index.en.md` siblings with mirrored front matter so sidebar weights stay aligned.
- `layouts/partials/` and `layouts/shortcodes/` override hugo-theme-relearn (e.g., `layouts/shortcodes/svg.html` pulls from `svg/`); extend these instead of touching `themes/hugo-theme-relearn`.
- Shared styling lives in `assets/css/theme-grafioschtrader.css`, pass-through files belong in `static/`, and Hugo-generated `public/` / `resources/` should only be refreshed via `hugo --cleanDestinationDir`.
- Store reusable diagrams under `svg/` or next to the Markdown that embeds them so shortcodes resolve predictable filenames.

## Build, Test, and Development Commands
- `hugo server --disableFastRender -D --buildFuture --navigateToChanged` previews both languages with drafts at http://localhost:1313/gt-user-manual/.
- `hugo --gc --minify --printI18nWarnings --cleanDestinationDir` produces the deployable `public/`, prunes unused resources, and surfaces translation gaps.
- `hugo server --renderToDisk --printUnusedTemplates` previews while writing HTML snapshots that can be zipped for reviewers.
- Use Hugo Extended v0.120+ so the Relearn theme SCSS and custom CSS variables compile correctly.

## Coding Style & Naming Conventions
- Front matter uses YAML fences; keep `title`, `date`, `draft`, `weight`, and `archetype` synced across languages and prefer ISO timestamps.
- Reserve `#` for page titles, rely on `##`/`###` for sections, and stick to Markdown lists or tables unless HTML is unavoidable.
- Name folders after their domain (e.g., `watchlistinstrument/`), keep filenames lowercase, and keep supporting media near the page that embeds it.
- Wrap callouts with the existing shortcodes (`{{% notice %}}`, `{{< svg icon="..." >}}`, mermaid fences, etc.) and keep styling changes inside `assets/css/theme-grafioschtrader.css`.

## Testing Guidelines
- Run `hugo --gc --minify --printI18nWarnings` before every commit; today that build is the test suite.
- Add `--i18n-warnings --printUnusedTranslations --printPathWarnings` to ensure `_index.de.md` and `_index.en.md` remain aligned and to detect orphaned layouts.
- Spot-check `public/search/index.json` and a few affected HTML pages in Chromium and Firefox to confirm menus, SVGs, and notices render correctly.

## Commit & Pull Request Guidelines
- Git history currently only shows `Initial commit`, so adopt an imperative style (e.g., `docs: explain tenantportfolio filters`) and keep each commit focused.
- Include regenerated `public/` artifacts whenever the published site changes, and avoid mixing content tweaks with layout or CSS overrides.
- PRs should list touched sections (`content/transaction/`, `layouts/shortcodes/svg.html`, etc.), link Grafioschtrader issues, attach screenshots or zipped `public/` previews for styling changes, and state whether `hugo --gc --minify` ran clean.