#!/usr/bin/python
############################################################################
#
# Copyright (C) 2019 keith <keith@rhizomatica.org>
#
# An extension that reads GSM measurement reports to the caller.
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
"""
Meas JSON Example:
{
{"time":1632853826, "imsi":"334070000000968",
 "name":"subscr-IMSI-334070000000968-TMS",
 "scenario":"",
 "chan_info":{"lchan_type":"TCH_F", "pchan_type":"TCH/F", "bts_nr":0, "trx_nr":0, "ts_nr":4, "ss_nr":0}, 
 "meas_rep":{"NR":150, 
             "UL_MEAS":{"RXL-FULL":-51, "RXL-SUB":-52, 
                        "RXQ-FULL":0, "RXQ-SUB":0}, 
             "BS_POWER":0, 
             "MS_TO":0, 
             "L1_MS_PWR":5, 
             "L1_FPC":false, 
             "L1_TA":0, 
             "BA1":true, 
             "DL_MEAS":{"RXL-FULL":-52, "RXL-SUB":-52, 
                        "RXQ-FULL":0, "RXQ-SUB":0}, 
                        "NUM_NEIGH":0, "NEIGH":[]}}
"""
import sys
sys.path.append("..")
from config import *
from subprocess import Popen, PIPE
import json

def handler(session, *args):
    log.debug('Handler for ext 147')
    session.answer()
    session.execute('set_audio_level', 'write 4')
    sub = Subscriber()
    try:
        imsi = sub.get_imsi_from_msisdn(session.getVariable('caller_id_number'))
    except (SubscriberException, NoDataException):
        session.execute('playback', '016_oops.gsm')
        session.hangup()        

    proc = Popen(["/usr/bin/ncat", "-U", "/tmp/json_socket"], stdout=PIPE, bufsize=1)

    with proc.stdout:
        for line in iter(proc.stdout.readline, b''):
            if not session.ready():
                log.info("MEAS REP: Session Not Ready [%s]", imsi)
                proc.stdout.close()
                proc.kill()
                sys.exit()

            try:
                jdata = json.loads(line)
            except ValueError:
                continue
            
            if jdata['imsi'] != imsi:
                continue

            num = jdata['meas_rep']['NR']
            if not (num < 3 or (num % 12 == 0)):
                continue

            try:
                bts_nr   = jdata['chan_info']['bts_nr']
                trx_nr   = jdata['chan_info']['trx_nr']
                ts_nr   = jdata['chan_info']['ts_nr']
                ul_full = abs(jdata['meas_rep']['UL_MEAS']['RXL-FULL'])
                dl_full = abs(jdata['meas_rep']['DL_MEAS']['RXL-FULL'])
                ul_Q    = jdata['meas_rep']['UL_MEAS']['RXQ-FULL']
                dl_Q    = jdata['meas_rep']['DL_MEAS']['RXQ-FULL']
                pwr     = jdata['meas_rep']['L1_MS_PWR']
            except KeyError:
                continue

            log.debug("Reading Meas Rep for %s [%s]", imsi, num)
            if num < 3:
                session.execute('say', 'en number pronounced %s' % bts_nr)
                session.execute('say', 'en number pronounced %s' % trx_nr)
                session.execute('say', 'en number pronounced %s' % ts_nr)
                continue
            session.execute('say', 'en number pronounced %s' % ul_full)  
            session.execute('say', 'en number pronounced %s' % dl_full)
            session.execute('say', 'en number pronounced %s' % ul_Q)
            session.execute('say', 'en number pronounced %s' % dl_Q)
            session.execute('say', 'en number pronounced %s' % pwr)
            #session.execute('playback', '$_ss')
    log.info("MEAS REP: stdout gone")
    proc.kill()
    session.hangup()
