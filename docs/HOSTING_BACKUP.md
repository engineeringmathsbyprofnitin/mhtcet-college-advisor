# Backup hosting plan (free): a second copy of the site on Cloudflare Pages

Status: a plan only. It has NOT been tried; button names on the Cloudflare site may differ from the steps below.

## Why
GitHub Pages is free but has soft limits (about 100 GB of downloads a month and 10 site builds an hour; GitHub's own documentation). One visit downloads roughly 0.3-0.6 MB (the page, one 0.8 MB data file that is compressed on the wire, and one to three cutoff files), so about 200,000 visits a month would approach the download limit. During a CAP season that is possible but not certain. The site's size is far below GitHub's 1 GB limit (working tree 26 MB, repository history 52 MB on 2026-11-25).
Nothing needs to be done now. Do this only if GitHub ever warns about bandwidth, or if you want a second address that keeps working when one host has trouble.

## Steps (about 15 minutes, no code)
1. Create a free account at Cloudflare (dash.cloudflare.com).
2. Left menu: Workers & Pages -> Create -> Pages -> Connect to Git -> choose GitHub -> allow access to the repository `mhtcet-college-advisor` only.
3. Settings: production branch `main`; framework preset **None**; build command **empty**; build output directory **/** (the repository root: its index.html sends visitors on to frontend/index.html, exactly like GitHub Pages).
4. Save and Deploy. Cloudflare gives an address like `https://<project>.pages.dev`. Open it and add `?preview=1` after `frontend/index.html` to check the real data, as on GitHub Pages.
5. From then on Cloudflare publishes a new copy by itself whenever the repository changes (the daily publish run commits only when the data really changed).

## What keeps working without any change
- The data address is relative (`data/` or `data-real/` in frontend/config.js), so the copy finds its own data.
- The Content-Security-Policy tag allows only the site's own address; a copy on another host is its own site, so nothing needs editing. (If you ever put the DATA files on a DIFFERENT address from the page, DATA_BASE_URL in frontend/config.js and `connect-src` in the policy tag of frontend/index.html must both name that address.)
- The "Data updated on ..." line and all banners are computed from the data files.

## Going public later
Whichever address you share, the switch from the old test data to the real data is still the one line `PUBLIC_DATA_FOLDER = "data-real/"` in frontend/config.js (see docs/RECOVERY.md); both copies follow it.
