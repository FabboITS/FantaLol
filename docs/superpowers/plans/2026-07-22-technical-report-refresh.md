# Technical Report Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refresh the Italian technical report so it accurately describes the current FantaLeague application.

**Architecture:** Use Python standard-library ZIP and XML support to update the DOCX Office Open XML package without external dependencies. Preserve package parts, document section properties, and named Word styles while replacing outdated report content.

**Tech Stack:** Python 3 standard library, Office Open XML, ZIP validation

## Global Constraints

- Keep the report in Italian.
- Preserve the existing cover, section structure, and visual style as closely as possible.
- Create a local `.backup.docx` before modifying the original.
- Do not execute any Git command.

---

### Task 1: Establish the Outdated Baseline

**Files:**
- Inspect: `fantalol-backend/relazione/Relazione_Tecnica_FantaLoL.docx`

- [ ] Extract the report text and assert that current integration and scoring descriptions are missing while the obsolete scoring formula is present.
- [ ] Confirm the check fails against the desired current-state requirements.

### Task 2: Back Up and Refresh the Report

**Files:**
- Create: `fantalol-backend/relazione/Relazione_Tecnica_FantaLoL.backup.docx`
- Modify: `fantalol-backend/relazione/Relazione_Tecnica_FantaLoL.docx`

- [ ] Copy the original DOCX to the backup path without overwriting an existing backup.
- [ ] Replace the document body through an English-named temporary Python script using `zipfile` and `xml.etree.ElementTree`.
- [ ] Reuse the existing `Title`, `Subtitle`, `Heading 1`, `Heading 2`, `Normal`, and list styles where available.
- [ ] Cover the current frontend, backend modules, administration, auction, dynamic rosters, formations, matchday lifecycle, scoring, integrations, security, tests, deployment, and future work in Italian.

### Task 3: Validate the Result

**Files:**
- Verify: `fantalol-backend/relazione/Relazione_Tecnica_FantaLoL.docx`
- Verify: `fantalol-backend/relazione/Relazione_Tecnica_FantaLoL.backup.docx`

- [ ] Run `unzip -t` on both DOCX files and require zero package errors.
- [ ] Extract the updated text and require PandaScore, Oracle's Elixir, timed auctions, dynamic roster sizes, postponed matchdays, arithmetic-mean scoring, frontend delivery, and administrator visibility.
- [ ] Require the obsolete eight-player roster and base-vote/MVP/captain formula claims to be absent.
- [ ] Compare package metadata and confirm the updated document retains styles, relationships, media, and section properties.
