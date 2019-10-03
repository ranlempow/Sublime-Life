import os
import sys
import tempfile
import urllib

def install_font(url):
    file = os.path.join(tempfile.gettempdir(), os.path.basename(url))
    with open(file, 'wb') as fp:
        url_p = os.path.dirname(url) + '/' + urllib.parse.quote(os.path.basename(url))
        print('download font from {}'.format(url_p))
        body = urllib.request.urlopen(url_p).read()
        fp.write(body)
    if sys.platform == 'win32':
        vbsfile = os.path.join(os.environ['TEMP'], os.path.basename(url) + '.vbs')
        # self.window.status_message('installing font: ' + file)
        print('installing font {}'.format(file))
        with open(vbsfile, 'w') as fp:
            fp.write("""
    Set objShell = CreateObject("Shell.Application")
    Set objFolder = objShell.Namespace(&H14&)
    objFolder.CopyHere("{}")
    """.format(file))
        os.system('wscript "{}"'.format(vbsfile))
    elif sys.platform == 'darwin':
        os.system('cp {} ~/Library/Fonts'.format(file))
    elif sys.platform == 'linux':
        os.system('cp {} ~/.local/share/fonts'.format(file))
    else:
        raise ValueError('unknown system {}'.fomrat(os.platform))

def has_font(font_filename):
    if sys.platform == 'win32':
        system_font_dir = [os.path.join(os.environ['WINDIR'], 'Fonts')]
        if isinstance(font_filename, tuple):
            font_filename = font_filename[1]
    elif sys.platform == 'darwin':
        system_font_dir = [os.path.expanduser('~/Library/Fonts'), '/Library/Fonts']
        if isinstance(font_filename, tuple):
            font_filename = font_filename[0]
    elif sys.platform == 'linux':
        system_font_dir = [os.path.expanduser('~/.local/share/fonts'), '/usr/share/fonts', '/usr/local/share/fonts']
        if isinstance(font_filename, tuple):
            font_filename = font_filename[0]
    else:
        raise ValueError('unknown system {}'.fomrat(os.platform))

    font_filename = font_filename.lower().split('.')[0]
    for font_dir in system_font_dir:
        if os.path.exists(font_dir):
            files = [f.lower().split('.')[0] for f in os.listdir(font_dir)]
            if font_filename in files:
                return True
    return False
