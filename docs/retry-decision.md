# Retry Decision

## Decision

The current product decision is:

- Retry is supported only for the latest assistant message in a session.

This is an intentional constraint, not an implementation accident.

## Why

Retrying an older assistant message would create ambiguity for all later turns:

- later user prompts may depend on the original answer
- later assistant messages may no longer match the revised history
- replacing historical content could silently corrupt conversation meaning

Restricting retry to the latest assistant message keeps the conversation state coherent without introducing version trees, branch history, or replay logic.

## Current Behavior

- Backend rejects retry requests for non-latest assistant messages with:
  - `400 Only the latest assistant message can be retried`
- Frontend only renders the retry button for the latest assistant message
- Successful retry updates the existing message content in place

## Future Extension

If historical retry is required later, it should be treated as a redesign task rather than a small patch. Likely options would include:

- branch the conversation from a chosen historical turn
- replay later turns against the new answer
- preserve both old and new answer versions

Until one of those models is selected, latest-only retry is the safest product rule.
