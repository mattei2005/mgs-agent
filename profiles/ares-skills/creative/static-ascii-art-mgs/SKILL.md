---
name: static-ascii-art-mgs
description: "MGS static ASCII art: terminal-safe banners, cowsay, boxes, image-to-ASCII and custom monospaced scenes. Use for still output; use ascii-video for animation."
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [ASCII, Art, Banners, Creative, Text-Art, pyfiglet, cowsay, boxes]
---

# MGS Static ASCII Art

## Use when

Use for one-off static ASCII output: banners, logos, speech bubbles, decorative text boxes, image-to-ASCII stills, QR/weather terminal art, and hand-built monospaced scenes. For animated MP4/GIF or audio-reactive output, use `ascii-video` instead.

## Standards

- Choose width, character ramp, spacing and contrast for the target monospaced surface.
- Keep ordinary chat banners within 60 columns unless the destination is known to support more.
- Preserve artist signatures when using existing ASCII artwork.
- Preview the rendered output before delivery; verify line wrapping and legibility.
- Do not install packages or call remote services unless the task requires it.

## Tool routing

- Text banner: `pyfiglet`/FIGlet.
- Speech bubble or novelty character: `cowsay`.
- Decorative frame: `boxes`.
- Image conversion: `ascii-image-converter` or `jp2a`.
- Colored terminal text: `toilet`; warn that ANSI color may not render in chat.
- Custom scene: Unicode box-drawing, block and geometric characters.

## Detailed reference

Read `references/original-ascii-art.md` for the preserved tool catalog, examples, setup commands and decision flow inherited from the previous local bundled-skill extension.
