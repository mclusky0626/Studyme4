#!/bin/zsh

cd "${0:A:h}" || exit 1
exec /usr/bin/env python3 scripts/local_launcher.py run
