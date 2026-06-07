# Company OS thread title/language pitfall — 2026-06-07

## Trigger

In a long-running MGS OS restructuring Discord thread, Rodolfo challenged why the agent changed the thread title and changed it to Spanish.

## Durable lesson

For Company OS work, a Discord thread is a persistent workstream. Once the thread is open and its objective is still the same, do not auto-rename it from short acknowledgements, replies, or phase reports.

If a title ever must be created or changed because the topic truly changed, keep the title in the dominant language of the workstream/user message. For Rodolfo's MGS OS threads this is normally PT-BR. Never introduce Spanish/another language because of model drift or a generic title heuristic.

## Correct handling pattern

1. Treat `Ok`, `continue`, `próximo`, `vamos`, and similar replies as continuation of the current phase/block when the surrounding thread is still Company OS restructuring.
2. Anchor to the replied/quoted message and last execution report before deciding the next action.
3. Do not rename the thread unless Rodolfo explicitly asks or the topic changes clearly and durably.
4. If a title update is truly needed, use the current thread language, not an inferred or translated language.
5. If the agent accidentally renamed the thread or used the wrong language, acknowledge the operational mistake directly, restore/stop renaming if possible, and continue from the correct block without defensiveness.

## Bad pattern to avoid

- Applying generic Discord-title heuristics to every short message.
- Treating a short `Ok` as a new standalone topic.
- Translating a PT-BR operational thread title into Spanish or English.
- Explaining the title rule instead of owning the mistake and correcting behavior.
