import sublime
import sublime_plugin
import os


class MakeOneLineCodeCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        code = self.view.substr(self.view.sel()[0])
        lines = [ln.strip('\t ') for ln in code.split('\n')]
        sublime.set_clipboard('; '.join(lines))

def plugin_loaded():
    tool_settings = sublime.load_settings('RansTool.sublime-settings')
    if tool_settings.get("bootstrapped"):
        return


    pks_settings = sublime.load_settings('Package Control.sublime-settings')
    installed = pks_settings.get("installed_packages", [])
    pkgs = [
        "Boxy Theme",
        "Boxy Theme Addon - Font Face",
        "EditorConfig",
        "GitGutter",
        "Google Spell Check",
        "IMESupport",
        "MarkdownEditing",
        "SublimeLinter",
        "TodoReview",
        "Open Anything (ranlempow)",
        "Extra Completion (ranlempow)",
        "SublimeLinter-CleanCode (ranlempow)",
        "RansTool (ranlempow)",
        "Ancient (ranlempow)"
    ]
    pks_settings.set("installed_packages", list(set(installed + pkgs)))
    sublime.save_settings('Package Control.sublime-settings')

    defaults = {
        "color_scheme": "Packages/User/SublimeLinter/Ancient (SL).tmTheme",
        "fold_buttons": False,
        "font_face": "consolas",
        "font_size": 12,
        "highlight_line": True,
        "ignored_packages":
        [
            "GitGutter",
            "Vintage"
        ],
        "indent_to_bracket": True,
        "show_encoding": True,
        "theme": "Boxy Tomorrow.sublime-theme",
        "theme_sidebar_font_lg": True,
        "theme_tab_font_sm": True,
        "theme_tab_size_md": True
    }
    base_settings = sublime.load_settings('Preferences.sublime-settings')
    for key, value in defaults.items():
        base_settings.set(key, value)
    sublime.save_settings('Preferences.sublime-settings')

    tool_settings.set("bootstrapped", True)
    sublime.save_settings('RansTool.sublime-settings')

    welcome_file = os.path.join(sublime.packages_path(), 'Sublime-RansTool', 'welcome.txt')
    sublime.active_window().open_file(welcome_file)

