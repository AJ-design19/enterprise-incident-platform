# SOP: Auth Service Errors and Login Failures

**Service:** auth-service
**Owning Team:** identity-team
**Severity Guidance:** Any full login outage is P1-Critical; latency degradation without
full failure is typically P2-High or P3-Medium.

## Symptoms
- Users unable to log in, receiving 500 or 401 errors
- Elevated login latency (p99 above 1s)
- Spike in failed authentication attempts in logs

## Immediate Triage Steps
1. Check the most recent deployment to `auth-service`. Config or code pushed within the
   last 2 hours is the most common cause of sudden full outages — check the deploy log first.
2. Check connectivity to the `identity-provider-api` (external/third-party IdP if federated
   login is enabled).
3. Check `auth-db` health and replication lag.
4. If only latency is affected (not full outage), check bcrypt/password-hashing cost factor
   configuration — an accidental increase in hashing rounds is a known past cause of latency
   spikes (see INC-1008).

## Mitigation
- If a recent deploy is implicated: roll back immediately to the last known-good version.
- If `identity-provider-api` is degraded: enable local session validation fallback if
  configured, and notify the IdP vendor.
- If hashing cost factor was changed: revert to the standard configured value.

## Verification
- Confirm successful login via synthetic test account.
- Confirm error rate on `/v1/auth/login` returns to baseline (<0.5%).

## Prevention
- Require canary deployment stage for all `auth-service` releases before full rollout.
- Add automated alerting on authentication error-rate deltas immediately after any deploy.
