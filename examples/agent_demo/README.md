# Agent Demo: Folder-based Inbox/Outbox Pattern

Drop files in `inbox/`, run the agent, results split into `output/` subfolders.

## How it works

1. `pipeline.ai` defines the extraction schema and flag rules
2. `run_agent.py` parses, compiles, and runs the pipeline
3. Results are split into `output/clean/`, `output/flagged/`, `output/errors/`
4. Every run appends to `output/audit/log.jsonl`

## Run manually

```bash
cd examples/agent_demo
uv run python run_agent.py
```

## Run on a schedule (cron)

```bash
*/5 * * * * cd /path/to/examples/agent_demo && uv run python run_agent.py >> /var/log/aidsl-agent.log 2>&1
```

Add new files to `inbox/` at any time. Each run processes all files.
