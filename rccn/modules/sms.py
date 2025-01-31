#!/usr/bin/env python
# -*- coding: utf-8 -*-
############################################################################
#
# Copyright (C) 2013 tele <tele@rhizomatica.org>
# Copyright (C) 2017 Keith Whyte <keith@rhizomatica.org>
#
# SMS module
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
from config import *
import urllib, obscvty, time
from modules.subscriber import Subscriber, SubscriberException
from modules.numbering import Numbering, NumberingException
from threading import Thread
import ESL
import binascii
import gsm0338
import smpplib
import smpplib.gsm
sys.path.append("..")

class SMSException(Exception):
    pass

class SMS:

    def __init__(self):
        self.server = kannel_server
        self.port = kannel_port
        self.username = kannel_username
        self.password = kannel_password
        self.charset = 'UTF-8'
        self.coding = 2
        self.context = 'SMS_LOCAL'
        self.source = ''
        self.destination = ''
        self.internal_destination = ''
        self.text = ''
        self.save_sms = 1

        self.numbering = Numbering()

    def filter(self):
        if self.destination in extensions_list:
            return False
        if len(self.destination) < 5:
            sms_log.info('Dropping SMS on floor because destinaton: %s' % self.destination)
            return True
        if self.charset == '8-BIT' and len(self.destination) < 7:
            sms_log.info('Dropping 8-BIT SMS with destinaton: %s' % self.destination)
            return True
        drop_regexp = ['simchautosynchro.+', 'DSAX[0-9]+ND', 'Activate:dt=', 'REG-REQ?v=3;', '^GWDR']
        for regexp in drop_regexp:
            if re.search(regexp, self.text):
                sms_log.info('Dropping SMS on floor because text matched %s' % regexp)
                return True
        return False

    def webphone_sms(self, source, destination, text, coding):
        if not ('webphone_prefix' in globals() and
                isinstance(webphone_prefix, list) and
                isinstance(sip_central_ip_address, list)):
            sms_log.warning('SMS for Webphone but required config missing.')
            return False
            if not self.destination[:5] in webphone_prefix:
                sms_log.warning('WEBPHONE SMS for non webphone extension?')
            return False
        sms_log.debug('WEBPHONE SMS from %s for %s Coding(%s)' % (source, destination, coding))
        self.source = source+'@sip.rhizomatica.org'
        self.destination = destination
        self.text = text
        simple_dest = self.destination+'@'+ sip_central_ip_address[0]
        sip_profile = 'outgoing'
        charset = self.charset
        if coding == 8:
            charset = 'UTF-16BE'
        if coding == 1:
            charset = 'gsm03.38'
        # text is a <str>
        _ustr = text.decode(charset)
        try:
            # Send UTF-8 to SIP
            sipmsg_body_text = _ustr.encode(self.charset, 'replace')
            event = ESL.ESLevent("CUSTOM", "SMS::SEND_MESSAGE")

            sms_log.debug('SMS to SIP: Source is %s' % self.source)
            sms_log.debug('SMS to SIP: Dest: %s' % simple_dest)
            sms_log.debug('Text: %s' % _ustr)

            event.addHeader("from", self.source)
            event.addHeader("to", simple_dest)
            event.addHeader("sip_profile", sip_profile)
            event.addHeader("dest_proto", "sip")
            event.addHeader("type", "text/plain")
            # Todo, see how we can actually get the result of this back here?
            #event.addHeader("blocking", "true")
            event.addBody(sipmsg_body_text)

            con = ESL.ESLconnection("127.0.0.1", "8021", "ClueCon")
            ret = con.sendEvent(event)
            con.disconnect()
            status = ret.getHeader('Reply-Text')
            sms_log.info('WEBPHONE SMS SENT Status:[%s]', status)
            if status[:3] == '+OK':
                return True
            return False
        except Exception as excep:
            sms_log.info('Exception with Webphone SMS or FS Event: %s' % excep)
            return False

    def sip_sms(self):
        if use_sip != 'yes':
            return False
        if self.destination == '':
            return False
        try:
            sip_endpoints = self.numbering.is_number_sip_connected_no_session(self.destination)
            sip_endpoint = sip_endpoints.split(',')[0]
        except Exception as e:
            sms_log.info('Exception: %s' % e)
            return False
        sms_log.info('SIP SMS? %s' % sip_endpoint)
        if not sip_endpoint:
            return False

        m = re.compile('sofia/([a-z]*)/sip:(.*)').search(sip_endpoint)

        if m:
            sip_profile = m.group(1)
            sip_contact = (m.group(2))
            params = sip_contact.split(';')
            # Get fs_path param.
            res = re.compile('^fs_path=')
            search = filter(res.match, params)

            if len(search) > 0: # Have fs_path
                bracket = re.compile('fs_path=%3C(.*)%3E').search(search[0])
                if bracket:
                    params = urllib.unquote(bracket.group(1)).split(';')
                    path = params[0].replace('sip:', '')
                    r = re.compile('received=*')
                    rec = filter(r.match, params)
                    received = rec[0].replace('received=sip:', '')
                else:
                    import code
                    code.interact(local=locals())
                    path = search[0]
                    received = urllib.unquote(path).split('=')[1].split('@')[1]
            else:
                received = 'None'

        if sip_profile == 'internalvpn':
            simple_dest = self.destination+'@'+vpn_ip_address
            if path == sip_central_ip_address:
                self.source = self.source+'@sip.rhizomatica.org'
                simple_dest = self.destination+'@'+ sip_central_ip_address +';received='+received
        else:
            simple_dest = sip_profile+'/'+sip_contact
        try:
            con = ESL.ESLconnection("127.0.0.1", "8021", "ClueCon")
            event = ESL.ESLevent("CUSTOM", "SMS::SEND_MESSAGE")
            sms_log.info('SMS to SIP: Source is %s' % self.source)
            sms_log.info('SMS to SIP: Dest: %s' % simple_dest)
            sms_log.info('SMS to SIP: Received: %s' % received)
            sms_log.info('Text: %s' % self.text.decode(self.charset, 'replace'))
            sms_log.info('Text: %s' % type(self.text))
            sms_log.info('Coding: %s' % self.coding)
            event.addHeader("from", self.source)
            event.addHeader("to", simple_dest)
            event.addHeader("sip_profile", sip_profile)
            event.addHeader("dest_proto", "sip")
            event.addHeader("type", "text/plain")
            if self.coding == '0':
                msg = self.text.decode('utf8', 'replace')
            else:
                msg = self.text.decode(self.charset, 'replace')
            sms_log.info('Type: %s' % type(msg))
            sms_log.info('Text: %s' % msg)
            event.addBody(msg.encode(self.charset, 'replace'))
            con.sendEvent(event)
            return True
        except Exception as e:
            api_log.info('Caught Error in sms sip routine: %s' % e)


    def receive(self, source, destination, text, charset, coding):
        self.charset = charset
        self.coding = coding
        self.source = source
        self.text = text
        self.internal_destination = destination
        if destination.find('+') > 1:
            destination = destination.split('+')[0]
        self.destination = destination

        sms_log.info('Received SMS: %s %s %s %s %s' % (source, destination, text, charset, coding))
        #sms_log.info(binascii.hexlify(text))
        # SMS_LOCAL | SMS_INTERNAL | SMS_INBOUND | SMS_OUTBOUND | SMS_ROAMING

        # some seemingly autogenerated SMS we just want to drop on the floor:
        try:
            if self.filter():
                return
        except Exception as e:
            api_log.info('Caught an Error in sms:filter %s' % e)
            pass

        #if sip_sms():
        #    return

        try:
            sub = Subscriber()
            # check if source or destination is roaming
            try:
                if not (source == '10000' or self.numbering.is_number_known(source)):
                    sms_log.info('Sender unauthorized send notification')
                    self.context = 'SMS_UNAUTH'
                    self.coding = 2
                    self.send(config['smsc'], source, config['sms_source_unauthorized'])
                    return
                if self.numbering.is_number_roaming(source):
                    sms_log.info('Source number is roaming')
                    self.roaming('caller')
                    return
            except NumberingException as e:
                sms_log.info('Sender unauthorized send notification message (exception)')
                self.context = 'SMS_UNAUTH'
                self.coding = 2
                self.send(config['smsc'], source, config['sms_source_unauthorized'])
                return

            try:
                if self.numbering.is_number_roaming(destination):
                    sms_log.info('Destination number is roaming')
                    self.roaming('called')
                    return
            except NumberingException as e:
                sms_log.info('Destination unauthorized send notification message')
                self.context = 'SMS_UNAUTH'
                self.send(config['smsc'], source, config['sms_destination_unauthorized'])
                return

            try:
                source_authorized = sub.is_authorized(source, 0)
            except SubscriberException as e:
                source_authorized = False
            try:
                destination_authorized = sub.is_authorized(destination, 0)
            except SubscriberException as e:
                destination_authorized = False

            sms_log.info('Source_authorized: %s Destination_authorized: %s' % (str(source_authorized), str(destination_authorized)))


            if (not source_authorized and
                    not self.numbering.is_number_internal(source) and
                    not self.numbering.is_number_webphone(source)):
                sms_log.info('Sender unauthorized send notification message (EXT)')
                self.context = 'SMS_UNAUTH'
                self.coding = 2
                self.send(config['smsc'], source, config['sms_source_unauthorized'])
                return

            if self.numbering.is_number_local(destination):
                sms_log.info('SMS_LOCAL check if subscriber is authorized')
                # get auth info
                sub = Subscriber()
                source_authorized = sub.is_authorized(source, 0)
                destination_authorized = sub.is_authorized(destination, 0)
                try:
                    if source_authorized and destination_authorized:
                        sms_log.info('Forward SMS back to BSC')
                        # number is local send SMS back to SMSc
                        self.context = 'SMS_LOCAL'
                        # Decision was not to send coding on here.....
                        self.send(source, destination, text, charset)
                    else:
                        if not self.numbering.is_number_local(source) and destination_authorized:
                            sms_log.info('SMS_INTERNAL Forward SMS back to BSC')
                            self.context = 'SMS_INTERNAL'
                            self.send(source, destination, text, charset)
                        else:
                            if destination_authorized and not self.numbering.is_number_local(source):
                                sms_log.info('SMS_INBOUND Forward SMS back to BSC')
                                # number is local send SMS back to SMSc
                                self.context = 'SMS_INBOUND'
                                self.send(source, destination, text, charset)
                            else:
                                self.charset = 'UTF-8'
                                self.coding = 2
                                self.save_sms = 0
                                self.context = 'SMS_UNAUTH'
                                if not source_authorized and len(destination) != 3:
                                    sms_log.info('Sender unauthorized send notification message')
                                    self.send(config['smsc'], source, config['sms_source_unauthorized'])
                                else:
                                    sms_log.info('Destination unauthorized inform sender with a notification message')
                                    self.send(config['smsc'], source, config['sms_destination_unauthorized'])

                except SubscriberException as e:
                    raise SMSException('Receive SMS error: %s' % e)
            else:
        
                # dest number is not local, check if dest number is a shortcode
                if destination in extensions_list:
                    sms_log.info('Destination number is a shortcode, execute shortcode handler')
                    extension = importlib.import_module('extensions.ext_'+destination, 'extensions')
                    try:
                        sms_log.debug('Exec shortcode handler')
                        extension.handler('', source, destination, text)
                    except ExtensionException as e:
                        raise SMSException('Receive SMS error: %s' % e)
                else:
                    # check if sms is for another location
                    if self.numbering.is_number_webphone(destination):
                        self.webphone_sms(source, destination, text, self.coding)
                        return
                    if self.numbering.is_number_internal(destination) and len(destination) == 11:
                        sms_log.info('SMS is for another site')
                        try:
                            site_ip = self.numbering.get_site_ip(destination)
                            sms_log.info('Send SMS to site IP: %s' % site_ip)
                            self.context = 'SMS_INTERNAL'
                            self.send(source, destination, text, self.charset, site_ip)
                        except NumberingException as e:
                            raise SMSException('Receive SMS error: %s' % e)
                    elif len(destination) != 3:
                        # dest number is for an external number send sms to sms provider
                        self.context = 'SMS_OUTBOUND'
                        sms_log.info('SMS is for an external number send SMS to SMS provider')
                        self.send(config['smsc'], source,
                                  'Lo sentimos, destino '+str(destination)+ ' no disponible', 'utf-8')
                    else:
                        sms_log.info('SMS for %s was dropped' % destination)

        except NumberingException as e:
            raise SMSException('Receive SMS Error: %s' % e)

    def prepare_txt_for_kannel(self, text, charset):
        # Kannel wants a coding param in the POST
        # GSM 03.38=0 UTF-8=1, UCS2=2
        # and we need a str.
        charset_to_kannel_coding = {'0':'UTF-8', '2':'UTF-16BE'}
        if type(text) == unicode:
            sms_log.debug('Have unicode')
            self.coding = self.determine_coding(text)
            self.charset = charset_to_kannel_coding[self.coding]
            str_text = text.encode(self.charset)
            return (str_text, text)
        try:
            sms_log.debug('Have string, trying %s', charset)
            unicode_text = unicode(text, charset)
            self.coding = self.determine_coding(unicode_text)
            self.charset = charset_to_kannel_coding[self.coding]
            str_text = unicode_text.encode(self.charset)
            return (str_text, unicode_text)
        except Exception as ex:
            sms_log.info('Encoding Error: %s', str(ex))
            self.charset = self.determine_coding(text, charset)
            unicode_text = text.decode(self.charset)
            str_text = text.decode('UTF-8', 'replace').encode(self.charset)
            return (str_text, unicode_text)

    def send(self, source, destination, text, charset='utf-8', server=config['local_ip']):
        '''
        Send an SMS either:
        1) To the local system via:
            a) HTTP POST to kannel or
            b) SUMBIT_SM using libsmpp to local SMSC listener
        2) http POST to a remote RAPI:receive()
        '''
        sms_log.info('SMS Send: Text: <%s> Charset: %s' % (text, charset))
        # We don't trust the caller to send us unicode, or to send a correct charset, if any.
        sms_log.info('Type of text: %s', type(text))

        if 'use_kannel' in globals() and use_kannel == 'yes':
            str_text, unicode_text = self.prepare_txt_for_kannel(text, charset)
        else:
            str_text = ''
            if type(text) != unicode:
                # this could crash if we are fed bullshit.
                unicode_text = text.decode(charset)
            else:
                unicode_text = text

        if server == config['local_ip']:
            try:
                sms_log.info('Send SMS to Local: %s %s %s' % (source, destination, text))
                self.local_smpp_submit_sm(source, destination, unicode_text, str_text)
                if self.save_sms:
                    sms_log.info('Save SMS in the history')
                    self.save(source, destination, self.context)
                return True
            except SMSException as ex:
                sms_log.error("Local submit failed: %s" % str(ex))
                return False

        try:
            sms_log.info('Send SMS to %s: %s %s %s' % (server, source, destination, unicode_text))
            if "+" not in self.internal_destination:
                destination = destination + '+1'
            else:
                s = self.internal_destination.split('+')
                destination = s[0] + '+' + str(int(s[1]) + 1)
                if int(s[1]) > 4:
                    sms_log.error("!! SMS is Looping(%s)", s[1])

            values = {'source': source, 'destination': destination,
                      'charset': self.charset, 'coding': self.coding,
                      'text': unicode_text, 'btext': '', 'dr': '', 'dcs': ''
                      }
            data = urllib.urlencode(values)
            t = Thread(target=self._t_urlopen, args=(server, data))
            t.start()
            sms_log.info('Started Remote RAPI Thread')
            if self.save_sms:
                sms_log.info('Save SMS in the history')
                self.save(source, destination, self.context)
        except IOError:
            # Never happen....
            raise SMSException('Error sending SMS to site %s' % server)


    def local_smpp_submit_sm(self, source, destination, unicode_text, str_text=''):
        if 'use_kannel' in globals() and use_kannel == 'yes':
            try:
                enc_text = urllib.urlencode({'text': str_text})
                kannel_post = "http://%s:%d/cgi-bin/sendsms?username=%s&password=%s&charset=%s&coding=%s&to=%s&from=%s&%s"\
                    % (self.server, self.port, self.username, self.password, self.charset,
                       self.coding, destination, source, enc_text)
                sms_log.info('Kannel URL: %s' % (kannel_post))
                res = urllib.urlopen(kannel_post).read()
                sms_log.info('Kannel Result: %s' % (res))
                return
            except IOError:
                raise SMSException('Error connecting to Kannel to send SMS')

        global _sent
        def _smpp_rx_submit_resp(pdu):
            global _sent
            sms_log.info("Sent (%s)", pdu.message_id)
            if pdu.command == "submit_sm_resp":
                _sent = pdu.status

        try:
            source = network_name if source == '10000' else source
            if not source.isdigit():
                ston = smpplib.consts.SMPP_TON_ALNUM
                snpi = smpplib.consts.SMPP_NPI_UNK
            else:
                ston = smpplib.consts.SMPP_TON_SBSCR
                snpi = smpplib.consts.SMPP_NPI_ISDN
            parts, encoding_flag, msg_type_flag = smpplib.gsm.make_parts(unicode_text)
            smpp_client = smpplib.client.Client("127.0.0.1", 2775, 90)
            if hasattr(smpplib.client, 'logger'):
                smpplib.client.logger.setLevel('INFO')
            else:
                smpp_client.logger.setLevel('INFO')
            smpp_client.set_message_received_handler(lambda pdu: sms_log.info("Rcvd while sending (%s)", pdu.command))
            smpp_client.set_message_sent_handler(_smpp_rx_submit_resp)
            smpp_client.connect()
            smpp_client.bind_transmitter(system_id="ISMPP", password="Password")
            _sent = -1
            for part in parts:
                pdu = smpp_client.send_message(
                    source_addr_ton=ston,
                    source_addr_npi=snpi,
                    source_addr=str(source),
                    dest_addr_ton=smpplib.consts.SMPP_TON_SBSCR,
                    dest_addr_npi=smpplib.consts.SMPP_NPI_ISDN,
                    destination_addr=str(destination),
                    data_coding=encoding_flag,
                    esm_class=msg_type_flag,
                    short_message=part,
                    registered_delivery=False,
                )
                while _sent < 0:
                    smpp_client.read_once()
            smpp_client.unbind()
            smpp_client.disconnect()
            del pdu
            del smpp_client
        except (IOError, smpplib.exceptions.ConnectionError) as ex:
            raise SMSException('Unable to Submit Message via SMPP %s' % str(ex))
        except smpplib.exceptions.PDUError as ex:
            smpp_client.unbind()
            smpp_client.disconnect()
            raise SMSException('SMPP Error Submitting Message %s' % str(ex))

    def check_decode0338(self, text):
        try:
            return text.decode('gsm03.38')
        except Exception as ex:
            sms_log.error(str(ex))
            try:
                gsm_shift_codec = gsm0338.Codec(single_shift_decode_map=gsm0338.SINGLE_SHIFT_CHARACTER_SET_SPANISH)
                return gsm_shift_codec.decode(text)[0]
            except Exception as ex:
                sms_log.error(str(ex))

    def determine_coding(self, unicode_str):
        if type(unicode_str) != unicode:
            raise SMSException('Input is not unicode')
        try:
            try:
                _test0338 = unicode_str.encode('gsm03.38')
                sms_log.debug('GSM03.38 OK "%s" -> "%s"' % (unicode_str, _test0338.decode('gsm03.38')))
                return '0'
            except ValueError as ex:
                sms_log.debug('Encoding to GSM03.38 default alphabet not possible. %s' % sys.exc_info()[1])
            _test0338s = gsm0338.Codec(single_shift_decode_map=gsm0338.SINGLE_SHIFT_CHARACTER_SET_SPANISH)
            _test = _test0338s.encode(unicode_str)[0]
            sms_log.debug('GSM03.38 Spanish Shift OK "%s" -> "%s"' % (unicode_str, _test0338s.decode(_test)[0]))
            return '2'
        except Exception as ex:
            template = "exception of type {0}. Arguments:\n{1!r}"
            print(template.format(type(ex).__name__, ex.args))
            sms_log.debug('Using GSM03.38 Spanish Shift not possible. %s' % sys.exc_info()[1])
            return '2'

    def roaming(self, subject):

        self.numbering = Numbering()
        self.subscriber = Subscriber()

        if subject == 'caller':
            # calling number is roaming
            # check if destination number is roaming as well
            if self.numbering.is_number_roaming(self.destination):
                # well destination number is roaming as well send SMS to current_bts where the subscriber is roaming
                try:
                    current_bts = self.numbering.get_current_bts(self.destination)
                    sms_log.info('Destination number is roaming send SMS to current_bts: %s' % current_bts)
                    if current_bts == config['local_ip']:
                        log.info('Current bts same as local site send call to local Kannel')
                        self.context = 'SMS_ROAMING_LOCAL'
                        self.send(self.source, self.destination, self.text, self.charset)
                    else:
                        # send sms to destination site
                        self.context = 'SMS_ROAMING_INTERNAL'
                        self.send(self.source, self.destination, self.text, self.charset, current_bts)
                except NumberingException as e:
                    sms_log.error(e)
            else:
                # destination is not roaming check if destination if local site
                if self.numbering.is_number_local(self.destination) and len(self.destination) == 11:
                    sms_log.info('Destination is a local number')

                    if self.subscriber.is_authorized(self.destination, 0):
                        sms_log.info('Send sms to local kannel')
                        self.context = 'SMS_ROAMING_LOCAL'
                        self.send(self.source, self.destination, self.text)
                    else:
                        # destination cannot receive SMS inform source
                        self.context = 'SMS_ROAMING_UNAUTH'
                        # Why receive here? Why not send?
                        self.receive(config['smsc'], source, config['sms_destination_unauthorized'],
                                     self.charset, self.coding)
                else:
                    # number is not local check if number is internal
                    if self.numbering.is_number_internal(self.destination) and len(self.destination) == 11:
                        # number is internal send SMS to destination site
                        current_bts = self.numbering.get_site_ip(self.destination)
                        self.context = 'SMS_ROAMING_INTERNAL'
                        self.send(self.source, self.destination, self.text, self.charset, current_bts)
                    else:
                        # check if number is for outbound.
                        # not implemented yet. just return
                        sms_log.info('Invalid destination for SMS')
                        return
        else:
            # the destination is roaming send call to current_bts
            try:
                current_bts = self.numbering.get_current_bts(self.destination)
                if current_bts == config['local_ip']:
                    sms_log.info('Destination is roaming on our site send SMS to local kannel')
                    self.context = 'SMS_ROAMING_LOCAL'
                    self.send(self.source, self.destination, self.text, self.charset)
                else:
                    sms_log.info('Destination is roaming send sms to other site')
                    self.context = 'SMS_ROAMING_INTERNAL'
                    self.send(self.source, self.destination, self.text, self.charset, current_bts)
            except NumberingException as e:
                sms_log.error(e)


    def save(self, source, destination, context):
        # insert SMS in the history
        try:
            cur = db_conn.cursor()
            cur.execute('INSERT INTO sms(source_addr,destination_addr,context) VALUES(%s,%s,%s)',
                        (source, destination, context))
        except psycopg2.DatabaseError as e:
            db_conn.rollback()
            raise SMSException('PG_HLR error saving SMS in the history: %s' % e)
        finally:
            db_conn.commit()
            cur.close()

    def send_immediate(self, num, text):
        appstring = 'OpenBSC'
        appport = 4242
        vty = obscvty.VTYInteract(appstring, '127.0.0.1', appport)
        cmd = 'subscriber extension %s sms sender extension %s send %s' % (num, config['smsc'], text)
        vty.command(cmd)

    def broadcast_to_all_subscribers(self, text, btype, location):
        sms_log.debug('Broadcast message to [%s], Location: [%s]' % (btype, location))
        if location == "all":
            location = False
        sub = Subscriber()
        _index = 1
        try:
            if btype == 'authorized':
                subscribers_list = sub.get_all_authorized(location)
            elif btype == 'unauthorized':
                subscribers_list = sub.get_all_unauthorized(location)
            elif btype == 'notpaid':
                subscribers_list = sub.get_all_notpaid(location)
            elif btype == 'connected':
                subscribers_list = sub.get_all_connected()
                _index = 0
            else:
                subscribers_list = []
        except NoDataException as ex:
            return False

        for mysub in subscribers_list:
            self.send(config['smsc'], mysub[_index], text)
            time.sleep(1)
            sms_log.debug('Broadcast message sent to [%s] %s' % (btype, mysub[_index]))

    def send_broadcast(self, text, btype, location):
        sms_log.info('Send broadcast SMS to all subscribers. text: %s' % text)
        if type(btype) is list:
            t = {}
            for bt in btype:
                t[bt] = Thread(target=self.broadcast_to_all_subscribers, args=(text, bt, location))
                t[bt].start()
            return
        sms_log.error('Bulk Message had no destinations')

    def _t_urlopen(self, url, data):
        try:
            res = urllib.urlopen('http://%s:8085/sms' % url, data)
            res.read()
            res.close()
            return res
        except IOError as ex:
            sms_log.error("FIMXE: SMS is lost (%s)", ex)
            return False

if __name__ == '__main__':
    sms = SMS()
    try:
        sms.send('10000', '66666248674', 'test')
        #sms.receive('68820132107','777','3010#68820135624#10','UTF-8',2)
        #sms.send_broadcasit('antani')
    except SMSException as e:
        print("Error: %s" % e)
