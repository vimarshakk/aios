# Examples

Copy-paste workflows for the AIOS CLI. All assume a running gateway
(`AIOS_GATEWAY_URL` set, or pass `--gateway <url>`).

```bash
# shorthand used below
alias a='aios --gateway http://localhost:8080'
```

## Notes

```bash
# Title + body (parsed from the phrase)
a "save a note titled Sprint Plan with body Finish v0.7.0 RC" --watch

# Shorter phrasing also works (save/capture/jot/store/keep)
a "jot a note called Standup with body Demo the new planner"
```

Result: a Markdown file under `~/.aios/notes/<Title>.md`.

## Filesystem

```bash
a "list files in my home directory" --watch
a "show the contents of my Documents folder"
```

## Git

```bash
a "show git status"
a "commit my changes with message wip: stabilization pass"
```

## Notifications

```bash
a "notify me that the build finished"
```

Most workflows end with a `desktop.notify` step so you get a confirmation.

## Mixed / web (needs Playwright + an LLM provider)

```bash
a "search Hacker News for AI and save a summary to notes" --watch
```

If no LLM provider is configured, the `llm.summarize` step fails gracefully with
`no available provider for capability 'llm.summarize'` — the goal ends `failed`
with a clear error rather than hanging.

## Watching goals

```bash
a goals                  # table of all goals
a goal <goal-id>         # full detail: tasks, result, events
a logs <goal-id>         # lifecycle events
a watch                  # live WebSocket stream of every goal
```

## Machine-readable output

```bash
a --json goal <goal-id>          # structured JSON
a --json goals | jq '.[] | select(.status=="failed")'
```

## Controlling execution

```bash
a pause <goal-id>
a resume <goal-id>
a cancel <goal-id>
a retry <goal-id>               # fresh run of a failed goal's objective
```

## Renaming the assistant

```bash
AIOS_ASSISTANT_NAME="Wysh AI" a version
```
