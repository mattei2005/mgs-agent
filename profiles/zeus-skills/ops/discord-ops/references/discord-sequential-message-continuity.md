# Discord continuity: unanswered sequential messages

## Trigger

Use this when a user sends several Discord messages in sequence, follows an unanswered question with `?`, `Oi`, another ping, or screenshots showing that a prior message was skipped.

## Contract

1. A later ping does not cancel an earlier substantive question. Track unresolved questions and answer them in order.
2. Read-only recent-channel context must never trigger a side effect, but it may establish that an earlier question is still unanswered. If the current actionable message is clearly a nudge about that omission, answer the unresolved question rather than replying only to the nudge.
3. If screenshots are attached to demonstrate the omission, inspect them and identify the highlighted unanswered question before responding.
4. Acknowledge the miss briefly, answer the actual question, and then provide current validated status if the question concerns a live operation.
5. Do not reinterpret a prior question as authorization for a restart, write, deletion, or permission change; answering context and executing context remain separate.

## Pitfall

Replying only `Oi` to a follow-up ping while a visible operational question remains unanswered is a continuity failure. The correct response resolves the pending question without inventing new authorization.
