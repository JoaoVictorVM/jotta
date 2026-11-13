# Model assumptions

Each harness mechanism exists because of an assumption about how coding agents fail. When models or the process change, revisit the assumption before keeping the mechanism.

| Mechanism | Assumption | Revisit when |
|---|---|---|
| Separate reviewer | Authors tend to be generous with their own work | Models or the process change |
| Retry limit | An agent may repeat the same strategy | Failures stop repeating |
| Structured state | The conversation may be interrupted or compacted | Native persistence becomes sufficient |
| Feature specs | Broad changes lose consistency without a contract | Evals show equivalent results without specs |
| Sensors | Rules written only in Markdown can be ignored | The rule stops being relevant |

Remove one mechanism at a time and compare the evals before retiring it.
