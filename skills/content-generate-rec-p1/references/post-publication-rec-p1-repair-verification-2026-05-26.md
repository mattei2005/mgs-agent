# Post-publication REC+P1 repair and verification (Marriott correction pattern)

Use this when Rodolfo/Raquel flags a published REC/P1 pair as visually or editorially wrong and asks for both the live articles and the future pipeline to be corrected.

## Durable lessons

1. **Repair the live posts and the pipeline**
   - Do not treat the correction as a one-off edit when the complaint exposes a repeatable flaw.
   - Patch the runner/template/skill hard gate that allowed the defect, then commit the relevant changes.

2. **Card-only LazyBlock image means only the card**
   - A visually polished card image still fails if it includes external background, canvas, border/moldura, scene, props, phone, person, shadow frame, or a mockup composition.
   - Correct by producing/uploading a normalized card-only asset, updating every LazyBlock occurrence in both REC and P1, and verifying public HTML no longer references the old media URL.

3. **Patch every LazyBlock occurrence, not just the first**
   - P1 pages can contain more than one `lazyblock/credit-card` block.
   - After updating, inspect the saved raw content for the old image URL/ID and forbidden generic copy. If any remain, regex-patch all LazyBlocks before reporting completion.

4. **REC comparison table must contain real competitor cards**
   - Placeholders like `another card in the same segment` or `a second comparable card` are blockers.
   - Use real same-market competitor card names, annual fees, and benefit positioning. If two real competitors are unavailable, fail the generation instead of publishing generic rows.

5. **Card descriptor must be commercial and benefit-led**
   - Block generic text such as `issuer terms`, `online account features`, `practical account features`, and similar neutral filler.
   - Prefer concise benefit copy, e.g. `Earn Marriott Bonvoy points, elite nights and travel rewards.`

6. **Yoast/readability can regress after manual repair**
   - Run the article validator on the exact final body after edits.
   - Re-run Yoast scoring after updating WP. If REC readability drops below green, repair sentence flow/transition words and re-score before final report.

7. **Public verification requires cache-busting and content assertions**
   - Fetch public URLs with a cache-busting query string, not just plain URL/HTTP 200.
   - Assert: new card URL present, old card URL absent, generic comparison placeholders absent, forbidden card descriptor absent, and real competitors present where applicable.

8. **Media deletion verification**
   - Use the safe delete script only for media created by the current run/repair and not referenced by the final posts.
   - A direct file URL may still respond because of CDN/cache or filesystem residue even after WordPress media deletion. Verify the WP REST media record returns 404 and the live posts no longer reference the old URL; report cache/CDN persistence transparently if asked.

## Minimal completion checklist

- [ ] REC raw content contains the new card image and no old image URL.
- [ ] P1 raw content contains the new card image in every LazyBlock and no old image URL.
- [ ] REC comparison table has two real competitors with real facts.
- [ ] Card `texto` is short, commercial, benefit-led, and ends cleanly.
- [ ] `validate-article.sh` passed on the exact final REC body.
- [ ] Yoast REC and P1 scores are green or the exception is clearly reported.
- [ ] Public cache-busted pages pass content assertions.
- [ ] Obsolete media is safe-deleted or explicitly reported as retained.
- [ ] Runner/skill/template hard gate is patched and committed when the issue is systemic.
