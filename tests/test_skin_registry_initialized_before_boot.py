"""Appearance registry must be initialized before any throw-prone boot code.

Regression guard for the "Failed to load settings: Cannot access '_SKINS' before
initialization" bug. The appearance helper functions in boot.js are function
DECLARATIONS, so they are hoisted and callable before their `const`/`let` data
is initialized. If any top-level boot statement throws before the registry
declaration runs, `_SKINS` stays in its temporal dead zone and a later call to
`_buildSkinPicker` (from the settings panel) throws a TDZ ReferenceError.

The fix keeps the pure-data registry (`_THEMES`, `_SKINS`, `_VALID_THEMES`,
`_VALID_SKINS`, `_LEGACY_THEME_MAP`, and the `let` state vars) at the very top
of boot.js, ahead of the first top-level executable statement, so the hoisted
helpers can never observe them uninitialized.
"""

from pathlib import Path

REPO = Path(__file__).parent.parent
BOOT_JS = (REPO / "static" / "boot.js").read_text(encoding="utf-8")


def _line_index_of(text, marker):
    idx = text.find(marker)
    assert idx != -1, f"marker not found in boot.js: {marker!r}"
    return text.count("\n", 0, idx)


def test_skins_registry_declared_before_first_boot_statement():
    """`const _SKINS` must be declared before any top-level boot code that can throw."""
    skins_line = _line_index_of(BOOT_JS, "const _SKINS=[")
    # `_installPwaSidebarSwipeGesture()` is the first top-level function call
    # executed during boot.js evaluation (it runs before DOM readiness guards).
    first_action_line = _line_index_of(BOOT_JS, "_installPwaSidebarSwipeGesture();")
    assert skins_line < first_action_line, (
        "_SKINS registry must initialize before the first top-level boot "
        "statement; otherwise a hoisted helper (e.g. _buildSkinPicker) can be "
        "called while _SKINS is in its temporal dead zone"
    )


def test_whole_appearance_registry_is_early():
    """The full registry (themes, skins, valid sets, legacy map, state) is early."""
    skins_line = _line_index_of(BOOT_JS, "const _SKINS=[")
    first_action_line = _line_index_of(BOOT_JS, "_installPwaSidebarSwipeGesture();")
    for marker in (
        "const _THEMES=[",
        "const _VALID_THEMES=",
        "const _VALID_SKINS=",
        "const _LEGACY_THEME_MAP=",
        "let _resolvedThemeBaseDark=false;",
    ):
        line = _line_index_of(BOOT_JS, marker)
        assert line < first_action_line, (
            f"appearance registry entry {marker!r} must be declared before the "
            "first top-level boot statement"
        )


def test_skins_registry_still_declared_exactly_once():
    """The move must not have left a duplicate `const _SKINS` declaration."""
    assert BOOT_JS.count("const _SKINS=[") == 1, (
        "duplicate const _SKINS declaration would raise a SyntaxError"
    )
