try:
    from gunicorn.glogging import Logger
except Exception:  # pragma: no cover
    # Gunicorn depends on fcntl and cannot be imported on native Windows.
    class Logger:  # type: ignore[no-redef]
        def access(self, resp, req, environ, request_time):
            return


def _normalize_path_from_environ(environ):
    raw_path = (
        environ.get("RAW_URI")
        or environ.get("REQUEST_URI")
        or environ.get("PATH_INFO")
        or ""
    )
    return raw_path.split("?", 1)[0]


def should_skip_access_log(environ):
    path = _normalize_path_from_environ(environ)
    user_agent = (environ.get("HTTP_USER_AGENT") or "").lower()

    if path in HumanOnlyGunicornLogger.EXCLUDED_PATHS:
        return True

    if any(token in user_agent for token in HumanOnlyGunicornLogger.EXCLUDED_UA_TOKENS):
        return True

    return False


class HumanOnlyGunicornLogger(Logger):
    """Filter noisy automated probes out of Gunicorn access logs."""

    EXCLUDED_PATHS = {
        "/health",
        "/.well-known/appspecific/com.chrome.devtools.json",
    }

    EXCLUDED_UA_TOKENS = (
        "uptimerobot",
        "kube-probe",
        "render",
        "pingdom",
        "statuscake",
        "healthcheck",
    )

    @staticmethod
    def _normalize_path(environ):
        return _normalize_path_from_environ(environ)

    def access(self, resp, req, environ, request_time):
        if should_skip_access_log(environ):
            return

        super().access(resp, req, environ, request_time)