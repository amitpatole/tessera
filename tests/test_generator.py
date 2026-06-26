"""The generator is deterministic: same seed ⇒ identical bytes, no global-random drift."""

from __future__ import annotations

from tessera.ledger import GeneratorConfig, generate


def test_same_seed_same_warehouse() -> None:
    a = generate(GeneratorConfig(seed=123))
    b = generate(GeneratorConfig(seed=123))
    assert a.model_dump_json() == b.model_dump_json()


def test_different_seed_different_warehouse() -> None:
    a = generate(GeneratorConfig(seed=1))
    b = generate(GeneratorConfig(seed=2))
    assert a.model_dump_json() != b.model_dump_json()


def test_seed_is_isolated_from_global_random() -> None:
    import random

    random.seed(999)
    first = generate(GeneratorConfig(seed=55)).model_dump_json()
    # Perturb the global RNG; a correct generator uses its own Random and is unaffected.
    random.random()
    random.random()
    second = generate(GeneratorConfig(seed=55)).model_dump_json()
    assert first == second
