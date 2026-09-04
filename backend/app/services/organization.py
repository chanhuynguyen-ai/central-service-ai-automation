from app.models.models import User


class DirectManagerNotFoundError(RuntimeError):
    pass


def resolve_direct_manager(user: User) -> User | None:
    manager = user.manager

    if manager is None:
        return None

    if not manager.is_active:
        return None

    return manager


def require_direct_manager(user: User) -> User:
    manager = resolve_direct_manager(user)

    if manager is None:
        raise DirectManagerNotFoundError(
            f"No active direct manager configured for user {user.email}"
        )

    return manager