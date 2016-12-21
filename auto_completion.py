import sublime
import sublime_plugin
import re
import os
import sys
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'thirdparty'))
import watchdog
from watchdog.observers.polling import PollingObserver as Observer



class CompletionCache(watchdog.events.FileSystemEventHandler):
    def __init__(self, base):
        self.base = base
        self._cache = {}
        self.observer = Observer()
        self.observer.schedule(self, self.base, recursive=False)
        self.observer.start()

    def load(self, path):
        try:
            with open(path, encoding='utf-8') as fp:
                return json.load(fp)
        except OSError:
            return None

    def get(self, key):
        path = os.path.join(self.base, key)
        path = os.path.normcase(path)
        if path not in self._cache:
            self._cache[path] = self.load(path)
        return self._cache[path]

    def stop(self):
        self.observer.stop()

    def on_modified(self, event):
        path = os.path.normcase(event.src_path)
        if path in self._cache:
            self._cache[path] = self.load(path)


def plugin_loaded():
    Language.BASE_DIR = os.path.join(sublime.packages_path(), 'User', 'ExtraCompletion')
    if Language.cache is None:
        Language.cache = CompletionCache(Language.BASE_DIR)

def plugin_unloaded():
    if Language.cache is not None:
        Language.cache.stop()
        Language.cache = None

class Language:
    BASE_DIR = None
    cache = None
    def __init__(self, view):
        self.view = view
        self.settings = sublime.load_settings('sbc-setting.sublime-settings')

    def get_lang(self):
        syntax_name = self.view.settings().get("syntax")
        return re.match(".*/(.+).(tmLanguage|sublime-syntax)", self.view.settings().get("syntax")).group(1)

    def load_completion(self, completion_name):
        return self.cache.get('sbc-api-' + completion_name + '.sublime-settings')

    def validate(self, completion):
        return completion is not None and completion.get('completions') is not None

    def get_language_group(self):
        main_completion = self.load_completion(self.get_lang())
        if not self.validate(main_completion):
            return []
        other_completions = []
        for completion_name in main_completion.get('includes_completions', []):
            completion = self.load_completion(completion_name)
            if self.validate(completion):
                other_completions.append(completion)
        return [main_completion] + other_completions

    def get_settings_group(self):
        settings_completions = []
        for completion_name in self.settings.get('includes_completions', []):
            completion = self.load_completion(completion_name)
            if self.validate(completion):
                settings_completions.append(completion)
        return settings_completions

    def iter_definition_with_scope(self, point):
        for completion in self.get_language_group() + self.get_settings_group():
            if completion.get('scope') is None or self.view.match_selector(point, completion.get('scope')):
                for define in completion.get('completions'):
                    yield define


class CompletionsPackageEventListener(sublime_plugin.ViewEventListener):
    def __init__(self, view):
        super().__init__(view)
        self.lang = Language(view)

    def on_query_completions(self, prefix, locations):
        
        self.completions = []
        for define in self.lang.iter_definition_with_scope(locations[0]):
            if isinstance(define, list):
                self.completions.append(define)
                continue
            if 'trigger' not in define:
                trigger = define['symbol']
                if 'type' in define:
                    trigger += r'\t' + define['type']
            else:
                trigger = define['trigger']
            contents = define.get('contents', define['symbol'])
            self.completions.append([trigger, contents])

        if not self.completions:
            return []

        # extend word-completions to auto-completions
        compDefault = [self.view.extract_completions(prefix)]
        compDefault = [(item, item) for sublist in compDefault for item in sublist if len(item) > 3]
        compDefault = list(set(compDefault))

        completions = [tuple(attr) for attr in self.completions]
        completions.extend(compDefault)
        return completions
