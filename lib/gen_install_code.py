

def install_code():
    import urllib.request,os,hashlib
    # h = '6f4c264a24d933ce70df5dedcf1dcaee' + 'ebe013ee18cced0ef93d5f746d80ef60'
    pf = 'Package Control.sublime-package'
    ipp = sublime.installed_packages_path()
    urllib.request.install_opener( urllib.request.build_opener( urllib.request.ProxyHandler()) )
    by = urllib.request.urlopen( 'http://packagecontrol.io/' + pf.replace(' ', '%20')).read()
    # dh = hashlib.sha256(by).hexdigest()
    # ( print('Error validating download (got %s instead of %s), please try manual install' % (dh, h)) if
    #     dh != h else 
    #     open(os.path.join(ipp, pf), 'wb').write(by)
    # )
    sublime.message_dialog('Error validating download (size %d < 250k), please try manual install' % (len(by))) if \
    len(by) < 1024 * 250 else \
    open(os.path.join(ipp, pf), 'wb').write(by)
    pks = sublime.load_settings('Package Control.sublime-settings')
    pks.set("installed_packages", list(set(pks.get("installed_packages", []) + ['RansTool (ranlempow)'])))
    pks.set('repositories', ["https://raw.githubusercontent.com/ranlempow/Sublime-Life/master/repository.json"])
    sublime.save_settings('Package Control.sublime-settings')
    sublime.set_timeout(lambda: sublime.message_dialog("Please restart Sublime Text to continuity install Sublime-Life"), 500)

if __name__ == '__main__':
    import inspect
    lines = inspect.getsource(install_code)
    lines = lines.split('\n')[1:]
    lines = [ ln[4:] for ln in lines if ln and ln[4] != '#' ]
    lines = [ ( ln[:-1] if ln[-1] == '\\' else ln + ';') for ln in lines ]
    print(''.join(lines))
