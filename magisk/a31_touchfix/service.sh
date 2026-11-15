#!/system/bin/sh
# A31 (IST40XX) touch watchdog v3 for the One UI GSI port.
# v3 change: "screen is lit" is no longer judged only by the backlight node. On this ROM the
# backlight node can read 0 while the screen is on (minimum brightness / doze), so the v2 watchdog
# never ran its repair. Now: lit = backlight != 0 OR power manager wakefulness == Awake.
# - finds the touchscreen input node by name (index can change)
# - repairs when the screen is lit and the input is disabled
# - repairs when the chip stops answering (get_chip_id != 0x4050), checked right after the
#   screen turns on and every 10 s while it is on (2 consecutive failures needed)
# - logs every action to /data/local/tmp/a31_touchfix.log (+ logcat tag A31touchfix)
B=/sys/class/backlight/panel/brightness
C=/sys/class/sec/tsp/cmd
ST=/sys/class/sec/tsp/cmd_status
RS=/sys/class/sec/tsp/cmd_result
LOG=/data/local/tmp/a31_touchfix.log

note() {
  echo "$(date '+%m-%d %H:%M:%S') $*" >> $LOG
  log -t A31touchfix "$*"
  if [ "$(wc -c < $LOG 2>/dev/null)" -gt 200000 ]; then
    tail -n 400 $LOG > $LOG.tmp && mv $LOG.tmp $LOG
  fi
}

find_node() {
  for d in /sys/class/input/input*; do
    if [ "$(cat $d/name 2>/dev/null)" = "sec_touchscreen" ]; then
      echo $d/enabled
      return
    fi
  done
}

# 0 = screen lit
lit() {
  b=$(cat $B 2>/dev/null)
  if [ -n "$b" ] && [ "$b" != "0" ]; then return 0; fi
  dumpsys power 2>/dev/null | grep -m1 -q 'mWakefulness=Awake'
}

PROBE=""
probe() {
  echo get_chip_id > $C 2>/dev/null
  sleep 0.3
  s=$(cat $ST 2>/dev/null)
  r=$(cat $RS 2>/dev/null)
  PROBE="$s/$r"
  case "$s:$r" in
    OK:*0x4050*) return 0 ;;
  esac
  return 1
}

fix() {
  reason="$1"
  note "FIX ($reason) bright=$(cat $B 2>/dev/null) enabled=$(cat $E 2>/dev/null) probe=$PROBE irq=$(grep -i ist40 /proc/interrupts | head -1 | tr -s ' ' | cut -c1-60)"
  for c in singletap_enable,0 aot_enable,0 spay_enable,0 aod_enable,0; do echo $c > $C; done
  echo 1 > $E; sleep 0.3; echo 0 > $E; sleep 0.3; echo 1 > $E
  sleep 0.5
  if probe; then
    note "fix ok: chip answers ($PROBE)"
  else
    note "fix: chip still NOT answering ($PROBE)"
  fi
  last_fix=$(date +%s)
}

E=$(find_node)
[ -n "$E" ] || E=/sys/class/input/input3/enabled
note "touchfix v3 started, node=$E"
screen_was_on=0
last_probe=0
last_fix=0
while true; do
  if lit; then
    n=$(find_node); [ -n "$n" ] && E=$n
    en=$(cat $E 2>/dev/null)
    now=$(date +%s)
    if [ "$en" = "0" ]; then
      fix "enabled=0 with lit screen"
    elif [ "$screen_was_on" = "0" ] || [ $((now - last_probe)) -ge 10 ]; then
      [ "$screen_was_on" = "0" ] && sleep 1.5
      last_probe=$(date +%s)
      if ! probe; then
        sleep 1
        if ! probe && [ $((last_probe - last_fix)) -ge 20 ]; then
          fix "chip unresponsive"
        fi
      fi
    fi
    screen_was_on=1
  else
    screen_was_on=0
  fi
  sleep 2
done
