#!/bin/zsh
# Spike S14, second run (#166): the scripted sign-in and the headless read started by launchd, with
# the screen locked and nobody at the Mac. Read only, local only, one shot.
#
#   spikes/s14_launchd.sh install HH:MM   the family installs a LaunchAgent that fires once at HH:MM
#   spikes/s14_launchd.sh uninstall       removes it (do it after the run)
#   spikes/s14_launchd.sh run             what launchd calls: signin on a fresh profile, then read
#
# Claude wrote this; the family installs it (constitution III: Claude never starts the real sign-in).
# The log keeps instants and states only; see s14_scripted_signin.py for what the sign-in logs.
set -u

LABEL="io.alfabeta.spike-s14"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
HERE="${0:A:h}"
REPO="${HERE:h}"
OUT="$HOME/.alfabeta/${S14_STUDENT:-s1}/data/spike-166"
LOG="$OUT/s14.log"

note() { mkdir -p -m 700 "$OUT"; print -r -- "$(date +%Y-%m-%dT%H:%M:%S)	$*" | tee -a "$LOG"; }

screen_state() {
  # CGSSessionScreenIsLocked is present in the console session only while the screen is locked.
  if ioreg -n Root -d1 | grep -q CGSSessionScreenIsLocked; then print locked; else print unlocked; fi
}

case "${1:-}" in
  install)
    [[ "${2:-}" == <->:<-> ]] || { print -u2 "usage: $0 install HH:MM"; exit 2; }
    hour=$((10#${2%%:*})); minute=$((10#${2##*:}))
    uv_path="$(command -v uv)" || { print -u2 "uv not found"; exit 2; }
    mkdir -p "$HOME/Library/LaunchAgents"
    cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key><array><string>/bin/zsh</string><string>${HERE}/s14_launchd.sh</string><string>run</string></array>
  <key>EnvironmentVariables</key><dict><key>PATH</key><string>${uv_path:h}:/usr/bin:/bin:/usr/sbin:/sbin</string></dict>
  <key>StartCalendarInterval</key><dict><key>Hour</key><integer>$hour</integer><key>Minute</key><integer>$minute</integer></dict>
  <key>StandardOutPath</key><string>$OUT/s14-launchd.out</string>
  <key>StandardErrorPath</key><string>$OUT/s14-launchd.out</string>
</dict></plist>
EOF
    mkdir -p -m 700 "$OUT"
    launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null
    launchctl bootstrap "gui/$(id -u)" "$PLIST" && note "LAUNCHD_INSTALLED	at=$(printf %02d:%02d $hour $minute)"
    ;;
  uninstall)
    launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null
    rm -f "$PLIST" && note "LAUNCHD_REMOVED"
    ;;
  run)
    cd "$REPO" || exit 1
    note "LAUNCHD_RUN	screen=$(screen_state)	claude_app=$(pgrep -q "Claude Helper" && print open || print closed)"
    # A profile of its own for this run, so the sign-in really runs instead of reusing this morning's session.
    export S14_PROFILE="classroom-profile-s14-launchd-$(date +%Y%m%d-%H%M)"
    caffeinate -i uv run -q --with playwright==1.64.1 python spikes/s14_scripted_signin.py signin
    signin=$?
    read_exit=-
    if (( signin == 0 )); then
      caffeinate -i uv run -q --with playwright==1.64.1 python spikes/s14_scripted_signin.py read
      read_exit=$?
    fi
    note "LAUNCHD_END	screen=$(screen_state)	signin_exit=$signin	read_exit=$read_exit"
    ;;
  *)
    print -u2 "usage: $0 install HH:MM | uninstall | run"; exit 2;;
esac
