# Timestamp normalization containment

Independent Building Lab Phase 3.5 confirmed an input-validation reliability defect
against foundation `961e437`: UTC normalization can raise an arithmetic range error
for a syntactically valid offset date. The contact collector classifies the unexpected
exception as a storage fault and stops; subsequent valid events are not collected.

Severity: medium availability impact within an authorized publisher's collection
path. No authentication bypass, data disclosure or cross-tenant acceptance was observed.
Broader HTTP models share this timestamp type; the correction keeps their validation
failures inside the normal validation boundary too.

Minimal correction: convert only UTC-conversion OverflowError to a validation
ValueError. Preserve all other exceptions, timezone requirements and valid date behavior.
No storage-failure handling, authorization, timestamp windows or payload contract changes.

Regression: two range-edge cases for shared type validation, three valid boundary/offset
controls, and two contact cases proving rejection followed by valid-event persistence.
Before correction: four failures / nineteen passes in the SQLite targeted suite.
After correction: twenty-three passes. Independent live replay and broader regression
evidence are retained in the separate Building Lab reports.

This branch is isolated; no merge or deployment is performed. Operators still need
collector failure monitoring and explicit retry: broker acknowledgments do not establish
application persistence, and clean-session downtime can lose observations.
