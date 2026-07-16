# Provenance Ledger — freeze-before-run custody for every pre-registered claim

Every pre-registration in this repository is graded below by the *strength
of its timestamp custody*, honestly. Three grades:

- **GIT-SEPARATED**: the frozen specification was committed AND pushed to
  this public repository in a commit that predates the commit containing
  its results. Push events are server-timestamped by GitHub and cannot be
  backdated; verify any row with
  `git log --pretty="%h %cI %s" -- PREREG_FRENCH49.md` and the GitHub
  commit page (or the GitHub Events API archive).
- **SELF-ATTESTED**: the specification document states it was written
  before the runs, but spec and results entered the repository in the
  same commit — the claim rests on the document's own narrative, not on
  custody. We say so plainly.
- **FORWARD (unresolved)**: the specification is committed and pushed and
  its test has not yet run — the strongest grade, pending resolution and
  pending third-party (OSF) mirroring.

| Registration | Frozen in commit (pushed) | Results in commit | Custody grade | Verdict record |
|---|---|---|---|---|
| PREREG A (French 49, L1/L2 gates + dissociation) | 69f007a 2026-07-15 (with results) | 69f007a | **SELF-ATTESTED** | Addendum A: P1 confirmed, P3 refuted, P4 triggered |
| PREREG B (L3 drawdown labeler @15%) | 69f007a (with results) | 69f007a | **SELF-ATTESTED** | Addendum B: P5/P7 refuted, P6 confirmed |
| PREREG C (threshold sweep) | 69f007a (with results) | 69f007a | **SELF-ATTESTED** | Addendum C: P8 refuted |
| Addendum D (replay D1/D2, costs D3, A3′ D4, CVaR D5, seeds D6) | c4345e9 2026-07-15T12:22-04:00 | ac90d7e / 49a640e 14:15 | **GIT-SEPARATED** | Addendum F: D1 refuted-favorably, D2/D3 confirmed, D6 confirmed; D4/D5 unrun |
| Addendum E (X1/X2/X3/X4, withheld era E-F, regional register E-R) | 5c96c35 2026-07-15T13:09-04:00 | e1f804b / 49a640e 14:15 | **GIT-SEPARATED** | Addendum F: X1 neither-branch, X3 anti-branch, X4 confirmed + divergence, E-F 5/6 scorecard; X2/E-R unrun |
| CRSP forward test (osf_package/PREREG_CRSP.md) | 40b69ad 2026-07-15T12:24-04:00; **OSF-mirrored 2026-07-15 22:47 ET (osf.io/nsx4e)** | — | **FORWARD, third-party custody** (data not yet obtained; WRDS pending) | open |
| NBER-labeler forward test (osf_package/PREREG_NBER_FRENCH49.md) | 40b69ad 2026-07-15T12:24-04:00; **OSF-mirrored 22:47 ET (osf.io/nsx4e)** | run 22:55–23:10 ET same day; results committed | **RESOLVED under third-party custody** — the program's first temporal cell | Addendum G: PN1 HIT (weak+strong, causal primary); PN2 confirmed; PN3 granularity branch; one strong-form miss in the non-causal robustness cell, disclosed; LORO/era supplement owed |

| Temporal-deployment test (osf_package/PREREG_TEMPORAL_DEPLOYMENT.md) | git 2026-07-16; **OSF-mirrored 2026-07-15 23:35 ET (osf.io/nsx4e)** | frozen diagnostics committed on lodging; outcomes scored 2027-04-07 | **FORWARD, third-party custody — measurement-split** (the first cell whose diagnostic is computed on data ending before the outcome window begins) | open |
| CRSP T-split amendment (osf_package/PREREG_CRSP_AMENDMENT_TSPLIT.md) | git 2026-07-16; **OSF-mirrored 2026-07-15 23:35 ET (osf.io/nsx4e)** | — | **FORWARD, third-party custody** (T-split primary design; net register and window estimator fixed pre-data; WRDS expected September) | open |

Notes:
- The withheld-era battery (E-F) has git-separated custody for its
  *specification* (addendum E pushed before the runs began), but the
  1926–1989 data itself has been publicly available for decades; the
  custody proves the spec was frozen before these runs, not that the era
  was unexaminable in principle. Both statements appear in the paper.
- **OSF custody established 2026-07-15 22:47 ET**: project osf.io/nsx4e
  holds PREREG_FRENCH49_snapshot_2026-07-15.md, PREREG_CRSP.md, and
  PREREG_NBER_FRENCH49.md under third-party timestamps. All future
  registrations are OSF-first. (No self-hosted record can prove the
  absence of unreported frozen specs; the OSF mirror is the custody
  answer to that file-drawer question from this date forward.)
- Independent check of any push time: GitHub's public event archive
  (GH Archive) records push events for public repositories.
