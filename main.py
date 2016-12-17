import sublime, sublime_plugin

class CompletionsPackageEventListener(sublime_plugin.ViewEventListener):
    def __init__(self, view):
        super().__init__(view)
        self.settings = sublime.load_settings('sbc-setting.sublime-settings')

    def on_query_completions(self, prefix, locations):

        self.completions = []
        for API_Keyword in self.settings.get('completion_active_list', []):
            # If completion active
            if self.settings.get('completion_active_list').get(API_Keyword):
                sbc_api = sublime.load_settings('sbc-api-' + API_Keyword + '.sublime-settings')

                scope = sbc_api.get('scope')
                if scope and self.view.match_selector(locations[0], scope):
                    self.completions += sbc_api.get('completions')

        if not self.completions:
            return []

        # extend word-completions to auto-completions
        compDefault = [self.view.extract_completions(prefix)]
        compDefault = [(item, item) for sublist in compDefault for item in sublist if len(item) > 3]
        compDefault = list(set(compDefault))

        completions = [tuple(attr) for attr in self.completions]
        completions.extend(compDefault)
        return completions
