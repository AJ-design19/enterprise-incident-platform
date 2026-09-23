# SOP: Payment API Timeout and Latency Issues

**Service:** payment-api
**Owning Team:** payments-team
**Severity Guidance:** Treat sustained timeout rates above 5% as P1-Critical.

## Symptoms
- Checkout requests failing or hanging with 504/timeout responses
- Elevated p95/p99 latency on `/v1/payments/charge`
- Connection pool exhaustion warnings in application logs

## Immediate Triage Steps
1. Check `payment-db` connection pool utilization via the DB dashboard. If utilization
   is above 90%, this is very likely the root cause.
2. Check for long-running queries or batch jobs on `payment-db` that may be holding locks.
3. Check `session-cache` (Redis) health — payment-api falls back to synchronous DB reads
   when the cache is unavailable, which can cause cascading latency.
4. Check `api-gateway` for upstream 502/504 errors that may indicate a broader gateway issue
   rather than a payment-api-specific problem.

## Mitigation
- If connection pool exhaustion is confirmed: temporarily increase the pool size via the
  `PAYMENT_DB_POOL_SIZE` config and restart the affected pods.
- If a long-running batch job is holding locks: reschedule or kill the job (coordinate with
  the data team before killing jobs that touch financial records).
- If session-cache is down: fail over to the standby Redis node.
- Enable the circuit breaker on `payment-api` -> `payment-gateway-api` if the third-party
  payment gateway itself is degraded, to fail fast instead of queuing requests.

## Verification
- Confirm p95 latency on `/v1/payments/charge` returns below 300ms.
- Confirm timeout error rate drops below 1% over a 10-minute rolling window.
- Re-run a synthetic checkout transaction end-to-end.

## Prevention
- Review connection pool sizing quarterly against peak traffic projections.
- Add alerting on connection pool utilization at the 80% threshold, not just at exhaustion.
- Schedule all batch jobs touching `payment-db` outside of 09:00-21:00 UTC peak hours.
