# Yazio nutrition ingestion

Exports your Yazio nutrition, body, and exercise data into `data/yazio/` using
[`yazio-exporter`](https://github.com/aleksandr-bogdanov/yazio-exporter).

This is the **Yazio data source** for the Health Intelligence Dashboard
(see [`../../task(2).md`](../../task(2).md) §4.2 and §19.4).

## What gets exported

- Daily diary (consumed items, calories, macros)
- 40+ micronutrients (vitamins & minerals)
- Weight / body measurements
- Exercise logs and water intake
- Generated `analysis.md` (statistics) and `llm_prompt.txt` (LLM-ready prompt)

Three serializations are produced: **JSON**, **CSV**, and **SQLite**.

## Prerequisites

- Python 3.11+ (you have 3.14)
- `pip install yazio-exporter` (already installed: v0.2.0)
- A Yazio account using **email/password** login (Google/Apple/Facebook social
  logins are NOT supported by the exporter — set a Yazio password first if needed)

> The CLI installs to
> `C:\Users\<you>\AppData\Roaming\Python\Python314\Scripts\yazio-exporter.exe`,
> which is not on PATH. The `export.ps1` script below calls it by full path.

## Usage

1. Copy the credentials template and fill it in (never commit the real file):

   ```powershell
   Copy-Item ..\..\.env.example ..\..\.env
   notepad ..\..\.env
   ```

2. Run the export from this folder:

   ```powershell
   .\export.ps1
   ```

   This logs in (saving a token to a git-ignored `token.txt`), then runs
   `export-all` for JSON, CSV, and SQLite into `data/yazio/`.

## Manual commands (equivalent)

```powershell
$exe = "$env:APPDATA\Python\Python314\Scripts\yazio-exporter.exe"
& $exe login   you@email.com 'password' -o ..\..\token.txt
& $exe export-all you@email.com 'password' -o ..\..\data\yazio --format json
& $exe export-all you@email.com 'password' -o ..\..\data\yazio --format csv
& $exe export-all you@email.com 'password' -o ..\..\data\yazio --format sqlite
```

## Privacy

- `data/yazio/`, `token.txt`, and `.env` are all git-ignored.
- Treat the exported files as sensitive personal health data.
- See the project root README for the full privacy policy.
