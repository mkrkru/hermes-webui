"""Regression tests for the sidebar workspace filter state.

The top-level workspace filter pills (All / per-workspace chips) were removed —
the sidebar is now a pure workspace tree. The filter state and predicate remain
declared but are inert (no UI sets the active workspace filter anymore). This
file pins that contract.
"""

from __future__ import annotations

import pathlib

JS = pathlib.Path(__file__).parent.parent / "static" / "sessions.js"


def _js() -> str:
    return JS.read_text(encoding="utf-8")


def test_workspace_filter_state_declared():
    js = _js()
    assert "let _activeWorkspaceFilter = null;" in js
    assert "function _setActiveWorkspaceFilter(ws)" in js


def test_workspace_filter_predicate_partition():
    js = _js()
    assert (
        "if(_activeWorkspaceFilter!==null && String(s.workspace||'')!==_activeWorkspaceFilter) continue;"
        in js
    )


def test_workspace_filter_predicate_reference_rows():
    js = _js()
    assert (
        "if(_activeWorkspaceFilter!==null && String(s.workspace||'')!==_activeWorkspaceFilter) return false;"
        in js
    )


def test_workspace_filter_chips_removed():
    js = _js()
    # The top-level workspace filter pills (project-bar) are gone.
    assert "const wsCounts=new Map();" not in js
    assert "allChip.onclick=()=>{_setActiveWorkspaceFilter(null);};" not in js
    assert "chip.onclick=()=>{_setActiveWorkspaceFilter(wsPath);};" not in js


def test_workspace_group_label_helper():
    js = _js()
    assert "function _sessionWorkspaceLabel(session)" in js


def test_workspace_grouping_replaces_date_bucketing():
    js = _js()
    assert "const unpinnedByWorkspace=[...unpinned].sort((a,b)=>" in js
    assert "const label=_sessionWorkspaceLabel(s);" in js


def test_project_filter_chips_removed():
    js = _js()
    # The old project filter render site is gone.
    assert "const hasUnprojected=profileFiltered.some(s=>!s.project_id);" not in js
    assert "noneChip.textContent='Unassigned';" not in js
