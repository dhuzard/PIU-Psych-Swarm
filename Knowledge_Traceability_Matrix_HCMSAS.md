# HCMSAS Knowledge Traceability Matrix

> **Swarm:** Home Cage Monitoring Scientific Agent Squad (HCMSAS)
> **Purpose:** Log every major factual claim, inference, or speculation made during swarm operation, with source, agent, and epistemic tag.
> **Format:** Append new rows at the bottom. Never delete rows — mark superseded entries as `[SUPERSEDED]`.

---

## Column Definitions

| Column | Description |
|---|---|
| `claim_id` | Unique identifier (e.g., HCM-001) |
| `claim` | The specific factual claim or assertion |
| `epistemic_tag` | [FACT] / [INFERENCE] / [SPECULATION] / [MISSING] / [MISSING SOURCE] / [PLATFORM-SPECIFIC] / [CONTESTED] |
| `source` | DOI, author+year, or internal reference |
| `agent` | Which HCMSAS agent logged the claim |
| `mnms_category` | Which MNMS metadata category this relates to (if applicable) |
| `notes` | Caveats, disagreements, or flagged uncertainty |
| `status` | active / superseded |

---

## Traceability Log

| claim_id | claim | epistemic_tag | source | agent | mnms_category | notes | status |
|---|---|---|---|---|---|---|---|
| HCM-000 | Matrix initialized for HCMSAS swarm on branch claude/hcmsas-team-launch-CzF8W | [FACT] | internal | HCMSAS_DrNexus | provenance_and_versioning | Baseline entry | active |

---

*Append new entries below this line.*
