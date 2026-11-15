#!/system/bin/sh
# A31 LTE guard v2
# The A31 modem hangs (MD WDT) on LTE and the network drops. This module reacts at the FIRST reset:
# while the modem is still restarting it sets the SIM to 3G/2G only, so the phone comes back on
# 3G+ (HSPA+) instead of hanging again on LTE. No airplane mode, no extra restart.
# LTE is retried later, only when the screen is off (so a retry never interrupts you):
# after 30 min, then 1 h, 2 h, 4 h if it fails again quickly. If LTE then stays up 30 min it resets to 30 min.
# Controls (create the file to use):
#   /data/local/tmp/lte_guard.off      pause the guard (restores LTE, stays paused until you delete it)
#   /data/local/tmp/lte_guard.lte_now  try LTE right now (the file is removed automatically)
# Log: /data/local/tmp/a31_lte_guard.log

LOG=/data/local/tmp/a31_lte_guard.log
D=/data/local/tmp/lte_guard
OFF=/data/local/tmp/lte_guard.off
NOW=/data/local/tmp/lte_guard.lte_now
STAY=/data/local/tmp/lte_guard.stay3g   # permanent 3G+: LTE is never retried (delete the file + touch lte_now to go back)
AUTO=1001101001110000111   # GSM/WCDMA/LTE(+CA): the normal "auto" set
G3=1100001110000111        # GSM/WCDMA only (no LTE)
GRACE=25                   # ignore resets this soon after our own mode switch
mkdir -p $D

note() {
  echo "$(date '+%m-%d %H:%M:%S') $*" >> $LOG
  if [ "$(wc -c < $LOG 2>/dev/null)" -gt 100000 ]; then tail -n 300 $LOG > $LOG.t && mv $LOG.t $LOG; fi
}
now() { date +%s; }
rd() { v=$(cat $D/$1 2>/dev/null); echo "${v:-0}"; }
# setmode MASK want   (want = lte | nolte). While the modem restarts the radio refuses the change
# silently, so apply it repeatedly and verify with get-allowed until it really took effect.
setmode() {
  i=0; ok=1
  while [ $i -lt 40 ]; do
    cmd phone set-allowed-network-types-for-users -s 0 "$1" > /dev/null 2>&1
    cur=$(cmd phone get-allowed-network-types-for-users -s 0 2>/dev/null)
    case "$2" in
      nolte) case "$cur" in *LTE*) ;; *GSM*|*UMTS*) ok=0; break ;; esac ;;
      lte)   case "$cur" in *LTE*) ok=0; break ;; esac ;;
    esac
    i=$((i + 1)); sleep 2
  done
  now > $D/lastsw
  return $ok
}
level_secs() {
  case "$1" in
    0) echo 1800 ;;
    1) echo 3600 ;;
    2) echo 7200 ;;
    *) echo 14400 ;;
  esac
}
screen_off() { ! dumpsys power 2>/dev/null | grep -m1 -q 'mWakefulness=Awake'; }
restore_lte() {
  if setmode $AUTO lte; then echo 0 > $D/fb; now > $D/lte_since; note "LTE restored ($1)"
  else note "LTE restore FAILED ($1), will retry"; fi
}

until [ "$(getprop sys.boot_completed)" = "1" ]; do sleep 3; done
sleep 30
note "lte_guard v2 started (fallback_until=$(rd fb))"

# a fallback that expired while the phone was off
if [ "$(rd fb)" != "0" ] && [ "$(now)" -ge "$(rd fb)" ]; then restore_lte "boot, fallback expired"; fi

# timer: restore LTE when allowed; while a fallback is active keep the SIM on 3G/2G
# (a reboot or the system can put LTE back, which would make the phone crash again unprotected)
(
  chk=0
  while true; do
    fb=$(rd fb)
    if [ "$fb" != "0" ]; then
      n=$(now)
      if [ "$n" -lt "$fb" ] && [ ! -f $OFF ] && [ "$n" -ge "$chk" ]; then
        chk=$((n + 60))
        case "$(cmd phone get-allowed-network-types-for-users -s 0 2>/dev/null)" in
          *LTE*) setmode $G3 nolte && note "3G/2G re-applied (LTE had been put back)" ;;
        esac
      fi
      if [ -f $OFF ]; then rm -f $STAY; restore_lte "guard paused"
      elif [ -f $NOW ]; then rm -f $NOW $STAY; restore_lte "requested"
      elif [ -f $STAY ]; then :   # permanent 3G+: never retry LTE
      elif [ "$n" -ge "$fb" ]; then
        # only retry while the screen is off; if it stays on for hours, retry anyway after 2x the wait
        dur=$(level_secs $(rd level))
        if screen_off || [ "$n" -ge $((fb + dur)) ]; then restore_lte "retry, screen off"; fi
      fi
    fi
    sleep 15
  done
) &

# watcher: modem reset events from ccci_mdinit
logcat -b main -T 1 -s ccci_mdinit:D 2>/dev/null | while read line; do
  case "$line" in
    *"md status event 12"*)
      [ -f $OFF ] && continue
      n=$(now)
      [ "$n" -lt "$(rd fb)" ] && continue
      [ $((n - $(rd lastsw))) -lt $GRACE ] && continue
      lvl=$(rd level)
      since=$(rd lte_since)
      if [ "$since" -gt 0 ]; then
        up=$((n - since))
        if [ "$up" -ge 1800 ]; then lvl=0; elif [ "$up" -le 900 ] && [ "$lvl" -lt 3 ]; then lvl=$((lvl + 1)); fi
      fi
      secs=$(level_secs $lvl)
      if setmode $G3 nolte; then
        echo $lvl > $D/level
        echo $(( $(now) + secs )) > $D/fb
        note "modem reset -> 3G/2G for ${secs}s (level $lvl)"
      else
        note "modem reset, but could not switch to 3G/2G (radio unavailable)"
      fi
      ;;
  esac
done
