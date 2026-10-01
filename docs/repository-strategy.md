# Repository and license review

Reviewed 2026-10-01 for the Ring primary track, AWS Builder and Open Source
mini-challenges. Engineering recommendations only; no eligibility or legal guarantee.
No license or GitHub visibility change was made.

## Verified requirements

The [official rules](https://amazonappdev2026.devpost.com/rules) permit a public
GitHub main project with an open-source license **or** a private project shared
with reviewers. The Open Source mini-challenge separately requires an additional
open-source project or a contribution to a public repository during the event,
with contribution/repository URLs, GitHub username and an explanation.

The [organizer clarification](https://amazonappdev2026.devpost.com/updates/46456-got-an-idea)
and [FAQ](https://amazonappdev2026.devpost.com/details/faqs) confirm private main
repositories are allowed. Give access to testing@devpost.com and GitHub users
chris-trag, knmeiss, giolaq, anishamalde, mosesroth and emersonsklar. Check that
invitations are accepted; they expire after seven days. Recheck the rules before submission.

## Current exposure and MIT

GitHub metadata confirmed marwanehmamouchi05/nodum is public. Its tracked source,
tests, policy engine, Ring adapter, authentication implementation, frontend,
configuration examples, docs and reachable commit history are exposed. Git author
metadata is also public. No committed live secret or database was confirmed.

The current [LICENSE](../LICENSE) is MIT. It permits use, copying, modification,
distribution, sublicensing and commercial sale, subject to keeping its copyright
and permission notice with copies/substantial portions. It does not require
downstream proprietary modifications to be published. See the
[OSI license text](https://opensource.org/license/mit).

Making a repository private or changing a future license does not retrieve
already distributed copies. Do not assume past MIT permissions can be revoked.
Obtain qualified advice on contribution ownership, existing grants, trademarks,
patents and third-party rights before changing licensing.

## Recommendation

Keep MIT on the already published hackathon snapshot through judging. This is a
low-risk recommendation, **not a rule that Nodum must stay public**. The main
repository may be made private under the published private-review path, provided
all required reviewers actually have access and the submission remains runnable.
Do not claim guaranteed eligibility; organizers decide it.

If protecting new work before judging is important, privately develop future
commercial additions and preserve the reviewable submitted version. Retain its
license/notices. A proprietary main-repo license change is unnecessary for
privatization and needs a separate ownership/licensing review.

After judging, separate:

1. **Public demo snapshot:** synthetic data, simulator adapters, setup instructions,
   tests and honest verification limits; retain MIT and dependency notices.
2. **Open Source mini-challenge toolkit/contribution:** useful generic connector
   contracts, mock event fixtures or deterministic test helpers, with meaningful
   documented work done during the event. Prefer MIT for a new toolkit extracted
   from this MIT code, retaining attribution. Follow an upstream project's license
   for contributions. Merely renaming/reposting the main repo is not a guarantee
   of a qualifying additional contribution.
3. **Private commercial development:** new manufacturer-specific adapters,
   certification work, production identity/security deployment, customer-specific
   policies, tenant configuration, analytics and commercial integrations. Keep
   customer data, credentials and operational playbooks out of public repositories.
   Privacy does not substitute for secure design or revoke existing MIT grants.

Keep the separate toolkit/contribution public and licensed for review. The main
submission can follow either permitted visibility path; do not remove source,
assets or instructions needed for judges to run the submitted system.

## Dependencies and assets

The frontend runtime lockfile lists React, React DOM and Scheduler under MIT.
Their notice is shipped in frontend/public/third-party-notices.txt. Development
dependencies include MIT/ISC/BSD/Apache/BlueOak licenses, MPL-2.0 Lightning CSS
packages and CC-BY-4.0 caniuse-lite data. Do not describe every dependency as MIT.
Backend package metadata includes MIT/MIT-0, BSD, Apache, PSF and dual-license
entries. Installed dependency notices must remain with redistributed components.
This metadata review is not a complete distribution-license or vulnerability audit.

The provenance/license of frontend/src/assets/hero.png is not established by
this audit. Verify ownership and permitted use before the final demo; likewise
review bundled logos, video/music and manufacturer trademarks. A repository
license alone does not establish rights to every asset or provider service.
