from __future__ import annotations

from keith_ivt.diagnostics import install_console_logging, install_excepthook, log_runtime_error


def run() -> None:
    install_console_logging()
    install_excepthook()
    try:
        from keith_ivt.ui.simple_app import main
        main()
    except Exception as exc:
        log_runtime_error("Application startup or mainloop failed", exc)
        raise


if __name__ == "__main__":
    run()
