# Stage 15a: hardening audit (read-only; nothing in the code changed)

Method: code reading plus simulated failures and odd inputs run through the real loader and engine on the published real data (2026-11-25).

## Findings: already good
- **No unsafe page code**: no innerHTML, insertAdjacentHTML, document.write, eval or new Function in frontend/*.js; all text goes through textContent, so text inside the data files cannot inject markup.
- **No tracking or storage**: no cookies, localStorage, sessionStorage, beacons or XMLHttpRequest. Only static files are fetched. What a student types never leaves the browser.
- **Old phones**: the five page scripts are plain ES5 (no arrow functions, let/const, template strings, optional chaining, async/await). The fingerprint check is skipped on very old browsers instead of failing.
- **Downloads**: every data file is checked against its SHA-256 fingerprint; one automatic retry; 20-second timeout per request; the manifest is always fetched fresh (no-cache) and data files have unique names, so a browser can never mix old and new files.
- **Odd inputs** (20 cases: percentile -5/101/"abc"/NaN/null, budget -1/NaN/0, no branch, no district, unknown priority, 100,000-character branch name, unknown category/candidate type/university...): no exception in any case; clear messages ("percentile must be a number between 0 and 100", "Choose at least one branch" ...).
- **Failures** (offline, manifest 404, server 500, damaged file, one wrong byte in the data, Wi-Fi sign-in page instead of JSON, empty manifest, flaky first request): all end in a plain LoadError message; the flaky case recovers by itself.
- **Speed**: worst case (all 124 branch names, all 2,150 results, three priorities) takes about 0.4 s and about 45 MB on this machine; one branch about 0.35 s. A slow phone may need several seconds, not minutes. Data per visit: about 0.8 MB base file (smaller on the wire, GitHub Pages compresses JSON) plus one to three cutoff files of up to 0.2 MB.

## Findings: weak spots (proposed for 15b)
1. **Technical load messages.** A 404 on a data file reads "Could not load data/cutoffs/GOPENH.5b75....json (status 404)"; the Wi-Fi sign-in case reads "The data file data/manifest.json is damaged". Better: "The data was updated a moment ago. Please reload the page." and "The answer was not the data (a Wi-Fi sign-in page?). Check your connection and reload."
2. **No Content-Security-Policy.** The page has no inline scripts or styles, so a strict policy is possible (scripts, styles, images and fetches only from the site itself). GitHub Pages cannot send headers, so it would be a meta tag. Risk: a wrong policy could blank the page, and no real browser is available here to test it; the owner would have to check it on the phone (one-line removal if it breaks).
3. **No plain privacy line.** The page could say: "No cookies, no tracking. What you type stays in your browser." (true today, verified above).
4. **No backup hosting plan.** GitHub Pages has soft limits (about 100 GB a month). At about 0.5 MB a visit that is roughly 200,000 visits; a CAP-season peak could approach it. The page already builds its data address from one setting (DATA_BASE_URL in frontend/config.js), so a copy on another free host (Cloudflare Pages or Netlify) is possible; a written plan is missing (unverified: not tried here).
5. **Empty gender is accepted by the engine** (returned 20 results); the form requires it, so students cannot hit this, but the engine should refuse it too (the same engine file is used by the optional backend).

## Not checked (cannot be checked here)
Real browsers (no browser in the sandbox), real phones, real network speed, GitHub Pages bandwidth.
