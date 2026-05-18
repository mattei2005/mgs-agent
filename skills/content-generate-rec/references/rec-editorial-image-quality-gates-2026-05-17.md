# REC editorial and image quality gates — 2026-05-17

Use this reference when tightening REC production quality after Rodolfo/Raquel identifies readability, card image, or featured image issues.

## Trigger

Rodolfo flagged that recent REC posts (Marbles Credit Card and Barclaycard Avios Credit Card) violated established editorial and visual standards:

1. Paragraph structure was too dense.
2. The Barclaycard Avios card image appeared vertical/tall, making the LazyBlock card presentation disproportionate across devices.
3. The Barclaycard Avios featured image included unnecessary frames/overlays instead of the approved three-layer composition.

## Durable rules confirmed

### Editorial readability gate

REC body validation must enforce all of these before publication:

- Final visible word count: 450–500 words.
- Each paragraph: maximum ~30 words, matching the “up to 3 visual lines” editorial expectation.
- Each H2/subtitle section: maximum 4 paragraphs.
- Long sentences: no more than 20% of all sentences may exceed 20 words.

Do not treat these as soft Yoast suggestions. They are publication gates.

### Card image gate

The card artwork used in the LazyBlock and featured composition must always be horizontal/landscape.

If a downloaded or manually supplied card image is vertical/tombstone:

1. Rotate it to landscape before upload.
2. Crop near-white/transparent borders after rotation.
3. Use the normalized horizontal asset for both the LazyBlock and featured-image generation.
4. Do not publish a REC with a vertical/tall card image.

### Featured image composition gate

The featured image should contain only three essential layers:

1. A realistic premium background scene.
2. The same horizontal card, enlarged and centered.
3. One realistic person as the top layer, slightly overlapping the card above.

Reject/regenerate images containing:

- Frames, molduras, picture frames, mockup frames or decorative panels.
- Duplicate cards, extra cards or card fragments.
- UI overlays, badges, stickers or phone screens.
- Hands holding/touching/pinching the card.
- Any unnecessary objects that make the composition look like a collage/mockup rather than a premium realistic ad image.

## Implementation notes from this correction

The quality gates belong in different canonical layers:

- Template: editorial rules and visual spec for the vertical/language.
- Validator script: mechanical enforcement of paragraph/sentence/section limits.
- Runner/SKILL pipeline: hard gates for card orientation and featured composition.
- Featured generation prompt: direct negative instructions for Gemini.

When a user reports this kind of issue, update the relevant canonical layer instead of relying on memory or chat reminders.

## Verification pattern

For a dry-run article, inspect the validator JSON and expect values similar to:

```json
{
  "status": "PASS",
  "style": {
    "avg_paragraph_words": 19.9,
    "max_paragraph_words": 27,
    "max_section_paragraphs": 4,
    "long_sentence_ratio": 0.0556,
    "style": "pass"
  }
}
```

For card orientation, a synthetic vertical card should return `rotated=true` and horizontal dimensions after normalization.