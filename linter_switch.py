# noqa: D, V
import sublime
import sublime_plugin

import os
import sys


class LinterSwitch:
    def __init__(self, window):
        self.window = window
        self.plugin_settings = sublime.load_settings('SublimeLinter.sublime-settings')
        try:
            sys.path.insert(0, os.path.join(sublime.packages_path(), 'SublimeLinter'))
            from lint import linter   # noqa
            self.linter = linter
            self.installed = True
        except ImportError:
            self.installed = False

    def is_enable(self):
        return self.installed and self.plugin_settings.get('user').get('@disable') is not True

    def enable(self):
        if self.installed and not self.is_enable():
            view = self.window.active_view()
            self.window.run_command('sublimelinter_toggle_setting',
                                    {'setting': '@disable', 'value': None})
            view.run_command('save')
            sublime.active_window().status_message("SublimeLinter is enabled")
            

    def disable(self):
        if self.installed and self.is_enable():
            self.window.run_command('sublimelinter_toggle_setting',
                                    {'setting': '@disable', 'value': True})
            self.linter.Linter.clear_all()
            sublime.active_window().status_message("SublimeLinter is disabled")


class ToggleLinterCommand(sublime_plugin.WindowCommand):
    def run(self):
        switcher = LinterSwitch(self.window)
        if switcher.is_enable():
            switcher.disable()
        else:
            switcher.enable()
