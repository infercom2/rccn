import sys, os, logging, time, re, glob, importlib
import psycopg2
import psycopg2.extras
import sqlite3
import json
import riak
import unidecode
import socket
import time
import datetime
import urllib, urllib2
from unidecode import unidecode
from riak.transports.pbc.transport import RiakPbcTransport
from logging import handlers as loghandlers
from decimal import Decimal
from datetime import date
from config_values import *

class PGEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, date):
            return str(obj)
        if isinstance(obj, Decimal):
            return str(obj)
        return json.JSONEncoder.default(self, obj)

RIAK_TIMEOUT = 7000

# Loggers
mode = 'a'
maxBytes = 104857600
backupCount = 5
formatter = logging.Formatter('%(asctime)s => %(name)-7s: %(levelname)-8s [%(module)s.%(funcName)s:%(lineno)d] %(message)s')

smlog = loghandlers.RotatingFileHandler(rhizomatica_dir+'/rccn/log/rccn.log', mode, maxBytes, backupCount)
smlog.setFormatter(formatter)

blog = loghandlers.RotatingFileHandler(rhizomatica_dir+'/rccn/log/billing.log', mode, maxBytes, backupCount)
blog.setFormatter(formatter)

alog = loghandlers.RotatingFileHandler(rhizomatica_dir+'/rccn/log/rapi.log', mode, maxBytes, backupCount)
alog.setFormatter(formatter)

slog = loghandlers.RotatingFileHandler(rhizomatica_dir+'/rccn/log/subscription.log', mode, maxBytes, backupCount)
slog.setFormatter(formatter)

smslog = loghandlers.RotatingFileHandler(rhizomatica_dir+'/rccn/log/sms.log', mode, maxBytes, backupCount)
smslog.setFormatter(formatter)

rlog = loghandlers.RotatingFileHandler(rhizomatica_dir+'/rccn/log/reseller.log', mode, maxBytes, backupCount)
rlog.setFormatter(formatter)

roaminglog = loghandlers.RotatingFileHandler(rhizomatica_dir+'/rccn/log/roaming.log', mode, maxBytes, backupCount)
roaminglog.setFormatter(formatter)

purgerlog = loghandlers.RotatingFileHandler(rhizomatica_dir+'/rccn/log/purger.log', mode, maxBytes, backupCount)
purgerlog.setFormatter(formatter)

hlrsynclog = loghandlers.RotatingFileHandler(rhizomatica_dir+'/rccn/log/hlr_sync.log', mode, maxBytes, backupCount)
hlrsynclog.setFormatter(formatter)

logging.basicConfig()

if not 'default_log_level' in locals():
    default_log_level=logging.INFO

#CRITICAL 50
#ERROR    40
#WARNING  30
#INFO     20
#DEBUG    10
#NOTSET   0

# initialize logger RCCN
log = logging.getLogger('RCCN')
log.addHandler(smlog)
log.setLevel(default_log_level)

# initialize logger BILLING
bill_log = logging.getLogger('RCCN_BILLING')
bill_log.addHandler(blog)
bill_log.setLevel(default_log_level)

# initialize logger API
api_log = logging.getLogger('RCCN_API')
api_log.addHandler(alog)
api_log.setLevel(default_log_level)

# initialize logger RSC
subscription_log = logging.getLogger('RCCN_RSC')
subscription_log.addHandler(slog)
subscription_log.setLevel(default_log_level)

# initialize logger SMS
sms_log = logging.getLogger('RCCN_SMS')
sms_log.addHandler(smslog)
sms_log.setLevel(default_log_level)

# initialize logger RESELLER
res_log = logging.getLogger('RCCN_RESELLER')
res_log.addHandler(rlog)
res_log.setLevel(default_log_level)

# initialize logger ROAMING
roaming_log = logging.getLogger('RCCN_ROAMING')
roaming_log.addHandler(roaminglog)
roaming_log.setLevel(default_log_level)

# initialize logger PURGER
purger_log = logging.getLogger('RCCN_PURGER')
purger_log.addHandler(roaminglog)
purger_log.setLevel(default_log_level)

# initialize logger HLR SYNC
hlrsync_log = logging.getLogger('RCCN_HLRSYNC')
hlrsync_log.addHandler(hlrsynclog)
hlrsync_log.setLevel(default_log_level)


class NoDataException(Exception):
    pass

# Extensions
class ExtensionException(Exception):
    pass
class ExtensionExceptionOK(Exception):
    pass

extensions_list = []
os.chdir(rhizomatica_dir+'/rccn/extensions/')
files = glob.glob(rhizomatica_dir+'/rccn/extensions/ext_*.py')
for f in files:
    file_name = f.rpartition('.')[0]
    ext_name = file_name.split('_')[1]
    extensions_list.append(ext_name)

# With this code revision, the db MUST be at revision 14, regardless of what config_values might have.
db_revision = '14'

# initialize DB handler
db_conn = None
config = {}
try:
    db_conn = psycopg2.connect(database=pgsql_db, user=pgsql_user, password=pgsql_pwd, host=pgsql_host)
    cur = db_conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("SELECT value from meta WHERE key='db_revision'")
    PG_revision=cur.fetchone()
    db_conn.commit()
    if 'argv' in dir(sys):
        log.info("Config is loaded by %s", os.path.basename(sys.argv[0]))
        if os.path.basename(sys.argv[0]) == 'rapi.py' and PG_revision[0] != db_revision:
            try:
                log.info("Upgrading DB Revision to Version %s" % db_revision)
                revision_dir=rhizomatica_dir + '/db/migration/'
                current=int(PG_revision[0])
                revisions=os.listdir(revision_dir)
                while current < int(db_revision):
                    current = current + 1
                    filename = [fn for fn in revisions if int(fn[:3]) == current]
                    if len(filename) and os.path.isfile(revision_dir + filename[0]):
                        cur.execute(open(revision_dir + filename[0], 'r').read())
                    else:
                        log.warning("Could not find Database Migration File")
            except (psycopg2.DatabaseError, OSError) as e:
                log.warning("Failed to Upgrade Database Revision! (%s)" % e)
    cur.execute('SELECT * FROM site')
    site_conf = cur.fetchone()
    config['site_name'] = site_conf['site_name']
    config['internal_prefix'] = site_conf['postcode']+site_conf['pbxcode']
    config['local_ip'] = site_conf['ip_address']

    # load SMS shortcode into global config
    cur.execute('SELECT smsc_shortcode,sms_sender_unauthorized,sms_destination_unauthorized FROM configuration')
    smsc = cur.fetchone()
    db_conn.commit()
    config['smsc'] = smsc[0]
    config['sms_source_unauthorized'] = smsc[1]
    config['sms_destination_unauthorized'] = smsc[2]
except psycopg2.DatabaseError as e:
    log.error('Database connection error %s' % e)
    sys.exit(-1)

# Connect to riak
#riak_client = riak.RiakClient(protocol='http', host='127.0.0.1', http_port=8098)
# use protocol buffers
try:
    riak_client = riak.RiakClient(host=riak_ip_address, pb_port=8087, protocol='pbc', RETRY_COUNT=1)
except socket.error(111, 'Connection refused'):
    log.error('RK_HLR error: unable to connect')

# load modules
from modules import subscriber
Subscriber = subscriber.Subscriber
SubscriberException = subscriber.SubscriberException

from modules import numbering
Numbering = numbering.Numbering
NumberingException = numbering.NumberingException

from modules import billing
Billing = billing.Billing

from modules import credit
Credit = credit.Credit
CreditException = credit.CreditException

from modules import configuration
Configuration = configuration.Configuration
ConfigurationException = configuration.ConfigurationException

from modules import statistics
CallsStatistics = statistics.CallsStatistics
CostsStatistics = statistics.CostsStatistics
LiveStatistics = statistics.LiveStatistics
StatisticException = statistics.StatisticException

from modules import sms
SMS = sms.SMS
SMSException = sms.SMSException

from modules import subscription
Subscription = subscription.Subscription
SubscriptionException = subscription.SubscriptionException

from modules import reseller
Reseller = reseller.Reseller
ResellerException = reseller.ResellerException
