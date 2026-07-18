# Operations Notes

## Daily checks
- Confirm the pm2 process is `online` with zero unexpected restarts.
- Scan the out-log for `Scored N chunks` lines: scoring cadence should follow
  validator query traffic; long silences usually mean network or axon issues,
  not model issues.
- The error log accumulates shutdown tracebacks (`KeyboardInterrupt`) from
  ordinary redeploys; only treat NEW tracebacks between scoring lines as real.

## Redeploy checklist
1. Verify the model artifact path exists before restarting.
2. Restart via the launch script so environment variables stay consistent.
3. Tail the log until the first `Scored` line to confirm end-to-end health.

## Latency
Validator-side scoring tolerates slow responses up to the network timeout;
prefer correctness and stable memory usage over micro-optimizing latency.
