# GB-CC-EN Editorial Contract — REC / P1 / REC+P1

Status: draft active contract
Owner: MGS / Zeus architecture
Scope: UK credit-card content in English for REC, P1 and REC+P1 operations
Source policy: current official issuer source, not editorial cache

## 1. Authority

This file is the active editorial source of truth for GB credit-card REC/P1 production.

Authority order for content decisions:

1. User request for the current task.
2. This contract.
3. Runtime hard gates and validators in the runners.
4. Site configuration in `data/sites.json`.
5. Historical references only when explicitly consulted for audit or migration.

Historical files under `references/` are not active production rules unless their rule has been promoted into this contract or into runtime validation.

## 2. Core business model

MGS uses four article types/products:

- REC: short recommendation article.
- P1: longer complementary article.
- REC+P1: one operational request that produces a REC and its complementary P1.
- SEO: separate future product, out of scope here.

REC+P1 is not a third article template. It is one business operation composed of two separate article generations.

User journey:

```text
REC → P1 → official issuer/bank page
```

REC sells interest. P1 explains and prepares the reader to continue to the official issuer page.

## 3. No editorial cache policy

Production content must not use editorial card cache.

Do not use `data/card-cache.db` or card-cache scripts as a source for:

- card benefits;
- rewards;
- representative APR;
- annual fee;
- eligibility;
- product positioning;
- descriptor/tag/headline;
- opening angle;
- body copy;
- table copy;
- CTA copy;
- official URL, unless explicitly approved as a temporary manual fallback;
- image, unless separately validated in the current run.

Allowed technical data/caches:

- `data/sites.json` for site configuration.
- `data/wp-term-cache.json` for WordPress taxonomy IDs.
- `data/rec-fingerprints.db` or successor QA DB for similarity history only.
- logs/audit files for traceability.

If current official source extraction fails, the correct behavior is to ask for a valid official URL or explicit facts, not silently fall back to editorial cache.

## 4. Source-of-truth policy

The current official issuer/product page is the source of truth for product facts.

Rules:

- Do not invent benefits, fees, APR, bonuses, eligibility rules, or application terms.
- Do not treat third-party summaries as final truth.
- If a reader-rendered version of the same official URL is used because the issuer blocks normal fetches, it must still represent the same official URL.
- If the official page does not expose usable product content, block publication or ask Rodolfo/Raquel for the correct official link/facts.
- Financial terms can change; do not rely on stale historical/cache data.

## 5. Common editorial rules

Applies to REC and P1.

### Required

- English content for GB credit-card vertical.
- Product-specific facts and examples.
- Product facts must be translated into perceived user benefits: show how the feature feels in a real use case, not only what the feature is.
- For rewards cards, benefit copy must explain practical usage of the rewards system: everyday spending, recurring payments, online purchases, vouchers, Pay with Rewards/offset mechanics, welcome bonus, partner/network acceptance, and international use when each fact is confirmed by the official source.
- Concrete confirmed values such as welcome-bonus points and estimated cash value must be surfaced when available; do not reduce them to weak phrasing like `can feel useful`.
- APR, fees and repayment cautions must be contextualized in natural language. Avoid dropping raw regulatory strings into body copy unless the section specifically needs the exact figure.
- Keep financial-responsibility warnings in strategic places; do not let repeated defensive language dominate benefit sections or erase conversion intent.
- Tone must be professional, accessible, confident and human; persuasive without exaggeration, never cold product inventory.
- Clear distinction between site content and official issuer application process.
- Respect official source limitations.
- Use compliant language: no guaranteed approval, no unsupported claims.
- Mention that final rates/terms are determined by the issuer when relevant.
- Avoid generic copy that could apply to any card.
- Avoid abstract benefit filler such as `value is easier to picture`, `can feel useful`, or `might be relevant` when a concrete use case can be written from official facts.
- Avoid generic wrap-up sentences that merely say the article is avoiding generic assumptions. Replace them with practical, card-specific user outcomes or remove them.
- Avoid repeated openings across different cards.
- Avoid placeholders and internal notes.
- Preserve card identity in images.
- Open REC/P1 with the user's concrete problem or outcome, not with a technical inventory of the product.
- LazyBlock tags must be benefit-led, specific and commercially useful; they must not repeat the product category already obvious from the card name.

### Forbidden

- Placeholder phrases such as `Check issuer terms` as table/content filler.
- Visible extraction failures such as `Not stated on the official product page`, `N/A`, `unknown`, or `official source states Not stated`.
- Generic lines like `Apply now and get benefits today` without specific value.
- Reused boilerplate paragraphs across cards, especially eligibility/application copy that could apply unchanged to any issuer.
- Copying paragraphs from another card article.
- Copying REC body prose into P1.
- Using old cache facts to generate new articles.
- Generic LazyBlock labels such as `Card benefits`, `Credit card`, `Official terms`, `Transfer fee`, or truncated labels such as `Over 1`.
- Numeric/fragmented LazyBlock labels such as `2`, `0`, `24`, `2.99`, or any label created by cutting a decimal or fee string.
- Redundant LazyBlock labels that only repeat the card category/name, such as `Balance transfer` on a card already named Balance Transfer.
- Ambiguous fee claims in LazyBlock labels such as `No fees` when the product has a balance-transfer fee or any other material fee.
- Table columns beyond the approved schema for REC comparison table.
- Card image with phone mockup, hand, lifestyle background, vertical crop, frame, props, or UI context in the LazyBlock.

## 5A. Experience-led category map

Every article must write from the reader's practical experience, not from a banking feature list. The silent editorial question is:

```text
How does this card improve this person's real routine, decision or experience?
```

A card feature should not be presented as a bare function, fee, rate or reward category. When the official source confirms a feature, translate it into a realistic user context, emotional payoff and practical outcome. Do not invent benefits, savings, eligibility, approval odds, insurance, limits, rates, perks or categories that are not supported by the current official source or explicit user-provided facts.

### Category interpretation rules

Use the card's confirmed facts to identify one primary category and any real secondary categories. Many cards are hybrid products, so the article must combine relevant angles when the product genuinely supports them. Examples: cashback + travel rewards, premium + airline, digital bank + crypto, freelancer + business, digital nomad + multi-currency, green + digital experience.

When a confirmed feature fits one or more category examples, adapt the approach into natural variations instead of copying the example wording. Build multiple combinations from the card's real characteristics so the pattern scales across many articles without producing repeated boilerplate.

Required workflow for REC and P1 drafting:

1. Identify the primary user routine behind the card.
2. Identify confirmed secondary routines or lifestyle contexts.
3. Select the dominant emotion or practical payoff.
4. Convert each important official feature into a real-use scenario.
5. Vary wording, sentence structure and benefit framing across sections.
6. Keep financial responsibility, but do not let cautions erase the commercial appeal.
7. Verify that every persuasive line remains fact-based.

### Category tone matrix

```text
Category                    | Dominant experience to write toward
----------------------------|---------------------------------------------------------------
Cashback                    | Everyday spending feels smarter because routine purchases return value.
Travel rewards              | Trips, bookings and overseas purchases feel more rewarding and manageable.
Airline                     | Frequent flights feel less stressful through loyalty, baggage or airport convenience.
Hotel rewards               | Regular stays feel more comfortable, practical or affordable over time.
Luxury / premium            | Higher spending and travel feel smoother through convenience, time-saving and access.
Credit builder              | Credit improvement feels like gradual progress, not financial judgment.
Secured                     | Starting or rebuilding credit feels more controlled, accessible and structured.
Balance transfer            | Existing balances feel more manageable through relief, organisation and lower pressure.
Low APR                     | Occasional borrowing feels more predictable and easier to plan responsibly.
Business / corporate        | Professional spending feels more organized and separated from personal finances.
Student                     | Early financial independence feels simpler, safer and more structured.
Retail / store              | Shopping with a familiar brand feels more worthwhile when purchases already happen.
BNPL / installment          | Larger purchases feel easier to budget through predictable payments, without impulse pressure.
Digital bank                | Daily money management feels faster, simpler and more app-driven.
Crypto / Web3               | Digital assets feel more connected to practical everyday spending, without hype.
Multi-currency              | International payments feel simpler across currencies and countries.
Digital nomad               | Remote-work travel feels more flexible through global payments and currency convenience.
Gamer                       | Entertainment spending feels more relevant to gaming habits and digital platforms.
Subscription / membership   | Recurring digital payments feel more rewarding or easier to optimize.
AI-driven finance           | Spending decisions feel more organized through automated insights and reduced manual effort.
Green / sustainable         | Spending feels more aligned with personal values, without moralising or greenwashing.
Teen / family               | Family spending feels more transparent, educational and controlled.
Fuel / fleet                | Driving or transport costs feel more predictable and operationally organized.
Healthcare / medical        | Recurring health expenses feel more stable and easier to organize, without drama.
Freelancer / creator        | Variable income and project spending feel more organized and flexible.
E-commerce seller           | Inventory, ads and online business costs feel easier to centralize and track.
Islamic finance             | Financial tools feel aligned with ethical or religious principles through transparency.
Community / cooperative     | The financial relationship feels more personal, local or community-connected.
Investment-linked           | Everyday spending feels more connected to long-term habits, without return promises.
```

### Category-specific cautions

- Cashback: do not exaggerate savings or make cashback sound like investing.
- Travel: do not repeat `travel rewards` mechanically or turn the article into tourism copy.
- Airline/hotel: do not list only miles/points; explain airport or stay experience when supported.
- Premium: avoid arrogance, ostentation or artificial luxury language.
- Credit builder/secured/student: avoid negative labels such as `poor credit`, punitive tone or making the card feel inferior.
- Balance transfer/low APR/BNPL: do not encourage debt, impulse spending or aggressive financial advice.
- Business/freelancer/e-commerce/fleet: avoid cold accounting/software language; connect features to daily operational organization.
- Crypto/Web3/AI: avoid hype, speculative promises and overly technical jargon.
- Green/community/Islamic/family/healthcare: avoid moralising, political framing, religious simplification or emotional exploitation.

### Hybrid card rule

If a card belongs to multiple categories, the article must connect the combined experience instead of treating the category as a label. The reader does not think in banking niches; the reader thinks in practical questions:

```text
Does this simplify my routine?
Does this improve my trips?
Does this organize my work?
Does this reduce costs I already have?
Does this fit my lifestyle or values?
```

The final copy should feel like a useful recommendation and a natural analysis of real-life fit, not a technical sheet, bank catalogue or table of benefits.

## 6. Image rules

### LazyBlock card image

The LazyBlock card image must be the isolated card only.

Required:

- horizontal/card-like aspect;
- transparent or clean isolated background;
- no person;
- no phone mockup;
- no hand;
- no props;
- no lifestyle scene;
- no external frame or page UI;
- card design must not be hallucinated or changed.

Manual image quality and size scope:

- The final LazyBlock card asset must be visually acceptable in context, not merely technically valid: brand/card identity readable, no gross pixelation at displayed size, no broken edges/notches, no canvas residue, no blur severe enough to make the card look fake or low-effort.
- Prefer the highest-quality available source that preserves the real card design. If the supplied image is low quality but an official/better source is available, use the better validated source instead of blindly preserving the supplied file.
- If Rodolfo/Raquel supplied the image and identity/semantics are correct, useful crop width below 600px is a warning, not a blocker.
- Small manual card images may publish after normalization only when the card renders correctly inside the LazyBlock/card UI.
- Low source resolution, visible pixelation, or forced upscaling must be reported as `LOW_QUALITY_SOURCE`/warning in the final response unless a better source replaced it.
- Identity mismatch, wrong product, mockup/context image, failed normalization, or visibly poor final LazyBlock rendering remains a blocker.

Manual banner/canvas extraction scope:

- If the supplied or discovered image is a banner, article thumbnail, social graphic or canvas with the actual card inside it, never upload the whole image into LazyBlock.
- Extract only the real card object; remove headline, logo text, decorative waves/background, white canvas, borders and frame-like padding.
- If the card object inside the source is vertical/portrait, rotate the card itself into horizontal orientation before upload.
- After extraction, build a LazyBlock-safe asset: card centered, enough breathing room to avoid CSS clipping, and either clean transparency or a neutral solid background when transparency exposes edge/notch artifacts.
- Preview the final asset against the real card-container context before publishing. If a border, semicircle/notch, canvas residue or clipped edge appears, repair the asset before upload/report.
- The final card asset, not the original banner/intermediate image, must be used downstream for featured-image generation.

If the supplied or discovered card image cannot be normalized into a valid isolated card image, block or ask for a correct card image.

### Featured image

Featured image can be contextual/commercial, but must preserve the card identity and pass semantic audit.

REC and P1 featured images in the same REC+P1 operation must be different assets and different visual concepts.

Required:

- REC and P1 must use different WordPress media IDs and different source URLs.
- REC and P1 must not reuse the same generated file, same uploaded media, or same composition with only minor crop/filename changes.
- Featured generation must use the final validated LazyBlock card asset after extraction/rotation/edge repair, not the original banner, raw source or any rejected intermediate file.
- If the card asset is repaired after publish, regenerate and re-upload affected featured images from the repaired card asset; do not leave featured images based on the bad source.
- REC featured image should work as the short commercial/recommendation hook.
- P1 featured image should work as the application/deep-dive support image, with a clearly different scene, framing, background or foreground treatment.
- During post-publish repair, replacing one side's featured image must not accidentally point both REC and P1 to the same media item.

Validation: before final report, verify both public pages and/or REST records show distinct `featured_media` IDs and distinct featured image URLs. If they match, repair before reporting success. Also verify the rendered/public pages reference the final card asset and do not reference the raw banner or rejected intermediate media.

## 7. REC contract

REC is the short recommender.

### Purpose

- Spark interest quickly.
- Present the strongest confirmed card benefits.
- Use a light commercial/recommendation tone.
- Route the reader to P1 for more detail.

### Tone

- Clear, practical, benefit-led.
- More commercial than P1, but not hype.
- Human and specific, not generic finance filler.

### Structure intent

REC should include:

1. Specific opening/subtitle based on a confirmed benefit or positioning angle.
2. Short explanation of why the card may be worth considering.
3. LazyBlock card component.
4. Main benefit sections.
5. Comparison/positioning table when applicable.
6. CTA/button route to P1.

### REC hard requirements

- Shorter than P1.
- Must mention the specific card name and confirmed benefits.
- Must not be a long application guide.
- Must not use placeholder table values.
- Comparative table schema must be exactly approved by runtime/template.
- CTA should send user from REC to P1 when P1 exists or is part of the request.
- Opening must translate the card into a user outcome/difficulty (interest saved, repayment breathing room, fee control, rewards use), not merely say it has confirmed costs/benefits.
- Benefit sections must convert technical benefits into perceived benefits. Example: do not only say `No foreign transaction fees`; explain that overseas card purchases can feel easier because the reader is not adding a typical FX card fee to every eligible purchase.
- For rewards REC, the first benefit pass must balance everyday use and travel use when both are supported. Do not turn a broad rewards card into only a travel card because it has no foreign transaction fees.
- Rewards REC must make the points system concrete: explain how points can be earned from planned/routine spending and why Mastercard/network acceptance can make earning feel consistent across everyday purchases, online stores or international spending when supported by the source.
- If the official source confirms a welcome bonus, include the point amount/value and the trigger in plain language, not as a generic `welcome bonus` mention.
- If the official source confirms Pay with Rewards, vouchers or purchase offset/redeem mechanics, explain what that means in practical user terms instead of saying only `use points`.
- REC comparison table should stand on its own. Do not add generic paragraphs after the table explaining `Compared with...`, `The table is a quick orientation tool`, or `Rates and terms can change`; use that space for the next useful subtitle/section.
- REC top-of-page is a monetisation surface: the title/summary and first 1-2 paragraphs appear before the ad and before the card on mobile, so they must carry the strongest commercial intent keywords for ad relevance and click-through to P1.
- For balance-transfer REC, the first visible summary/paragraphs must include terms such as balance transfer, 0% interest/interest-free, months, existing debt/card debt, repayments, interest pressure/savings, and transfer fee when supported by facts.
- LazyBlock tags must be selected from the strongest visible benefits and validated for specificity.

### REC must not

- Become a neutral encyclopedia page.
- Use vague repeated openings.
- Use stale cache facts.
- Promise approval.
- Send user directly to issuer when the intended flow is REC → P1.

## 8. P1 contract

P1 is the longer complementary article.

### Purpose

- Explain the card in more depth.
- Help the reader evaluate costs, benefits, eligibility context and application flow.
- Route the reader to the official issuer/bank page.

### Tone

- More detailed and decision-oriented than REC.
- Practical and explanatory.
- Still readable and human; not generic, not mechanically templated.

### Structure intent

P1 should include:

1. Specific opening/subtitle based on the card's confirmed value proposition.
2. Contextual featured image in article and as WordPress featured image.
3. LazyBlock card component with official issuer CTA.
4. Main benefits section.
5. Costs/fees/APR section when officially stated.
6. Eligibility/application context where officially available.
7. Practical usage or maximization section.
8. Final CTA to official issuer page with clear redirection language.

### P1 hard requirements

- P1 button routes to official issuer/bank URL.
- P1 must use current official source facts.
- P1 must not rely on REC body copy.
- P1 must not be a stretched REC.
- P1 must not use cache facts.
- P1 must be long enough to function as a complementary deep-dive, but not padded with generic filler.
- P1 opening must lead with the user problem/outcome before technical fees and application mechanics.
- P1 introduction paragraphs should stay within 30–35 words each where possible, so mobile paragraphs remain compact.
- P1 must establish commercial/emotional context in the first blocks: what pain is being solved, what outcome improves, and why the reader should care now.
- P1 benefit sections should explain why the benefit matters in real usage, not only list extracted facts.
- P1 benefit sections must build mini-contexts, not stack isolated sentences. Each short paragraph should connect context + benefit + practical implication.
- For rewards P1, dedicate enough space to concrete differentiators: welcome bonus amount/value/trigger, points earning on eligible routine spending, redemption/use mechanics, Mastercard acceptance, online/recurring spending and international purchases when confirmed.
- P1 must not overuse hedging phrases such as `may suit`, `can feel`, `might fit`, or `could be relevant`. Use confident, compliant phrasing when the statement is supported, e.g. `is particularly relevant for...`.
- Keep raw APR/fee figures inside costs/conditions context and explain the practical meaning. Do not let regulatory phrasing interrupt benefit-led sections.
- P1 section composition should adapt to the card identity: more travel/rewards, low-rate, premium, everyday, institutional or technical depending on the product and audience. Do not force every card into the same rigid section voice.
- For balance-transfer P1s, context must explicitly connect to debt, interest pressure, repayment simplification, multiple payments, and financial organisation when supported by the product facts.
- The final P1 subtitle/closing section must be concise and structurally controlled: normally no more than five paragraphs. Condense repeated warnings and use the ending to summarize ideal user profile, core advantage and issuer CTA.

### P1 must not

- Copy REC paragraphs or REC opening.
- Reuse REC benefit prose as its own body.
- Preserve REC descriptor/tag by default without validation.
- Use generic fallback lines as the main explanation.
- Turn into a short recommendation page.

## 9. REC+P1 orchestration contract

REC+P1 is one operational request, two independent generations.

Correct production model:

```text
request REC+P1
→ run REC generation/validation
→ publish or prepare REC
→ pass minimal metadata only
→ run P1 generation/validation in separate context
→ publish or prepare P1
→ validate REC → P1 → issuer path
→ report both articles together
```

The orchestrator must not generate article prose. It coordinates execution and validation only.

### Allowed REC → P1 handoff

| Field | Allowed | Notes |
|---|---:|---|
| `card_name` | yes | technical identity |
| `card_slug` | yes | technical identity |
| `rec_post_id` | yes | linking |
| `rec_url` | yes | linking |
| `official_url` | yes | source reference |
| validated `card_image_id` / `card_image_url` | yes | technical reuse only after validation |
| REC paragraphs/body | no | prevents editorial contamination |
| REC opening/subtitle | no | prevents repetition |
| REC benefit prose | no | prevents P1 becoming expanded REC |
| REC descriptor/tag labels | no by default | only if explicitly validated/promoted |
| card-cache data | no | not source of truth |

### Required validations for REC+P1

- REC exists and passes REC QA.
- P1 exists and passes P1 QA.
- REC points to P1.
- P1 points to the official issuer page.
- P1 does not copy REC body/opening.
- Final report includes both URLs and validation evidence.

## 10. Hard gates

Hard gates block publication or require repair before claiming success.

### Common hard gates

- Missing usable official source.
- Placeholder text in final content.
- Internal notes or `Review`-style text in public fields.
- Invalid card image for LazyBlock.
- Missing required URL/link.
- Public verification failure.
- Yoast/readability below agreed green threshold when that threshold is active.
- Invalid taxonomy/tag format.
- Missing validated card image in P1 when it depends on REC image.

### REC-specific hard gates

- Invalid comparison table schema.
- Missing real competitor data when comparison table is required.
- Subtitle/excerpt over active length limit.
- REC CTA not routing correctly to P1 when REC+P1 is requested.

### P1-specific hard gates

- P1 official CTA not routing to issuer.
- P1 body below/above active word-count bounds.
- P1 copies REC body/opening.
- P1 uses REC descriptor/tag as unvalidated editorial fallback.

## 11. Semantic validators

Semantic validators catch issues that deterministic gates do not catch.

Initial validators should detect:

- generic opening phrases;
- repeated openings across recent cards;
- near-duplicate body sections;
- REC tone becoming too neutral/informational;
- P1 tone becoming REC-like or too promotional;
- missing card-specific benefits;
- rewards cards mentioning points, welcome bonuses, Pay with Rewards or network acceptance without practical examples or confirmed concrete values;
- excessive defensive/regulatory language crowding out benefits;
- repeated weak hedges (`can feel`, `might`, `could`, `may`) where a supported, confident sentence is possible;
- overlong closing sections, especially P1 final subtitles exceeding the structural paragraph limit;
- overly template-like sections;
- conclusion/meta description too similar to previous posts.

High-risk semantic failures should trigger regeneration or block pending review, not only produce a hidden warning.

## 12. Warnings

Warnings should be visible in the final report but do not automatically block.

Examples:

- minor source extraction limitation with explicit fallback facts;
- slower than expected image generation;
- non-critical Yoast suggestions above minimum threshold;
- public page verification succeeded but with non-critical rendering quirks.

Warnings must not be reported as clean success.

## 13. Manual QA boundary

Raquel/Rodolfo manual QA remains valuable for editorial judgment, but routine deterministic failures must not depend on manual QA.

Manual QA should focus on:

- final editorial taste;
- commercial strength;
- brand fit;
- nuanced tone;
- strategic prioritization of benefits.

Manual QA should not be needed to catch:

- placeholders;
- invalid images;
- wrong table columns;
- missing links;
- obvious duplicated openings;
- cache-stale facts;
- REC/P1 link errors.

## 14. Reporting requirements

Final REC/P1/REC+P1 report must include:

- article type(s);
- site;
- card name;
- REC URL when applicable;
- P1 URL when applicable;
- official issuer URL;
- image validation status;
- table validation status for REC;
- duplicate/similarity validation status;
- public verification status;
- total user-perceived operation time;
- warnings, if any.

Do not report only successful runner duration when retries, repairs or surrounding orchestration consumed more time.

## 15. Migration notes

This contract is a draft. Before reducing `SKILL.md` or editing runners:

1. Review this contract with Rodolfo/Raquel.
2. Confirm which REC/P1 template rules are fully represented here.
3. Confirm no-cache editorial policy.
4. Promote any missing durable rule from recent references into this file.
5. Only then reduce `SKILL.md` and update runners.
