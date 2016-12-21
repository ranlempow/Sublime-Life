# noqa: D, V, E501

import sublime
import sublime_plugin

import re
import os
import sys
import json
import subprocess

MAIN_COMPLETION_FILE = 'sbc-api-{language} [{suffix}].sublime-settings'
SUB_COMPLETION_FILE = 'sbc-api-{completion_name}.sublime-settings'
MOUNTED_SYNTAX_FILE = '{language} [{suffix}]{ext}'
MOUNTED_SYNTAX_NAME = '{language} [{suffix}]'


def plugin_loaded():
    ExtraCompletionManager.BASE_DIR = os.path.join(sublime.packages_path(), 'User', 'ExtraCompletion')
    ExtraCompletionManager._debug = sublime.load_settings('ExtraCompletion.sublime-settings').get('debug', False)
    os.makedirs(ExtraCompletionManager.BASE_DIR, exist_ok=True)

class Mounter:
    @classmethod
    def find_builtin_syntax_resource(cls, lang):
        resources = []
        resources += sublime.find_resources('{}.tmLanguage'.format(lang))
        resources += sublime.find_resources('{}.sublime-syntax'.format(lang))
        return resources[-1] if resources else None

    def __init__(self, config):
        self.config = config

    def mount_all(self):
        syntax_resource = self.find_builtin_syntax_resource(self.config.language)
        if syntax_resource is None:
            raise Exception('Builtin Syntax "{}" not found'.format(self.config.language))

        path, ext = os.path.splitext(syntax_resource)
        basename = os.path.basename(path)
        mounted_name = MOUNTED_SYNTAX_FILE.format(language=basename, suffix=self.config.suffix, ext=ext)

        with open(os.path.join(ExtraCompletionManager.BASE_DIR, mounted_name), 'w', encoding='utf-8') as fp:
            syntax_content = sublime.load_resource(syntax_resource)
            syntax_content = self.mount_sublime_syntax(syntax_content)
            syntax_content = self.mount_tmLanguage(syntax_content)
            syntax_content = self.mount_wordsets(syntax_content)
            fp.write(syntax_content)

    def mount_words(self, syntax_content, start, end, words):
        replacer = re.compile(start + r'\|.*?\|' + end, re.M | re.DOTALL)
        syntax_content = replacer.sub('|'.join(words), syntax_content)
        return syntax_content

    def mount_wordsets(self, syntax_content):
        if self.config.wordsets:
            for start, end, wordscope in self.config.wordsets:
                words = [define['symbol'] for define in self.config.completions if define.get('scope') == wordscope]
                syntax_content = self.mount_words(syntax_content, start, end ,words)
        return syntax_content

    def mount_sublime_syntax(self, syntax_content):
        # rename
        syntax_content = re.sub(r'name:\s+(.+)',
                                r'name: \1 [' + self.config.suffix + ']',
                                syntax_content, count=1)
        # replace acceptable file extensions of source
        if self.config.file_extensions is not None:
            extlist = '[{}]'.format(', '.join(self.config.file_extensions))
            syntax_content = re.sub(r'file_extensions:\s+([\w\s\[\]\,-]+)(?=\n\w)',
                                    r'file_extensions: ' + extlist,
                                    syntax_content, count=1)
        # replace acceptable first line match in source
        if self.config.first_line_match:
            syntax_content = re.sub(r'first_line_match:\s+(.+)',
                                    r'first_line_match: ' + self.config.first_line_match,
                                    syntax_content, count=1)

        return syntax_content

    def mount_tmLanguage(self, syntax_content):
        # rename
        syntax_content = re.sub(r'<key>name</key>\s*<string>(.+)</string>',
                                   r'\n\t<key>name</key>\n\t<string>\1 [' + self.config.suffix + ']</string>',
                                   syntax_content, count=1)

        # replace acceptable file extensions of source
        if self.config.file_extensions is not None:
            extlist = '<array>{}</array>'.format('\n'.join('<string>{}</string>'.format(ext) for ext in self.config.file_extensions))
            syntax_content = re.sub(r'<key>fileTypes</key>.+?</array>',
                                    r'<key>fileTypes</key>' + extlist,
                                    syntax_content, count=1, flags=re.DOTALL)

        # replace acceptable first line match in source
        if self.config.first_line_match:
            syntax_content = re.sub(r'<key>firstLineMatch</key>.+?</string>',
                                    r'<key>firstLineMatch</key><string>{}</string>'.format(self.config.first_line_match),
                                    syntax_content, count=1, flags=re.DOTALL)
        return syntax_content





# reference: http://docs.sublimetext.info/en/latest/reference/completions.html
class BuildConfig:
    def __init__(self, config, config_path):
        self.config_path = config_path
        for fixed in ['language',                   # the origin language, should exist in sublime syntex list
                      'suffix',                     # the name of inherited sub-language (suffix must equels setting name),
                                                    #   suffix should uniqul.
                      'scope',                      # scepe of completions
                      'completions'                 # definition list, include function, constance...
                      ]:
            setattr(self, fixed, config[fixed])
        for optional in ['wordsets',                # [(start, end, type), ...] a list to replace builtin words
                         'file_extensions',         # apply this sub-language when match extensions
                         'first_line_match',        # apply this sub-language when match first line in source code
                         'includes_completion',     # include other completion file
                         'build'                    # a map contains commands for build sub-completion
                         ]:
            setattr(self, optional, config.get(optional, None))
    
    def do_build(self):
        if self.build is not None:
            cwd = os.getcwd()
            try:
                os.chdir(os.path.dirname(self.config_path))
                for name, command in self.build.items():
                    ExtraCompletionManager.debug('build: "{}" using "{}"', name, command)
                    proc = subprocess.Popen(command, shell=True, stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
                    proc.wait(timeout=30)
                    if proc.returncode == 0:
                        sub_json = proc.stdout.read().replace(b'\r\n', b'\n').decode('utf-8')
                    else:
                        raise Exception('build command faild "{}"'.format(command))
                    sub_config = json.loads(sub_json)
                    with open(os.path.join(ExtraCompletionManager.BASE_DIR,
                                           SUB_COMPLETION_FILE.format(completion_name=name)),
                              'w', encoding='utf-8') as fp:
                        fp.write(sub_json)
            finally:
                os.chdir(cwd)

    def resolve_includes(self):
        if self.includes_completion is not None:
            for completion_name in self.includes_completion:
                completion = sublime.load_settings(SUB_COMPLETION_FILE.format(completion_name=completion_name))
                if completion.get('completions') is not None:
                    self.completions += completion.get('completions')


class ExtraCompletionManager:
    BASE_LOCATION = 'Packages/User/ExtraCompletion/'
    BASE_DIR = None
    _debug = False

    @classmethod
    def debug(cls, message, *context, **kwargs):
        if cls._debug:
            print(message.format(*context, **kwargs))

    def remove_file(self, filename):
        try:
            filepath = os.path.join(self.BASE_DIR, filename)
            os.remove(filepath)
            self.debug('remove file: {}', filepath)
        except FileNotFoundError:
            pass

    def list_main_completions(self):
        main_completions = []
        for file in os.listdir(self.BASE_DIR):
            path, ext = os.path.splitext(file)
            basename = os.path.basename(path)
            match = re.match(r'^(.+) \[(.+)\]$', basename)
            if match and ext.endswith(('.tmLanguage', '.sublime-syntax')):
                language, suffix = match.groups()
                main_completions.append([language, suffix, ext])

        return main_completions

    def install_by_view(self):
        self.debug('install_by_view')
        view = sublime.active_window().active_view()
        json_config = view.substr(sublime.Region(0, view.size()))
        loaded_config = json.loads(json_config)
        config = BuildConfig(loaded_config, view.file_name())
        config.do_build()
        config.resolve_includes()

        mounter = Mounter(config)
        mounter.mount_all()
        with open(os.path.join(self.BASE_DIR, 
                               MAIN_COMPLETION_FILE.format(**config)),
                  'w', encoding='utf-8') as fp:
            fp.write(json_config)

    def install(self, config):
        pass

    def compile(self, name):
        pass

    def remove(self, name):
        for language, suffix, ext in self.list_main_completions():
            if name == MOUNTED_SYNTAX_NAME.format(language=language, suffix=suffix):
                break
        else:
            return
        self.remove_file(MOUNTED_SYNTAX_FILE.format(language=language, suffix=suffix, ext=ext))
        self.remove_file(MAIN_COMPLETION_FILE.format(language=language, suffix=suffix))



class ExtraCompletionInstallByViewCommand(sublime_plugin.ApplicationCommand):
    def run(self, *args):
        manager = ExtraCompletionManager()
        manager.install_by_view()


class ExtraCompletionRemoveCommand(sublime_plugin.WindowCommand):

    def run(self):
        manager = ExtraCompletionManager()
        completions_list = manager.list_main_completions()
        items = []
        for language, suffix, ext in completions_list:
            items.append(MOUNTED_SYNTAX_NAME.format(language=language, suffix=suffix))

        def on_done(select):
            if select == -1:
                return
            manager.remove(items[select])
        self.window.show_quick_panel(items, on_done)

