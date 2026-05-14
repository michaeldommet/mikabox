"""
MikaBox CLI Entry Point
=======================

Usage::

    python -m mikabox
    python -m mikabox --log-level DEBUG
    python -m mikabox --server-host 192.168.1.50 --server-port 8000
"""

import argparse
import logging
import sys

from . import __version__, __app_name__


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="mikabox",
        description=f"{__app_name__} v{__version__} — AI-powered smart speaker for kids.",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging verbosity (default: INFO).",
    )
    parser.add_argument(
        "--server-host",
        type=str,
        default=None,
        help="Home server IP address (overrides env/config).",
    )
    parser.add_argument(
        "--server-port",
        type=int,
        default=None,
        help="Home server port (overrides env/config).",
    )
    parser.add_argument(
        "--device-id",
        type=str,
        default=None,
        help="Device identifier (overrides env/config).",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"{__app_name__} {__version__}",
    )

    args = parser.parse_args()

    # ── Logging Setup ─────────────────────────────────────────────
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s │ %(name)-22s │ %(levelname)-7s │ %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stdout,
    )

    # Suppress noisy third-party loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("websockets").setLevel(logging.WARNING)

    logger = logging.getLogger("mikabox")

    # ── Config Overrides ──────────────────────────────────────────
    import os
    if args.server_host:
        os.environ["MIKABOX_SERVER_HOST"] = args.server_host
    if args.server_port:
        os.environ["MIKABOX_SERVER_PORT"] = str(args.server_port)
    if args.device_id:
        os.environ["MIKABOX_DEVICE_ID"] = args.device_id

    # Re-import config after env overrides
    from .config import DeviceConfig
    config = DeviceConfig()

    logger.info("Starting %s v%s", __app_name__, __version__)
    logger.info("Server: %s", config.server_http_url)
    logger.info("Device ID: %s", config.device_id)

    # ── Launch ────────────────────────────────────────────────────
    from .main_controller import MainController

    controller = MainController()
    try:
        controller.run()
    except KeyboardInterrupt:
        logger.info("Interrupted by user.")
    finally:
        controller.shutdown()


if __name__ == "__main__":
    main()
