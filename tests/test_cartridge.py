from __future__ import annotations

from pathlib import Path

import pytest

from asme.canonical import ContractError
from asme.cartridge import DomainCartridge
from asme.workspace import DomainWorkspace, WorkspaceLayout


def test_cartridge_binds_prompt_programs_and_named_read_resources(
    tmp_path: Path, declared_domain
) -> None:
    prompt = tmp_path / "prompt.txt"
    extractor = tmp_path / "extractor"
    scorer = tmp_path / "scorer"
    prompt.write_text("Solve {input}\n", encoding="utf-8")
    extractor.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    scorer.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    cartridge = DomainCartridge.from_paths(
        domain=declared_domain,
        prompt=prompt,
        extractor=extractor,
        scorer=scorer,
        read_resources={},
    )
    assert {item.path for item in cartridge.files} == {
        "extractor",
        "prompt.txt",
        "scorer",
    }
    assert {item.mode for item in cartridge.files if item.path != "prompt.txt"} == {0o700}


def test_cartridge_rejects_source_content_that_differs_from_domain_seal(
    tmp_path: Path, declared_domain
) -> None:
    prompt = tmp_path / "prompt.txt"
    extractor = tmp_path / "extractor"
    scorer = tmp_path / "scorer"
    prompt.write_text("changed prompt\n", encoding="utf-8")
    extractor.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    scorer.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    with pytest.raises(ContractError, match="prompt"):
        DomainCartridge.from_paths(
            domain=declared_domain,
            prompt=prompt,
            extractor=extractor,
            scorer=scorer,
            read_resources={},
        )


def test_workspace_stores_and_rechecks_cartridge_before_mutation(
    tmp_path: Path, declared_domain
) -> None:
    prompt = tmp_path / "prompt.txt"
    extractor = tmp_path / "extractor"
    scorer = tmp_path / "scorer"
    prompt.write_text("Solve {input}\n", encoding="utf-8")
    extractor.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    scorer.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    cartridge = DomainCartridge.from_paths(
        domain=declared_domain,
        prompt=prompt,
        extractor=extractor,
        scorer=scorer,
        read_resources={},
    )
    workspace = DomainWorkspace(
        domain_id=declared_domain.domain_id,
        layout=WorkspaceLayout.under(tmp_path / "domain"),
    )
    workspace.initialize(domain=declared_domain, max_iterations=1, cartridge=cartridge)
    assert (workspace.layout.domain_root / "cartridge/extractor").is_file()
    (workspace.layout.domain_root / "cartridge/prompt.txt").write_text(
        "tampered\n", encoding="utf-8"
    )
    with pytest.raises(ContractError, match="cartridge"):
        workspace.apply(operation="skip-seed")
