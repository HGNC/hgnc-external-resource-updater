"""CLI entrypoint for the HGNC external resource updater batch job."""

import sys

from hgnc_external_resource_updater.config import Settings
from hgnc_external_resource_updater.exceptions import ConfigError, ServiceError
from hgnc_external_resource_updater.logging_config import configure_logging
from hgnc_external_resource_updater.services.main_service import MainService


def main(argv: list[str] | None = None) -> int:
    """Run the HGNC external resource updater batch job.

    This function is the controller for the batch job. It handles
    configuration loading, logging setup, service wiring, and
    exit-code mapping. It MUST NOT contain business logic.

    Args:
        argv: Command-line arguments. Defaults to ``sys.argv[1:]``.

    Returns:
        Exit code: 0 for success, 1 for unexpected error,
        2 for configuration error, 3 for domain error.
    """
    argv = argv or sys.argv[1:]
    configure_logging()

    try:
        settings = Settings()
    except ConfigError:
        return 2
    except Exception:
        return 2

    try:
        service = MainService.from_settings(settings)
        service.run()
    except ConfigError:
        return 2
    except ServiceError:
        return 3
    except Exception:
        return 1
    return 0
