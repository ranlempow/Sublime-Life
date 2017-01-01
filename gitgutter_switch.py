

import sublime
import sublime_plugin
from package_control.package_disabler import PackageDisabler
from package_control.package_manager import PackageManager
from package_control.settings import preferences_filename, load_list_setting


class GitGutterSwitch:
    def __init__(self):
        self.pkg_manager = PackageManager()
        self.pkg_disabler = PackageDisabler()
        self.installed = 'GitGutter' in self.pkg_manager.list_all_packages()

    def is_enable(self):
        settings = sublime.load_settings(preferences_filename())
        ignored = load_list_setting(settings, 'ignored_packages')
        return 'GitGutter' not in ignored

    def enable(self):
        if self.installed and not self.is_enable():
            self.pkg_disabler.reenable_package('GitGutter', 'enable')
            for view in sublime.active_window().views():
                view.run_command("git_gutter")

    def disable(self):
        if self.installed and self.is_enable():
            from GitGutter.git_gutter_show_diff import GitGutterShowDiff
            for view in sublime.active_window().views():
                showdiff = GitGutterShowDiff(view, None)
                showdiff._clear_all()
                showdiff._update_status(0, 0, 0, "", "")
            self.pkg_disabler.disable_packages('GitGutter', 'disable')


def plugin_loaded():
    switcher = GitGutterSwitch()
    sublime.set_timeout(lambda: switcher.disable(), 2500)


class EnableGitGutterCommand(sublime_plugin.WindowCommand):
    def run(self):
        switcher = GitGutterSwitch()
        switcher.enable()


class DisableGitGutterCommand(sublime_plugin.WindowCommand):
    def run(self):
        switcher = GitGutterSwitch()
        switcher.disable()


class ToggleGitGutterCommand(sublime_plugin.WindowCommand):
    def run(self):
        switcher = GitGutterSwitch()
        if switcher.is_enable():
            switcher.disable()
        else:
            switcher.enable()

