# End-to-end scenario

Runs IntraForge the way a shop uses it, on the **test copy** (https://127.0.0.1:9543, test data only), and writes
a PDF report with a screenshot per step.

```bash
# from apps/frontend (for @playwright/test); uses the installed Google Chrome
NODE_PATH="$(pwd)/node_modules" node ../../replica/reports/scenario/scenario.cjs <out-folder> <test-copy>/TEST_LOGINS.txt <site.zip>
# reportlab + pillow in any Python environment
python ../../replica/reports/scenario/build_pdf.py <out-folder> ../../replica/design/control-center operations.json report.pdf
```

`site.zip` is any zip with an `index.html` containing the text "IntraForge scenario". Credentials are read from the
test copy's own `TEST_LOGINS.txt` and never printed. The internet steps use the real Cloudflare tunnel and
harmongt.uk, and take their automatic name back at the end.
