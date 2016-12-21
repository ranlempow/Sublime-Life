import re

syntax_content = """
%YAML 1.2
---
name: Python
file_extensions:
  - py
  - py3
  - pyw
  - pyi
  - rpy
  - cpy
  - SConstruct
  - Sconstruct
  - sconstruct
  - SConscript
  - gyp
  - gypi
  - Snakefile
  - wscript
first_line_match: ^#!/.*\\bpython\d?\\b
scope: source.python
"""

print(re.search(r'name:\s+(.+)', syntax_content).group(0))
print(re.search(r'file_extensions:\s+([\w\s\[\]\,-]+)(?=\n\w)', syntax_content).group(0))
print(re.search(r'first_line_match:\s+(.+)', syntax_content).group(0))

syntax_content = """
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>comment</key>
	<string>CoffeeScript Syntax: version 1</string>
	<key>fileTypes</key>
	<array>
		<string>coffee</string>
		<string>Cakefile</string>
		<string>coffee.erb</string>
		<string>cson</string>
		<string>cjsx</string>
	</array>
	<key>firstLineMatch</key>
	<string>^#!.*\bcoffee</string>
	<key>foldingStartMarker</key>
	<string>^\s*class\s+\S.*$|.*(-&gt;|=&gt;)\s*$|.*[\[{]\s*$</string>
	<key>foldingStopMarker</key>
	<string>^\s*$|^\s*[}\]]\s*$</string>
	<key>keyEquivalent</key>
	<string>^~C</string>
	<key>name</key>
	<string>CoffeeScript</string>
	<key>patterns</key>
	<array>
		<dict>
			<key>captures</key>
"""

print(re.search(r'<key>name</key>\s*<string>(.+)</string>', syntax_content).group(0))
print(re.search(r'<key>fileTypes</key>.+?</array>', syntax_content, flags= re.DOTALL).group(0))
print(re.search(r'<key>firstLineMatch</key>.+?</string>', syntax_content, flags= re.DOTALL).group(0))
