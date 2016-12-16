import sublime_plugin
from package_control.package_disabler import PackageDisabler
from GitGutter.git_gutter_show_diff import GitGutterShowDiff


class EnableGitGutterCommand(sublime_plugin.WindowCommand, PackageDisabler):
    def run(self):
        self.reenable_package('GitGutter', 'enable')
        for view in self.window.views():
            view.run_command("git_gutter")


class DisableGitGutterCommand(sublime_plugin.WindowCommand, PackageDisabler):
    def run(self):
        for view in self.window.views():
            showdiff = GitGutterShowDiff(view, None)
            showdiff._clear_all()
            showdiff._update_status(0, 0, 0, "", "")
        self.disable_packages('GitGutter', 'disable')
