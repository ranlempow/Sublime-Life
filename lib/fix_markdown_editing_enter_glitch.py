'''
Monkey-patch the MarkdownEditing package.
fix the problem that press enter on list-items with CJK input method enabled.
Without this fix, press enter on list-items cause erase the line.

usage:
    python2 remark.py
'''

import zipfile
import os
import json
import re

def fix_markdown_editing_enter_glitch(installed_packages_path, tmp_path):
    pkg_file = os.path.join(installed_packages_path, 'MarkdownEditing.sublime-package')
    pkg_backup = os.path.join(tmp_path, '/tmp/MarkdownEditing_backup.sublime-package')
    pkg_writing = os.path.join(tmp_path, '/tmp/MarkdownEditing_writing.sublime-package')

    try:
        os.remove(pkg_writing)
    except FileNotFoundError:
        pass


    zin = zipfile.ZipFile(pkg_file, 'r')
    zout = zipfile.ZipFile(pkg_writing, 'w')
    for item in zin.infolist():
        buf = zin.read(item.filename)
        if item.filename == "Default (OSX).sublime-keymap":
            print(item)
            # obj = json.loads(buf.decode('utf-8'))
            # print(obj)
            buf = re.sub(rb'\n    { "keys": \["enter"\][^&]*?\n    },\n', b'\n', buf)
            # print(buf.decode('utf-8'))
        zout.writestr(item, buf)
    zout.close()
    zin.close()


    try:
        os.remove(pkg_backup)
    except FileNotFoundError:
        pass

    print("backup '{}' to '{}'".fomrat(pkg_file, pkg_backup))
    os.rename(pkg_file, pkg_backup)
    os.rename(pkg_writing, pkg_file)


if __name__ == '__main__':
    # only usable on macos
    pkg_path = os.path.expanduser('~/Library/Application Support/Sublime Text 3/Installed Packages')
    fix_markdown_editing_enter_glitch(pkg_path, '/tmp')

