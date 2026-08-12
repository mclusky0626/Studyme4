#!/bin/zsh

cd "${0:A:h}" || exit 1
/usr/bin/env python3 scripts/local_launcher.py configure
status=$?
echo
read "reply?Enter를 누르면 창이 닫혀."
exit $status
