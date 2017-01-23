# noqa: V, D
import sublime
import sublime_plugin

from package_control.package_installer import PackageInstallerThread
from package_control.thread_progress import ThreadProgress
from package_control.package_manager import PackageManager
from package_control.package_disabler import PackageDisabler


class MakeOneLineCodeCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        code = self.view.substr(self.view.sel()[0])
        lines = [ln.strip('\t ') for ln in code.split('\n') if not ln.strip('\t ').startswith('#')]
        sublime.set_clipboard('; '.join(lines))


def install(package, on_complete):
    disabler = PackageDisabler()
    manager = PackageManager()
    if package in disabler.disable_packages(package, 'install'):
        def inner_on_complete():
            disabler.reenable_package(package, 'install')
            on_complete()
    else:
        inner_on_complete = on_complete

    thread = PackageInstallerThread(manager, package, inner_on_complete)
    thread.start()
    ThreadProgress(
        thread,
        'Installing package %s' % package,
        'Package %s successfully installed' % package
    )


def chain_install(packages, on_complete=None):
    queue = packages[:]
    
    def launch_next():
        if queue:
            package = queue.pop(0)
            install(package, on_complete=launch_next)
        else:
            if on_complete:
                sublime.set_timeout(on_complete, 1000)
    launch_next()


def plugin_loaded():
    tool_settings = sublime.load_settings('RansTool.sublime-settings')
    if tool_settings.get("bootstrapped") is True:
        return

    # base_settings = sublime.load_settings('Preferences.sublime-settings')
    # base_settings.set("ignored_packages", ["Markdown"])
    # sublime.save_settings('Preferences.sublime-settings')

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
        "Ancient (ranlempow)"
    ]
    
    def after_installation():
        defaults = {
            "color_scheme": "Packages/Ancient (ranlempow)/Ancient.tmTheme",
            "fold_buttons": False,
            "font_face": "consolas",
            "font_size": 12,
            "highlight_line": True,
            "ignored_packages":
            [
                "Markdown",      # must disable for MarkdownEditing
                "GitGutter",     # disable by default
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

        tool_settings = sublime.load_settings('RansTool.sublime-settings')
        tool_settings.set("bootstrapped", True)
        sublime.save_settings('RansTool.sublime-settings')
        sublime.active_window().status_message("Sublime Life is successful installed")

    chain_install(pkgs, after_installation)

