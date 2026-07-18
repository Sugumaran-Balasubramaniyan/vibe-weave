#!/usr/bin/env bash
set -euo pipefail

font="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
regular="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
audio="/tmp/vibe-weave-narration.mp3"
output="static/vibe-weave-explainer.mp4"

.venv/bin/edge-tts --voice en-US-AvaMultilingualNeural --rate=+4% --text "Picture a Vibe run with three smart agents moving in parallel. Each one is doing good work, but they are making one different assumption. That is where Vibe Weave steps in. Before code is written, every agent shares a tiny contract: what it will change, what it assumes, and how it will prove success. Weave spots the disagreement and asks one simple question. Who should be allowed to export invoices? Choose admins only, and that answer becomes a shared Decision Contract. Now Vibe can let every agent move quickly, in its own worktree, with one definition of done. The result is not just code that looks right. It is a team of agents that agrees on what right means. Vibe runs the agents. Vibe Weave makes them work as one." --write-media "$audio"

ffmpeg -y -f lavfi -i "color=c=0x171338:s=1280x720:r=30:d=47" -i "$audio" \
  -filter_complex "
    [0:v]
    drawbox=x=0:y=0:w=1280:h=720:color=0x171338:t=fill,
    drawbox=x=60:y=54:w=1160:h=612:color=0x221c52:t=fill:enable='between(t,0,47)',
    drawtext=fontfile=${font}:text='VIBE WEAVE':x=80:y=80:fontsize=32:fontcolor=0xD8FF7F:enable='between(t,0,47)',
    drawtext=fontfile=${font}:text='Parallel agents should agree before they edit.':x=(w-text_w)/2:y=180:fontsize=44:fontcolor=white:enable='between(t,0,9)',
    drawtext=fontfile=${regular}:text='Vibe runs the work.  Weave aligns the meaning.':x=(w-text_w)/2:y=248:fontsize=25:fontcolor=0xC9C6E8:enable='between(t,0,9)',
    drawbox=x=170:y=375:w=230:h=110:color=0x332B75:t=fill:enable='between(t,0,9)',
    drawbox=x=525:y=375:w=230:h=110:color=0x332B75:t=fill:enable='between(t,0,9)',
    drawbox=x=880:y=375:w=230:h=110:color=0x332B75:t=fill:enable='between(t,0,9)',
    drawtext=fontfile=${font}:text='FRONTEND':x=210:y=405:fontsize=22:fontcolor=white:enable='between(t,0,9)',
    drawtext=fontfile=${font}:text='BACKEND':x=575:y=405:fontsize=22:fontcolor=white:enable='between(t,0,9)',
    drawtext=fontfile=${font}:text='TESTS':x=955:y=405:fontsize=22:fontcolor=white:enable='between(t,0,9)',
    drawtext=fontfile=${regular}:text='Change contracts':x=225:y=452:fontsize=19:fontcolor=0xD8FF7F:enable='between(t,0,9)',
    drawtext=fontfile=${font}:text='1. Agents declare their assumptions':x=100:y=170:fontsize=40:fontcolor=white:enable='between(t,9,18)',
    drawtext=fontfile=${regular}:text='Frontend - signed-in users can export':x=160:y=280:fontsize=27:fontcolor=0xFFD0C5:enable='between(t,9,18)',
    drawtext=fontfile=${regular}:text='Backend and tests - admins only':x=160:y=340:fontsize=27:fontcolor=0xD8FF7F:enable='between(t,9,18)',
    drawbox=x=130:y=415:w=1020:h=110:color=0x4A2440:t=fill:enable='between(t,9,18)',
    drawtext=fontfile=${font}:text='CONFLICT - two meanings for the same feature':x=225:y=454:fontsize=28:fontcolor=white:enable='between(t,9,18)',
    drawtext=fontfile=${font}:text='2. Weave asks one useful question':x=100:y=170:fontsize=40:fontcolor=white:enable='between(t,18,30)',
    drawbox=x=165:y=270:w=950:h=175:color=0xF5E8B9:t=fill:enable='between(t,18,30)',
    drawtext=fontfile=${font}:text='Who may export invoices?':x=(w-text_w)/2:y=310:fontsize=38:fontcolor=0x382A00:enable='between(t,18,30)',
    drawtext=fontfile=${regular}:text='Answer - admins only':x=(w-text_w)/2:y=375:fontsize=29:fontcolor=0x5D4300:enable='between(t,18,30)',
    drawtext=fontfile=${font}:text='3. One decision. Three aligned agents.':x=100:y=170:fontsize=40:fontcolor=white:enable='between(t,30,47)',
    drawbox=x=160:y=280:w=960:h=86:color=0x245B3C:t=fill:enable='between(t,30,47)',
    drawtext=fontfile=${font}:text='DECISION CONTRACT - authorization = admin_only':x=205:y=310:fontsize=27:fontcolor=white:enable='between(t,30,47)',
    drawtext=fontfile=${regular}:text='separate worktrees  ->  shared proofs  ->  safe result':x=(w-text_w)/2:y=450:fontsize=30:fontcolor=0xD8FF7F:enable='between(t,30,47)',
    drawtext=fontfile=${font}:text='Vibe runs agents. Weave makes them agree.':x=(w-text_w)/2:y=545:fontsize=31:fontcolor=white:enable='between(t,30,47)'
    [v]" -map "[v]" -map 1:a -c:v libx264 -pix_fmt yuv420p -c:a aac -b:a 128k -shortest "$output"

rm -f "$audio"
