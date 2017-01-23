import sublime
import sublime_plugin

import os
import urllib


class ChooseFontCommand(sublime_plugin.WindowCommand):
    baseurl = 'https://github.com/ranlempow/fonts/raw/master'
    fonts = {
        'Yahei Consolas Hybrid': ['yahei consolas hybrid 1', '雅黑體',
                                  '{baseurl}/Yahei.Consolas.1.13.ttf'],
        'Consolas': ['consola', '最熱門',
                     '{baseurl}/consola.ttf'],
        'Inconsolata': ['inconsolata-regular', '最好看',
                        '{baseurl}/Inconsolata-Regular.ttf'],
        'MingLiU': ['mingliu', '細明體',
                    '{baseurl}/mingliu.ttc'],
        'SimSun': ['simsun', '宋體',
                   '{baseurl}/simsun.ttc'],
        'Meiryo': ['meiryo', '日本明體',
                   '{baseurl}/meiryo.ttc'],
        'Meiryo UI': ['meiryo', '介面明體',
                      '{baseurl}/meiryo.ttc'],
    }
    suites = [
        ('Yahei Consolas Hybrid', '13', 'latin CJK mono'),
        ('Yahei Consolas Hybrid', '14', 'latin CJK mono'),
        ('Yahei Consolas Hybrid', '15', 'latin CJK mono'),
        ('Inconsolata', '12', 'latin CJK mono'),
        ('Inconsolata', '15', 'latin CJK mono'),
        ('Consolas', '12', 'latin mono'),
        ('Consolas', '13', 'latin mono'),
        ('Consolas', '14', 'latin mono'),
        ('MingLiU', '11', 'CJK mono'),
        ('MingLiU', '12', 'CJK mono'),
        ('MingLiU', '15', 'CJK mono'),
        ('SimSun', '11', 'CJK mono'),
        ('SimSun', '12', 'CJK mono'),
        ('SimSun', '13', 'CJK mono'),
        ('Meiryo', '12', 'CJK'),
        ('Meiryo', '13', 'CJK'),
        ('Meiryo', '14', 'CJK'),
        ('Meiryo', '15', 'CJK'),
        ('Meiryo UI', '14', 'CJK'),
        ('Meiryo UI', '15', 'CJK'),
    ]
    targets = ['All File', 'Text File', 'Program Language File']
    def choose_suite(self, index):
        if index == -1:
            self.chosen = [None, None]
            return
        self.chosen[0] = index

        targetmenu = ['Set To ' + t for t in self.targets]
        self.window.show_quick_panel(targetmenu, self.choose_target)


    def choose_target(self, index):
        if index == -1:
            self.chosen = [None, None]
            return
        self.chosen[1] = index

        fontface, fontsize, *_ = self.suites[self.chosen[0]]
        fontsize = int(fontsize)
        target = self.targets[self.chosen[1]]

        system_font_dir = os.path.join(os.environ['WINDIR'], 'Fonts')
        font_filename = self.fonts[fontface][0]
        if font_filename not in [f.lower().split('.')[0] for f in os.listdir(system_font_dir)]:
            # need install font from internet
            url = self.fonts[fontface][2].format(baseurl=self.baseurl)
            self.window.status_message('downloading font from: ' + url)
            def download_font():
                self.download_font(url, target, fontface, fontsize)
            sublime.set_timeout(download_font, 200)
        else:
            self.setfont(target, fontface, fontsize)

    def download_font(self, url, target, fontface, fontsize):
        file = os.path.join(os.environ['TEMP'], os.path.basename(url))
        with open(file, 'wb') as fp:
            body = urllib.request.urlopen(url).read()
            fp.write(body)
        vbsfile = os.path.join(os.environ['TEMP'], os.path.basename(url) + '.vbs')
        self.window.status_message('installing font: ' + file)
        with open(vbsfile, 'w') as fp:
            fp.write("""
Set objShell = CreateObject("Shell.Application")
Set objFolder = objShell.Namespace(&H14&)
objFolder.CopyHere("{}")
""".format(file))

        os.system('wscript "{}"'.format(vbsfile))
        def setfont():
            self.setfont(target, fontface, fontsize)
        sublime.set_timeout(setfont, 1500)


    def setfont(self, target, fontface, fontsize):
        text_settings = sublime.load_settings('Markdown.sublime-settings')
        if target == 'All File':
            syntax_settings = sublime.load_settings('Preferences.sublime-settings')
            text_settings.erase('font_face')
            text_settings.erase('font_size')
        elif target == 'Program Language File':
            syntax_settings = sublime.load_settings('Preferences.sublime-settings')
        elif target == 'Text File':
            syntax_settings = text_settings

        syntax_settings.set('font_face', fontface)
        syntax_settings.set('font_size', fontsize)

        sublime.save_settings('Preferences.sublime-settings')
        sublime.save_settings('Markdown.sublime-settings')


    def run(self):
        
        self.chosen = [None, None]
        fontmenu = ['{1}px {0}: {2} {3}'.format(*(suite + (self.fonts[suite[0]][1],)))
                    for suite in self.suites]
        self.window.show_quick_panel(fontmenu, self.choose_suite)
