# Stage 16c-1: feedback link

Owner's decision (2026-11-25): option A, a Google Form: https://forms.gle/bVYF5XgabwBbMoup6 (opened and read on 2026-11-25: title "MHT-CET College Advisor"; asks for an email address (required, recorded by Google) and "Describe about the problem you face").

## Page change (frontend/index.html, footer)
"Found a mistake or a problem? Tell us (opens a Google Form in a new tab). That form is run by Google and may ask for your email address; this page itself sends nothing." The link opens in a new tab with rel="noopener noreferrer" (the form does not learn the page address). The older sentence now reads "We do not ask for your name, phone or email on this page." because the form does ask for an email.
The Content-Security-Policy is not affected (a link is a navigation, not a load); tests/csp_page.test.js now allows exactly this one foreign address and nothing else (deliberate change); tests/feedback_link.test.js (2 tests).

## Owner decision to consider (Google Forms settings, not code)
The form requires an email address. Students are mostly 17-18 and the site promises not to collect personal data. If you do not need to reply to people, in the form's Settings you can switch off "Collect email addresses" (and, if you like, add a "Your email (optional)" question). I cannot see or change your form settings; the page text says "may ask", so it stays true either way.
You read the answers in the form's Responses tab (or a linked Google Sheet).
