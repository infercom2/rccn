#!/bin/bash

. /etc/profile.d/rccn-functions.sh

RHIZO_DIR="/var/rhizomatica/rrd"

for default in 0 1 2 3 4 5 ; do
  eval _channels_$default=0:0
done

mybts=`echo "show bts" | nc -q1 localhost 4242 | grep ^BTS | awk '{ print $2 }'`
echo $mybts > $RHIZO_DIR/mybts

trx=0
tries=0
# For some reason, it can fail, if 0, try a few times to avoid false negative.
while [ $trx -eq 0 ] || [ $tries -gt 3 ] ; do
	trx=`echo "show trx" | nc -q1 0 4242 | egrep '( |Carrier) NM State.*OK' | wc -l`
	((tries=tries+1))
done

echo $trx > /tmp/trxOK

ns=`ns | wc -l`
echo $ns > /tmp/gprs_ns

pdp=`pdpc`
echo $pdp > /tmp/pdp_contexts
rrdtool update $RHIZO_DIR/pdp_contexts.rrd N:$pdp

mmc=`mmc`
echo $mmc > /tmp/mm_contexts
rrdtool update $RHIZO_DIR/mm_contexts.rrd N:$mmc

for bts in $mybts ; do
  if [ "$OSMO_STACK" == "split" ] ;then

    _bts_vty=`echo "show bts $bts" | nc -q1 localhost 4242 | grep 'Number.*channels used'`
    eval _channels_$bts=`echo -e "$_bts_vty" | \
     awk 'BEGIN { tchF=0; tchH=0; tchD=0; sdcch4=0; sdcch8=0; } \
     /TCH\/F channels used/ {tchF=$6}; \
     /TCH\/H channels used/ {tchH=$6}; \
     /TCH\/F_TCH\/H_PDCH channels used/ {tchD=$6}; \
     /SDCCH4 channels used/ {sdcch4=$6}; \
     /SDCCH8 channels used/ {sdcch8=$6}; \
     END { print tchF+tchH+tchD":"sdcch4+sdcch8 }'`

  else

    eval _channels_$bts=`echo "show bts $bts" | nc -q1 localhost 4242 |\
     awk 'BEGIN {tch=0;sdcch=0} /TCH\// {gsub("\\\(|\\\)","",$3) split($3,a,"\\\/"); tch=a[1]}; /SDCCH/ { gsub("\\\(|\\\)","",$3) split($3,a,"\\\/"); sdcch+=a[1] } END {print tch":"sdcch}'`

  fi
done
rrdtool update $RHIZO_DIR/bts_channels60.rrd N:$_channels_0:$_channels_1:$_channels_2:$_channels_3:$_channels_4:$_channels_5

