# CareerRadar default watch list: 50 companies shaping AI and future tech (2026)

Checked 2026-10-25. Every board below was hit with one request per company; the job count is
what the endpoint returned that day. Machine-readable copy: `companies.json` (same folder).
Probe scripts: `probe/` (`probe.py` for ATS boards, `custom.py` for big-tech endpoints).

Selection: breadth over depth, so each segment has enough companies for a trend to show up
(frontier labs 7, big tech 7, chips 10, infra/data 9, dev tools/apps 8, robotics/autonomy 7,
fintech/platform 2). Each "why" cites the company's own site.

Totals: 50 picked, **48 verified** (Meta and Tesla block non-browser clients). 33 run on
existing ATS fetchers (Greenhouse 14, Ashby 17, Lever 1, Workable 1), 4 on existing big-tech
fetchers (Google, DeepMind via Google, Microsoft, Apple; small extensions needed), 13 need new
fetchers (see the last section).

## Frontier AI labs

| Company | Why it matters (source) | Board | Jobs |
|---|---|---|---|
| OpenAI | Maker of ChatGPT and GPT models ([about](https://openai.com/about/)) | `ashby:openai` | 793 |
| Anthropic | Maker of Claude; AI safety and research company ([company](https://www.anthropic.com/company)) | `greenhouse:anthropic` | 682 |
| Google DeepMind | Alphabet's AI lab behind Gemini ([about](https://deepmind.google/about/)). Its careers page links to Google careers filtered `company=DeepMind` ([careers](https://deepmind.google/careers/)) | `google` + `company=DeepMind` | 125 |
| SpaceXSI (formerly xAI) | Grok developer; site and Greenhouse board now branded SpaceXSI ([company](https://x.ai/company)) | `greenhouse:xai` (board name "SpaceXSI") | 298 |
| Mistral AI | Europe's leading frontier lab, open-weight models ([about](https://mistral.ai/about)) | `ashby:mistral.ai` (dot kept, from mistral.ai/careers) | 225 |
| Cohere | Enterprise LLMs, secure deployment ([about](https://cohere.com/about)) | `ashby:cohere` | 116 |
| Thinking Machines Lab | New frontier research lab ([site](https://thinkingmachines.ai/)) | `ashby:thinkingmachines` | 52 |

## Hyperscalers / big tech

| Company | Why it matters (source) | Board / endpoint | Jobs |
|---|---|---|---|
| Google | Gemini, Google Cloud, custom TPUs ([TPU](https://cloud.google.com/tpu)) | existing `google` fetcher; global page `google.com/about/careers/applications/jobs/results/` (ds:1) | 3473 |
| Microsoft | Azure AI, Copilot ([AI](https://www.microsoft.com/en-us/ai)) | existing `microsoft` fetcher; `apply.careers.microsoft.com/api/pcsx/search?domain=microsoft.com&location=` | 2440 |
| Amazon | AWS Bedrock and Trainium chips ([Trainium](https://aws.amazon.com/ai/machine-learning/trainium/)) | NEW `amazon`: `https://www.amazon.jobs/en/search.json?result_limit=N&offset=N` | 10000 (looks capped: one category alone returned 2562; page by category to get the real total) |
| Meta | Llama, Meta Superintelligence Labs ([MSL](https://www.meta.com/superintelligence/)) | NEW `meta`: `metacareers.com/jobs` returns 400 to curl; GraphQL behind a browser session. **Not verified** | n/a |
| Apple | Apple Intelligence ([page](https://www.apple.com/apple-intelligence/)) | existing `apple` fetcher; `jobs.apple.com/en-us/search` embeds `totalRecords` | 4452 |
| Oracle | OCI AI infrastructure ([page](https://www.oracle.com/ai-infrastructure/)) | NEW `oracle-hcm`: `https://eeho.fa.us2.oraclecloud.com/hcmRestApi/resources/latest/recruitingCEJobRequisitions?onlyData=true&expand=requisitionList&finder=findReqs;siteNumber=CX_45001,limit=25` (`TotalJobsCount`) | 2495 |
| Salesforce | Agentforce AI-agent platform ([page](https://www.salesforce.com/agentforce/)) | NEW `workday:salesforce.wd12.myworkdayjobs.com/salesforce/External_Career_Site` | 1573 |

## AI chips / hardware

| Company | Why it matters (source) | Board / endpoint | Jobs |
|---|---|---|---|
| NVIDIA | AI accelerators, networking, CUDA ([data center](https://www.nvidia.com/en-us/data-center/)) | NEW `workday:nvidia.wd5.myworkdayjobs.com/nvidia/NVIDIAExternalCareerSite` | 2000 |
| AMD | Instinct GPUs ([Instinct](https://www.amd.com/en/products/accelerators/instinct.html)) | NEW `jibe` (iCIMS-backed): `https://careers.amd.com/api/jobs?page=1&limit=100` (`totalCount`) | 1263 |
| Intel | CPUs and Intel Foundry ([foundry](https://www.intel.com/content/www/us/en/foundry/overview.html), 403 to curl, loads in a browser) | NEW `workday:intel.wd1.myworkdayjobs.com/intel/External` | 787 |
| Broadcom | AI data-center Ethernet switching ([switching](https://www.broadcom.com/products/ethernet-connectivity/switching)) | NEW `workday:broadcom.wd1.myworkdayjobs.com/broadcom/External_Career` | 366 |
| Qualcomm | On-device AI, mobile/PC/auto ([AI](https://www.qualcomm.com/artificial-intelligence)) | Eightfold PCSX, same API as Microsoft: `https://careers.qualcomm.com/api/pcsx/search?domain=qualcomm.com&query=&location=&start=0` | 2069 |
| Arm | CPU architecture for AI devices and servers ([AI](https://www.arm.com/markets/artificial-intelligence)) | NEW `talentbrew` (Radancy) HTML: `careers.arm.com/search-jobs`, `data-total-job-results` | 440 |
| Micron | HBM memory for AI accelerators ([HBM](https://www.micron.com/products/memory/hbm)) | NEW `workday:micron.wd1.myworkdayjobs.com/micron/External` | 3123 |
| Cerebras | Wafer-scale WSE-3 chip ([chip](https://www.cerebras.ai/chip)) | `ashby:cerebras` | 122 |
| Groq | LPU inference chips and cloud ([site](https://groq.com/)) | NEW `gem`: `https://api.gem.com/job_board/v0/groq/job_posts/` (board found as `jobs.gem.com/groq` on groq.com/careers) | 37 |
| Tenstorrent | RISC-V AI computers ([site](https://tenstorrent.com/)) | `greenhouse:tenstorrent` | 119 |

## AI infra / data platforms

| Company | Why it matters (source) | Board | Jobs |
|---|---|---|---|
| Databricks | Data + AI platform ([platform](https://www.databricks.com/product/data-intelligence-platform)) | `greenhouse:databricks` | 896 |
| Snowflake | AI Data Cloud ([AI](https://www.snowflake.com/en/product/ai/)) | `ashby:snowflake` | 355 |
| Scale AI | Data and evals for labs and governments ([site](https://scale.com/)) | `greenhouse:scaleai` | 171 |
| CoreWeave | Specialist AI GPU cloud ([site](https://www.coreweave.com/)) | `greenhouse:coreweave` | 316 |
| Hugging Face | Open-source model hub ([site](https://huggingface.co/)) | `workable:huggingface` (v3 POST `total`) | 6 |
| Together AI | AI-native cloud for open models ([site](https://www.together.ai/)) | `greenhouse:togetherai` | 85 |
| Cloudflare | Serverless GPU inference on its edge (Workers AI) ([docs](https://developers.cloudflare.com/workers-ai/)) | `greenhouse:cloudflare` | 454 |
| Fireworks AI | Open-model inference and fine-tuning ([site](https://fireworks.ai/)) | `ashby:fireworks` | 91 |
| Lambda | GPU cloud ([site](https://lambda.ai/)) | `ashby:lambda` | 99 |

## Dev tools / AI apps

| Company | Why it matters (source) | Board | Jobs |
|---|---|---|---|
| Anysphere (Cursor) | Leading AI coding agent ([site](https://cursor.com/)) | `ashby:cursor` | 126 |
| Cognition | Devin, autonomous software engineer ([site](https://cognition.ai/)) | `ashby:cognition` | 105 |
| Perplexity | AI answer engine, Comet browser ([hub](https://www.perplexity.ai/hub)) | `ashby:perplexity` | 132 |
| ElevenLabs | Voice AI models and agents ([site](https://elevenlabs.io/)) | `ashby:elevenlabs` | 159 |
| Harvey | Vertical AI for legal ([site](https://www.harvey.ai/)) | `ashby:harvey` | 358 |
| Sierra | AI customer-service agents ([site](https://sierra.ai/)) | `ashby:sierra` | 210 |
| Glean | Enterprise AI search and agents ([site](https://www.glean.com/)) | `greenhouse:gleanwork` | 131 |
| Vercel | AI SDK, v0, AI app hosting ([AI](https://vercel.com/ai)) | `greenhouse:vercel` | 95 |

## Robotics / autonomy

| Company | Why it matters (source) | Board / endpoint | Jobs |
|---|---|---|---|
| Waymo | Leading robotaxi operator ([site](https://waymo.com/)) | `greenhouse:waymo` | 366 |
| Tesla | FSD, Optimus humanoid ([AI](https://www.tesla.com/AI), 403 to curl) | NEW `tesla`: `tesla.com/cua-api/apps/careers/state` returns 403 (Akamai). **Not verified**, browser only | n/a |
| Figure AI | General-purpose humanoid ([site](https://www.figure.ai/)) | `greenhouse:figureai` | 104 |
| Physical Intelligence | Robot foundation models ([site](https://www.physicalintelligence.company/)) | `ashby:physicalintelligence` | 45 |
| Wayve | End-to-end embodied AI for driving ([site](https://wayve.ai/)) | `ashby:wayve` (from wayve.ai/careers/join-us) | 178 |
| Applied Intuition | Physical-AI software for vehicles and defense ([site](https://www.appliedintuition.com/)) | `ashby:applied` (from its careers page) | 328 |
| Anduril | Autonomous defense systems ([site](https://www.anduril.com/)) | `greenhouse:andurilindustries` (`meta.total` 2511) | 2511 |

## Fintech / platform (AI-leading)

| Company | Why it matters (source) | Board | Jobs |
|---|---|---|---|
| Stripe | Agentic commerce and AI billing on Stripe ([docs](https://docs.stripe.com/agents)) | `greenhouse:stripe` | 719 |
| Palantir | AIP, LLMs on private enterprise and government data ([AIP](https://www.palantir.com/platforms/aip/)) | `lever:palantir` | 309 |

## Runners-up (just missed)

All boards verified 2026-10-25 unless noted.

| Company | Segment | Board | Jobs | Why it missed |
|---|---|---|---|---|
| Reflection AI | frontier lab | `ashby:reflectionai` | 45 | Smaller open-weight lab; labs already well covered |
| Safe Superintelligence | frontier lab | `ashby:ssi` (linked from ssi.inc) | 0 listed | No public openings, nothing to trend |
| Etched | AI chips | `ashby:etched` | 116 | Single-product transformer ASIC; chips segment full |
| Modal | AI infra | `ashby:modal` | 43 | Overlaps Together/Fireworks/Lambda |
| Datadog | infra/observability | `greenhouse:datadog` | 433 | Strong, but AI is not its core |
| Replit | dev tools | `ashby:replit` | 37 | Small board; Cursor/Cognition cover agentic coding |
| Lovable | dev tools | `ashby:lovable` | 81 | Overlaps Vercel v0 / Replit |
| Notion | AI apps | `ashby:notion` | 140 | AI is a feature, not the product |
| Figma | dev/design tools | `greenhouse:figma` | 138 | Same reason |
| Decagon | AI apps | `ashby:decagon` | 134 | Overlaps Sierra |
| Runway | AI apps (video) | `ashby:runway-ml` (from runwayml.com/careers; `ashby:runway` is a different 3-job board) | 48 | Generative video; small board |
| Black Forest Labs | frontier lab (image) | `ashby:black-forest-labs` | 13 | Very small board |
| Zoox | robotics | `lever:zoox` | 236 | Amazon-owned, Waymo covers robotaxi |
| 1X | robotics | `ashby:1x` | 101 | Overlaps Figure |
| ServiceNow | enterprise platform | `smartrecruiters:ServiceNow` | 715 | Enterprise AI agents, overlaps Salesforce |

Not resolved (guessed tokens all failed; needs a browser look): Skild AI (skild.ai/career is
JS-rendered; `ashby:skild`, `ashby:skild-ai`, `greenhouse:skildai` 404), Shopify (own site, no ATS
in HTML), Uber and Dell (Workday guesses returned 422, site names unknown).

## New fetchers needed (grouped, most reused first)

Existing fetchers (Greenhouse, Ashby, Lever, Workable, Apple, Google, Microsoft) cover 37 of the
50 boards directly. The rest:

| Fetcher | Companies (top 50) | Count | Notes |
|---|---|---|---|
| **workday** | NVIDIA, Intel, Broadcom, Salesforce, Micron | **5** | POST `https://<tenant>.wd<n>.myworkdayjobs.com/wday/cxs/<tenant>/<site>/jobs` `{"limit":20,"offset":N,"searchText":"","appliedFacets":{}}`; `total` in response. Also runners-up Boston Dynamics (`bostondynamics.wd1/.../Boston_Dynamics`, 83) and Adobe (`adobe.wd5/.../external_experienced`, 297). Most reused. |
| pcsx (Eightfold) | Qualcomm | 1 | Same API as the existing `microsoft` fetcher; generalise it to `pcsx:<host>/<domain>` instead of a new one |
| amazon | Amazon | 1 | `amazon.jobs/en/search.json`, `hits` capped at 10000; page by category or location |
| oracle-hcm | Oracle | 1 | Oracle Recruiting Cloud REST, `siteNumber=CX_45001` |
| jibe | AMD | 1 | `careers.amd.com/api/jobs`, `totalCount` |
| gem | Groq | 1 | `api.gem.com/job_board/v0/<board>/job_posts/` |
| talentbrew (Radancy) | Arm | 1 | HTML only; `search-jobs/results` paging |
| meta | Meta | 1 | Not verified: GraphQL behind browser session; likely browser fallback |
| tesla | Tesla | 1 | Not verified: Akamai 403; browser fallback |

Extensions to existing fetchers:

- `google`: add a `company=` filter (DeepMind: 125 jobs), and a global (no-location) mode for a
  company-wide weekly snapshot.
- `microsoft`, `apple`: tokens are locations today; a global snapshot needs an empty-location mode
  (both endpoints answered with an empty location: 2440 and 4452).
