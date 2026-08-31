"""Tests for the font picker (Settings → Appearance) — client-side font-family override.

Mirrors the structure of test_font_size_setting.py: static-source assertions
pinning the pre-paint boot script, the picker placement in the Appearance
pane, the CSS override mechanism, and i18n coverage.
"""
import os
import re

_SRC = os.path.join(os.path.dirname(__file__), "..")


def _read(name):
    return open(os.path.join(_SRC, name), encoding="utf-8").read()


_FONT_VALUES = [
    "system-ui", "segoe-ui", "helvetica", "verdana",
    "trebuchet", "georgia", "times", "ui-mono",
]


class TestFontPickerBootScript:
    """index.html must apply the font choice pre-paint (no FOUC)."""

    def test_boot_script_reads_hermes_font_picker(self):
        html = _read("static/index.html")
        assert "hermes-font-picker" in html, (
            "index.html pre-paint script must read 'hermes-font-picker' from localStorage"
        )

    def test_boot_script_sets_data_font_picker_attribute(self):
        html = _read("static/index.html")
        assert "dataset.fontPicker" in html, (
            "pre-paint script must set document.documentElement.dataset.fontPicker"
        )

    def test_boot_script_allowlist_covers_every_value(self):
        """The inline allowlist must accept every value font-picker.js can set,
        otherwise a valid persisted choice is dropped on reload."""
        html = _read("static/index.html")
        for value in _FONT_VALUES:
            assert f"'{value}':1" in html, (
                f"pre-paint allowlist must include '{value}'"
            )


class TestFontPickerHtml:
    """The picker must live in Settings → Appearance, below the theme selector."""

    def _appearance_bounds(self, html):
        start = html.find('id="settingsPaneAppearance"')
        assert start != -1, "settingsPaneAppearance not found"
        next_pane_markers = [
            'id="settingsPanePreferences"',
            'id="settingsPaneSystem"',
            'id="settingsPaneConversation"',
        ]
        next_pane_starts = [html.find(m, start + 1) for m in next_pane_markers]
        end = min([p for p in next_pane_starts if p != -1] or [len(html)])
        return start, end

    def test_picker_present(self):
        html = _read("static/index.html")
        assert 'id="fontPicker"' in html, "index.html must contain the #fontPicker select"

    def test_picker_appears_exactly_once(self):
        html = _read("static/index.html")
        assert html.count('id="fontPicker"') == 1, (
            "#fontPicker must appear exactly once — duplicate IDs violate the "
            "HTML spec and break the change-listener wiring"
        )

    def test_picker_lives_in_appearance_pane(self):
        html = _read("static/index.html")
        start, end = self._appearance_bounds(html)
        picker = html.find('id="fontPicker"')
        assert start < picker < end, (
            "Font picker must live inside settingsPaneAppearance only"
        )

    def test_picker_is_below_theme_selector(self):
        html = _read("static/index.html")
        start, end = self._appearance_bounds(html)
        pane = html[start:end]
        theme = pane.find('id="themePickerGrid"')
        picker = pane.find('id="fontPicker"')
        assert theme != -1 and picker != -1, (
            "both theme grid and font picker must exist in the Appearance pane"
        )
        assert theme < picker, "Font picker must appear below the theme selector"

    def test_picker_not_in_other_panes(self):
        html = _read("static/index.html")
        pane_ids = [
            'id="settingsPaneAppearance"',
            'id="settingsPanePreferences"',
            'id="settingsPaneSystem"',
            'id="settingsPaneConversation"',
        ]
        for pane_id in pane_ids[1:]:
            start = html.find(pane_id)
            if start == -1:
                continue
            # Bound the scan to the next settings pane so the window cannot
            # spill into a later pane's markup in the source order.
            following = [html.find(p, start + 1) for p in pane_ids]
            end = min([p for p in following if p != -1] or [len(html)])
            assert 'id="fontPicker"' not in html[start:end], (
                f"font picker must not appear in {pane_id}"
            )

    def test_theme_default_option_present(self):
        html = _read("static/index.html")
        assert '<option value="default" data-i18n="font_family_theme_default">' in html, (
            "picker must offer a 'Theme default' option wired to the i18n key"
        )

    def test_assets_linked(self):
        html = _read("static/index.html")
        assert 'href="static/font-picker.css?v=__WEBUI_VERSION__"' in html, (
            "font-picker.css must be linked from index.html (after style.css)"
        )
        assert 'src="static/font-picker.js?v=__WEBUI_VERSION__" defer' in html, (
            "font-picker.js must be loaded deferred from index.html"
        )


class TestFontPickerCss:
    """font-picker.css must override the theme/skin font variables."""

    def test_overrides_font_ui_variable_for_every_value(self):
        css = _read("static/font-picker.css")
        for value in _FONT_VALUES:
            assert f':root[data-font-picker="{value}"]' in css, (
                f"font-picker.css must define a --font-ui override for '{value}'"
            )

    def test_dark_variant_rules_exist(self):
        css = _read("static/font-picker.css")
        for value in _FONT_VALUES:
            assert f':root.dark[data-font-picker="{value}"]' in css, (
                f"dark-mode selector must exist for '{value}' so skin "
                ".dark rules cannot out-rank the override"
            )

    def test_overrides_conversation_variable(self):
        css = _read("static/font-picker.css")
        assert "--font-conversation:var(--font-ui)" in css, (
            "override must also pin --font-conversation so message prose follows"
        )

    def test_stacks_match_inline_option_previews(self):
        """Each <option> preview font and each CSS override must use the same
        leading family, so the dropdown preview shows what will be applied."""
        html = _read("static/index.html")
        css = _read("static/font-picker.css")
        for value in _FONT_VALUES:
            m_opt = re.search(
                r'<option value="%s" style="font-family:([^"]+)">' % re.escape(value), html
            )
            m_css = re.search(
                r'data-font-picker="%s"\]\{--font-ui:([^;]+);' % re.escape(value), css
            )
            assert m_opt and m_css, f"value '{value}' must exist in both HTML and CSS"
            opt_first = m_opt.group(1).split(",")[0].strip().strip("'\"")
            css_first = m_css.group(1).split(",")[0].strip().strip("'\"")
            assert opt_first == css_first, (
                f"'{value}': option preview family ({opt_first!r}) must match "
                f"the applied stack ({css_first!r})"
            )


class TestFontPickerJs:
    """font-picker.js must expose the pick/apply/sync trio."""

    def test_pick_font_function_exists(self):
        js = _read("static/font-picker.js")
        assert "function _pickFont(" in js, "font-picker.js must define _pickFont()"

    def test_apply_font_function_exists(self):
        js = _read("static/font-picker.js")
        assert "function _applyFontPickerFont(" in js, (
            "font-picker.js must define _applyFontPickerFont()"
        )

    def test_pick_font_persists_to_localstorage(self):
        js = _read("static/font-picker.js")
        idx = js.find("function _pickFont(")
        block = js[idx:idx + 400]
        assert "localStorage.setItem(_FONT_PICKER_KEY" in block, (
            "_pickFont must persist the choice under 'hermes-font-picker'"
        )

    def test_default_clears_override(self):
        js = _read("static/font-picker.js")
        idx = js.find("function _applyFontPickerFont(")
        block = js[idx:idx + 600]
        assert "delete document.documentElement.dataset.fontPicker" in block, (
            "'Theme default' must clear the data-font-picker attribute"
        )

    def test_unknown_values_sanitize_to_default(self):
        js = _read("static/font-picker.js")
        assert "function _sanitizeFontPickerValue(" in js, (
            "font-picker.js must sanitize unknown/stale stored values"
        )
        assert "_FONT_PICKER_VALUES.indexOf(value)!==-1 ? value : _FONT_PICKER_DEFAULT" in js, (
            "sanitizer must fall back to 'default' for unknown values"
        )

    def test_key_matches_boot_script(self):
        js = _read("static/font-picker.js")
        html = _read("static/index.html")
        assert "const _FONT_PICKER_KEY='hermes-font-picker'" in js
        assert "hermes-font-picker" in html


class TestFontPickerI18n:
    """en and ru locales must carry the label + 'Theme default' keys."""

    def _locale_block(self, src, anchor, stop_anchor):
        start = src.find(anchor)
        assert start != -1, f"locale anchor {anchor!r} not found"
        end = src.find(stop_anchor, start)
        return src[start:end if end != -1 else start + 30000]

    def test_en_keys(self):
        src = _read("static/i18n.js")
        en = self._locale_block(src, "settings_label_send_key: 'Send Key',", "cmd_")
        assert "settings_label_font_family:" in en
        assert "font_family_theme_default:" in en
        assert "settings_label_font_family: 'Font'," in en
        assert "font_family_theme_default: 'Theme default'," in en

    def test_ru_keys(self):
        src = _read("static/i18n.js")
        ru = self._locale_block(src, "settings_label_send_key: 'Клавиша отправки',", "cmd_")
        assert "settings_label_font_family: 'Шрифт'," in ru
        assert "font_family_theme_default: 'Как в теме'," in ru
