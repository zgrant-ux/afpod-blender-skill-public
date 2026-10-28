#!/bin/zsh
# 4K, 20% slower, no-sound variant of the AF Pod package: renders into renders_4k_slow/<piece>/, encodes into out/4K SLOW - NO SOUND/
cd "${0:A:h}/.."
pieces=("$@"); (( $#pieces )) || pieces=(intro trans_drip trans_splat trans_sweep endcard)
for p in $pieces; do
  rm -rf "renders_4k_slow/$p"; mkdir -p renders_4k_slow; s=$(date +%s)
  /Applications/Blender.app/Contents/MacOS/Blender -b -P scripts/afpod_scene.py -- $p "renders_4k_slow/$p" --slow 1.2 --pct 200 --samples 96 > "renders_4k_slow/$p.log" 2>&1
  echo "$p: $(find renders_4k_slow/$p -name 'f_*.png' | wc -l | tr -d ' ') frames in $(( $(date +%s) - s ))s"
done
python3 scripts/encode.py --src renders_4k_slow --out "out/4K SLOW - NO SOUND" --tag "4K SLOW" --nosound $pieces 2>&1 | grep -v Fontconfig
python3 scripts/encode.py --src renders_4k_slow --out "out/1080 SLOW - NO SOUND" --tag "1080 SLOW" --nosound --size 1920x1080 $pieces 2>&1 | grep -v Fontconfig
