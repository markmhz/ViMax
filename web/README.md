# ViMax Web

The Web workspace uses the existing ViMax agent loop and JSONL event stream. It does not implement workflow decisions in the browser.

From the `ViMax` repository root, create the private local agent configuration once:

```bash
cp configs/agent.example.yaml configs/agent.local.yaml
```

```bash
cd web
npm install
npm run dev
```

Or from the repository root:

```bash
./vimax web
```

The default address is `http://127.0.0.1:4173`. Override it with `VIMAX_WEB_HOST` and `VIMAX_WEB_PORT`.

Production mode:

```bash
cd web
npm run build
cd ..
./vimax web start
```

Agent credentials continue to come from ViMax environment variables or `configs/agent.local.yaml`.

Web Settings writes `configs/agent.local.yaml`. Empty `api_key` / `model` / `base_url` fields in `configs/idea2video.yaml` and `configs/script2video.yaml` are filled from that file (and `VIMAX_*` env) via `utils/agent_pipeline_bridge.py`, so the same keys work for CLI pipelines.

For novel2video, configure **Embedding** and **Reranker** in Settings (no YAML hand-edit). Upload a `.txt`/`.md` and plan via `novel_path` (e.g. `uploads/chapter.txt`). Oversized novels are truncated for planning with the full text saved under `novel2video/novel/novel_full.txt`. Saving Settings while a turn is running defers agent reload until the turn finishes. Video Settings accepts optional `provider` (`openrouter` | `yunwu` | `google`).

The Web UI defaults to Simplified Chinese. Locale maps live in `src/i18n/` (UI) and `i18n.mjs` (API errors). Set `DEFAULT_LOCALE` / `LOCALE` to `'en'` to restore English.
