#!/bin/bash

#                                                                          #
# Note that currently osmo-msc does internal cleaning of the SMS database. #
# So for a split stack we probably do not want to run this script.         #
#                                                                          #

. /etc/profile.d/rccn-functions.sh

LOGFILE="/var/log/sms_cleanup.log"
SMS_DB="/var/lib/osmocom/hlr.sqlite3"
if [ "$OSMO_STACK" == "split" ] ;then
SMS_DB=$OSMO_SMS
fi

SMS_DB_BKP="/home/rhizomatica/sms/hlr_`date '+%d%m%Y'`.sqlite3"

function logc() {
	txt=$1
	echo "[`date '+%d-%m-%Y %H:%M:%S'`] $txt" >> $LOGFILE
}

logc "Run database cleanup. Current DB size: `ls -sh $SMS_DB | awk '{print $1}'`"
logc "Make backup copy of SMS db"
#cp -f $SMS_DB $SMS_DB_BKP

total_sms=`echo 'select count(*) from SMS;' | sqlite3 -init <(echo .timeout 1000) $SMS_DB`
total_sms_delivered=`echo 'select count(*) from SMS where sent is not null;' | sqlite3 -init <(echo .timeout 1000) $SMS_DB`
total_sms_old=`echo "select count(*) from SMS where created < datetime('now', '-4 day');" | sqlite3 -init <(echo .timeout 1000) $SMS_DB`

logc "Total SMS: $total_sms Delivered: $total_sms_delivered SMS older than 4 days: $total_sms_old"
logc "Cleanup DB"

# Delete Any Broadcast SMS to a subscriber that is currently not authorised and also has not been seen for two weeks.
if [ "$OSMO_STACK" == "split" ] ; then
  echo "ATTACH \"/var/lib/osmocom/hlr.db\" as hlr; \
  DELETE from SMS where src_ton=5 and exists (select msisdn,nam_cs,last_lu_seen \
  from hlr.subscriber where msisdn = sms.dest_addr and last_lu_seen < datetime('now', '-14 day') and nam_cs = 0);" | sqlite3 -init <(echo .timeout 1000) $SMS_DB
else
  echo "DELETE from SMS where src_ton=5 and exists (select * from subscriber where subscriber.extension = sms.dest_addr AND subscriber.expire_lu < datetime('now', '-14 day') and subscriber.authorized = 0);" | sqlite3 -init <(echo .timeout 1000) $SMS_DB
fi
# Delete any SMS in the database that was created more than 6 hours ago and has been sent.
echo "DELETE from SMS where created < datetime(\"now\", \"-6 hours\") and sent is not null;" | sqlite3 -init <(echo .timeout 1000) $SMS_DB
# Delete any broadcast message that is not delivered after 7 days.
echo "DELETE from SMS where created < datetime(\"now\", \"-7 day\") and src_ton=5 and sent is null;" | sqlite3 -init <(echo .timeout 1000) $SMS_DB

if [ "$OSMO_STACK" != "split" ] && [[ $(date +%u) == 1 ]]; then
	logc "running extra cleanup tasks"
	# Delete any SMS older than 3 months where the destination subscriber does not exist anymore
	echo "DELETE FROM SMS WHERE id IN
	(SELECT sms.id from sms LEFT OUTER JOIN subscriber
	ON (sms.dest_addr = subscriber.extension)
	WHERE subscriber.extension IS NULL
	AND sms.created < datetime('now', '-3 months'));" | sqlite3 -init <(echo .timeout 1000) $SMS_DB
	# Delete any SMS older than 6 months where the destination subscriber is not authorised.
	echo "DELETE FROM SMS WHERE id IN
	(SELECT sms.id from sms LEFT OUTER JOIN subscriber
	ON (sms.dest_addr = subscriber.extension)
	WHERE subscriber.authorized = 0 AND subscriber.expire_lu < datetime('now', '-6 months')
	AND sms.created < datetime('now', '-6 months'));" | sqlite3 -init <(echo .timeout 1000) $SMS_DB
fi

logc "DB size after cleanup: `ls -sh $SMS_DB | awk '{print $1}'`"
