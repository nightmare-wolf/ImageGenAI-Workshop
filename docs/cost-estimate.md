# Cost Estimate — RunPod (25 / 50 / 100 attendees)

The only meaningful variable cost is GPU image generation on RunPod Serverless (per-second,
scale-to-zero). Everything else (backend, Postgres, Redis, observability) fits on one small CPU
host and rounds to a few dollars for the day.

> **Pricing basis (RunPod Serverless, 2026).** Mid-tier GPUs (A4000 / RTX 4000-class, 16 GB) ≈
> **$0.58/hr Flex, $0.40/hr Active**; RTX 4090 (24 GB) ≈ **$1.10/hr Flex, $0.77/hr Active**.
> Converted to per-second: 4090 = **$0.000306/s Flex, $0.000214/s Active**; A4000-class =
> **$0.000161/s Flex, $0.000111/s Active**. Flex = scale-on-demand (cold starts possible); Active =
> kept warm (≈30% cheaper, billed even when idle). Verify on the day — see Sources.

## Assumptions

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| GPU | RTX 4090 serverless | Fits SDXL-Turbo/SD-1.5 with headroom; fast = less billed time |
| Model / steps | SDXL-Turbo, ~4 steps | Few-step = ~2–3 s/image |
| Billed seconds per image | **4 s** | 3 s gen + ~1 s overhead (conservative) |
| Generates per attendee (whole event) | **150** | Heavy prompt iteration; many text-only attempts still call the backend |
| Hot generation window | **2.5 h** | CTF blocks; scale-to-zero during intro/break/debrief |
| Peak concurrency factor | attendees × 0.27 | ≈1 generate/attendee/15 s × 4 s each |
| Active-worker reservation | sized to peak concurrency | For reliability (no cold starts mid-block) |

## Model A — Reserved Active workers (recommended for reliability)

Reserve enough **Active** workers to cover peak concurrency for the 2.5 h hot window; they absorb all
compute. Cost = `workers × 9000 s × $0.000214`.

| Attendees | Peak workers | Active-worker cost (2.5 h) | + 25% flex overflow | **Recommended budget** |
|----------:|:------------:|---------------------------:|--------------------:|-----------------------:|
| 25 | 7 | $13.48 | $3.37 | **~$17** |
| 50 | 14 | $26.96 | $6.74 | **~$34** |
| 100 | 27 | $51.98 | $13.00 | **~$65** |

## Model B — Flex-only (cheapest; accepts occasional cold-start waits)

Pay only per generated image at the Flex rate, no reservation:
`attendees × 150 × 4 s × $0.000306`.

| Attendees | Total images | GPU-seconds | **Flex cost** |
|----------:|-------------:|------------:|--------------:|
| 25 | 3,750 | 15,000 | **$4.59** |
| 50 | 7,500 | 30,000 | **$9.18** |
| 100 | 15,000 | 60,000 | **$18.36** |

> **Recommendation:** run a **small Active base** (e.g., 4–8 warm workers) for snappy UX during hot
> blocks, with **Flex autoscale** for overflow, and **scale-to-zero** otherwise. Real cost lands
> between Models A and B — call it **$15 / $30 / $55** for 25 / 50 / 100 as a planning number.

## Non-GPU + one-time costs

| Item | Cost | Notes |
|------|------|-------|
| Backend/DB/Redis/observability host | ~$1–3 for the day | One small CPU VM or RunPod CPU pod (~$0.10/hr × ~10 h incl. setup), or prorated $20–40/mo VM |
| Object storage + egress (images) | < $1 | Images are small; purged after event |
| Dev + load-test GPU burn (one-time) | $20–40 | Building/testing the pipeline and the load test |
| **Day-of total (incl. GPU, recommended)** | **~$20 / $35 / $60** | for 25 / 50 / 100 attendees |

## Budget guardrails (enforced in platform, not just UI)

- **Hard spend cap** on the RunPod endpoint + a budget alarm.
- **Max-workers ceiling** so a cold-start storm can't autoscale unbounded.
- **Per-token + per-IP rate limits** and a concurrency cap in the backend.
- **Scale-to-zero** outside hot windows; **pre-warm active workers** ~20 min before each CTF block.
- **Auto-failover to `mock`** image gen if spend/latency thresholds trip — the workshop continues
  because flags live in the app layer, not the pixels.

These cushions mean even a 4× misestimate at 100 attendees is a ~$250 ceiling, not a runaway bill.

## Sources

- [RunPod Serverless Pricing — docs.runpod.io](https://docs.runpod.io/serverless/pricing)
- [RunPod GPU Cloud Pricing — runpod.io/pricing](https://www.runpod.io/pricing)
- [RunPod Pricing 2026 analysis — gpuperhour.com](https://gpuperhour.com/providers/runpod)
