"""Explicit persistent synthetic judge installation; never a customer bootstrap."""
import os

from app.config import ConfigurationError


def prepare_judge_demo(repository, now):
    """Seed an empty, separately selected repository once, without resetting records."""
    from demo_product import seed_demo

    with repository.transaction():
        organization = repository.get_structure_node("demo")
        if organization and organization.demo:
            return
        if repository.list_auth_users() or repository.list_structure_nodes() or repository.list_people():
            raise ConfigurationError("Judge demo requires an empty separate database; existing records were preserved")
        seed_demo(repository, now, presentation=True, password=os.environ["NODUM_JUDGE_PASSWORD"])
