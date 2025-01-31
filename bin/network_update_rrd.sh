#!/bin/bash

. /etc/profile.d/rccn-functions.sh

RHIZO_DIR="/var/rhizomatica/rrd"

channels=`echo "show network" | nc -q1 localhost 4242 | awk 'BEGIN {tch=0;sdcch=0;su=0;st=0} /TCH\/(H|F):/ {tch=$2}; /SDCCH/ {gsub("\\\(|\\\)", "", $3) split($3, a, "\\\/"); su+=a[1]; st+=a[2]; sdcch = (st>0) ? (su/st)*100 : 0;}; {sub(/%/,"",tch);}; END { print tch":"sdcch }'`
rrdtool update $RHIZO_DIR/bsc_channels.rrd N:$channels

broken=`echo "show lchan" | nc -q1 localhost 4242 | grep BROKEN | wc -l`
rrdtool update $RHIZO_DIR/broken.rrd N:$broken

calls=`fs_cli --timeout=5000 --connect-timeout=5000 -x 'show calls count' | grep total | awk '{print $1}'`
rrdtool update $RHIZO_DIR/fs_calls.rrd N:$calls

if [ "$OSMO_STACK" == "split" ] ;then
  count=`echo "show rate-counters" | nc -q1 localhost 4242 | \
    awk 'BEGIN {cr=0;crn=0} /chreq:total/ {cr=$2} /chreq:no_channel:/ {crn=$2} /chreq:max_delay_exceeded/ {exit} END {print cr":"crn":"}'`
  stats=`echo "show statistics" | nc -q1 localhost 4254 | \
    awk 'BEGIN {lur=0;lurr=0;sms_mo=0;sms_mt=0;moc=0;moca=0;mtc=0;mtca=0}; \
    /Location Updat.* Res/ {lur=$4;lurr=$6} \
    /SMS MO/ {sms_mo=$4}; \
    /SMS MT/ {sms_mt=$4} \
    /MO Calls/ {moc=$4;moca=$6}; \
    /MT Calls/ {mtc=$4;mtca=$6} \
    END {print lur":"lurr":"sms_mo":"sms_mt":"moc":"moca":"mtc":"mtca}'`
else
  count=""
  stats=`echo "show statistics" | nc -q1 localhost 4242 | awk 'BEGIN {cr=0;crn=0;lur=0;lurr=0;sms_mo=0;sms_mt=0;moc=0;moca=0;mtc=0;mtca=0}; /Channel Requests/ {cr=$4;crn=$6} /Location Updat.* Res/ {lur=$4;lurr=$6} /SMS MO/ {sms_mo=$4}; /SMS MT/ {sms_mt=$4} /MO Calls/ {moc=$4;moca=$6}; /MT Calls/ {mtc=$4;mtca=$6} END {print cr":"crn":"lur":"lurr":"sms_mo":"sms_mt":"moc":"moca":"mtc":"mtca}' `

fi
rrdtool update $RHIZO_DIR/stats.rrd N:$count$stats

if [ "$OSMO_STACK" == "nitb" ] ;then
  online_reg_subs=`echo "select count(*) from Subscriber where length(extension) = 11 and lac>0;" | sqlite3 -init <(echo .timeout 1000) /var/lib/osmocom/hlr.sqlite3`
  online_noreg_subs=`echo "select count(*) from Subscriber where length(extension) = 5 and lac>0;" | sqlite3 -init <(echo .timeout 1000) /var/lib/osmocom/hlr.sqlite3`
fi
if [ "$OSMO_STACK" == "split" ] ;then
  # osmo-msc is lacking any simple subscriber count. Do this for the time being:
  online_reg_subs=`echo "SELECT count(last_lu_seen) FROM subscriber WHERE nam_cs = 1 AND last_lu_seen \
                        IS NOT NULL and last_lu_seen > datetime('now', '-1 hour');" \
                        | sqlite3 -init <(echo .timeout 1000) /var/lib/osmocom/hlr.db`
  online_noreg_subs=`echo "SELECT count(last_lu_seen) FROM subscriber WHERE nam_cs = 0 AND last_lu_seen \
                        IS NOT NULL and last_lu_seen > datetime('now', '-1 hour');" \
                        | sqlite3 -init <(echo .timeout 1000) /var/lib/osmocom/hlr.db`
fi

[ -z $online_reg_subs  ] && online_reg_subs=0
[ -z $online_noreg_subs  ] && online_noreg_subs=0

rrdtool update $RHIZO_DIR/hlr.rrd N:$online_reg_subs:$online_noreg_subs

$RHIZO_DIR/../bin/network_graph_rrd.sh > /dev/null
