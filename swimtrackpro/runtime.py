"""Runtime dependencies shared by incrementally migrated route modules."""

_get_pg_connection = None
_load_data = None


def configure(*, get_pg_connection, load_data):
    global _get_pg_connection, _load_data
    _get_pg_connection = get_pg_connection
    _load_data = load_data


def get_pg_connection():
    if _get_pg_connection is None:
        raise RuntimeError("SwimTrackPro runtime is not configured")
    return _get_pg_connection()


def load_data():
    if _load_data is None:
        raise RuntimeError("SwimTrackPro runtime is not configured")
    return _load_data()
