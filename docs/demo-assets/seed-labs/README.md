# Seed labs for CRE-26 demo video

Three importable lab files that match the pre-production checklist in
`docs/DEMO_VIDEO.md`. Load them once before recording so beats 1, 4, and 6
are zero-prep on the day.

## Files

| File                       | Used in beat(s) | Purpose                                    |
| -------------------------- | --------------- | ------------------------------------------ |
| `security-stack.json`      | 1, 3, 5         | The hero topology shown in the cold open   |
| `empty.json`               | 4               | Blank canvas for the drag-and-drop demo    |
| `networking-triangle.json` | 6 (2s cut)      | Cisco+Juniper+VyOS for the "what else" reel|

## How to import

Backend must be running on `:5000`.

```bash
cd docs/demo-assets/seed-labs
for f in security-stack.json empty.json networking-triangle.json; do
  curl -fsS -X POST http://localhost:5000/api/labs/import \
    -H 'Content-Type: application/json' \
    --data-binary @"$f" \
    | python3 -m json.tool
done
```

Or from the UI: **Labs → Import → pick file**.

## Verify

```bash
curl -fsS http://localhost:5000/api/labs | python3 -m json.tool | grep '"name"'
```

You should see `"Security Stack"`, `"Empty Canvas"`, `"Networking Triangle"`.

## Node positions

Positions (`x`, `y`) are pre-tuned for a 1920×1080 canvas zoomed to 100%.
If your dev canvas is sized differently you may want to nudge them in the
UI and re-export — but they should land in roughly the right place for any
modern viewport.

## Why the configs look sparse

`config` is a free-form JSON blob the backend stores as-is. For the demo
we only need `role`/`services` hints so the node labels render meaningful
chips in the UI. Real lab deployments fill in more (cpu pinning,
cloud-init, etc.) — that's out of scope here.
