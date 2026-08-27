# DOC036 Variant Holdout V1 Freeze Manifest

- Question set: `data/variant_holdout_v1_spec.yaml`
- Question IDs: `V01` through `V20`
- Question count: 20
- Expected supported answers: 16
- Expected abstentions: 4
- Supported-question focus: DOC036
- First-run artifact prefix: `variant_holdout_v1`
- Branch: `feature/variant-pi-requirements`
- Git baseline HEAD: `ac698b715c55f42779c36182b85f193f3cd7c7ed`
- Pre-run artifact state: answer report, checkpoint, metrics, and first-run audit were absent
- Set-separation check: PASS against official, engineering, variant-development, and all four earlier holdout specifications
- Policy: execute exactly once without tuning retrieval, prompting, intent routing, answer validation, fallback behavior, corpus artifacts, or question wording

## Pre-run SHA-256 values

| Frozen input | SHA-256 |
|---|---|
| `data/variant_holdout_v1_spec.yaml` | `4a758409f75e1a0e696a5c5f83ae051ff607497b38cd94c49654a5fcb3c4daa3` |
| `src/conservation_intelligence/chatbot.py` | `57ba554fb564bb928866c211469ade813d610e10a8fa8ee719b562403fd1734f` |
| `src/conservation_intelligence/repository.py` | `951a3f7f1b046d792f6b6f107be8f2b85c244d6b94b5fbefae835b7ee991bf4b` |
| `src/conservation_intelligence/semantic.py` | `b6e8a39f00df7aef9e3a5e5dfbd901345dc89b0e34ae6decec71861e75577dab` |
| `config.yaml` | `5b9da3b8e932013908cc96d6f0382e168d6af4eea7d5afadf4acb1eeac1eedfa` |
| `db/conservation.db` | `c5408d3c7fe9c22661fd3b6b5359a096666711194db220723f3f9008b737ed79` |
| `vector_index/manifest.json` | `0f388c0b526daef4244f0435a1f0147d3c5d06e5ddb5126a7c4c1a8cde762898` |
| `scripts/12_evaluate_fresh_holdout.py` | `d8fd71e0090ae69809f54d28c848d7dd5cfcdac69e83712de7b60e51ab7cc9a7` |

This manifest was created after schema, balance, uniqueness, DOC036-focus,
and set-separation validation and before any OpenAI request for V01-V20.
The first-run outputs are immutable evaluation evidence and must not be
overwritten or used as a repair/retest cycle.

