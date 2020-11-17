#!/usr/bin/env python3

from asterisk.ami import AMIClient
from asterisk.ami import SimpleAction
import time
import re
import yaml
import paho.mqtt.client as mqtt



def ReadConfig():
    with open('/opt/asterisk_status/configuration.yaml') as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
    return config


class AsteriskStatus():
    isconnected = False
    client = None

    def __init__(self):
        self.config = ReadConfig()
        self.mqttc = mqtt.Client()

    def logout(self):
        self.client.logoff()

    # Gets the Caller ID

    def cid_start(self, cid):
        self.cid_response = None
        self.client = AMIClient(address=self.config['asterisk']['ip'], port=self.config['asterisk']['port'])
        self.client.login(username=self.config['asterisk']['user'], secret=self.config['asterisk']['pass'])
        self.client.add_event_listener(self.connection_listener)
        self.client.add_event_listener(self.cid_listener)
        self.sendaction_cid(cid)
        return self.cid_response

    def sendaction_cid(self, cid):
        action = SimpleAction('DBGet', Family=self.config['asterisk']['dbname'], Key=cid)
        future = self.client.send_action(action)
        if future.response.status == 'Success':
            while self.cid_response is None:
                time.sleep(0.001)
        self.logout()

    def cid_listener(self, event, **kwargs):
        if event.name == 'DBGetResponse':
            self.cid_response = event['Val']

    # Starts the main program

    def connection_start(self):
        try:
            self.tmp_events = []
            self.events = []

            self.client = AMIClient(address=self.config['asterisk']['ip'], port=self.config['asterisk']['port'])
            self.client.login(username=self.config['asterisk']['user'], secret=self.config['asterisk']['pass'])
            self.client.add_event_listener(self.connection_listener)
            self.sendaction_status()

            self.mqttc.username_pw_set(self.config['mqtt']['user'], password=self.config['mqtt']['pass'])
            self.mqttc.connect(self.config['mqtt']['ip'])
            self.mqttc.loop_start()
        except Exception as e:
            print(e)

    def get_cid(self, cid):
        ass = AsteriskStatus()
        return ass.cid_start(cid)
        
    def sendaction_status(self):
        try:
            action = SimpleAction('Status')
            future = self.client.send_action(action)
        except Exception as e:
            print(e)

    def connection_listener(self, event, **kwargs):
        try:
            #print(event.name)
            if event.name == 'FullyBooted':
                #print("---===Started===---")
                self.isconnected = True
            elif event.name == 'Shutdown':
                #print("This is shuting down!!!")
                self.isconnected = False
            elif event.name == 'Status':
                self.tmp_events.append(event)
            elif event.name == 'StatusComplete':
                for num, event in enumerate(self.tmp_events):
                    self.tmp_events[num]['chan_re'] = event['Channel']
                    ass = re.match(r'\w*\/(\w*)-\w*', event['Channel'])
                    if ass is not None:
                        self.tmp_events[num]['chan_re'] = ass.group(1)
                self.events = self.link_events(self.tmp_events)
                self.tmp_events = []
            elif event.name in ['Newstate', 'HangupRequest',]:
                self.sendaction_status()
        except Exception as e:
            print(e)

    def link_events(self, events):
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

                cid_from_txt = cid_from if cid_from is not None else filtered_event['CallerIDNum']
                cid_to_txt = cid_to if cid_to is not None else filtered_event['Exten']
                lines_status_txt = ', '.join(lines_status)

                out_print = f"{cid_from_txt}->{cid_to_txt} [{lines_status_txt}]"
                all_event_prints.append(out_print)

            if len(all_event_prints) > 0:
                topublish = ', '.join(all_event_prints)
            else:
                topublish = 'idle'
            print(topublish)
            self.mqttc.publish(self.config['mqtt']['topic'], topublish)

        except Exception as e:
            print(e)

        return events


if __name__ == "__main__":
    ast = AsteriskStatus()
    ast.connection_start()
    while True:
        time.sleep(1)
    ast.logout()

