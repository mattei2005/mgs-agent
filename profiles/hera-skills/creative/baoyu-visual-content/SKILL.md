---
name: baoyu-visual-content
description: "Use when producing Baoyu-style educational visual content: article illustrations, knowledge comics, or infographics. Consolidates style selection, prompt construction, storyboard/layout choices, and palette consistency."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [baoyu, illustration, comic, infographic, visual-content, prompts]
    related_skills: []
---

# Baoyu Visual Content

## Overview

Use this umbrella for Baoyu-style visual production across three related outputs: article illustrations, educational/knowledge comics, and infographics. The shared class is visual explanation: analyze the source idea, choose a suitable visual format, keep style/palette consistent, and produce image-generation-ready prompts or structured storyboards.

## When to Use

- The user asks for Baoyu-style article illustrations or cover art.
- The task is to turn knowledge, biography, or tutorial material into comics.
- The task needs a structured infographic with layout/style choices.
- The user asks for Chinese educational visual formats such as 信息图 or 知识漫画.

## Shared Workflow

1. Identify the communication goal: explain, compare, persuade, summarize, or narrate.
2. Pick the output family:
   - **Article illustration** for a single concept or editorial lead image.
   - **Knowledge comic** for sequential explanation, biography, tutorials, or scenarios.
   - **Infographic** for structured facts, comparisons, timelines, systems, or taxonomies.
3. Choose style and palette deliberately; do not mix incompatible presets across a set.
4. Convert source content into visual units: focal metaphor, panels, modules, icons, captions, and hierarchy.
5. Write prompts with composition, subject, style, palette, text policy, and negative constraints.
6. If generating multiple images, maintain reusable character/style notes.

## Output Families

### Article Illustrations

Use when one strong image should support an article. Emphasize concept metaphor, editorial clarity, palette consistency, and a prompt that avoids overcrowding.

### Knowledge Comics

Use when sequence matters. Build a panel-by-panel storyboard, recurring characters if useful, tone, layout, and per-panel prompt/caption guidance.

### Infographics

Use when structure matters. Pick a layout pattern first (matrix, roadmap, hub-spoke, dashboard, layers, etc.), then select visual style and write module-level content.

## Support Files

The absorbed skill packages are re-homed under `references/article-illustrator/`, `references/comic/`, and `references/infographic/` so their detailed style libraries, layouts, tones, palettes, and prompt templates remain discoverable without three separate roots.

## Common Pitfalls

1. Choosing a visual family before understanding the communication goal.
2. Mixing style presets across a multi-image deliverable.
3. Asking image models to render dense text; prefer labels/captions outside the image or minimal legible text.
4. Skipping storyboard/layout planning and jumping directly to a prompt.
5. Losing character consistency across comic panels.

## Verification Checklist

- [ ] Output family selected and justified.
- [ ] Style and palette are explicit and consistent.
- [ ] Prompt/storyboard includes composition and content hierarchy.
- [ ] Detailed references were consulted for the chosen family when needed.
