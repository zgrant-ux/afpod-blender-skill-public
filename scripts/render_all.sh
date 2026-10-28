#!/bin/zsh
# Render every piece of the AF Pod YouTube package (full 1080p, transparent PNG sequences) into renders/<piece>/
cd "${0:A:h}/.."
pieces=("$@"); (( $#pieces )) || pieces=(intro trans_drip trans_splat trans_sweep endcard)
for p in $pieces; do
  rm -rf "renders/$p"; s=$(date +%s)
  /Applications/Blender.app/Contents/MacOS/Blender -b -P scripts/afpod_scene.py -- $p "renders/$p" --samples 48 > "renders/$p.log" 2>&1
  n=$(find "renders/$p" -name 'f_*.png' | wc -l | tr -d ' ')
  echo "$p: $n frames in $(( $(date +%s) - s ))s"
done
