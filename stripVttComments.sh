#!/bin/bash
TTX_PATH="sources/vtt_data/CascadiaCode.ttx"
if ! sed -e '/\* VTT 6\./d' < "$TTX_PATH" > "$TTX_PATH.$$"; then
    printf "failed; not replacing ttx source\n" >&2
    exit 1
fi
printf "done.\n" >&2
mv "$TTX_PATH.$$" "$TTX_PATH"
