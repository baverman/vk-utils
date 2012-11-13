#!/bin/sh
exec vk-get-video -e "aria2c -x 5 -c -o {fname} {url}" "$(xsel -b)"