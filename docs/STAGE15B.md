# Stage 15b: hardening fixes

Owner's decision (2026-11-25): yes, including the Content-Security-Policy tag.

## Changes
- **Content-Security-Policy tag** in frontend/index.html (first tag after charset): `default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; form-action 'none'`. Nothing from outside the site can run or load; no inline script/style exists on the page (frontend/data-check.html, a maintenance page, is left without the tag because it has one inline style). tests/csp_page.test.js (5 tests) fails if anyone later adds an inline script, a style attribute, an event handler, a foreign address, innerHTML or eval, because the page would break silently under the policy.
- **Plain load messages** (frontend/dataloader.js): 404 -> "The data was updated a moment ago. Please reload the page."; server error -> "The data server did not answer properly (status N). Please try again in a few minutes."; offline -> "Could not load the data. Please check your internet connection and try again."; sign-in page instead of data -> "What came back was not the data (a Wi-Fi sign-in page can cause this). Please check your connection and reload the page." File names are no longer shown (kept in `error.url` for diagnosis). tests/loader_messages.test.js (6 tests).
- **Footer**: added "The page uses no cookies and no tracking." (verified: no cookies, storage, beacons or XMLHttpRequest in the page scripts).
- **docs/HOSTING_BACKUP.md**: plan for a free second copy on Cloudflare Pages (untried).
- **Audit corrections** in docs/STAGE15A.md: the privacy line already existed; empty gender in the engine stays as it is (only general seats apply, so it cannot over-promise; a mandatory gender broke 47 engine tests for no student benefit; the change was reverted).

## Owner check on the phone (needed: a real browser was not available here)
Open the page (also with ?preview=1) and check: the page looks normal; "Show my recommendations" works; the results appear; "Download PDF" works. If anything is missing or blank, delete the line that starts `<meta http-equiv="Content-Security-Policy"` in frontend/index.html (pencil icon on GitHub) and tell me what you saw. The PDF download (a temporary file created in the browser) is the one function most likely to be affected on some phones.

## Tests
JS with real data and the full Python suite pass (numbers in the reply).
