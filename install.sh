#!/bin/sh

ST_PACKAGE_PATH="${ST_PACKAGE_PATH:-$HOME/Library/Application Support/Sublime Text 3}"
# case $0 in
# 	/*) 	ZERO="$(dirname "$0")";;
# 	*) 		ZERO="$PWD/$(dirname "$0")";;
# esac

if [ ! -e "$ST_PACKAGE_PATH/Installed Packages/Package Control.sublime-package" ]; then
	tmppc="${TMPDIR:-/tmp}/Package Control.sublime-package"
	curl -fsSL 'http://packagecontrol.io/Package%20Control.sublime-package' > "$tmppc"

	mkdir -p "$ST_PACKAGE_PATH/Installed Packages"
	mv "$tmppc" "$ST_PACKAGE_PATH/Installed Packages/Package Control.sublime-package"
	echo "install Package Control.sublime-package" >&2
fi

pkconfig="$ST_PACKAGE_PATH/Packages/User/Package Control.sublime-settings"
if [ ! -e "$pkconfig" ]; then
	mkdir -p "$ST_PACKAGE_PATH/Packages/User"
	cat > "$pkconfig" <<EOF
{
	"installed_packages":
	[
		"Package Control",
		"RansTool (ranlempow)",
	],
	"repositories":
	[
		"https://raw.githubusercontent.com/ranlempow/Sublime-Life/master/repository.json"
	]
}
EOF
	# cp "$ZERO/Package Control.sublime-settings.template" "$pkconfig"
	echo "install $pkconfig" >&2
elif ! cat "$pkconfig" | grep "RansTool (ranlempow)" >/dev/null; then
	# if sed -e 's/"installed_packages":\n\t\[/"installed_packages":\n\t\[\n\t\t"RansTool (ranlempow)",\n/' "$pkconfig" > "${TMPDIR:-/tmp}/Package Control.sublime-settings"; then
	cfg=$(cat "$pkconfig" | tr '\n' '\f')
	if cfg=$(printf %s\\n "$cfg" | sed 's/"installed_packages":\(\r\f\|\r\|\f\)\t\[/"installed_packages":["RansTool (ranlempow)",/'); then
		printf %s\\n "$cfg" | tr '\f' '\n' > "${TMPDIR:-/tmp}/Package Control.sublime-settings"
		echo "mv ${TMPDIR:-/tmp}/Package Control.sublime-settings" >&2
		echo "rewrite $pkconfig" >&2
		mv "${TMPDIR:-/tmp}/Package Control.sublime-settings" "$pkconfig"
	else
		exit 1
	fi
else
	echo "RansTool already installed" >&2
fi

