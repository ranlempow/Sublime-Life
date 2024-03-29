# noqa: V, D, E501
import sublime
import sublime_plugin

import os
import sys
import time
import threading

from package_control.package_installer import PackageInstallerThread
from package_control.thread_progress import ThreadProgress
from package_control.package_manager import PackageManager
from package_control.package_disabler import PackageDisabler

from .lib import install_font
from .lib.fix_markdown_editing_enter_glitch import fix_markdown_editing_enter_glitch

class MakeOneLineCodeCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        code = self.view.substr(self.view.sel()[0])
        lines = [ln.strip('\t ') for ln in code.split('\n') if not ln.strip('\t ').startswith('#')]
        sublime.set_clipboard('; '.join(lines))


class FixMarkdwonEditingEnterGlitchCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        fix_markdown_editing_enter_glitch(sublime.installed_packages_path(), sublime.cache_path())


def fix_convert_to_utf8_prompt():
    # hack ConvertToUTF8: consider ASCII as UTF8
    origine_code = '''\
        if not_detected:
            # using encoding detected by ST
            encoding = view_encoding
        else:
            show_selection(view, [
                ['{0} ({1:.0%})'.format(encoding, confidence), encoding],
                ['{0}'.format(view_encoding), view_encoding]
            ])
'''
    hack_code = '''\
        if not_detected:
            # using encoding detected by ST
            encoding = view_encoding
        elif encoding == 'ASCII' and view_encoding == 'UTF-8':
            encoding = view_encoding
        else:
            show_selection(view, [
                ['{0} ({1:.0%})'.format(encoding, confidence), encoding],
                ['{0}'.format(view_encoding), view_encoding]
            ])
'''

    target_py_path = os.path.join(sublime.packages_path(), 'ConvertToUTF8', 'ConvertToUTF8.py')
    with open(target_py_path, 'r') as f:
        newcode = f.read().replace(origine_code.replace('    ', '\t'), hack_code.replace('    ', '\t'))
    with open(target_py_path, 'w') as f:
        f.write(newcode)


class FixConvertToUtfPrompt(sublime_plugin.TextCommand):
    def run(self, edit):
        fix_convert_to_utf8_prompt()


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
            time.sleep(0.2)
            remove(manager, package, on_complete=launch_next)
        elif install_queue:
            package = install_queue.pop(0)
            time.sleep(0.2)
            install(manager, package, on_complete=launch_next)
        elif processes_queue:
            process = processes_queue.pop(0)
            time.sleep(0.2)
            process.update(on_complete=launch_next)
        elif on_complete:
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
        "INI",
        ]),
    ("1.4.1", [
        "GitGutter",
        "Boxy Theme",
        "Boxy Theme Addon - Font Face",
        ], [
        "Theme - Monokai Pro",
        "SublimeLinter-addon-toggler",
        ]),
    ("1.5.0", [
        ], [
        "AdvancedNewFile",
        "AlignTab",
        "All Autocomplete",
        "ChineseLocalizations",
        "FileDiffs",
        "HexViewer",
        "Line Endings Unify",
        "Outline",
        "PlainTasks",
        "RawLineEdit",
        "SideBarEnhancements",
        "StringEncode",
        "SyncedSideBar",
        "SyntaxManager",
        # "Terminal",
        "TrailingSpaces",
        "Trimmer",
        ]),
    ("1.5.1", [
        'ChineseLocalizations'
        ], []),
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

    md_defaults = {
        # "color_scheme": "Packages/User/SublimeLinter/Ancient (SL).tmTheme",
        "color_scheme": "Packages/Ancient (ranlempow)/Ancient.tmTheme",
        "draw_centered": False,
        "highlight_line": True,
        "line_numbers": True,
        "margin": 32
    }
    markdown_settings = sublime.load_settings('Markdown.sublime-settings')
    for key, value in md_defaults.items():
        markdown_settings.set(key, value)
    sublime.save_settings('Markdown.sublime-settings')

@since("1.4.0")
def setting140():
    # change some defualt setting
    defaults = {
        "fold_buttons": False,
        # "font_face": "Hack Nerd Font",

        "font_size": 16,
        "show_full_path": True,
        "theme_sidebar_folder_atomized": True,
        "theme_sidebar_folder_mono": True,
    }
    base_settings = sublime.load_settings('Preferences.sublime-settings')
    for key, value in defaults.items():
        base_settings.set(key, value)
    sublime.save_settings('Preferences.sublime-settings')


@since("1.4.1")
def setting141():
    # change some defualt setting

    if not install_font.has_font('Hack Regular Nerd Font Complete.ttf'):
        install_font.install_font('{baseurl}/Hack Regular Nerd Font Complete.ttf'.format(
                baseurl='https://github.com/ranlempow/fonts/raw/master'))

    defaults = {
        "font_face": "Hack Nerd Font",
        "theme": "Monokai Pro.sublime-theme",

    }
    base_settings = sublime.load_settings('Preferences.sublime-settings')
    for key, value in defaults.items():
        base_settings.set(key, value)
    base_settings.erase('theme_sidebar_font_lg')
    base_settings.erase('theme_tab_font_sm')
    base_settings.erase('theme_tab_size_md')
    base_settings.erase('theme_sidebar_folder_atomized')
    base_settings.erase('theme_sidebar_folder_mono')
    sublime.save_settings('Preferences.sublime-settings')

    sublimelinter_defaults = {
        "gutter_theme": "Packages/Theme - Monokai Pro/Monokai Pro.gutter-theme",
        "styles": [
            {
                "mark_style": "none",
                "priority": 1,
                "scope": "region.orangish",
                "icon": "warning",
                "types": [
                    "warning"
                ]
            },
            {
                "mark_style": "none",
                "priority": 1,
                "scope": "region.redish",
                "icon": "error",
                "types": [
                    "error"
                ]
            }
        ],
        "lint_mode": "save",
        "show_panel_on_save": "view",
    }
    sb_settings = sublime.load_settings('SublimeLinter.sublime-settings')
    for key, value in sublimelinter_defaults.items():
        sb_settings.set(key, value)
    sublime.save_settings('SublimeLinter.sublime-settings')

@since("1.5.0")
def setting150():
    if sys.platform == 'darwin':
        fix_markdown_editing_enter_glitch(sublime.installed_packages_path(), sublime.cache_path())

    defaults = {
        "preview_on_right_click": False,
        "close_windows_when_empty": True,
        "theme_sidebar_folder_atomized": True,
        "theme_sidebar_folder_mono": True,
    }
    base_settings = sublime.load_settings('Preferences.sublime-settings')
    for key, value in defaults.items():
        base_settings.set(key, value)

    # hack ConvertToUTF8: consider ASCII as UTF8
    fix_convert_to_utf8_prompt()

@since("1.5.2")
def setting150():
    defaults = {
        "theme": "Monokai Pro (Filter Spectrum).sublime-theme",
    }
    base_settings = sublime.load_settings('Preferences.sublime-settings')
    for key, value in defaults.items():
        base_settings.set(key, value)


class ToolProgressMemory:
    def __init__(self):
        self.tool_settings = sublime.load_settings('RansTool.sublime-settings')

    def load_progress_version(self):
        previous_version = tuple_ver(self.tool_settings.get("previous_version", "0.0.0"))
        # if tool_settings.get('bootstrapped') is True and previous_version == (0, 0, 0):
        #     previous_version = (0, 0, 1)
        current_version = tuple_ver(self.tool_settings.get("current_version"))
        return previous_version, current_version

    def save_progress_version(self, new_version):
        self.tool_settings.set('previous_version', string_ver(new_version))
        sublime.save_settings('RansTool.sublime-settings')


def plugin_loaded():
    # tool_settings = sublime.load_settings('RansTool.sublime-settings')
    # previous_version = tuple_ver(tool_settings.get("previous_version", "0.0.0"))
    # if tool_settings.get('bootstrapped') is True and previous_version == (0, 0, 0):
    #     previous_version = (0, 0, 1)
    # current_version = tuple_ver(tool_settings.get("current_version"))
    progress_memory = ToolProgressMemory()
    previous_version, current_version = progress_memory.load_progress_version()

    candidate_remove = []
    candidate_install = []
    for since, removes, installs in pakages_since:
        since = tuple_ver(since)
        if previous_version < since <= current_version:
            for rm in removes:
                if rm in candidate_install:
                    candidate_install.remove(rm)
                elif rm not in candidate_remove:
                    candidate_remove.append(rm)
            for ins in installs:
                if ins in candidate_remove:
                    candidate_remove.remove(ins)
                elif ins not in candidate_install:
                    candidate_install.append(ins)

    confighome = os.environ.get('XDG_CONFIG_HOME', os.path.expanduser('~/.config'))
    configpath = os.environ.get('ST_LIFE_USERCONFIG_PATH', os.path.join(confighome, 'sublime-life'))

    extra_packages_file = os.path.join(configpath, 'extra-packages.ini')
    if os.path.exists(extra_packages_file):
        with open(extra_packages_file) as f:
            extra_packages = [pkg.strip() for pkg in f.readlines() if pkg.strip() ]
        for expkg in extra_packages:
            if expkg in candidate_remove:
                candidate_remove.remove(expkg)
            elif expkg not in candidate_install:
                candidate_install.append(expkg)

    installed_packages = PackageManager().list_packages()
    remove_packages = []
    install_packages = []
    for inspkg in candidate_install:
        if inspkg in installed_packages:
            print('RanTool install {} (Skip, already installed)'.format(inspkg))
        else:
            print('RanTool install {}'.format(inspkg))
            install_packages.append(inspkg)

    for rmpkg in candidate_remove:
        if rmpkg not in installed_packages:
            print('RanTool remove {} (Skip, not exist)'.format(rmpkg))
        else:
            print('RanTool remove {}'.format(rmpkg))
            remove_packages.append(rmpkg)


    processes = []
    for p in UpdateProcess.update_processes:
        if previous_version < p.since <= current_version:
            processes.append(p)

    def on_complete():
        progress_memory.save_progress_version(current_version)
        # tool_settings.set('previous_version', string_ver(current_version))
        # sublime.save_settings('RansTool.sublime-settings')
        if remove_packages or install_packages or processes:
            if previous_version == (0, 0, 0):
                sublime.active_window().status_message("Sublime Life is successful installed")
            else:
                sublime.active_window().status_message("Sublime Life is successful updated")
        else:
            sublime.active_window().status_message("Sublime Life is nothing to update")

    chain_update(remove_packages, install_packages, processes, on_complete=on_complete)
    # if remove_packages or install_packages or processes:
    #     chain_update(remove_packages, install_packages, processes, on_complete=on_complete)
    # else:
    #     on_complete(nomsg=True)
    #     # tool_settings.set('previous_version', string_ver(current_version))
    #     # sublime.save_settings('RansTool.sublime-settings')
