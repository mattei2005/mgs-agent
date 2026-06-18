# Personal invitation video workflow — photo integration and slide quality

Use for personal/family invitation videos (birthday, baby party, wedding, etc.) when the user provides a child/person photo plus a visual reference.

## Durable lessons from Daniel safari invitation

### 1. Treat the supplied photo as part of the scene, not an overlay

Bad pattern:
- Place the person photo as a square/rectangle on top of the background.
- Add a generic border that is unrelated to the illustration.
- Let text cards cover the photo.

Better pattern:
- Identify a diegetic container in the background and mask the photo into it:
  - car windshield -> arched/trapezoid windshield mask;
  - circular frame/medallion -> true circular mask;
  - picture frame -> frame-shaped mask;
  - balloon/window/sign -> matching organic shape.
- Crop the person photo for the container:
  - circle: face centered, shoulders included, avoid hands/adult support;
  - windshield: wider crop with face/upper body, clipped to glass shape;
  - avoid visible adult hands unless intentionally part of the image.
- Add scene-consistent finishing: shadow, rim, glass shine/reflection, slight color/contrast adjustment.

### 2. Build as slides/scenes, not random text appearing on top

For invitation videos, prefer a 3-slide structure:

```text
Slide 1 — identity / hero photo
- Title on existing plaque/sign.
- Person photo integrated into the scene.
- Minimal supporting line.

Slide 2 — invitation phrase
- Text in thematic plaque, parchment, ribbon, leaf frame, balloon, etc.
- Do not cover the person photo.

Slide 3 — event details
- Date/time/address in a stable, readable sign.
- Keep all critical details visible long enough to read.
```

### 3. Text must be designed, not pasted

Avoid:
- white rectangular boxes;
- text that appears from nowhere with no visual reason;
- tiny address lines compressed into a small card;
- generic system-font blocks that look like TXT pasted on video.

Use:
- wooden plaques, parchment, ribbons, leaves, badges, clouds, or frames matching the theme;
- larger font for date/time/place;
- short lines and strong contrast;
- one stable final details panel rather than several disappearing address fragments.

### 4. Validate visually before delivery

Before delivering:
- create contact sheets at key timestamps;
- check whether the photo still looks square/rectangular;
- check whether text panels feel like part of the theme;
- check mobile legibility of event details;
- verify no text covers the child/person photo;
- verify metadata sanitizer output and ffprobe dimensions/audio/duration.

## Example critique signals to act on

If Rodolfo says:
- “os fundos ficaram bons, mas…” -> preserve background, change layout/compositing.
- “deveria fazer slides” -> restructure scene timing; don’t just re-render same single composition.
- “a foto não deveria ser quadrada” -> use shape mask that matches scene container.
- “textos parecem feitos no txt” -> replace boxes with theme-native plaques/signage.

## Output notes

When comparing GPT/OpenAI and Grok/xAI versions, label the provider honestly and keep version differences clear. If one backend gives a better container for the photo (e.g., Grok circular medallion), say so directly.