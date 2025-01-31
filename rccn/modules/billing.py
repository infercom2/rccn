############################################################################
#
# Copyright (C) 2013 tele <tele@rhizomatica.org>
#
# Billing module
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

import sys, re
import math
sys.path.append("..")
from config import *
from modules.subscriber import Subscriber, SubscriberException
from modules.configuration import Configuration, ConfigurationException

class BillingException(Exception):
    pass

class Billing:
    """ Rating/Billing """
 
    def get_matching_prefix(self, arr_prefixes, num):
        """ Get matching prefix

        :param arr_prefixes: Array containing list of prefixes
        :param num: Phone number
        """
        for idx, val in enumerate(arr_prefixes):
            if num.startswith(val):
                return (val, idx)
        return False

    def get_call_duration(self, balance, cost):
        """ Calculate call duration

        :param balance: Current balance
        :param cost: Cost
        """
        call_min = Decimal(balance) / Decimal(cost)
        total_call_sec = int((call_min * 60))
        return total_call_sec

    def get_call_cost(self, duration, cost):
        if duration == 0:
            return Decimal(0)
        call_duration_min = Decimal(duration) / 60
        final_call_duration = 1 if call_duration_min == 0 else math.ceil(call_duration_min)
        call_cost = Decimal(str(final_call_duration)) * Decimal(str(cost))
        return Decimal(call_cost).quantize(Decimal('0.01'))
        
    def get_rate(self, destination_number):
        # DIRTY: identify which logger to use
        # FIXME: Make this more readable and implement valid number prefix lookup.

        frame = sys._getframe(2)
        
        if frame.f_code.co_name == 'fsapi':
            logz = bill_log
        else:
            logz = log
        
        dest = ""
        # check for 00 or + and strip it from the number
        if destination_number[0] == '+':
            dest = destination_number[1:]
        if re.search(r'^00', destination_number) != None:
            dest = destination_number[2:]
        if dest == "":
            dest = destination_number

        # get prefix
        dd = dest[0:1]

        cur = db_conn.cursor()
        cur.execute("SELECT * FROM rates WHERE prefix = %(prefix)s OR prefix LIKE %(prefix2)s", {'prefix': dd, 'prefix2': dd+'%'})
        rates = cur.fetchall()

        logz.info('Prefix to check: %s' % dd)

        if rates == None:
            logz.error('Could not find a valid destination')
        else:
            prefixes = []
            real_rate_index = 0
            real_rate_prefix = []
            for rate in rates:
                prefixes.append(rate[2].strip())
                real_rate_prefix.append({real_rate_index: rate[2].strip()})
                real_rate_index += 1
            prefixes.sort(key=len, reverse=True)
            myprefix = self.get_matching_prefix(prefixes, dest)
            if myprefix:
                logz.info('Found matching prefix %s for destination %s' % (myprefix[0], dest))
            else:
                logz.info('Could not find matching prefix for destination %s', dest)
                return ('0','Unknown','000', Decimal('20'))

            final_idx = 0
            for entry in real_rate_prefix:
                if myprefix[0] in entry.values():
                    final_idx = entry.keys()[0]
            myrate = rates[final_idx]
            logz.info('Destination %s as a rate of %.2f pesos per minute' % (myrate[1], myrate[3]))
            return myrate


    def bill(self, session, subscriber, destination_number, context, duration):
        if context == 'LOCAL':
            bill_log.info('===========================================================================')
            bill_log.info('LOCAL Context')
            bleg_connected = session.getVariable('bleg_uuid')
            hangup_cause = session.getVariable('hangup_cause')
            #subscriber = session.getVariable('bleg_destination_number')
            #print session.getVariable('bleg_billsec')

            configuration = Configuration()
            try:
                _charge_local = configuration.check_charge_local_calls()
                if _charge_local == 1:
                    _charge = configuration.get_charge_local_calls()
                    if duration > int(_charge[1]):
                        call_cost = _charge[0]
                    else:
                        call_cost = 0
                else:
                    return
            except:
                bill_log.error('Error reading local calls charge config.')
                return

            # set destination_name and cost for the CDR
            session.setVariable('destination_name', 'Local')
            session.setVariable('cost', str(call_cost))
            bill_log.info('Call duration: %d sec Call cost: %.2f' % (duration, call_cost))

            if call_cost > Decimal('0.00'):
                sub = Subscriber()
                try:
                    previous_balance = sub.get_balance(subscriber)
                    current_balance = previous_balance - call_cost
                    real_balance = 0 if current_balance < 0 else current_balance
                    bill_log.info('Previous balance: %.2f Current Balance: %.2f' % (previous_balance, real_balance))
                    sub.set_balance(subscriber, real_balance)
                    bill_log.info('Billing %s completed successfully' % subscriber)
                except SubscriberException as e:
                    bill_log.error('Error during billing the subscriber: %s' % e)
            else:
                bill_log.info('Call too short to Bill')

        if context == 'OUTBOUND':
            bill_log.info('===========================================================================')
            bill_log.info('OUTBOUND Context Bill subscriber %s destination %s' % (subscriber, destination_number))

            sub = Subscriber()
            # get rate
            rate = self.get_rate(destination_number)
            log_dest = rate[1]
            package = sub.get_package(subscriber)
            if package == 1 and rate[1] == "Mexico Cellular-Telcel":
                bill_log.info('Subscriber has package, removing 5 mins from call duration of %s seconds', duration)
                log_dest = rate[1] + ' (P)'
                duration = duration - 300
                if duration < 0:
                    duration = 0
            if 'charge_outbound_rate_type' in globals() and charge_outbound_rate_type == 'sec':
                call_cost = Decimal(math.ceil((rate[3]/60)*duration * 100) / 100).quantize(Decimal('0.01'))
            else:
                call_cost = self.get_call_cost(duration, rate[3])

            try:
                previous_balance = sub.get_balance(subscriber)
                current_balance = previous_balance - call_cost
                if current_balance < 0:
                    # There was not enough balance to cover the rounded up minutes
                    real_balance = 0
                    # Log what we ACTUALLY deducted in the CDR
                    call_cost = previous_balance
                else:
                    real_balance = current_balance
                bill_log.info('Previous balance: %.2f Current Balance: %.2f' % (previous_balance, real_balance))
                sub.set_balance(subscriber, real_balance)
                bill_log.info('Billing %s completed successfully' % subscriber)
            except SubscriberException as e:
                bill_log.error('Error during billing the subscriber: %s' % e)

            # set destination_name and cost for the CDR
            session.setVariable('destination_name', log_dest)
            session.setVariable('cost', str(call_cost))
            bill_log.info('Call duration: %d sec Call cost: %.2f' % (duration, call_cost))

        if context == 'INBOUND':
            bill_log.info('===========================================================================')
            bill_log.info('INBOUND Context')
            bleg_connected = session.getVariable('bleg_uuid')
            hangup_cause = session.getVariable('hangup_cause')
            subscriber = session.getVariable('bleg_destination_number')
            #print session.getVariable('bleg_billsec')
            configuration = Configuration()

            if (bleg_connected != '' and bleg_connected != None) and hangup_cause == 'NORMAL_CLEARING':
                bill_log.info('Call B-leg was connected. Bill subscriber %s' % subscriber)
                try:
                    charge_info = configuration.get_charge_inbound_calls()
                    if charge_info[1] == 'call':
                        bill_log.info('Charge type: per call, Cost: %s' % charge_info[0])
                        call_cost = charge_info[0]
                        try:
                            sub = Subscriber()
                            previous_balance = sub.get_balance(subscriber)
                            current_balance = previous_balance - call_cost
                            bill_log.info('Previous balance: %.2f Current Balance: %.2f' % (previous_balance, current_balance))
                            sub.set_balance(subscriber, current_balance)
                            bill_log.info('Billing %s completed successfully' % subscriber)
                        except SubscriberException as e:
                            bill_log.error('Error during billing the subscriber: %s' % e)
                    elif charge_info[1] == 'min':
                        bill_log.info('Charge type rate per min, cost per min: %s' % charge_info[0])
                        # BUG: Cannot get b-leg billsec from FS. Use the billsec of a-leg instead
                        call_cost = self.get_call_cost(duration, charge_info[0])
                        bill_log.info('Call duration %s sec Call cost: %s' % (duration, call_cost))
                        try:
                            sub = Subscriber()
                            previous_balance = sub.get_balance(subscriber)
                            current_balance = previous_balance - call_cost
                            bill_log.info('Previous balance: %.2f Current Balance: %.2f' % (previous_balance, current_balance))
                            sub.set_balance(subscriber, current_balance)
                            bill_log.info('Billing %s completed successfully' % subscriber)
                        except SubscriberException as e:
                            bill_log.error('Error during billing the subscriber: %s' % e)
                except ConfigurationException as e:
                    bill_log.error(e)
            else:
                bill_log.info('Call B-leg was not connected. Not billing subscriber %s' % subscriber)

if __name__ == '__main__':
    bill = Billing()
    print(bill.get_call_cost(139, 0.25))
    #bill.get_rate('0019728390082')
    #bill.get_rate('005219514404014')
