############################################################################
#
# Copyright (C) 2013 tele <tele@rhizomatica.org>
# Copyright (C) 2018 keith <keith@rhizomatica.org>
#
# Contexts call processing
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

from config import *

class Context:
    """ Context object """

    NOT_CREDIT_ENOUGH = '002_saldo_insuficiente.gsm'
    NOT_AUTH = '013_no_autorizado.gsm'
    NOT_REGISTERED = '015_no_access.gsm'
    WRONG_NUMBER = '007_el_numero_no_es_corecto.gsm'
    BRIDGE_PARALLEL = ','
    BRIDGE_SERIES = '|'


    def __init__(self, session, modules):
        """ Init

        :param session: FS session
        :param modules: Array of modules instances to be used in the object
        """
        self.eng_codes = {'profile': 0, 'codec': 0}
        self.session = session
        self.destination_number = self.session.getVariable('destination_number')
        self.calling_number = self.session.getVariable('caller_id_number')
        self.calling_host = self.session.getVariable("sip_network_ip")

        self.subscriber = modules[0]
        self.numbering = modules[1]
        self.billing = modules[2]
        self.configuration = modules[3]

    def get_audio_file(self, disposition):
        return {
            "DESTINATION_OUT_OF_ORDER" : "008_el_numero_no_esta_disponible.gsm",
            "NO_ANSWER"                : "008_el_numero_no_esta_disponible.gsm",
            "NO_USER_RESPONSE"         : "008_el_numero_no_esta_disponible.gsm",
            "SUBSCRIBER_ABSENT"        : "008_el_numero_no_esta_disponible.gsm",
            "USER_BUSY"                : "009_el_numero_esta_ocupado.gsm",
            "UNALLOCATED_NUMBER"       : "007_el_numero_no_es_corecto.gsm",
            "NO_ROUTE_DESTINATION"     : "007_el_numero_no_es_corecto.gsm",
            "RESOURCE_UNAVAIL"         : "005_todas_las_lineas_estan_ocupadas.gsm",
            "INVALID_GATEWAY"          : "010_no_puede_ser_enlazada.gsm",
            "GATEWAY_DOWN"             : "010_no_puede_ser_enlazada.gsm",
            "CALL_REJECTED"            : "007_el_numero_no_es_corecto.gsm",
            "NORMAL_TEMPORARY_FAILURE" : "010_no_puede_ser_enlazada.gsm", # B-leg IP unreachable
            "RECOVERY_ON_TIMER_EXPIRE" : "011_no_hay_conx_a_comunidad.gsm", # Timeout
            "INCOMING_CALL_BARRED"     : "013_no_autorizado.gsm",
            "OUTGOING_CALL_BARRED"     : "015_no_access.gsm",
            "SERVICE_UNAVAILABLE"      : "016_oops.gsm"
        }.get(disposition, "016_oops.gsm")

    def get_codec(self, default=''):
        _override = self.eng_codes['codec']
        codecs = ['', 'G729', 'PCMA', 'GSM', 'AMR', 'OPUS']
        if _override >= len(codecs):
            return ''
        codec = codecs[_override]
        if codec != '':
            log.info('Forcing CODEC: %s', codec)
            return codec
        return default

    def get_gateways(self, callee, default=''):
        _override = self.eng_codes['profile']
        if _override == 0:
            if default:
                return [['', default]]
            return self.numbering.get_gateways(callee)
        gws = self.numbering.get_gateways('')
        gws.insert(0, ['',''])
        if _override >= len(gws):
            return [['', default]]
        log.info('Forcing Profile: %s', gws[_override][1])
        return [gws[_override]]

    def bridge(self, callee):
        """ All calls that are progressing arrive here
            Avoids duplication of code
        """
        # FIXME: Fix all this globals thing.
        if not 'mncc_codec' in globals():
            mncc_codec = 'GSM'
        else:
            mncc_codec = globals()['mncc_codec']
        if not 'inter_codec' in globals():
            inter_codec = 'AMR'
        else:
            inter_codec = globals()['inter_codec']

        mncc_port = '5050'
        inter_port = '5040'
        endpoints = []
        bridge_params = ''
        bridge_mode = self.BRIDGE_PARALLEL

        def add_local_ep():
            bridge_params = ',bridge_early_media=false'
            endpoint = 'sofia/internal/sip:' + str(callee) + '@' + mncc_ip_address + ':' + mncc_port
            codec = self.get_codec(mncc_codec)
            endpoints.append("[absolute_codec_string='^^:" + codec + "'" + bridge_params + "]" + endpoint)

        def add_sip_ep():
            sip_endpoint = self.numbering.is_number_sip_connected(self.session, callee)
            if sip_endpoint:
                codec = self.get_codec('PCMA:G729')
                endpoints.append("[absolute_codec_string='^^:" + codec + "'" + bridge_params + "]" + sip_endpoint)

        def add_internal_ep():
            endpoint = 'sofia/internalvpn/sip:' + str(callee) + '@' + str(site_ip) + ':' + inter_port
            bridge_params = ',bridge_early_media=true'
            codec = self.get_codec(inter_codec)
            endpoints.append("[absolute_codec_string='^^:" + codec + "'" + bridge_params + "]" + endpoint)

        self.session.execute('set', "continue_on_fail="
                             "DESTINATION_OUT_OF_ORDER,"
                             "USER_BUSY,"
                             "NO_ANSWER,"
                             "NO_ROUTE_DESTINATION,"
                             "NO_USER_RESPONSE,"
                             "UNALLOCATED_NUMBER,"
                             "INVALID_GATEWAY,"
                             "GATEWAY_DOWN,"
                             "CALL_REJECTED,"
                             "NORMAL_TEMPORARY_FAILURE,"
                             "INVALID_PROFILE,"
                             "RECOVERY_ON_TIMER_EXPIRE,"
                             "BEARERCAPABILITY_NOTIMPL,"
                             "NETWORK_OUT_OF_ORDER")

        # The default for hangup_after_bridge is false but no harm to have it here
        self.session.execute('set', 'hangup_after_bridge=false')
        self.session.execute('set', 'fail_on_single_reject=NO_ANSWER,USER_BUSY,CALL_REJECTED,ALLOTTED_TIMEOUT')
        # If we get early media, we'd ignore it.. (in case need late neg.)
        self.session.execute('set', 'ignore_early_media=false')
        # can we set the port?
        #self.session.execute('set', 'remote_media_port=60000')
        #self.session.execute('set', 'ringback=${us-ring}')
        self.session.execute('set', 'originate_continue_on_timeout=true')

        # Defaults to sending the call to the local SIP to MNCC UA
        _context = self.session.getVariable('context')
        log.info("Bridge Context: %s", _context)
        # build an array of all possible sip endpoints, then bridge.

        if _context == 'OUTBOUND':
            """
            OUTBOUND: Call has intl destination.
            """

            ''' TODO
            try:
                codec = self.configuration.get_meta('outbound_codec')
            except ConfigurationException as e:
                log.error(e)
            '''
            codec = self.get_codec('G729')
            bridge_mode = self.BRIDGE_SERIES
            try:
                gws = self.get_gateways(callee)
                if len(gws) is 0 or gws[0][1] == '':
                    log.error('Error in getting a Gateway to use for the call')
                    self.session.execute('playback', '%s' % self.get_audio_file('INVALID_GATEWAY'))
                    self.session.hangup('INVALID_GATEWAY')
                    return
                log.debug('Use gateway(s): %s', gws)
            except NumberingException as numex:
                log.error(numex)
                self.session.execute('playback', '%s' % self.get_audio_file('INVALID_GATEWAY'))
                return False
            bridge_params = ',sip_cid_type=pid'
            for gw in gws:
                timeout = 14 if gw[1] == 'sems' else 6
                endpoint = 'sofia/gateway/' + gw[1] + '/' + str(callee)
                endpoints.append("[progress_timeout=" + str(timeout) + ","
                                 "absolute_codec_string='^^:" + codec + "'" + bridge_params + "]" + endpoint)

            if 'JB_out' in globals() and JB_out != '':
                self.session.execute('export', 'rtp_jitter_buffer_during_bridge=true')
                self.session.execute('export', 'nolocal:jitterbuffer_msec=' + JB_out)

        if _context == 'ROAMING_OUTBOUND':
            """
            ROAMING_OUTBOUND: Sending the intl call from a roaming user via their home site, for billing etc.
            """
            self.session.execute('set', 'ringback=%(500,500,450,500);%(250,1000,450,500)')
            self.session.execute('set', 'instant_ringback=true')
            site_ip = self.numbering.get_site_ip(self.session.getVariable('caller_id_number'))
            add_internal_ep()

        if (_context == 'INBOUND' or _context == 'LOCAL' or
                _context == 'INTERNAL_INBOUND' or _context == "ROAMING_LOCAL" or
                _context == 'SUPPORT'):
            """
            INBOUND: Call from Voip Provider
            LOCAL: from local() to local user.
            INTERNAL_INBOUND:  call for local called number is originating another site.
            ROAMING_LOCAL: A local/internal user is calling a local/foreign user that is here.
            """
            if 'lcls' in globals() and lcls == 1:
                if _context == 'LOCAL': # or _context == "ROAMING_LOCAL":
                    # TODO: Check which contexts are only local BTS calls.
                    self.session.setVariable('bypass_media_after_bridge', 'true')

            if _context == "INBOUND":
                _cid = self.numbering.prefixplus(self.session.getVariable('caller_id_number'))
            else:
                _cid = self.session.getVariable('caller_id_number')
            self.session.setVariable('effective_caller_id_number', '%s' % _cid)
            self.session.setVariable('effective_caller_id_name', '%s' % self.session.getVariable('caller_id_name'))
            self.session.execute('set', 'ringback=${us-ring}')
            if 'JB_in' in globals() and JB_in != '':
                self.session.execute('export', 'rtp_jitter_buffer_during_bridge=true')
                self.session.execute('export', 'jitterbuffer_msec=' + JB_in)

            #self.session.preAnswer()
            add_local_ep()
            if _context == "SUPPORT" and not self.numbering.is_number_local(self.destination_number):
                site_ip = self.numbering.get_site_ip(self.destination_number)
                add_internal_ep()
            if use_sip and not self.numbering.is_number_internal(self.destination_number):
                # Foreign user will not be (SIP) registered here.
                add_sip_ep()
            if _context == "ROAMING_LOCAL": # Also bridge to home in case our info is incorrect.
                site_ip = self.numbering.get_site_ip(self.destination_number)
                if site_ip != self.calling_host and site_ip != config['local_ip']: # But don't loop back to origin!
                    add_internal_ep()

        if (_context == 'INTERNAL' or _context == 'ROAMING_INTERNAL'
                or _context == "ROAMING_INBOUND" or _context == "ROAMING_BOTH"):
            """
            INTERNAL:           A-leg: Call to another site.
            ROAMING_INTERNAL:   A-leg: Call from a roaming user (here), is to another roaming user.
            ROAMING_BOTH:       A-leg: Call from a roaming user (here) B-leg: callee is roaming here.
            ROAMING_INBOUND:    A-leg: Call from VoIP provider to a (local) roaming user.   B-leg: local,sip,remote
            """
            site_ip = False
            try:
                site_ip = self.numbering.get_current_bts(callee)
            except NumberingException as ne:
                # FIXME: Again, we don't know if not exists or other error :(
                log.error(ne)
            try:
                if not site_ip or site_ip == config['local_ip']:
                    site_ip = self.numbering.get_site_ip(callee)
            except NumberingException as ne:
                log.error(ne)
                self.session.execute('playback', '%s' % self.get_audio_file('UNALLOCATED_NUMBER'))
                self.session.hangup('UNALLOCATED_NUMBER')
                return
            self.session.setVariable('destination_name', site_ip)
            if _context == "ROAMING_INBOUND":
                _cid = self.numbering.prefixplus(self.session.getVariable('caller_id_number'))
            else:
                _cid = self.session.getVariable('caller_id_number')
            self.session.setVariable('effective_caller_id_number', '%s' % _cid)
            self.session.setVariable('effective_caller_id_name', '%s' % self.session.getVariable('caller_id_number'))
            self.session.execute('set', 'ringback=%(500,500,450,500);%(250,1000,450,500)')
            self.session.execute('set', 'instant_ringback=true')
            #self.session.execute('set', 'bridge_early_media=true')
            self.session.execute('set', 'ignore_early_media=false')

            if _context != 'INTERNAL':
                self.session.execute('set', 'ringback=${us-ring}')
                add_local_ep()
                #add_sip_ep()
            if site_ip != self.calling_host and site_ip != config['local_ip']:
                # Don't bridge the call back to the origin or to our own internal profile.
                add_internal_ep()

        if _context[:8] == 'ROAMING_':
            self.session.execute('set', "continue_on_fail=true")

        if _context == 'WEBPHONE':
            if not callee[:5] in webphone_prefix:
                log.error('Webphone context without a webphone callee number?')
                self.session.execute('playback', '%s' % self.get_audio_file('UNALLOCATED_NUMBER'))
                self.session.hangup('UNALLOCATED_NUMBER')
            self.session.execute('set', 'ringback=%(500,300,440,400);%(450,800,440,400)')
            self.session.execute('set', 'sip_h_Jitsi-Conference-Room=%s' % ("Room" + callee[-1:]))
            codec = self.get_codec('PCMA:OPUS')
            bridge_params = ''
            gws = self.get_gateways(callee,'rhizomatica')
            if len(gws) is 0:
                log.error('Error in getting a Gateway to use for the call')
                self.session.execute('playback', '%s' % self.get_audio_file('INVALID_GATEWAY'))
                self.session.hangup('INVALID_GATEWAY')
                return
            log.debug('Use gateway(s): %s', gws)
            for gw in gws:
                endpoint = 'sofia/gateway/' + gw[1] + '/' + str(callee) + '|'
                endpoints.append("[absolute_codec_string='^^:" + codec + "'" + bridge_params + "]" + endpoint)

        # Now bridge B-leg of call.
        log.info('Bridging to (%s) EP(s):', _context)
        for ep in endpoints:
            log.info('---> \033[92;1m%s\033[0m', ep)
        bridge_str = bridge_mode.join(endpoints)
        self.session.execute('bridge', bridge_str)

        # ============== AFTER THE BRIDGE ==============

        _orig_disp = str(self.session.getVariable('originate_disposition'))
        _ep_disp = str(self.session.getVariable('endpoint_disposition'))
        _ctime = float(self.session.getVariable('created_time'))/1000000
        _atime = float(self.session.getVariable('answered_time'))/1000000
        # Note that if the A leg hangs up, then the last bridge hangup
        # is not from the connected B-leg.
        _hup_cause = str(self.session.getVariable('last_bridge_hangup_cause'))
        if _hup_cause == '':
            log.info("HUP CAUSE was empty.")
            _hup_cause = "NORMAL_CLEARING"
        if _orig_disp == "":
            log.info("ORIG DISP was empty.")
            _orig_disp = "NORMAL_CLEARING"

        log.info('Bridge Finished with B-leg of Call, orig_disp(%s) ep_disp(%s) hup_cause(%s)',
                 _orig_disp, _ep_disp, _hup_cause)
        if _atime > 0:
            _duration = "%0.2f" % (time.time() - _atime)
            log.info('Approx Timings, S->A(%0.2f) Duration(%s)',
                     (_atime - _ctime), _duration)
        else:
            _duration = "N/A"

        if _orig_disp == "SUCCESS":
            if _ep_disp == "ANSWER":
                return (str(_hup_cause) + ", " + str(_duration))
            if _ep_disp == "EARLY MEDIA":
                self.session.hangup(str(_hup_cause))
                if _hup_cause != "NORMAL_CLEARING":
                    return False
                else:
                    return True

        if _orig_disp == "ORIGINATOR_CANCEL":
            self.session.hangup(str(_orig_disp))
            return True

        if (_context != "ROAMING_LOCAL" and _context != "ROAMING_BOTH" and
                _context[:8] == "ROAMING_" and _orig_disp == "UNALLOCATED_NUMBER"):
            # Don't play audio to an incoming roaming call for a number that is
            # unknown to OsmoHLR, this would kill any another bridge.
            # Also it might not be correct.
            self.session.hangup("SUBSCRIBER_ABSENT")
            return

        if ((_context == "ROAMING_LOCAL" or _context == "ROAMING_BOTH") and
                _orig_disp == "UNALLOCATED_NUMBER"):
            log.debug("Forcing DESTINATION_OUT_OF_ORDER for UNALLOCATED_NUMBER")
            _orig_disp = "DESTINATION_OUT_OF_ORDER"
            _hup_cause = "DESTINATION_OUT_OF_ORDER"

        if (self.calling_host != mncc_ip_address and
                (_context == "INTERNAL_INBOUND" or _context == "ROAMING_INTERNAL" or
                 _context == "ROAMING_LOCAL")):
            log.debug("Not playing Audio to %s", self.calling_host)
            # Let the caller side deal with audio feedback
            self.session.hangup(str(_hup_cause))
            return True

        if _context == "SUPPORT":
            _hup_cause = "RESOURCE_UNAVAIL"

        # Playback our own audio based on originate disposition.
        if (_orig_disp == "NORMAL_CLEARING" or _orig_disp == "DESTINATION_OUT_OF_ORDER" or
                _orig_disp == "NORMAL_TEMPORARY_FAILURE"):
            _audio_f = self.get_audio_file(_hup_cause)
        else:
            _audio_f = self.get_audio_file(_orig_disp)
        if _orig_disp == "RECOVERY_ON_TIMER_EXPIRE" and _context == "OUTBOUND":
            _audio_f = self.get_audio_file("GATEWAY_DOWN")

        log.debug('Playback to caller: <%s>', _audio_f)
        if _audio_f != "":
            #self.session.execute('info')
            self.session.execute('playback', '%s' % _audio_f)
            log.debug('Playback Finished.')
            # Don't hangup here if you want to go back into the inbound loop.
            if not _context == "INBOUND":
                self.session.hangup(str(_orig_disp))

    def webphone(self):

        self.session.setVariable('context', 'WEBPHONE')
        self.bridge(self.destination_number)

    def outbound(self):
        """ Outbound context. Calls to be sent out using the VoIP provider """
        self.session.setVariable('context', 'OUTBOUND')
        subscriber_number = self.session.getVariable('caller_id_number')
        # check subscriber balance
        log.debug('Check subscriber %s balance', subscriber_number)
        try:
            current_subscriber_balance = Decimal(self.subscriber.get_balance(subscriber_number))
        except SubscriberException as _ex:
            log.error(_ex)
            self.session.execute('playback', self.NOT_CREDIT_ENOUGH)
            self.session.hangup('OUTGOING_CALL_BARRED')
        try:
            subscriber_package = self.subscriber.get_package(subscriber_number)
        except NoDataException as noe:
            subscriber_package = 0
        except SubscriberException as _ex:
            log.error(_ex)
            self.session.execute('playback', self.get_audio_file('SERVICE_UNAVAILABLE'))
            self.session.hangup('SERVICE_UNAVAILABLE')
            raise

        log.debug('Current subscriber balance: %.2f', current_subscriber_balance)
        log.debug('Current subscriber package: %d', subscriber_package)

        if current_subscriber_balance > Decimal('0.00') or subscriber_package == 1:
            # subscriber has enough balance/package to make a call
            self.session.setVariable('billing', '1')
            rate = self.billing.get_rate(self.destination_number)
            total_call_duration = self.billing.get_call_duration(current_subscriber_balance, rate[3])
            if subscriber_package == 1:
                if rate[1] == "Mexico Cellular-Telcel":
                    log.info("Subscriber has package, adding five minutes to call duration.")
                    total_call_duration = total_call_duration + 300
                    self.session.execute('set', 'execute_on_answer_4=sched_broadcast +%s playback::tone_stream://%%(175,120,550,440);loops=4' %
                                        (total_call_duration - 10))
                elif current_subscriber_balance == Decimal('0.00'):
                    log.info("Zero Balance and destination not included in package.")
                    self.session.execute('playback', '002_saldo_insuficiente.gsm')
                    self.session.hangup()
                    return
            # Set destination_name here for CDR.
            self.session.setVariable('destination_name', rate[1])
            log.info('Total duration for the call before balance end is set to %d sec', total_call_duration)
            self.session.execute('set', 'execute_on_answer_1=sched_hangup +%s normal_clearing both' %
                                 total_call_duration)

            if current_subscriber_balance > Decimal('0.00'):
                # If the subscribers balance will be used, then schedule announcments
                self.session.execute('set', 'execute_on_answer_2=sched_broadcast +%s playback::004_saldo_se_ha_agotado.gsm' %
                                    (total_call_duration - 3))
                if total_call_duration > 59:
                    self.session.execute('set',
                                         'execute_on_answer_3=sched_broadcast +%s playback::003_saldo_esta_por_agotarse.gsm' %
                                         (total_call_duration - 30))

            # set correct caller id based on the active provider
            try:
                caller_id = self.numbering.get_callerid(subscriber_number, self.destination_number)
            except NumberingException as ex:
                log.error(ex)

            if caller_id != None:
                log.info('Set caller id to %s', caller_id)
                self.session.setVariable('effective_caller_id_number', '%s' % caller_id)
                self.session.setVariable('effective_caller_id_name', '%s' % caller_id)
                self.session.execute('set', 'sip_h_P-Charge-Info=%s' % subscriber_number)
            else:
                log.error('Error getting the caller id for the call')
                self.session.setVariable('effective_caller_id_number', 'Unknown')
                self.session.setVariable('effective_caller_id_name', 'Unknown')
            self.bridge(self.destination_number)
        else:
            log.debug('Subscriber doesn\'t have enough balance to make a call')
            # play announcement not enough credit and hangup call
            self.session.execute('playback', '002_saldo_insuficiente.gsm')
            self.session.hangup()

    def get_chans(self, search):
        self.session.execute("set",
                             "_internalcount=${regex(${show channels like "+ search +
                             "}|/[^0-9]*([0-9]+) total./|%1)}")
        count = self.session.getVariable('_internalcount')
        try:
            if count is None:
                return 999
            if count.decode().isnumeric():
                return int(count)
        except ValueError:
            return 999


    def get_local_chans(self):
        self.session.execute("set",
                             "_internalcount=${regex(${show channels like "+ mncc_ip_address +
                             "}|/[^0-9]*([0-9]+) total./|%1)}")
        count = self.session.getVariable('_internalcount')
        try:
            if count is None:
                return 999
            if count.decode().isnumeric():
                return int(count)
        except ValueError:
            return 999

    def local(self):
        """ Local context. Calls destined for our BSC """
        calling_number = self.session.getVariable('caller_id_number')
        if self.numbering.is_number_internal(calling_number):
            self.session.setVariable('context', 'INTERNAL_INBOUND')
        else:
            self.session.setVariable('context', 'LOCAL')
            # Check if local call has to be billed to local subscriber:
            try:
                if self.configuration.check_charge_local_calls() == 1:
                    rate = self.configuration.get_charge_local_calls()
                    log.debug('Check subscriber %s balance', calling_number)
                    try:
                        current_subscriber_balance = Decimal(self.subscriber.get_balance(calling_number))
                    except SubscriberException as _ex:
                        log.error(_ex)
                        current_subscriber_balance = Decimal(0)
                    log.debug('Current subscriber balance: %.2f', current_subscriber_balance)
                    if current_subscriber_balance >= rate[0]:
                        log.info('LOCAL call will be billed at %s after %s seconds', rate[0], rate[1])
                        self.session.setVariable('billing', '1')
                    else:
                        log.debug('Subscriber doesn\'t have enough balance to make a call')
                        self.session.execute('playback', self.NOT_CREDIT_ENOUGH)
                        self.session.hangup()
                        return
            except ConfigurationException as _ex:
                log.error(_ex)

        # Check if the call duration has to be limited
        local_chans = self.get_local_chans()
        self.session.consoleLog("notice", "There are %s local channels in use" % local_chans)
        if not ('unlimit_chans_max' in globals() and local_chans < unlimit_chans_max):
            try:
                limit = self.configuration.get_local_calls_limit()
                if limit != False:
                    if limit[0] == 1:
                        log.info('Limit call duration to: %s seconds', limit[1])
                        self.session.execute('set',
                                             'execute_on_media=playback::tone_stream://%(100,50,650,500);loops=2 mux')
                        self.session.execute('set', 'execute_on_answer_1=sched_hangup +%s normal_clearing both' % limit[1])
                        self.session.execute('set',
                                             'execute_on_answer_2=sched_broadcast +%s playback::tone_stream://%%(200,50,650,500);loops=2' %
                                             (limit[1] - 10))
            except ConfigurationException as _ex:
                log.error(_ex)
        log.info('Take it to the Bridge..')
        return self.bridge(self.destination_number)

    def check_test(self):
        if self.destination_number == config['internal_prefix'] + '00000':
            self.session.answer()
            self.session.execute("sched_hangup", "+600")
            self.session.execute("displace_session",
                                 "tone_stream://%(250,300,860,840);%(150,9000,740,760);loops=-1 mux")
            self.session.execute("echo")
            return True
        if self.destination_number == config['internal_prefix'] + '00001':
            self.session.answer()
            self.session.execute("sched_hangup", "+600")
            self.session.execute("playback", test_playback)
            return True


    def inbound_ivr(self):

        self.session.answer()
        loop_count = 0
        while self.session.ready() and loop_count < 6:
            loop_count += 1
            log.debug('Playback welcome message [%s]', loop_count)
            log.debug('Collect DTMF to call internal number')
            _greet = "001_bienvenidos.gsm"
            _path = self.session.getVariable('sound_prefix') + '/' + _greet
            if not os.path.isfile(_path):
                log.error("!! Audio file(%s) not found!!", _path)
                _greet = "000_default.gsm"
            dest_num = self.session.playAndGetDigits(5, 11, 3, 10000, "#", _greet,
                                                     self.WRONG_NUMBER, "\\d+")
            if not self.session.ready():
                log.debug('Session not ready. Failed to collect digits.')
                return -1
            if dest_num == '':
                continue
            log.debug('Collected digits: %s', dest_num)
            if len(dest_num) == 5:
                self.destination_number = config['internal_prefix'] + dest_num
            elif len(dest_num) == 11:
                self.destination_number = dest_num
            try:
                if self.check_test():
                    return True
                if self.subscriber.is_authorized(dest_num, 1) and (len(dest_num) == 11 or len(dest_num) == 5):
                    self._check_inbound_billing()
                    log.info('Send call to subscriber %s', self.destination_number)
                    self.session.setVariable('accountcode', self.destination_number)
                    ret = self._check_inbound_roaming()
                    if not ret:
                        ret = self.bridge(self.destination_number)
                        if not ret:
                            continue
                        else:
                            return ret
                    else:
                        return ret
                else:
                    self._play_error(self.destination_number)
            except SubscriberException as _ex:
                log.error(_ex)
                self.session.execute('playback', self.WRONG_NUMBER)
                self.session.hangup("UNALLOCATED_NUMBER")
                return -1

    def _check_inbound_billing(self):
        try:
            if self.configuration.check_charge_inbound_calls() == 1:
                log.info('INBOUND call will be billed')
                self.session.setVariable('billing', '1')
        except ConfigurationException as _ex:
            log.error(_ex)

    def _play_error(self, num):
        try:
            if len(num) == 5:
                num = config['internal_prefix'] + num
            sub = self.subscriber.get(num)
            log.info('Subscriber %s is not authorized', num)
            self.session.execute('playback', self.NOT_AUTH)
        except SubscriberException:
            log.info('Subscriber %s doesn\'t exist.', num)
            self.session.execute('playback', self.WRONG_NUMBER)

    def _check_inbound_roaming(self):
        try:
            if self.numbering.is_number_roaming(self.destination_number):
                log.info('Inbound Called number tagged as roaming on (%s)',
                         self.numbering.get_current_bts(self.destination_number))
                self.session.setVariable('context', 'ROAMING_INBOUND')
                self.bridge(self.destination_number)
                return True
        except NumberingException as _ex:
            log.error(_ex)
            self.session.execute('playback', self.WRONG_NUMBER)
        return False

    def inbound(self):
        """ Inbound context. Calls coming from the VoIP provider """
        self.session.setVariable('context', 'INBOUND')
        subscriber_number = None
        try:
            log.info('Check if (%s) is assigned to a subscriber for direct calling',
                     self.destination_number)
            subscriber_number = self.numbering.get_did_subscriber(self.destination_number)
            if subscriber_number is None:
                log.debug('Check if Called Number is a Valid Local Subscriber Number')
                if self.numbering.is_number_local(self.destination_number):
                    subscriber_number = self.destination_number
        except NumberingException as _ex:
            log.error(_ex)

        if subscriber_number == None:
            return self.inbound_ivr()

        log.info('INBOUND call progressing to: %s', subscriber_number)
        try:
            if not (self.subscriber.is_authorized(subscriber_number, 1) and len(subscriber_number) == 11):
                log.error('DID assigned but subscriber %s does not exist or is not authorized', subscriber_number)
                self._play_error(subscriber_number)
                return False

            log.info('Send call to internal subscriber %s', subscriber_number)
            self.session.setVariable('effective_caller_id_number', '%s' % self.session.getVariable('caller_id_number'))
            self.session.setVariable('effective_caller_id_name', '%s' % self.session.getVariable('caller_id_name'))
            if not self._check_inbound_roaming():
                return self.bridge(subscriber_number)

        except SubscriberException as _ex:
            log.error(_ex)
            self.session.execute('playback', self.WRONG_NUMBER)
            self.session.hangup('UNALLOCATED_NUMBER')
        return -1

    def internal(self):
        """ Internal context. Calls for another site routed using internal VPN """
        self.session.setVariable('context', 'INTERNAL')
        self.bridge(self.destination_number)

    def roaming(self):
        """ Roaming context. Calls to subscribers that are currently roaming """
        try:
            site_ip = self.numbering.get_current_bts(self.destination_number)
            # if current bts is local site send call to local LCR
            # We actually do the same thing now in the bridge anyway..
            if site_ip == config['local_ip']:
                log.info('Called number is roaming on our site send call to MNCC')
                self.session.setVariable('context', 'ROAMING_LOCAL')
                self.bridge(self.destination_number)
            else:
                log.info('Called number is tagged as roaming, bridge call to location: %s', site_ip)
                self.session.setVariable('context', 'ROAMING_INTERNAL')
                self.bridge(self.destination_number)
        except NumberingException as _ex:
            log.error(_ex)

    def roaming_caller(self):

        self.destination_number = self.numbering.detect_mx_short_dial(self.destination_number)
        if self.numbering.is_number_intl(self.destination_number):
            log.info('Roaming number calls an (inter)national number.')
            calling = self.session.getVariable('caller_id_number')
            site_ip = self.numbering.get_site_ip(calling)
            if site_ip == config['local_ip']:
                #check if home_bts is same as local site, (error in roaming data)
                # if yes send call to local context outbound
                # FIXME: we should never exec this code.
                log.info('?? WTF! ?? Caller is found to be roaming on home site, send call to voip provider')
                return self.outbound()

            log.info('Send call to home_bts %s of roaming user', site_ip)
            self.session.setVariable('context', 'ROAMING_OUTBOUND')
            return self.bridge(self.destination_number)

        if self.numbering.is_number_roaming(self.destination_number):
            # well destination number is roaming as well, send call to the current_bts where the subscriber is roaming
            try:
                site_ip = self.numbering.get_current_bts(self.destination_number)
                log.info('Called number is roaming send call to current_bts: %s', site_ip)
                self.session.setVariable('context', 'ROAMING_INTERNAL')
                if site_ip == config['local_ip']:
                    self.session.setVariable('context', 'ROAMING_BOTH')
                return self.bridge(self.destination_number)
            except NumberingException as _ex:
                log.error(_ex)
                return False

        # destination number is not roaming check if destination number is for local site
        if (len(self.destination_number) == 11 and
                self.numbering.is_number_local(self.destination_number)):
            log.info('Called number is a local number')

            if not self.subscriber.is_authorized(self.destination_number, 0):
                self.session.execute('playback', self.NOT_AUTH)
                self.session.hangup('OUTGOING_CALL_BARRED')
                return False

            # check if the call duration has to be limited
            local_chans = self.get_chans(wan_ip_address)
            self.session.consoleLog("notice", "There are %s local channels in use" % local_chans)
            try:
                limit = self.configuration.get_local_calls_limit()
                if limit != False:
                    if limit[0] == 1:
                        log.info('Limit call duration to: %s seconds', limit[1])
                        self.session.execute('set',
                                             'execute_on_answer_1=sched_hangup +%s normal_clearing both' % limit[1])
            except ConfigurationException as _ex:
                log.error(_ex)
            log.info('Send roaming call to local MNCC')
            self.session.setVariable('context', 'ROAMING_LOCAL')
            return self.bridge(self.destination_number)

        # number is not local, check if number is internal
        if (len(self.destination_number) == 11 and
                self.numbering.is_number_internal(self.destination_number)):
            # number is internal send call to destination site
            try:
                site_ip = self.numbering.get_site_ip(self.destination_number)
                log.info('Send call to site IP: %s', site_ip)
                self.session.setVariable('context', 'ROAMING_INTERNAL')
                self.bridge(self.destination_number)
            except NumberingException as _ex:
                log.error(_ex)
            return

        if self.numbering.is_number_webphone(self.destination_number):
            self.webphone()
            return

        # called number must be wrong, hangup call
        log.error("End of Dialplan with <%s> -> <%s>", self.calling_number, self.destination_number)
        self.session.execute('playback', '%s' % self.get_audio_file('SERVICE_UNAVAILABLE'))
        #self.session.hangup()
