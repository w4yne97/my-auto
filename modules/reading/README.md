# modules/reading/

User-editable config for the reading module. Python code lives at `src/auto/reading/`.

## What's in this directory

- `config/research_interests.yaml` — domains, keywords, scoring weights, vault path.
- `config/research_interests.example.yaml` — annotated template.

## Skills owned by this module

| Command | Description |
|---------|-------------|
| `/paper-search <keywords>` | Search arXiv for papers |
| `/paper-analyze <id>` | Deep-analyze a single paper |
| `/paper-import <input...>` | Bulk-import papers (ID / URL / title / PDF) |
| `/paper-deep-read <id>` | Frame-by-frame deep read, produces HTML report |
| `/insight-init <topic>` | Create a new Insight topic |
| `/insight-update <topic>` | Merge new papers into an existing topic |
| `/insight-absorb <topic/point> <source>` | Absorb knowledge into a specific tech point |
| `/insight-review <topic>` | Review topic status and open questions |
| `/insight-connect <topicA> [topicB]` | Discover cross-topic links |
| `/idea-generate` | Mine research opportunities from Insight graph |
| `/idea-develop <name>` | Advance an Idea through spark→exploring→validated |
| `/idea-review` | Global Idea dashboard |
| `/reading-config` | View/edit research interest config |
| `/reading-weekly` | Generate last-7-days weekly digest |

## Vault outputs

`$VAULT_PATH/{10_Daily,20_Papers,30_Insights,40_Ideas,40_Digests}/`
