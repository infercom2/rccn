############################################################################
# 
# Copyright (C) 2014 tele <tele@rhizomatica.org>
#
# Subscription module
# This file is part of RCCN
#
# RCCN is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# RCCN is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero Public License for more details.
#
# You should have received a copy of the GNU Affero Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
############################################################################

# Python3/2 compatibility
# TODO: Remove once python2 support no longer needed.
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import sys
sys.path.append("..")
from config import *

from modules.subscriber  import Subscriber, SubscriberException
from modules.sms import SMS, SMSException

class SubscriptionException(Exception):
    pass

class Subscription:

    def __init__(self, logger):
        self.logger = logger

    def subscription_info(self):
        sub = Subscriber()
        unpaid=self.get_unpaid_subscriptions()
        print('---\n\n')
        for number in unpaid:
            print('PostGres: '+number[0]+':')
            info=sub.print_vty_hlr_info(number)
            if "No subscriber found for extension" in info:
                print('OsmoHLR: '+info)
                print("Checking for 5 digit extension")
                info=sub.print_vty_hlr_info(number[0][-5:])
            print('OsmoHLR: '+ info)
            print('---\n\n')

    def get_unpaid_subscriptions(self):
        # get all subscribers that haven't paid yet
        # Shouldn't we only do this for those who are actually authorised?
        try:
            cur = db_conn.cursor()
            cur.execute('SELECT msisdn FROM subscribers WHERE subscription_status = 0')
            count = cur.rowcount
            if count > 0:
                subscribers_list = cur.fetchall()
                self.logger.info('Found %s subscribers with unpaid subscription to the service' % count)
                db_conn.commit()
                return subscribers_list
            else:
                db_conn.commit()
                self.logger.info('PG_HLR Everyone paid, we are good to go')
        except psycopg2.DatabaseError as e:
            raise SubscriptionException('PG_HLR error getting subscribers subscription_status: %s' % e)


    def update_subscriptions(self, status):
        try:
            cur = db_conn.cursor()
            cur.execute('UPDATE subscribers SET subscription_status=%(status)d' % {'status': status})
            count = cur.rowcount
            if count > 0:
                db_conn.commit()
                return count
            else:
                self.logger.info('PG_HLR No subscribers to update status found')
        except psycopg2.DatabaseError as e:
            raise SubscriptionException('PG_HLR error in updating subscriptions status: %s' % e)

    def deactivate_subscriptions(self, msg):
        try:
            sms = SMS()
            sub = Subscriber()
            cur = db_conn.cursor()
            cur.execute('SELECT msisdn FROM subscribers WHERE subscription_status = 0 AND authorized = 1')
            count = cur.rowcount
            if count > 0:
                self.logger.info('Found %d subscribers to be deactivated' % count)
                subscribers_list = cur.fetchall()
                db_conn.commit()
                for mysub in subscribers_list:
                    self.logger.debug('Send SMS that account is deactivated to %s' % mysub[0])
                    sms.send(config['smsc'],mysub[0], msg)
                    # disable subscriber
                    try:
                        sub.authorized(mysub[0], 0)
                    except SubscriberException as e:
                        raise SubscriptionException('PG_HLR error in deactivating subscription: %s' % e)
            else:
                db_conn.commit()
                self.logger.info('No subscribers need to be deactivate')
        except psycopg2.DatabaseError as e:
            raise SubscriptionException('PG_HLR error in checking subscriptions to deactivate: %s' % e)


    def send_subscription_fee_notice(self, msg):
        # get all subscribers
        try:
            sub = Subscriber()
            subscribers_list = sub.get_all()
        except SubscriberException as e:
            raise SubscriptionException('%s' % e)

        sms = SMS()

        for mysub in subscribers_list:
            self.logger.debug("Send sms to %s %s" % (mysub[1], msg))
            sms.send(config['smsc'],mysub[1], msg)

    def send_subscription_fee_reminder(self, msg):
        try:
            subscribers_list = self.get_unpaid_subscriptions()
        except SubscriptionException as e:
            raise SubscribtionException('ERROR in getting unpaid subscriptions')

        sms = SMS()
        sub = Subscriber()
        
        for mysub in subscribers_list:
            package = sub.get_package(mysub[0])
            self.logger.debug("Send sms to %s %s" % (mysub[0], msg))
            sms.send(config['smsc'],mysub[0], msg)
            if package > 0:
                self.logger.info("Deactivate Package for %s", mysub[0])
                sub.reset_package(mysub[0])
                sms.send(config['smsc'],mysub[0], "Su paquete ha sido desactivado.")
