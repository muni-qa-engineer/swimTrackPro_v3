import json
import os


# --- Notice Board Settings Helpers and Route ---
def get_setting(setting_key, default_value=''):
    settings_file = os.path.join(
        os.path.dirname(__file__),
        'settings.json'
    )

    if not os.path.exists(settings_file):
        return default_value

    try:
        with open(settings_file, 'r', encoding='utf-8') as f:
            settings = json.load(f)
        return settings.get(setting_key, default_value)
    except Exception:
        return default_value


def set_setting(setting_key, value):
    settings_file = os.path.join(
        os.path.dirname(__file__),
        'settings.json'
    )
    settings = {}

    if os.path.exists(settings_file):
        try:
            with open(settings_file, 'r', encoding='utf-8') as f:
                settings = json.load(f)
        except Exception:
            settings = {}

    settings[setting_key] = value

    with open(settings_file, 'w', encoding='utf-8') as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)


