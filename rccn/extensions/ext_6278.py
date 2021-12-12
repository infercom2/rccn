#!/usr/bin/python
############################################################################
#
# Copyright (C) 2021 keith <keith@rhizomatica.org>
#
# Extension 6278 (MASV) that sends broadcast SMS.
#
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
import sys
sys.path.append("..")
from config import *
from smpplib import consts as smpp_c

ME = '6278'

def resp(sender, text):
        sms = SMS()
        sms.send(ME, sender, text)
        del sms

def handler(session, *args):
    log.debug('Handler for ext 6278')
    if session:
        log.debug('Calls to Reseller shortcode rejected')
        return False

    if args[1] != ME:
        return smpp_c.SMPP_ESME_RINVDSTADR

    if 'admin_numbers' not in globals():
        return smpp_c.SMPP_ESME_RINVSRCADR
    if 'admin_pin' not in globals():
        return smpp_c.SMPP_ESME_RINVSRCADR

    # Check to see if the calling number is authorised to do admin functions.
    if args[0] not in admin_numbers:
        sms_log.error('Administration shortcode not allowed from [%s]', args[0])
        return smpp_c.SMPP_ESME_RINVSRCADR

    if args[3]:
        resp(args[0], "MENSAJE DEMASIADO LARGO")
        return smpp_c.SMPP_ESME_RSUBMITFAIL

    sms = SMS()
    # args[2] is already unicode.
    sms.send_broadcast(args[2], ['authorized'], 'all')
    return smpp_c.SMPP_ESME_ROK
