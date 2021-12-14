#!/usr/bin/python
############################################################################
#
# Copyright (C) 2021 keith <keith@rhizomatica.org>
#
# Extension 7272 (PASA) that transfers credit.
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

ME = '7272'

def resp(sender, text):
        sms = SMS()
        sms.send(ME, sender, text)
        del sms

def handler(session, *args):
    log.debug('Handler for ext 7272')
    if session:
        log.debug('Calls to SMS shortcode rejected')
        return False

    if args[1] != ME:
        return smpp_c.SMPP_ESME_RINVDSTADR

    sub  = Subscriber()
    cred = Credit()

    # Check to see if the calling number is authorised to do admin functions.
    if not sub.is_authorized(args[0], 0):
        sms_log.error('Credit transfer not allowed from [%s]', args[0])
        return smpp_c.SMPP_ESME_RINVSRCADR

    try:
        if not args[2]:
            resp(args[0], "MENSAJE MALFORMADO")
            return smpp_c.SMPP_ESME_ROK
    
        text = args[2]
        log.info('[%s] sent us SMS: <%s>', args[0], text)
        text_data = text.split(' ')
        command = text_data[0].upper()

        if not command == "PASA":
            resp(args[0], "MENSAJE MALFORMADO")
            return smpp_c.SMPP_ESME_ROK

        amount      = text_data[1]
        destination = text_data[2]

    except IndexError:
        resp(args[0], "ERROR")
        return smpp_c.SMPP_ESME_ROK

    try:
        ret = cred.transfer(args[0], destination, int(amount))
        if not ret:
            resp(args[0], "No se pudo pasar $%s a %s" % (amount, destination))
            return smpp_c.SMPP_ESME_ROK
        resp(args[0], "Se ha pasado $%s a %s" % (amount, destination))
        resp(destination, "Ud ha recibido $%s de %s" % (amount, args[0]))
    except Exception as exp:
        resp(args[0], "No se pudo pasar $%s a %s" % (amount, destination))
        resp(args[0], "ERROR: %s" % exp)
        return smpp_c.SMPP_ESME_ROK

    return smpp_c.SMPP_ESME_ROK
