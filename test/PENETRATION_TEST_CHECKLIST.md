# SilverTrade AI — Manual Penetration Testing Checklist (Phase 11)
# ========================================================================
# This checklist must be completed by a security professional before launch.
# All tests must pass with documented evidence.

## Authentication Tests

- [ ] SQL injection in login form (even with ORM — test it)
  - Evidence: _______________
  - Status: PASS / FAIL
  
- [ ] Brute force login — lockout after 5 attempts?
  - Evidence: _______________
  - Status: PASS / FAIL
  
- [ ] Session token entropy — is it cryptographically random?
  - Evidence: _______________
  - Status: PASS / FAIL
  
- [ ] Session fixation — can attacker set session cookie?
  - Evidence: _______________
  - Status: PASS / FAIL
  
- [ ] JWT/session cookie flags: HttpOnly ✓, Secure ✓, SameSite=Lax ✓
  - Evidence: _______________
  - Status: PASS / FAIL
  
- [ ] Logout invalidates server-side session (not just clears cookie)
  - Evidence: _______________
  - Status: PASS / FAIL
  
- [ ] Password reset token: single use, expires in 1 hour
  - Evidence: _______________
  - Status: PASS / FAIL
  
- [ ] Email verification token: single use, expires in 24 hours
  - Evidence: _______________
  - Status: PASS / FAIL

## Authorization Tests

- [ ] Horizontal privilege escalation:
  - [ ] User A's API key used to fetch User B's portfolio → 403
    - Evidence: _______________
    - Status: PASS / FAIL
  - [ ] User A's order ID used in User B's cancel request → 403
    - Evidence: _______________
    - Status: PASS / FAIL
  - [ ] User A's signal ID used in User B's execute request → 403
    - Evidence: _______________
    - Status: PASS / FAIL
  
- [ ] Direct object reference: /api/v1/orderbook?order_id=1 (someone else's order)
  - Evidence: _______________
  - Status: PASS / FAIL
  
- [ ] Admin endpoint accessible without admin flag → 403
  - Evidence: _______________
  - Status: PASS / FAIL
  
- [ ] Free user accessing Pro endpoint → 402 with upgrade prompt
  - Evidence: _______________
  - Status: PASS / FAIL

## Input Validation Tests

- [ ] Symbol injection: symbol="SBIN; DROP TABLE orders" → rejected
  - Evidence: _______________
  - Status: PASS / FAIL
  
- [ ] Quantity: quantity="-100" → rejected
  - Evidence: _______________
  - Status: PASS / FAIL
  
- [ ] Price: price="0" → rejected
  - Evidence: _______________
  - Status: PASS / FAIL
  
- [ ] Exchange: exchange="INVALID" → rejected
  - Evidence: _______________
  - Status: PASS / FAIL
  
- [ ] XSS in chat message → sanitized in response
  - Evidence: _______________
  - Status: PASS / FAIL
  
- [ ] SSRF: API callback URL pointing to internal service → blocked
  - Evidence: _______________
  - Status: PASS / FAIL
  
- [ ] CSRF: form submission without CSRF token → 400
  - Evidence: _______________
  - Status: PASS / FAIL

## Business Logic Tests

- [ ] Place order with quantity > holdings (short selling without shorts enabled) → blocked
  - Evidence: _______________
  - Status: PASS / FAIL
  
- [ ] Place buy order when daily loss limit hit → blocked
  - Evidence: _______________
  - Status: PASS / FAIL
  
- [ ] Execute same signal twice → second execution blocked
  - Evidence: _______________
  - Status: PASS / FAIL
  
- [ ] Signal > 5 minutes old → execution rejected
  - Evidence: _______________
  - Status: PASS / FAIL
  
- [ ] Portfolio value shows only current user's data after login
  - Evidence: _______________
  - Status: PASS / FAIL
  
- [ ] WebSocket: subscribe to another user's private channel → blocked
  - Evidence: _______________
  - Status: PASS / FAIL

## API Rate Limit Tests

- [ ] /auth/login: 6 requests in 1 minute → rate limited → 429
  - Evidence: _______________
  - Status: PASS / FAIL
  
- [ ] /api/v1/placeorder: 11 requests in 1 second → rate limited
  - Evidence: _______________
  - Status: PASS / FAIL
  
- [ ] /api/v1/signals: 200 requests in 1 hour → rate limited (free tier)
  - Evidence: _______________
  - Status: PASS / FAIL

## Summary

**Total Tests:** ___________
**Passed:** ___________
**Failed:** ___________
**Critical Findings:** ___________
**High Findings:** ___________
**Medium Findings:** ___________
**Low Findings:** ___________

**Launch Gate:** Zero Critical, Zero High findings allowed.

**Penetration Tester:** _______________
**Date:** _______________
**Signature:** _______________
