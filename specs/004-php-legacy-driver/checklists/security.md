# Security Requirements Quality Checklist: PHPLegacyDriver

**Purpose**: Validate completeness and clarity of security pattern detection, input validation, and safety requirements
**Created**: 2026-03-12
**Feature**: [spec.md](../spec.md)

## Security Pattern Detection Completeness

- [ ] CHK001 — Are SQL injection vector patterns explicitly enumerated beyond `mysql_query` with concatenation? [Completeness, Spec §FR-014]
- [ ] CHK002 — Are XSS detection patterns specified beyond `echo $_GET`/`$_POST`? [Completeness, Spec §FR-014]
- [ ] CHK003 — Is file inclusion vulnerability detection (`include($user_input)`) classified under SECURITY_SMELL or MODULE_LINK? [Ambiguity, Spec §FR-014]
- [ ] CHK004 — Are requirements defined for detecting `eval()`, `system()`, `exec()`, `shell_exec()`, `passthru()` as security anti-patterns? [Coverage, Gap]
- [ ] CHK005 — Are requirements defined for detecting insecure deserialization (`unserialize()` with user input)? [Coverage, Gap]
- [ ] CHK006 — Is the severity classification (critical/warning/info) documented with assignment criteria per security pattern? [Clarity, Spec §FR-014]

## SECURITY_SMELL Category

- [ ] CHK007 — Are the subtypes of SECURITY_SMELL exhaustively listed (SQL injection, XSS, file inclusion, and what else)? [Completeness, Spec §FR-014]
- [ ] CHK008 — Is the boundary between SECURITY_SMELL and PERSISTENCE clear when `mysql_query` is both a DB access and injection vector? [Ambiguity, Spec §FR-003, §FR-014]
- [ ] CHK009 — Are false positive mitigation requirements defined (e.g., `mysql_real_escape_string()` wrapping a query)? [Coverage, Gap]

## Input Handling Safety

- [ ] CHK010 — Are encoding fallback requirements (UTF-8 → latin-1) specified with clear failure modes? [Completeness, Spec Edge Cases]
- [ ] CHK011 — Is path traversal prevention specified when resolving include paths with `..`? [Coverage, Gap]
- [ ] CHK012 — Are requirements defined for maximum file size limits to prevent resource exhaustion? [Gap]
- [ ] CHK013 — Is the `needs_manual_review.json` format for security-related failures explicitly defined? [Clarity, Spec §FR-012]

## Anti-Patterns Mapping Security Coverage

- [ ] CHK014 — Are security-specific anti-pattern mappings defined for all 8 platforms (not just osCommerce/WordPress)? [Completeness, Spec §FR-024]
- [ ] CHK015 — Are the modern equivalents for security patterns (parameterized queries, Twig auto-escaping) consistently specified across all platform snippets? [Consistency, Spec §FR-024]
- [ ] CHK016 — Are requirements defined for detecting platform-specific security patterns (e.g., WordPress `wp_nonce` misuse, OpenMage `getModel()` injection)? [Coverage, Gap]

## Notes

- Spec FR-014 covers 3 security types (SQL injection, XSS, file inclusion) — OWASP Top 10 coverage is incomplete for PHP legacy
- Security patterns overlap with PERSISTENCE category (FR-003) — assignment priority rules needed
