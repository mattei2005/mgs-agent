---
name: creative-output-design
description: "Use when producing visual design artifacts, web/UI mockups, DESIGN.md token specs, architecture diagrams, hand-drawn diagrams, or design-system-inspired HTML/CSS. Umbrella for design direction, diagram format selection, templates, and verification."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [creative, design, diagrams, html, css, ui, design-systems, svg, excalidraw]
    related_skills: [p5js, pretext, ascii-video]
---

# Creative Output Design

## Overview

Use this umbrella for static or semi-static visual deliverables: web/UI design artifacts, disposable mockups, design token specs, architecture diagrams, and hand-drawn diagram files. Prefer one class-level entry point, then choose the right subsection/tool format.

## When to Use

- The user asks for a landing page, dashboard, prototype, deck-like HTML artifact, or polished one-off design.
- The user wants 2-3 visual directions before committing to implementation.
- The user asks for a DESIGN.md / design-token spec.
- The user wants an architecture, flow, sequence, concept, or infrastructure diagram.
- The user asks to mimic a known product's visual language.

## Boundary: design vs. MGS asset operations

This skill creates or specifies visual artifacts. It does not authorize Zeus to rename, classify, move, inventory, reconcile, or change campaign eligibility for MGS assets. Route that operational work to Ares and its canonical `creative-operations-mgs` workflow; naming and inventory remain governed by Ares's `creative-taxonomy-mgs`. In mixed requests, finish the design artifact here and hand the resulting file to Ares for operational intake and readback.

## Format Router

| User need | Use this path |
|---|---|
| Polished single-file HTML artifact | Claude-design workflow; see `references/absorbed-skill-md/claude-design.md` |
| Several disposable mockup variants | Sketch workflow; see `references/absorbed-skill-md/sketch.md` |
| Design-token contract for coding agents | DESIGN.md workflow and `templates/design-md-starter.md` |
| Dark technical/cloud architecture diagram | Architecture SVG/HTML templates under `templates/architecture-diagram/` |
| Editable hand-drawn diagram | Excalidraw JSON workflow and helpers under `references/excalidraw/` / `scripts/excalidraw/` |
| Known SaaS visual system inspiration | Templates under `templates/popular-web-designs/` |

## Operating Principles

1. **Pick the artifact format first.** HTML mockup, SVG diagram, `.excalidraw`, or DESIGN.md have different verification paths.
2. **Use real templates when available.** Do not recreate exact palettes or component systems from memory when a template exists.
3. **Keep diagrams semantically clear.** Label layers, flows, boundaries, protocols, and failure paths.
4. **For mockups, make comparison easy.** Put variants side-by-side or name files predictably.
5. **Verify the artifact opens.** For HTML/SVG, save and inspect in browser when possible; for JSON, validate parseability.

## Support Files

- `references/absorbed-skill-md/` contains the original detailed skill bodies.
- `templates/architecture-diagram/template.html` contains the dark SVG architecture starter.
- `templates/popular-web-designs/` contains product-inspired design systems.
- `templates/design-md-starter.md` contains the DESIGN.md starter file.
- `references/excalidraw/` and `scripts/excalidraw/` contain Excalidraw color/examples/upload helpers.

## Common Pitfalls

- Starting implementation before choosing output format.
- Flattening a design-system template into vague style adjectives.
- Producing a diagram image when the user needs an editable `.excalidraw` file.
- Claiming a design was previewed without actually opening/rendering it.

## Verification Checklist

- [ ] Correct artifact type chosen.
- [ ] Relevant template/reference consulted.
- [ ] Output file saved in a user-accessible path.
- [ ] HTML/SVG/JSON syntax checked or rendered.
- [ ] Final response includes exact file paths and any remaining assumptions.
