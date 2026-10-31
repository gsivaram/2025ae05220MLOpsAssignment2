Promotion decision: eduassist-academic-qa version 3 (v3, json) is promoted to the `production` alias.

JSON validity. EduAssist's application parses every reply as JSON with the fields answer, confidence and key_points, so format reliability is a hard gate rather than a nice-to-have. v3 returned valid JSON for 100% of the five questions and matched the full schema for 100%, while v1 reached 0%, v2 reached 0%: free-text or markdown answers would break the parser and require fragile post-processing.

Quality. On content, v3 mentioned 92% of the expected concepts per question (v1: 100%, v2: 100%). The longer free-text answers cover more concepts, but v3's compact answer still states the core idea, and a more complete answer the app cannot parse has no production value - the coverage gap is an accepted, monitored trade-off. The key_points list and the self-reported confidence level also give the front end structured material that free-text answers cannot provide.

Latency and tokens. Measured on the same five questions with gemini-3.5-flash-lite: v3 (1.32s, 87 in / 151 out tokens, $0.000403 per request, valid JSON 100%) versus v1 (2.43s, 22 in / 608 out tokens, $0.001526 per request, valid JSON 0%); v2 (1.93s, 46 in / 376 out tokens, $0.000955 per request, valid JSON 0%). The JSON prompt is longer on the input side, but input tokens are cheap and are processed in parallel; latency is dominated by output length, and the schema keeps answers compact.

Cost. At $0.30 / $2.50 per million input/output tokens (pricing date 2026-10-30, USD), v3 projects to $4.03 for 10,000 requests per month, against $15.26 for v1, $9.55 for v2. Because output tokens cost 8.3x more than input tokens, the shorter structured answer outweighs the extra prompt tokens.

Risks and next steps. Five questions at temperature 0 are a small sample; before a wider rollout the evaluation set should grow, valid_json should be monitored in production, and a strict parser with a retry should guard the rare invalid reply. Because the app loads prompts:/eduassist-academic-qa@production, a rollback is a single alias change.
