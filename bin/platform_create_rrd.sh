#!/bin/bash

RHIZO_DIR="/var/rhizomatica/rrd"

. /home/rhizomatica/bin/vars.sh

if [ ! -f $RHIZO_DIR/loadaverage.rrd ]; then
rrdtool create $RHIZO_DIR/loadaverage.rrd --step 300 \
DS:load1:GAUGE:600:0:U \
DS:load5:GAUGE:600:0:U \
DS:load15:GAUGE:600:0:U \
RRA:AVERAGE:0.5:1:10080 \
RRA:MIN:0.5:1440:1 \
RRA:MAX:0.5:1440:1 \
RRA:MIN:0.5:10080:1 \
RRA:MAX:0.5:10080:1 
fi

if [ ! -f $RHIZO_DIR/cpu.rrd ]; then
rrdtool create $RHIZO_DIR/cpu.rrd --step 300 \
DS:user:DERIVE:600:U:U \
DS:nice:DERIVE:600:U:U \
DS:sys:DERIVE:600:U:U \
DS:idle:DERIVE:600:U:U \
RRA:AVERAGE:0.5:1:576 \
RRA:AVERAGE:0.5:6:672 \
RRA:AVERAGE:0.5:24:732 \
RRA:AVERAGE:0.5:144:1460
fi

if [ ! -f $RHIZO_DIR/temperature.rrd ]; then
rrdtool create $RHIZO_DIR/temperature.rrd --step 300 \
DS:temp:GAUGE:600:0:U \
RRA:MAX:0.5:1:10080
fi

for bts_m in "${!BTS_MASTER[@]}" ; do
  if [ ! -f $RHIZO_DIR/bts-$bts_m.rrd ]; then
    rrdtool create $RHIZO_DIR/bts-$bts_m.rrd --step 300 \
    'DS:amps:GAUGE:600:0:U' \
    'RRA:AVERAGE:0.5:1:288' \
    'RRA:MIN:0.5:1:8928' \
    'RRA:MAX:0.5:1:8928'
  fi
done

if [ ! -f $RHIZO_DIR/voltage.rrd ]; then
rrdtool create $RHIZO_DIR/voltage.rrd --step 300 \
'DS:voltage:GAUGE:600:0:U' \
'RRA:AVERAGE:0.5:1:288' \
'RRA:MIN:0.5:1:8928' \
'RRA:MAX:0.5:1:8928'
fi

if [ ! -f $RHIZO_DIR/latency.rrd ]; then
rrdtool create $RHIZO_DIR/latency.rrd --step 300 \
'DS:latency:GAUGE:600:0:U' \
'RRA:AVERAGE:0.5:1:2016' \
'RRA:MIN:0.5:1:8928' \
'RRA:MAX:0.5:1:8928'
fi

if [ ! -f $RHIZO_DIR/vpnlatency.rrd ]; then
rrdtool create $RHIZO_DIR/vpnlatency.rrd --step 300 \
'DS:vpnlatency:GAUGE:600:0:U' \
'RRA:AVERAGE:0.5:1:2016' \
'RRA:MIN:0.5:1:8928' \
'RRA:MAX:0.5:1:8928'
fi

if [ ! -f $RHIZO_DIR/memory.rrd ]; then
rrdtool create $RHIZO_DIR/memory.rrd --step 300 \
DS:cached:GAUGE:600:U:U \
DS:buffer:GAUGE:600:U:U \
DS:free:GAUGE:600:U:U \
DS:total:GAUGE:600:U:U \
DS:swapt:GAUGE:600:U:U \
DS:swapf:GAUGE:600:U:U \
RRA:AVERAGE:0.5:1:576 \
RRA:AVERAGE:0.5:6:672 \
RRA:AVERAGE:0.5:24:732 \
RRA:AVERAGE:0.5:144:1460
fi

if [ ! -f $RHIZO_DIR/disk.rrd ]; then
rrdtool create $RHIZO_DIR/disk.rrd --step 300 \
DS:sizetot:GAUGE:600:0:U \
DS:sizeused:GAUGE:600:0:U \
RRA:AVERAGE:0.5:1:103740 \
RRA:MIN:0.5:12:2400 \
RRA:MAX:0.5:12:2400 \
RRA:AVERAGE:0.5:12:2400
fi

if [ ! -f $RHIZO_DIR/eth0.rrd ]; then
rrdtool create $RHIZO_DIR/eth0.rrd --step 300 \
DS:RX_bytes:COUNTER:600:0:U \
DS:RX_packets:COUNTER:600:0:U \
DS:RX_errors:COUNTER:600:0:U \
DS:RX_drops:COUNTER:600:0:U \
DS:RX_frame:COUNTER:600:0:U \
DS:TX_bytes:COUNTER:600:0:U \
DS:TX_packets:COUNTER:600:0:U \
DS:TX_errors:COUNTER:600:0:U \
DS:TX_drops:COUNTER:600:0:U \
DS:TX_carriers:COUNTER:600:0:U \
DS:collisions:COUNTER:600:0:U \
RRA:AVERAGE:0.5:1:1440 \
RRA:AVERAGE:0.5:30:336 \
RRA:AVERAGE:0.5:60:744 \
RRA:AVERAGE:0.5:1440:365 \
RRA:MIN:0.5:1:1440 \
RRA:MIN:0.5:30:336 \
RRA:MIN:0.5:60:744 \
RRA:MIN:0.5:1440:365 \
RRA:MAX:0.5:1:1440 \
RRA:MAX:0.5:30:336 \
RRA:MAX:0.5:60:744 \
RRA:MAX:0.5:1440:365 \
RRA:LAST:0.5:1:1440 \
RRA:LAST:0.5:30:336 \
RRA:LAST:0.5:60:744 \
RRA:LAST:0.5:1440:365
fi
