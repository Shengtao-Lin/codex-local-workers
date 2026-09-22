# Local Coder smoke example

This project was used for a real end-to-end Local Coder smoke test. The initial
`build_greeting()` implementation failed all four focused tests. The packet
authorized Qwen to modify only `greeting.py`; the tests were readable but
forbidden for modification.

The direct-LM-Studio runtime changed `greeting.py`, ran `py_compile`, and
completed with `4 passed`. A later schema-v2 compatibility run detected that no
further edit was required, passed preflight and focused pytest, and returned
`ready_for_review` in `.agent/last-local-coder-v2-report.json`.

Run the independent focused test with:

```powershell
.\.venv\Scripts\python.exe -B -m pytest tests\test_greeting.py -q
```
