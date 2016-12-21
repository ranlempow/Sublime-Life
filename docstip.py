# noqa: D, V, E501
import sublime_plugin
import sublime
import json
import re
import os.path


STYLE = """
body, h4, p {
    margin: 6px 0px;
}
body {
    padding: 0px 24px;
    font-size: 12px;
}
"""

class Language:
    def __init__(self, view):
        self.view = view
        self.settings = sublime.load_settings('sbc-setting.sublime-settings')

    def get_lang(self):
        return re.match(".*/(.*?).(tmLanguage|sublime-syntax)", self.view.settings().get("syntax")).group(1)

    def load_completion(self, completion_name):
        return sublime.load_settings('sbc-api-' + completion_name + '.sublime-settings')

    def validate(self, completion):
        return completion.get('completions') is not None

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


class IntelliDocsEventListener(LanguageMixin, sublime_plugin.ViewEventListener):
    cache = {}

    def __init__(self, view):
        super().__init__(view)
        self.settings = sublime.load_settings("IntelliDocs.sublime-settings")
        self.lang = Language(view)

    def debug(self, *text):
        if self.settings.get("debug"):
            print(*text)


    # ======== Deprecate =========

    def getLang(self, view):
        scope = view.scope_name(view.sel()[0].b)  # try to match against the current scope
        for match, lang in self.settings.get("docs").items():
            if re.match(".*"+match, scope):
                return lang
        # no match in predefined docs, return from syntax filename
        return re.match(".*/(.*?).(tmLanguage|sublime-syntax)", view.settings().get("syntax")).group(1)

    def getCompletions(self, view):
        # Find completions database for lang
        lang = self.getLang(view)
        if lang not in self.cache:  # DEBUG disable cache: or 1 == 1
            path_db = os.path.dirname(os.path.abspath(__file__))+"/db/%s.json" % lang
            self.debug("Loaded intelliDocs db:", path_db)
            if os.path.exists(path_db):
                self.cache[lang] = json.load(open(path_db))
            else:
                self.cache[lang] = {}
        return self.cache.get(lang)

    # ============================



    def getCompletions(self):
        completions = {}
        for define in self.lang.iter_definition_with_scope(self.view.sel()[0].b):
            if isinstance(define, dict) and 'syntax' in define:    
                completions[define['symbol']] = define
        return completions


    def excutePunctStart(self, punctuation_start):
        buff = self.view.substr(sublime.Region(punctuation_start - 100, punctuation_start))
        function_match = re.search('[a-zA-Z0-9_\$\.]+[ \t]*$', buff)
        func_name = function_match.group(0) if function_match else None

        # 'a.b.c' => ['a.b.c', 'b.c', 'c']
        function_names = []
        while func_name:
            function_names.append(func_name)
            if '.' not in func_name:
                break
            func_name = func_name.split('.', 1)[1]

        if function_names:
            self.debug(function_names)
            self.excuteFunctionNames(punctuation_start, function_names)

    def excuteFunctionNames(self, punctuation_start, function_names):
        completions = self.getCompletions()
        for function_name in function_names:
            completion = completions.get(function_name)
            if completion:
                break

        if completion:
            menus = ['<style>{style}</style><h4>{syntax}</h4><p>{descr}</p>'.format(style=STYLE, **completion)]
            if completion["params"]:
                menus.append('<h5>Args:</h5>')
                for parameter in completion["params"]:
                    menus.append('<p>{name}: {descr}</p>'.format(**parameter))
            self.debug(completion)
            self.view.show_popup(''.join(menus), location=punctuation_start, max_width=600)

    def on_selection_modified(self):
        punctuation_start = None
        point = self.view.sel()[0].a
        for p in [point - 1, point]:
            if self.view.substr(p) == '(' and self.view.classify(p) | sublime.CLASS_PUNCTUATION_START:
                punctuation_start = p

        if punctuation_start is not None:
            self.excutePunctStart(self.view, punctuation_start)
