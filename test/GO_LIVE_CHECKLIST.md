# SilverTrade AI — Pre-Launch Go-Live Checklist (Phase 11)
# ========================================================================
# Every item below must be ✅ before production launch.

## Domain & SSL

- [ ] Custom domain configured (not localhost or IP)
- [ ] SSL certificate valid, HTTPS enforced
- [ ] www redirect to apex domain (or vice versa)
- [ ] DNS TTL set appropriately

## Environment

- [ ] `.env.production` has all real values (no placeholders)
- [ ] `APP_KEY` is unique, 32+ bytes, generated fresh
- [ ] `API_KEY_PEPPER` is unique, 32+ bytes, generated fresh
- [ ] Stripe keys are LIVE keys (not test)
- [ ] OpenAI API key has billing limit set ($100/month cap)
- [ ] `FLASK_DEBUG=False` in production
- [ ] `FLASK_ENV=production`
- [ ] All Python venvs use uv `.venv`

## Database

- [ ] PostgreSQL is production instance (not local, not SQLite)
- [ ] Database connection string in .env (not hardcoded)
- [ ] All Alembic migrations applied
- [ ] Database backup job running
- [ ] Database connection pooling configured

## Security

- [ ] All Phase 11.1 security checks passed
- [ ] All Phase 11.2 penetration test checks passed
- [ ] No sensitive data in git history (check with `git log --all -S "password"`)
- [ ] `.gitignore` covers all `.env` files, secrets, model files
- [ ] Nginx security headers all set
- [ ] Rate limiting active for all endpoints
- [ ] Redis password set
- [ ] Admin endpoints accessible only to is_admin users

## Monitoring

- [ ] Prometheus scraping all services
- [ ] Grafana dashboards live
- [ ] Slack alert channel configured and tested
- [ ] Uptime monitoring (UptimeRobot or similar) watching all 4 services
- [ ] Error logging to `errors.jsonl` working

## Legal

- [ ] Terms of Service published and linked
- [ ] Privacy Policy published and linked
- [ ] Cookie consent banner live
- [ ] SEBI disclaimer on every page
- [ ] Legal review completed (signed off by lawyer)
- [ ] All fake performance stats removed

## Application

- [ ] All 11 phases verified complete
- [ ] Zero hardcoded fake data
- [ ] Login/signup/logout working
- [ ] Broker connection working with at least 3 brokers tested
- [ ] Signal generation working (not mock data)
- [ ] Order execution working end-to-end
- [ ] Risk engine blocking invalid orders
- [ ] AI chat returning real responses
- [ ] Missed opportunities showing real data
- [ ] Alerts sending real notifications
- [ ] Mobile responsive on iPhone + Android
- [ ] Test coverage >= 40%

## Business Readiness

- [ ] Stripe checkout working with live keys
- [ ] Pro subscription activation tested
- [ ] Free tier limits enforced
- [ ] Admin dashboard showing real metrics
- [ ] Support email / contact page working
- [ ] Onboarding email sent after registration

## Final Sign-Off

**I confirm that:**

- [ ] All 11 phases are marked complete with all tasks checked
- [ ] No phase was skipped or partially completed
- [ ] All security findings have been resolved
- [ ] Legal review has been obtained
- [ ] The product contains zero fake data
- [ ] The product contains zero broken functionality
- [ ] The risk engine protects users from loss-inducing mistakes
- [ ] Test coverage is >= 40% with critical paths at 100%
- [ ] The product can be used by a real trader with real money
    without them encountering a single lie, broken button,
    or unprotected risk

**Signed:** _______________
**Date:** _______________
