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


class IntelliDocsEventListener(sublime_plugin.EventListener):
    cache = {}

    def __init__(self):
        self.settings = sublime.load_settings("IntelliDocs.sublime-settings")

    def debug(self, *text):
        if self.settings.get("debug"):
            print(*text)

    def getLang(self, view):
        scope = view.scope_name(view.sel()[0].b)  # try to match against the current scope
        for match, lang in self.settings.get("docs").items():
            if re.match(".*"+match, scope):
                return lang
        # no match in predefined docs, return from syntax filename
        return re.match(".*/(.*?).tmLanguage", view.settings().get("syntax")).group(1)

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

    def excutePunctStart(self, view, punctuation_start):
        buff = view.substr(sublime.Region(punctuation_start - 100, punctuation_start))
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
            self.excuteFunctionNames(view, punctuation_start, function_names)

    def excuteFunctionNames(self, view, punctuation_start, function_names):
        completions = self.getCompletions(view)
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
            view.show_popup(''.join(menus), location=punctuation_start, max_width=600)

    def on_selection_modified(self, view):
        punctuation_start = None
        point = view.sel()[0].a
        for p in [point - 1, point]:
            if view.substr(p) == '(' and view.classify(p) | sublime.CLASS_PUNCTUATION_START:
                punctuation_start = p

        if punctuation_start is not None:
            self.excutePunctStart(view, punctuation_start)
