#!/bin/bash

RHIZO_DIR="/var/rhizomatica/rrd"

if [ ! -f $RHIZO_DIR/mm_contexts.rrd ]; then
rrdtool create $RHIZO_DIR/mm_contexts.rrd --step 60 \
DS:mm_contexts:GAUGE:120:0:U \
RRA:AVERAGE:0.5:1:10080 \
RRA:MIN:0.5:1440:1 \
RRA:MAX:0.5:1440:1 \
RRA:MIN:0.5:10080:1 \
RRA:MAX:0.5:10080:1
fi

if [ ! -f $RHIZO_DIR/pdp_contexts.rrd ]; then
rrdtool create $RHIZO_DIR/pdp_contexts.rrd --step 60 \
DS:pdp_contexts:GAUGE:120:0:U \
RRA:AVERAGE:0.5:1:10080 \
RRA:MIN:0.5:1440:1 \
RRA:MAX:0.5:1440:1 \
RRA:MIN:0.5:10080:1 \
RRA:MAX:0.5:10080:1
fi

if [ ! -f $RHIZO_DIR/bsc_channels.rrd ]; then
rrdtool create $RHIZO_DIR/bsc_channels.rrd --step 300 \
DS:tch:GAUGE:600:0:U \
DS:sdcch:GAUGE:600:0:U \
RRA:AVERAGE:0.5:1:10080 \
RRA:MIN:0.5:1440:1 \
RRA:MAX:0.5:1440:1 \
RRA:MIN:0.5:10080:1 \
RRA:MAX:0.5:10080:1
fi

if [ ! -f $RHIZO_DIR/broken.rrd ]; then
rrdtool create $RHIZO_DIR/broken.rrd --step 300 \
DS:broken:GAUGE:600:0:U \
RRA:AVERAGE:0.5:1:10080 \
RRA:MIN:0.5:1440:1 \
RRA:MAX:0.5:1440:1 \
RRA:MIN:0.5:10080:1 \
RRA:MAX:0.5:10080:1
fi

if [ ! -f $RHIZO_DIR/fs_calls.rrd ]; then
rrdtool create $RHIZO_DIR/fs_calls.rrd --step 300 \
DS:calls:GAUGE:600:0:U \
RRA:AVERAGE:0.5:1:10080 \
RRA:MIN:0.5:1440:1 \
RRA:MAX:0.5:1440:1 \
RRA:MIN:0.5:10080:1 \
RRA:MAX:0.5:10080:1
fi

if [ ! -f $RHIZO_DIR/hlr.rrd ]; then
rrdtool create $RHIZO_DIR/hlr.rrd --step 300 \
DS:online_reg_subs:GAUGE:600:0:U \
DS:online_noreg_subs:GAUGE:600:0:U \
RRA:AVERAGE:0.5:1:10080 \
RRA:MIN:0.5:1440:1 \
RRA:MAX:0.5:1440:1 \
RRA:MIN:0.5:10080:1 \
RRA:MAX:0.5:10080:1
fi

if [ ! -f $RHIZO_DIR/stats.rrd ]; then
rrdtool create $RHIZO_DIR/stats.rrd --step 300 \
DS:cr:COUNTER:600:0:U \
DS:crn:COUNTER:600:0:U \
DS:lur:COUNTER:600:0:U \
DS:lurr:COUNTER:600:0:U \
DS:sms_mo:COUNTER:600:0:U \
DS:sms_mt:COUNTER:600:0:U \
DS:moc:COUNTER:600:0:U \
DS:moca:COUNTER:600:0:U \
DS:mtc:COUNTER:600:0:U \
DS:mtca:COUNTER:600:0:U \
RRA:AVERAGE:0.5:1:2016 \
RRA:AVERAGE:0.5:30:3504
fi

if [ ! -f $RHIZO_DIR/bts_channels60.rrd ]; then
rrdtool create $RHIZO_DIR/bts_channels60.rrd --step 60 \
DS:tch0:GAUGE:120:0:U \
DS:sdcch0:GAUGE:120:0:U \
DS:tch1:GAUGE:120:0:U \
DS:sdcch1:GAUGE:120:0:U \
DS:tch2:GAUGE:120:0:U \
DS:sdcch2:GAUGE:120:0:U \
DS:tch3:GAUGE:120:0:U \
DS:sdcch3:GAUGE:120:0:U \
DS:tch4:GAUGE:120:0:U \
DS:sdcch4:GAUGE:120:0:U \
DS:tch5:GAUGE:120:0:U \
DS:sdcch5:GAUGE:120:0:U \
RRA:AVERAGE:0.5:1:10080 \
RRA:MIN:0.5:1440:1 \
RRA:MAX:0.5:1440:1 \
RRA:MIN:0.5:10080:1 \
RRA:MAX:0.5:10080:1
fi
