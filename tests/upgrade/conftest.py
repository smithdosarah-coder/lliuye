# -*- coding: utf-8 -*-
"""Upgrade tests are hermetic: all external I/O is stubbed or rejected."""
import socket

import pytest

import agent_credit.profile_enhancer as profile_enhancer
from agent_credit.case_retriever import CaseRetriever


@pytest.fixture(autouse=True)
def _offline_upgrade_suite(monkeypatch):
    monkeypatch.setattr(
        profile_enhancer,
        "enhance_enterprise_profile",
        lambda _profile: ({}, []),
    )
    monkeypatch.setattr(CaseRetriever, "retrieve", lambda *_args, **_kwargs: [])

    original_connect = socket.socket.connect
    original_connect_ex = socket.socket.connect_ex
    original_create_connection = socket.create_connection

    def _is_loopback(address):
        if isinstance(address, tuple) and address:
            return address[0] in {"127.0.0.1", "::1", "localhost"}
        return False

    def _connect(sock, address):
        if _is_loopback(address):
            return original_connect(sock, address)
        raise AssertionError("tests/upgrade must not access external network")

    def _connect_ex(sock, address):
        if _is_loopback(address):
            return original_connect_ex(sock, address)
        raise AssertionError("tests/upgrade must not access external network")

    def _create_connection(address, *args, **kwargs):
        if _is_loopback(address):
            return original_create_connection(address, *args, **kwargs)
        raise AssertionError("tests/upgrade must not access external network")

    monkeypatch.setattr(socket.socket, "connect", _connect)
    monkeypatch.setattr(socket.socket, "connect_ex", _connect_ex)
    monkeypatch.setattr(socket, "create_connection", _create_connection)
