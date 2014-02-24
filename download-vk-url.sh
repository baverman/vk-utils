#!/bin/sh
exec vk-get-video -e "aria2c --stream-piece-selector=geom -x 5 -c -o {fname} {url}" "$(xsel -b)"
