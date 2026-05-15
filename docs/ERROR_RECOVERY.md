# Error Recovery Notes

## Implemented in 0.5.0-alpha.1

- `SerialRetryPolicy` retries real serial write/query actions with bounded exponential backoff.
- `OutputOffGuard` performs best-effort output-off without masking the original shutdown path.
- `install_excepthook()` is idempotent.
- UI event logging writes to `logs/log.txt` through a single persistent writer to avoid duplicated messages.
- Hardware preflight performs IDN + output-off only.

## Not yet production-grade

- No full SCPI error queue drain (`:SYST:ERR?`) after every command.
- No hardware-specific recovery matrix for every 2400/2450 firmware version.
- No confirmed output-off readback from all supported models.
- No long-run serial soak test.

## During tomorrow's test

If a sweep errors:

1. Confirm the instrument output is OFF.
2. Save `logs/error.log` and `logs/console_last_run.log`.
3. Do not immediately repeat with a DUT attached.
4. Run the preflight again.
5. Retry with a dummy resistor and conservative compliance.
