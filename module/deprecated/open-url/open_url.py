# Open URL opens selected URLs, files, folders, or googles text
# Hosted at http://github.com/noahcoad/open-url
# test urls: google.com ~/tmp ~/tmp/tmp c:\noah c:\noah\tmp.txt c:\noah\tmp

# noqa: D, V

import sublime
import sublime_plugin

import os
import sys
import platform
import re
import fnmatch
import urllib
import urllib.parse
import webbrowser

sys.path.insert(0, os.path.dirname(__file__))
from domain import domains
from spec import Specification, WindowSingleton

_debug = False


def debug(*args):
    if _debug:
        print(*args)


class ActionDispitch:
    default_autoinfo = [
        {'type': 'file', 'action': 'file_menu'},
        {'type': 'folder', 'action': 'folder_menu'},
        {'type': 'web', 'pattern': ['*://*'], 'action': 'browse'},
        # list of known domains for short urls, like ironcowboy.co
        {'type': 'web', 'regex': r"\w[^\s]*\.(?:%s)[^\s]*\Z" % domains, 'action': 'browse_http'},
        {'action': 'browse_google'},
    ]

    def __init__(self, view, path_type, path, autoinfo=None):
        self.path = path
        self.type = path_type
        self.view = view
        self.autoinfo = autoinfo or self.get_autoinfo()

    def get_spec(self, *args, **kwargs):
        spec = Specification.get_spec(*args, **kwargs)
        return spec

    def finan_spec(self, spec):
        if self.autoinfo.get('singleton', False) and WindowSingleton:
            title = self.autoinfo.get('title')
            if title == '$BASE_NAME':
                title = os.path.basename(self.path)
            
            spec = WindowSingleton(spec,
                                   window_title=title,
                                   window_class=self.autoinfo.get('class'),
                                   title_instance=self.autoinfo.get('title_instance'),
                                   class_instance=self.autoinfo.get('class_instance'))
            spec.popen = spec.bring_top
        return spec

    def get_autoinfo(self):
        config = sublime.load_settings("open_url.sublime-settings")

        selected = []
        # see if there's already an action defined for this file
        for auto in config.get('autoactions', []) + self.default_autoinfo:
            # see if this line applies to this opperating system
            oscheck = ('os' not in auto
                       or auto['os'] == 'win' and platform.system() == 'Windows'
                       or auto['os'] == 'linux' and platform.system() == 'Linux'
                       or auto['os'] == 'mac' and platform.system() == 'Darwin'
                       or auto['os'] == 'posix' and (platform.system() == 'Darwin'
                                                     or platform.system() == 'Linux')
                       )

            # if the line is for this OS, then check to see if we have a file pattern match
            
            for pattern in auto.get('pattern', ['*']):
                match = all([oscheck,
                             fnmatch.fnmatch(self.path, pattern),
                             not (auto.get('type') and auto['type'] != self.type),
                             not (auto.get('regex') and not re.search(auto['regex'],
                                                                      self.path, re.IGNORECASE))
                             ])
                if match:
                    selected.append((
                                    -({'any': 0, 'posix': 1}).get(auto.get('os', 'any'), 2),
                                    -(sum(2 if c == '*' else 1 for c in pattern)
                                        - int('regex' in auto) * 10),
                                    -int('type' in auto),
                                    auto
                                    ))
                    break
        debug(selected)
        # give higher priority to the exact option
        assert(selected)
        selected = sorted(selected)
        return selected[0][3]
        

    def do_action(self, action=None, **kwargs):
        action = action or self.autoinfo['action']
        debug('path: {}'.format(self.path))
        debug('action: {}, autoinfo:{}'.format(action, self.autoinfo))
        if not hasattr(self, 'action_{}'.format(action)):
            raise Exception("undefined action")
        method = getattr(self, 'action_{}'.format(action))
        method()

    def action_reveal(self):
        """ Show the system file manager that select this file """
        spec = self.get_spec('dir' if os.path.isdir(self.path) else 'file', self.path)
        self.finan_spec(spec).popen()

    def action_open(self):
        autoinfo = self.autoinfo
        if autoinfo.get('app'):
            # OSX only
            spec = self.get_spec('open_with_app', self.path, app=autoinfo['app'])
        else:
            # default methods to open files
            spec = self.get_spec('open', self.path)
        spec.popen()

    def action_terminal(self, spec=None):
        """ run command in a terminal and pause if desired """
        spec = spec or self.path
        if self.autoinfo.get('pause'):
            spec = self.get_spec('pause', spec)
        if self.autoinfo.get('keep_open'):
            spec = self.get_spec('shell_keep_open', spec)
        spec = self.get_spec('terminal', spec)
        spec.popen()
            

    def action_run(self):
        if self.autoinfo.get('openwith'):
            # check if there are special instructions to open this file
            spec = self.get_spec('run_custom', self.path, app=self.autoinfo['openwith'])
        if self.autoinfo.get('terminal'):
            return self.action_terminal(self, spec)

        # run in detach process through regular way
        spec = self.get_spec('detach_run', self.path)
        spec.popen(cwd=os.path.dirname(self.path))

    def action_edit(self):
        # open the file for editing in sublime
        self.view.window().open_file(self.path)

    def action_edit_in_new_window(self):
        args = []
        executable_path = sublime.executable_path()
        if sublime.platform() == 'osx':
            app_path = executable_path[:executable_path.rfind(".app/") + 5]
            executable_path = app_path + "Contents/SharedSupport/bin/subl"
        else:
            executable_path = os.path.join(os.path.dirname(executable_path), 'subl')

        args.append(executable_path)
        path = os.path.abspath(self.path)
        
        args.append(path)
        spec = Specification(args)
        spec.quote()
        spec = self.get_spec('detach_run', spec)
        spec = self.get_spec('shell', spec)
        spec.popen()
        # subprocess.Popen(items, cwd=items[1])

    # def action_bring_reveal(self):
    #     # TODO: use action_reveal()
    #     # use with {title: '$BASE_NAME', class: 'CabinetWClass',
    #     #           title_instance: true, class_instance: true} usually
    #     spec = self.get_spec('dir' if os.path.isdir(self.path) else 'file', self.path)
    #     spec.popen()


    def action_empty_shell(self):
        title = os.path.basename(self.path)
        # use with {title: '$BASE_NAME', title_instance: true} usually
        spec = self.get_spec('set_title', ['cmd.exe'], title=title)
        spec = self.get_spec('detach_run', spec)
        spec = self.get_spec('shell', spec, cwd=self.path)
        spec = self.finan_spec(spec)
        spec.popen()


    def action_bring_browse(self):
        browser_class = {
            'firefox': 'MozillaWindowClass',
            'chrome': 'Chrome_WidgetWin_1',
        }
        using_browser = self.autoinfo.get('browser', 'chrome')
        singleton = WindowSingleton(webbrowser.get(using_browser).open,
                                    window_class=browser_class[using_browser],
                                    class_instance=True)
        singleton.bring_top()

    def action_browse(self):
        using_browser = self.autoinfo.get('browser', 'chrome')
        self.do_action('bring_browse')
        webbrowser.get(using_browser).open_new_tab(self.path)

    def action_browse_http(self):
        if "://" not in self.path:
            self.path = "http://" + self.path
        self.do_action('browse')

    def action_browse_google(self):
        self.path = "http://google.com/#q=" + urllib.parse.quote(self.path, '')
        self.do_action('browse')

    def action_add_folder_to_project(self):
        d = self.view.window().project_data() or {}
        d.setdefault('folders', []).append({'path': self.path})
        self.view.window().set_project_data(d)


    # for files, as the user if they's like to edit or run the file
    def action_file_menu(self):
        ActionDispitch(self.view, 'none', self.path, autoinfo={
                       "action": "menu",
                       "menu": ['edit',
                                'run',
                                'reveal',
                                'edit in new window',
                                'open'
                                ]
                       }).do_action()



    def action_folder_menu(self):
        ActionDispitch(self.view, 'none', self.path, autoinfo={
                       "action": "menu",
                       "menu": ['reveal',
                                'add folder to project',
                                'edit in new window'
                                ]
                       }).do_action()


    def action_menu(self):
        assert('menu' in self.autoinfo)
        menu = self.autoinfo['menu']

        def do(idx):
            if idx != -1:
                self.do_action(menu[idx].replace(' ', '_'))
        sublime.active_window().show_quick_panel(menu, do)




class OpenUrlMoreCommand(sublime_plugin.TextCommand):

    # enter debug mode on Noah's machine
    debug("open_url running in verbose debug mode")


    def run(self, edit=None, url=None, path_type=None, autoinfo=None):

        # sublime text has its own open_url command used for things like Help menu > Documentation
        # so if a url is specified, then open it instead of getting text from the edit window
        if url is None:
            url = self.selection()
        elif url == '$EDIT_FILE':
            url = self.view.file_name()
        elif url == '$EDIT_FOLDER':
            url = os.path.dirname(self.view.file_name())
        elif url == '$PROJECT_FOLDER':
            window = sublime.active_window()
            if window.project_file_name():
                url = os.path.dirname(window.project_file_name())
            else:
                return
        elif not url:
            return

        if autoinfo:
            ActionDispitch(self.view, path_type, url, autoinfo=autoinfo).do_action()
            return

        # expand variables in the path
        url = os.path.expandvars(url)

        # strip quotes if quoted
        if (url.startswith("\"") & url.endswith("\"")) | (url.startswith("\'") & url.endswith("\'")):
            url = url[1:-1]

        # find the relative path to the current file 'google.com'
        try:
            relative_path = os.path.normpath(os.path.join(os.path.dirname(self.view.file_name()), url))
        except (TypeError, AttributeError):
            relative_path = None

        # debug info
        debug("open_url debug : ", [url, relative_path])

        # if this is a directory, show it (absolute or relative)
        # if it is a path to a file, open the file in sublime (absolute or relative)
        # if it is a URL, open in browser
        # otherwise google it
        if os.path.isdir(url):
            ActionDispitch(self.view, 'folder', url).do_action()
        
        elif os.path.isdir(os.path.expanduser(url)):
            ActionDispitch(self.view, 'folder', os.path.expanduser(url)).do_action()

        elif relative_path and os.path.isdir(relative_path):
            ActionDispitch(self.view, 'folder', relative_path).do_action()
        
        elif os.path.exists(url):
            ActionDispitch(self.view, 'file', url).do_action()

        elif os.path.exists(os.path.expanduser(url)):
            ActionDispitch(self.view, 'file', os.path.expanduser(url)).do_action()
        
        elif relative_path and os.path.exists(relative_path):
            ActionDispitch(self.view, 'file', relative_path).do_action()
        
        else:
            ActionDispitch(self.view, 'web', url).do_action()


    # pulls the current selection or url under the cursor
    def selection(self):
        # new method to strongly enhance finding path-like string
        s = self.view.sel()[0]

        # expand selection to possible URL
        start = s.a
        end = s.b

        # match absolute path ex: c:/xxx, E:\xxx, /xxx
        # this match is accept only one space inside word
        abs_url = r'([A-Z]:)?[\\/](?:[^ ]| (?! |https?:))*'
        
        # match url path ex: http://xxx, xxx/xxx, xxx\xxx
        # this match not accept space
        file_url = r'(https?://)?([^ \\/]+[\\/])+([^ \\/]+)?'
        
        # unfold surrounding symbol
        merge_url = r'(\[)?(\()?(?P<url>{0})(?(2)\))(?(1)\])'

        # compose those matches together
        url_pattern = re.compile(merge_url.format('|'.join([abs_url, file_url])), re.I)


        # if nothing is selected, expand selection to nearest terminators
        if (start == end):
            line_region = self.view.line(start)
            terminator = list('\t\"\'><,;')

            # move the selection back to the start of the url
            while (start > line_region.a
                   and not self.view.substr(start - 1) in terminator):
                start -= 1

            # move end of selection forward to the end of the url
            while (end < line_region.b
                   and not self.view.substr(end) in terminator):
                end += 1

            url = self.view.substr(sublime.Region(start, end))
            for match in url_pattern.finditer(url):
                # make sure match at the cursor position
                if match.span('url')[0] < s.a - line_region.a < match.span('url')[1]:
                    return match.group('url')

        # grab the URL
        return self.view.substr(sublime.Region(start, end)).strip()

