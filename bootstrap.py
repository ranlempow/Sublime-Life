# noqa: V, D, E501
import sublime
import sublime_plugin

import time
import threading

from package_control.package_installer import PackageInstallerThread
from package_control.thread_progress import ThreadProgress
from package_control.package_manager import PackageManager
from package_control.package_disabler import PackageDisabler


class MakeOneLineCodeCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        code = self.view.substr(self.view.sel()[0])
        lines = [ln.strip('\t ') for ln in code.split('\n') if not ln.strip('\t ').startswith('#')]
        sublime.set_clipboard('; '.join(lines))


def tuple_ver(ver_string):
    return tuple(int(v) for v in ver_string.split('.'))


def string_ver(ver_tuple):
    return '.'.join(str(v) for v in ver_tuple)


class RemovePackageThread(threading.Thread, PackageDisabler):

    """
    A thread to run the remove package operation in so that the Sublime Text
    UI does not become frozen
    """

    def __init__(self, manager, package, on_complete=None):
        self.manager = manager
        self.package = package
        self.on_complete = on_complete
        threading.Thread.__init__(self)

    def run(self):
        # Let the package disabling take place
        time.sleep(0.7)
        self.result = self.manager.remove_package(self.package)

        # Do not reenable if removing deferred until next restart
        if self.result is not None:
            def unignore_package():
                self.reenable_package(self.package, 'remove')
                if self.on_complete:
                    sublime.set_timeout(self.on_complete, 10)
            sublime.set_timeout(unignore_package, 200)
        else:
            if self.on_complete:
                sublime.set_timeout(self.on_complete, 10)


def install(manager, package, on_complete):
    disabler = PackageDisabler()

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


def remove(manager, package, on_complete):
    disabler = PackageDisabler()

    if package in disabler.disable_packages(package, 'remove'):
        thread = RemovePackageThread(manager, package, on_complete)
        thread.start()
        ThreadProgress(
            thread,
            'Removing package %s' % package,
            'Package %s successfully removed' % package
        )
    else:
        on_complete()


class UpdateProcess:
    update_processes = []

    def __init__(self, since, fn):
        self.since = since
        self.fn = fn

    def update(self, on_complete=None):
        # if previous_version < self.since <= current_version:
        self.fn()
        if on_complete:
            sublime.set_timeout(on_complete, 100)


def chain_update(remove_packages, install_packages, processes, on_complete=None):
    manager = PackageManager()
    remove_queue = remove_packages[:]
    install_queue = install_packages[:]
    processes_queue = processes[:]

    def launch_next():
        if remove_queue:
            package = remove_queue.pop(0)
            remove(manager, package, on_complete=launch_next)
        elif install_queue:
            package = install_queue.pop(0)
            install(manager, package, on_complete=launch_next)
        elif processes_queue:
            process = processes_queue.pop(0)
            process.update(on_complete=on_complete)
        else:
            if on_complete:
                sublime.set_timeout(on_complete, 1000)
    launch_next()


def since(since_version):
    since_version = tuple_ver(since_version)

    def wrap(fn):
        p = UpdateProcess(since_version, fn)
        UpdateProcess.update_processes.append(p)
        UpdateProcess.update_processes = sorted(UpdateProcess.update_processes, key=lambda p: p.since)
        return p
    return wrap

pakages_since = [
    ("0.0.2", [], [
        "Boxy Theme",
        "Boxy Theme Addon - Font Face",
        "IMESupport",
        ]),
    ("1.0.0", [], [
        "EditorConfig",
        "GitGutter",
        "Google Spell Check",
        "MarkdownEditing",
        "SublimeLinter",
        "TodoReview",
        "Open Anything (ranlempow)",
        "Extra Completion (ranlempow)",
        "SublimeLinter-CleanCode (ranlempow)",
        "Ancient (ranlempow)",
        ]),
    ("1.3.2", [], [
        "A File Icon",
        ]),
    ("1.4.0", [
        "Open Anything (ranlempow)",
        "Extra Completion (ranlempow)",
        "SublimeLinter-CleanCode (ranlempow)",    
        ], [
        "Open URL",
        "Codecs33",
        "ConvertToUTF8",
        "Bats",
        "CMake",
        "INI",
        "Nix"
        ]),
]



@since("1.0.0")
def setting100():
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


@since("1.3.0")
def setting130():
    # Add to Markdown.sublime-settings
    # this is a hack to solve MarkdownEditing config problem
    markdown_settings = sublime.load_settings('Markdown.sublime-settings')
    md_defaults = {
        "color_scheme": "Packages/User/SublimeLinter/Ancient (SL).tmTheme",
        "draw_centered": False,
        "highlight_line": True,
        "line_numbers": True,
        "margin": 32
    }
    for key, value in md_defaults.items():
        markdown_settings.set(key, value)
    sublime.save_settings('Markdown.sublime-settings')

@since("1.4.0")
def setting140():
    # change some defualt setting
    markdown_settings = sublime.load_settings('Markdown.sublime-settings')
    md_defaults = {
        "fold_buttons": false,
        # "font_face": "Hack Nerd Font",

        "font_size": 16,
        "show_full_path": true,
        "theme_sidebar_folder_atomized": true,
        "theme_sidebar_folder_mono": true,
    }
    for key, value in defaults.items():
        base_settings.set(key, value)
    sublime.save_settings('Preferences.sublime-settings')



def plugin_loaded():
    tool_settings = sublime.load_settings('RansTool.sublime-settings')
    previous_version = tuple_ver(tool_settings.get("previous_version", "0.0.0"))
    if tool_settings.get('bootstrapped') is True and previous_version == (0, 0, 0):
        previous_version = (0, 0, 1)
    current_version = tuple_ver(tool_settings.get("current_version"))

    remove_packages = []
    install_packages = []
    for since, removes, installs in pakages_since:
        since = tuple_ver(since)
        if previous_version < since <= current_version:
            for rm in removes:
                if rm in install_packages:
                    install_packages.remove(rm)
                elif rm not in remove_packages:
                    remove_packages.append(rm)
            for ins in installs:
                if ins in remove_packages:
                    remove_packages.remove(ins)
                elif ins not in install_packages:
                    install_packages.append(ins)

    processes = []
    for p in UpdateProcess.update_processes:
        if previous_version < p.since <= current_version:
            processes.append(p)

    def on_complete():
        tool_settings.set('previous_version', '.'.join(current_version))
        sublime.save_settings('RansTool.sublime-settings')
        sublime.active_window().status_message("Sublime Life is successful installed")

    if remove_packages or install_packages or processes:
        chain_update(remove_packages, install_packages, processes, on_complete=on_complete)
    else:
        tool_settings.set('previous_version', string_ver(current_version))
        sublime.save_settings('RansTool.sublime-settings')
