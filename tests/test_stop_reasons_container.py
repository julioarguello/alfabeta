"""Spec 006's container read names its stops with these codes (amendment of 2026-11-17, FR-027, FR-028)."""

from __future__ import annotations

from alfabeta.model import StopReason

CONTAINER_READ = {
    "rejected",
    "second_factor",
    "other_sign_in",
    "wrong_password",
    "no_password",
    "docker_unavailable",
    "docker_low_memory",
    "browser_crashed",
    "unreachable",
    "disabled",
}


def test_the_container_reads_codes_are_stop_reasons() -> None:
    assert CONTAINER_READ <= {str(r) for r in StopReason}


def test_spec_001s_codes_keep_their_values() -> None:
    assert {"session_expired", "challenge", "unexpected_ui", "lock_busy"} <= {str(r) for r in StopReason}
