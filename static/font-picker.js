// Font picker (Settings → Appearance) — client-side font-family override.
//
// Storage: localStorage key 'hermes-font-picker'. The value is one of the
// keys in _FONT_PICKER_FONTS, or 'default' (= "Theme default": leave the
// skin/theme font untouched). The pre-paint inline script in index.html and
// the rules in font-picker.css are the source of truth for the actual font
// stacks; this module only validates the value and toggles the
// <html data-font-picker="..."> attribute that the CSS keys off.
//
// Script order: loaded deferred AFTER boot.js (see references on boot.js
// script order) — it is self-contained and does not depend on $ or any
// boot.js binding.

const _FONT_PICKER_KEY='hermes-font-picker';
const _FONT_PICKER_DEFAULT='default';
// Must stay in sync with the allowlist in the index.html pre-paint script
// and the selectors in static/font-picker.css.
const _FONT_PICKER_VALUES=['system-ui','segoe-ui','helvetica','verdana','trebuchet','georgia','times','ui-mono'];

// Unknown/stale stored values (e.g. a choice removed in a later release)
// fall back to "Theme default" instead of silently doing nothing.
function _sanitizeFontPickerValue(value){
  return _FONT_PICKER_VALUES.indexOf(value)!==-1 ? value : _FONT_PICKER_DEFAULT;
}

function _applyFontPickerFont(value){
  const key=_sanitizeFontPickerValue(value);
  if(key===_FONT_PICKER_DEFAULT){
    // "Theme default": clear the override so theme/skin font declarations win.
    delete document.documentElement.dataset.fontPicker;
  } else {
    document.documentElement.dataset.fontPicker=key;
  }
}

function _syncFontPicker(value){
  const sel=document.getElementById('fontPicker');
  if(sel) sel.value=_sanitizeFontPickerValue(value);
}

function _pickFont(value){
  const key=_sanitizeFontPickerValue(value);
  try{localStorage.setItem(_FONT_PICKER_KEY,key);}catch(_){}
  _applyFontPickerFont(key);
  _syncFontPicker(key);
}

(function initFontPicker(){
  let stored=null;
  try{stored=localStorage.getItem(_FONT_PICKER_KEY);}catch(_){}
  const value=_sanitizeFontPickerValue(stored);
  _applyFontPickerFont(value);
  const sel=document.getElementById('fontPicker');
  if(sel){
    sel.value=value;
    sel.addEventListener('change',function(){_pickFont(this.value);});
  }
})();
