#!/usr/bin/env python3

from asterisk.ami import AMIClient
from asterisk.ami import SimpleAction
import re

import paho.mqtt.client as mqtt
import traceback
import time
import json
import yaml


class AsteriskStatus():

    def __init__(self, config, callback):
        self.config = config
        self.callback = callback
        self.isconnected = False
        self.ami_client = None
        self.cids = {}

    def logout(self):
        self.ami_client.logoff()

    def connection_start(self):
        try:
            self.tmp_events = []

            if self.ami_client is None:
                self.ami_client = AMIClient(
                    address=self.config['ip'],
                    port=self.config['port'])
                self.ami_client.add_event_listener(self.connection_listener)
            self.ami_client.login(
                username=self.config['user'],
                secret=self.config['pass'])

            self.sendaction_status()
        except Exception:
            traceback.print_exc()

    def get_cid(self, cid):
        if self.config['dbname'] is not None:
            if cid not in self.cids:
                action = SimpleAction(
                    'DBGet',
                    Family=self.config['dbname'],
                    Key=cid)
                self.ami_client.send_action(action)
        return self.cids.get(cid, cid)

    def sendaction_status(self):
        try:
            action = SimpleAction('Status')
            self.ami_client.send_action(action)
        except Exception:
            traceback.print_exc()

    def connection_listener(self, event, **kwargs):
        try:
            if event.name not in ['PeerStatus', 'RTCPSent', 'VarSet', 'Registry']:
                print(f"callback: {event.name}")
            if event.name == 'FullyBooted':
                # print("---===Started===---")
                self.isconnected = True
            elif event.name == 'DBGetResponse':
                # print(event)
                self.cids[event['Key']] = event['Val']
            elif event.name == 'Shutdown':
                print("This is shuting down!!!")
                self.isconnected = False
            elif event.name == 'Status':
                self.tmp_events.append(event)
            elif event.name == 'StatusComplete':
                # print(self.tmp_events)
                for num, event in enumerate(self.tmp_events):
                    # Add caller id on the list of known caller names
                    caller_num = event['CallerIDNum']
                    caller_name = event['CallerIDName']
                    if caller_num not in self.cids:
                        if caller_name != '<unknown>':
                            self.cids[caller_num] = caller_name
                    # Find the channel name
                    self.tmp_events[num]['chan_re'] = event['Channel']
                    ass = re.match(r'\w*\/(\S*)-\w*', event['Channel'])
                    if ass is not None:
                        self.tmp_events[num]['chan_re'] = ass.group(1)
                self.link_events(self.tmp_events)
                self.tmp_events = []
            elif event.name in ['Newstate', 'HangupRequest', 'DialEnd', 'Hangup', 'SoftHangupRequest']:
                self.sendaction_status()
        except Exception:
            traceback.print_exc()

    def link_events(self, events):
        """"""
        calls_from = []
        calls_to = []
        cids_from = []
        cids_to = []
        channels = []
        contexts = []
        try:
            filtered_events = [event for event in events if event['Uniqueid'] == event['Linkedid']]
            linked_events = [event for event in events if event['Uniqueid'] != event['Linkedid']]
            all_event_prints = []

            for filtered_event in filtered_events:
                lines_status = []
                linked = [event for event in linked_events if event['Linkedid'] == filtered_event['Uniqueid']]

                cid_from = self.get_cid(filtered_event['CallerIDNum'])
                cid_to = self.get_cid(filtered_event['Exten'])
                lines_status.append(f"{filtered_event['chan_re']} ({filtered_event['ChannelStateDesc']})")
                for link in linked:
                    lines_status.append(f"{link['chan_re']} ({link['ChannelStateDesc']})")

                calls_from.append(filtered_event['CallerIDNum'])
                calls_to.append(filtered_event['Exten'])
                cids_from.append(cid_from)
                cids_to.append(cid_to)
                channels.append(filtered_event['chan_re'])
                contexts.append(filtered_event['Context'])

                lines_status_txt = ', '.join(lines_status)

                out_print = f"{cid_from}->{cid_to} [{lines_status_txt}]"
                all_event_prints.append(out_print)

            if len(all_event_prints) > 0:
                topublish = ', '.join(all_event_prints)
            else:
                topublish = 'idle'
            result = {
                "status": topublish,
                "calls_from": calls_from,
                "calls_to": calls_to,
                "cids_from": cids_from,
                "cids_to": cids_to,
                "channels": channels,
                "contexts": contexts
            }
            self.callback(result)

        except Exception:
            traceback.print_exc()


class MyMQTT():
    def __init__(self, config):
        self.config = config
        self.mqttc = mqtt.Client()
        self.mqttc.username_pw_set(
            self.config['mqtt']['user'],
            password=self.config['mqtt']['pass'])
        self.mqttc.connect(self.config['mqtt']['ip'])
        self.mqttc.loop_start()

    def setup_discovery(self):
        hass_config = {
            "icon": "mdi:phone-voip",
            "state_topic": self.config['mqtt']['topic'],
            "name": "Asterisk Call Status",
            "unique_id": "asterisk_callstatus",
            "device": {
                "identifiers": [
                    "Asterisk_Call_Status"
                ],
                "name": "Asterisk",
                "model": "Asterisk Call Status 0.5",
                "manufacturer": "bkbilly"
            }
        }
        topublish = json.dumps(hass_config)
        self.mqttc.publish(
            "homeassistant/sensor/asteriskcallstatus/config",
            topublish,
            retain=True)

    def publish(self, topublish):
        print(topublish)
        self.mqttc.publish(
            self.config['mqtt']['topic'],
            topublish['status'],
            retain=True)


if __name__ == "__main__":
    with open('configuration.yaml') as f:
        config = yaml.load(f, Loader=yaml.FullLoader)

    mymqtt = MyMQTT(config)
    if config['mqtt'].get('discovery', True):
        mymqtt.setup_discovery()
    ast = AsteriskStatus(config['asterisk'], mymqtt.publish)
    ast.connection_start()
    repeatTimes = 0
    while True:
        if not ast.isconnected:
            ast.connection_start()
        time.sleep(1)
        if repeatTimes > 60:
            repeatTimes = 0
            ast.sendaction_status()
    ast.logout()
