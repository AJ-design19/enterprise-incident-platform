# SOP: Session Cache (Redis) Failures

**Service:** session-cache
**Owning Team:** platform-team
**Severity Guidance:** Full unavailability affecting login/session state is P2-High;
degraded performance without user-facing impact is P3-Medium.

## Symptoms
- "Connection refused" or "READONLY" errors from Redis clients
- OOM (out of memory) errors on the Redis node
- Unexpected user logouts or session loss ("eviction storm")

## Immediate Triage Steps
1. Check Redis memory usage. If near `maxmemory`, check the `maxmemory-policy` setting —
   `noeviction` combined with a memory leak in a client library has caused OOM crashes before
   (see INC-1003).
2. Check for a recent client library version change; some versions have known memory leak
   issues with long-lived connections.
3. If sessions are being evicted unexpectedly, verify `maxmemory-policy` is set to
   `allkeys-lru` (not `noeviction`) as per standard config (see INC-1010).
4. Check replication status between primary and standby Redis nodes.

## Mitigation
- Restart the affected Redis node if memory is exhausted, after confirming a standby is
  ready to take traffic.
- Fail over to the standby node if the primary is unresponsive.
- Roll back the client library if a memory leak is suspected.
- Correct `maxmemory-policy` configuration and increase allocated memory if undersized.

## Verification
- Confirm memory usage stabilizes below 80% of `maxmemory`.
- Confirm no new eviction-related session-loss reports for 15 minutes.

## Prevention
- Pin client library versions and test upgrades in staging under load before rollout.
- Add alerting at 75% memory utilization, not just at OOM.
