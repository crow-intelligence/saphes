"""Shared pytest fixtures for saphes tests."""

import os

from hypothesis import HealthCheck, settings

# Mutation testing (mutmut) runs the same property test from multiple forked
# workers, which trips Hypothesis's ``differing_executors`` health check. This
# env-gated profile suppresses that check (and the shared example database) only
# during mutation runs — the normal test suite is unaffected.
settings.register_profile(
    "mutation",
    suppress_health_check=[HealthCheck.differing_executors],
    database=None,
    deadline=None,
)
if os.environ.get("SAPHES_MUTATION"):
    settings.load_profile("mutation")
