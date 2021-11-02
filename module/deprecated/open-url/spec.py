# noqa: D, V, E241
import sublime

import ctypes
import time
import platform
import subprocess

_debug = False


def debug(*args):
    if _debug:
        print(*args)

SPEC = {
    # dir explorer
    'dir': {
        'Darwin':       ['open', '<__path__>'],
        'Linux':        ['nautilus', '--browser', '<__path__>'],
        'Windows':      ['explorer', '<__path__>']
    },
    # file explorer
    'file': {
        'Darwin':       ['open', '-R', '<__path__>'],
        'Linux':        ['nautilus', '--browser', '<__path__>'],
        'Windows':      ['explorer /select,"<__path__>"']
    },
    'detach_run': {
        'Darwin':       ['nohup', '*__path__*'],
        'Linux':        ['nohup', '*__path__*'],
        'Windows':      ['start', '', '/I', '*__path__*']
    },
    # desktop open
    'open': {
        'Darwin':       ['open', '<__path__>'],
        'Linux':        ['xdg-open', '<__path__>'],
        'Windows':      ['<__path__>'],
    },
    'open_with_app': {
        'Darwin':       ['open', '-a', '<__app__>', '<__path__>']
    },
    'run_custom': {
        'Darwin':       ['*__app__*', '*__path__*'],
        'Linux':        ['*__app__*', '*__path__*'],
        'Windows':      ['*__app__*', '*__path__*']
    },
    'shell': {
        'Darwin':       ['/bin/sh', '-c', '*__path__*'],
        'Linux':        ['/bin/sh', '-c', '*__path__*'],
        'Windows':      ['cmd.exe /c "<__path__>"']         # need extra hidden at Popen
    },
    'shell_keep_open': {
        'Darwin':       ['/bin/sh', '-c', "'<__path__>; exec /bin/sh'"],
        'Linux':        ['/bin/sh', '-c', "'<__path__>; exec /bin/sh'"],
        'Windows':      ['cmd.exe /k "<__path__>"']
    },
    # terminal open
    # terminal_keep_open = terminal + shell_keep_open
    'terminal': {
        'Darwin':       ['/opt/X11/bin/xterm', '-e', '*__path__*'],
        'Linux':        ['/usr/bin/xterm', '-e', '*__path__*'],
        'Linux2':       ['gnome-terminal', '-x', '*__path__*'],
        'Windows':      ['cmd.exe /c "<__path__>"']
    },
    'set_title': {
        'Windows':      ['TITLE <__title__>& <__path__>']
    }
    # termain open with pause after running
    # 'pause': {
    #     'Darwin':       ['<__path__>; read -p "Press [ENTER] to continue..."'],
    #     'Linux':        ['<__path__>; read -p "Press [ENTER] to continue..."'],
    #     'Windows':      ['<__path__> & pause']
    # }
}


class Specification:
    dry_run = False

    def __init__(self, args, cwd=None, hidden=False):
        self.args = args
        self.hidden = hidden
        self.cwd = cwd

    def quote(self):
        self.args = ['"{}"'.format(arg) for arg in self.args]

    def popen(self):
        if debug:
            print("popen cmd: %s" % self.args)
        if self.dry_run:
            return

        startupinfo = None
        if self.hidden:
            from subprocess import STARTUPINFO, _winapi
            startupinfo = STARTUPINFO()
            startupinfo.dwFlags |= _winapi.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = _winapi.SW_HIDE

        subprocess.Popen(self.args[0] if len(self.args) == 1 else self.args,
                         cwd=self.cwd, startupinfo=startupinfo)

    @classmethod
    def get_spec(cls, intention, path, cwd=None, app=None, title=None):
        if not SPEC.get(intention):
            raise Exception('unrecognized intention "{}"'.format(intention))
        if not SPEC[intention].get(platform.system()):
            raise Exception('unsupported os')
        spec = SPEC[intention][platform.system()]
        
        def merge(target, token, source):
            if source is None:
                return target
            if isinstance(source, cls):
                source = source.args
            if not isinstance(source, list):
                source = [source]
            source_str = ' '.join(s if s else '""' for s in source)
            merged = []
            for arg in target:
                if arg == '*__{}__*'.format(token):
                    merged.extend(source)
                else:
                    merged.append(arg.replace('<__{}__>'.format(token), source_str))
            return merged

        spec = merge(spec, 'path', path)
        spec = merge(spec, 'app', app)
        spec = merge(spec, 'title', title or '')
        hidden = intention == 'shell' and platform.system() == 'Windows'
        return cls(spec, cwd=cwd, hidden=hidden)




if platform.system() == 'Windows':
    EnumWindows = ctypes.windll.user32.EnumWindows
    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool,
                                         ctypes.POINTER(ctypes.c_int),
                                         ctypes.POINTER(ctypes.c_int))
    GetClassName = ctypes.windll.user32.GetClassNameW
    GetWindowText = ctypes.windll.user32.GetWindowTextW
    GetWindowTextLength = ctypes.windll.user32.GetWindowTextLengthW
    IsWindowVisible = ctypes.windll.user32.IsWindowVisible
    SW_MINIMIZE = 6
    SW_RESTORE = 9
    ShowWindow = ctypes.windll.user32.ShowWindow
    GetForegroundWindow = ctypes.windll.user32.GetForegroundWindow

    def get_window_class(hWnd):
        buff = ctypes.create_unicode_buffer(100)
        GetClassName(hWnd, buff, 99)
        return buff.value


    def get_window_title(hWnd):
        length = GetWindowTextLength(hWnd)
        buff = ctypes.create_unicode_buffer(length + 1)
        GetWindowText(hWnd, buff, length + 1)
        return buff.value


    def list_window(match_class=None, match_title=None):
        hWnds = []

        def callback(hWnd, lParam):
            if IsWindowVisible(hWnd):
                hWnds.append(ctypes.addressof(hWnd.contents))
            return True
        EnumWindows(EnumWindowsProc(callback), 0)

        if match_class is not None:
            hWnds = filter(lambda hWnd: get_window_class(hWnd) == match_class, hWnds)
        if match_title is not None:
            hWnds = filter(lambda hWnd: get_window_title(hWnd) == match_title, hWnds)
        return list(hWnds)


    # reference: https://gist.github.com/EBNull/1419093
    def forceFocus(wnd):
        if GetForegroundWindow() == wnd:
            return True
        ShowWindow(wnd, SW_MINIMIZE)
        ShowWindow(wnd, SW_RESTORE)


    class WindowSingleton:
        _hash = None

        def __init__(self, cmd, id=None,
                     window_title=None, window_class=None,
                     title_instance=False, class_instance=False):
            assert(any([id, window_title, window_class]))
            self.cmd = cmd
            self.id = id
            self.window_title = window_title
            self.window_class = window_class

            # if ture, ensure() is not create window for same title more than one
            self.title_instance = title_instance

            # if ture, ensure() is not create window for same class more than one
            self.class_instance = class_instance
            debug(self.window_title, self.window_class, self.title_instance, self.class_instance)

        def do_create(self):
            if isinstance(self.cmd, Specification):
                self.cmd.popen()
            elif callable(self.cmd):
                self.cmd(self)
            else:
                proc = subprocess.Popen(self.cmd, shell=True)
                proc.wait()
            time.sleep(0.5)

        def create_window(self):
            def get_snapshot():
                return set(list_window(match_class=self.window_class,
                                       match_title=self.window_title))

            before = get_snapshot()
            self.do_create()

            # find the window who created recently is match the class and the title
            delta = get_snapshot() - before
            if delta:
                hWnd = list(delta)[0]
                return {'hWnd': hWnd, 'title': get_window_title(hWnd)}

        def ensure(self):
            # ensure window exist. otherwise, create new one and return its handle
            hash_id = self.id or self.window_title or self.window_class
            window = None
            # try to find opened window in hash first
            if self._hash.get(hash_id) is not None:
                _window = self._hash.get(hash_id)
                if all([IsWindowVisible(_window['hWnd']),        # test window exist
                        not (self.window_title is not None and
                             self.window_title != get_window_title(_window['hWnd'])),
                        not (self.window_class is not None and
                             self.window_class != get_window_class(_window['hWnd']))
                        ]):
                    window = _window
            debug('window in hash: {}'.format(window))

            # if this is a singlaton window,
            # search already opened window in system who are match class and title
            if window is None and (self.class_instance or self.title_instance):
                # class_instance: ensure the program with window_class exist and onlyone
                # title_instance: ensure the program with window_title exist and onlyone
                windows = list_window(match_class=self.window_class if self.class_instance else None,
                                      match_title=self.window_title if self.title_instance else None)
                if windows:
                    window = {'hWnd': windows[0], 'title': get_window_title(windows[0])}
            debug('window exists: {}'.format(window))

            if window is None:
                window = self.create_window()
            
            if window is None:
                raise Exception('unable excute program')

            self._hash.set(hash_id, window)
            # sublime.save_settings('singletion-hash.sublime-settings')
            return window['hWnd']

        def bring_top(self):
            hWnd = self.ensure()
            forceFocus(hWnd)
else:
    WindowSingleton = None


def plugin_loaded():
    # print(list(map(lambda x: (get_window_title(x), get_window_class(x)), list_window())))
    if WindowSingleton:
        WindowSingleton._hash = sublime.load_settings('singletion-hash.sublime-settings')


def plugin_unloaded():
    if WindowSingleton:
        sublime.save_settings('singletion-hash.sublime-settings')
