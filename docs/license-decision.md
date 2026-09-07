# License decision brief

Status: resolved 2026-09-01. The owner selected policy outcome 2 with MIT as the
permissive instrument (Gate A approval record, decision A4, Option A). This document
is retained as the decision brief; it is not a license grant and is not legal advice.

## Required outcome

The owner requires:

1. free community use;
2. attribution to Mani Saint-Victor, MD; and
3. a link to `https://manysaintvictormd.com` specifically on the using project's
   project page.

The third requirement is the deciding constraint. None of the standard licenses reviewed
below requires that exact placement for every kind of software project.

## Primary-source comparison

| Option | Free use and modification | Attribution or URL obligation | Exact project-page backlink | Practical consequence |
|---|---|---|---|---|
| MIT | Yes | Preserve copyright and permission notice in copies or substantial portions | No | Familiar and permissive, but cannot enforce the required backlink |
| Apache-2.0 plus NOTICE | Yes | Distributed derivative works must preserve applicable NOTICE attribution in one of several permitted locations | No | Strong permissive default with an express patent grant, but NOTICE placement remains flexible |
| CPAL-1.0 with Exhibit B | Yes, under reciprocal and network-use terms | May require a copyright notice, short phrase, image, and URL in a graphical interface at launch | No; the display obligation does not apply when there is no graphical interface | OSI-approved but substantially heavier and a poor fit for a command-line or agent skill |
| Attribution Assurance License | Yes | Requires signed license text in source and documentation plus author identity and URL at executable launch | No | OSI-approved but legacy, operationally intrusive, and still does not guarantee project-page placement |
| Attorney-reviewed custom attribution license | Depends on drafted terms | Can state the exact attribution, URL, and placement requirement | Potentially, if validly drafted | Best literal fit, but nonstandard terms increase review, compatibility, and adoption friction |

## Recommendation

Do not publish under MIT or Apache-2.0 while the project-page backlink remains a mandatory
condition. Those licenses preserve notices, not the exact web-page placement.

Choose between these two policy outcomes before release:

1. **Mandatory placement remains nonnegotiable.** Ask an open-source and intellectual
   property attorney to draft or review a custom attribution license. The document should
   define `project page`, covered uses, forks, packages without a web page, command-line
   use, larger works, cure periods, sublicensing, compatibility, and whether the condition
   applies to private use.
2. **Maximum community adoption becomes more important than mandatory placement.** Use a
   standard permissive license, preferably Apache-2.0 if its patent grant is wanted, keep
   the URL in NOTICE and CITATION metadata, and make project-page linking a prominent
   request rather than a license condition.

CPAL-1.0 and the Attribution Assurance License are not recommended defaults for this
project. They impose runtime-display obligations but still do not deliver the exact
project-page rule.

## Attribution is separate from prior art

A license controls permission and attribution. It does not determine inventorship,
patentability, or prior-art status.

The USPTO states that an internet publication can qualify as a printed publication when
it was sufficiently accessible to people concerned with the art. The posting date also
needs evidence. A future public release can preserve useful authorship and disclosure
evidence through:

- a dated public repository and immutable release tag;
- a release archive with recorded SHA-256 hashes;
- `PROVENANCE.md` separating the paper method from local contributions;
- `CITATION.cff` naming Mani Saint-Victor, MD and the project URL; and
- a release note describing the locally authored architecture and algorithms.

Those records can support evidence of what was disclosed, by whom, and when. They do not
guarantee legal priority or ownership.

Public disclosure can also affect patent rights. The USPTO describes a one-year United
States grace period for certain inventor-originated disclosures, while warning that many
other countries may deny patents when disclosure occurs before filing. If patent
protection is under consideration, obtain patent advice before publishing the source,
paper, public repository, or detailed algorithm description.

## Sources reviewed

- [MIT License, Open Source Initiative](https://opensource.org/license/mit)
- [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0.html)
- [Applying Apache License 2.0](https://www.apache.org/legal/apply-license)
- [Common Public Attribution License 1.0](https://opensource.org/license/cpal-1.0)
- [Attribution Assurance License](https://opensource.org/license/aal)
- [USPTO MPEP 2128, Printed Publications as Prior Art](https://www.uspto.gov/web/offices/pac/mpep/s2128.html)
- [USPTO, Pursuing International IP Protection](https://www.uspto.gov/patents/basics/international-protection/filing-patents-abroad)
- [Creative Commons FAQ on software licensing](https://creativecommons.org/faq/)

## Release gate

A4 was `RESOLVED` on 2026-09-01: Option A, MIT (code) plus CC BY 4.0
(docs/methodology) plus a NOTICE.md non-binding project-page link request, recorded
in the Gate A approval record maintained outside this tree. The `LICENSE` file,
license classifier, and CITATION license field now reflect that choice. Release
date, publication permission, and distribution permission still require the owner's
Gate 4 approval.
