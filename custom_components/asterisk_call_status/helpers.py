"""Asterisk Call Status helper."""
from PIL import Image, ImageFont, ImageDraw
from io import BytesIO
import logging

from asterisk.ami import AMIClient
from asterisk.ami import SimpleAction
import re
import pathlib

import traceback

_LOGGER = logging.getLogger(__name__)


def text_to_image(
        text: str,
        font_filepath: str,
        font_size: int,
        color: (int, int, int),
        img_size: (int, int),
        bg_color="white",
        font_align="center"):
    img = Image.new("RGB", img_size, color=bg_color)
    draw = ImageDraw.Draw(img)
    while True:
        font = ImageFont.truetype(font_filepath, size=font_size)
        _, _, w, h = draw.textbbox((0, 0), text, font=font)
        if w < img_size[0] and h < img_size[1]:
            break
        font_size -= 15
    draw_point = (
        int((img_size[0] - w) / 2),
        int((img_size[1] - h) / 2)
    )
    draw.text(draw_point, text, font=font, fill=color, align=font_align)
    with BytesIO() as f:
        img.save(f, format='PNG')
        return f.getvalue()


class AsteriskCallStatusHelper():

    def __init__(self, address, port, username, password, dbname=None, callback=None):
        self.address = address
        self.port = port
        self.username = username
        self.password = password
        self.dbname = dbname
        self.callback = callback
        self.isconnected = False
        self.ami_client = None
        self.image = None
        self.result = {}
        self.cids = {}

    def get_results(self):
        if not self.isconnected:
            _LOGGER.info("Not connected, trying to connect right now")
            self.connect()
        return self.result

    def save_results(self, result):
        text = ("\n").join(result.get('status').split())
        _LOGGER.info(f"Reading from font: {pathlib.Path(__file__).parent}/FrederickatheGreat-Regular.ttf")
        try:
            self.image = text_to_image(
                text,
                f"{pathlib.Path(__file__).parent}/FrederickatheGreat-Regular.ttf",
                200, (20, 0, 255), (1024, 600))
        except Exception as e:
            _LOGGER.error(e)
        _LOGGER.info("Created a new image as a self.image")

    def disconnect(self):
        self.ami_client.logoff()

    def connect(self):
        try:
            self.tmp_events = []

            if self.ami_client is None:
                self.ami_client = AMIClient(
                    address=self.address,
                    port=self.port)
                self.ami_client.add_event_listener(self.connection_listener)
            self.ami_client.login(
                username=self.username,
                secret=self.password)

            self.sendaction_status()
        except Exception:
            _LOGGER.error(traceback.format_exc())

    def get_cid(self, cid):
        if self.dbname is not None:
            if cid not in self.cids:
                action = SimpleAction(
                    'DBGet',
                    Family=self.dbname,
                    Key=cid)
                self.ami_client.send_action(action)
        return self.cids.get(cid, cid)

    def sendaction_status(self):
        try:
            action = SimpleAction('Status')
            self.ami_client.send_action(action)
        except Exception:
            _LOGGER.error(traceback.format_exc())

    def connection_listener(self, event, **kwargs):
        try:
            if event.name not in ['PeerStatus', 'RTCPSent', 'VarSet', 'Registry']:
                _LOGGER.info(f"callback: {event.name}")
            if event.name == 'FullyBooted':
                # _LOGGER.info("---===Started===---")
                self.isconnected = True
            elif event.name == 'DBGetResponse':
                # _LOGGER.info(event)
                self.cids[event['Key']] = event['Val']
            elif event.name == 'Shutdown':
                _LOGGER.info("This is shuting down!!!")
                self.isconnected = False
            elif event.name == 'Status':
                self.tmp_events.append(event)
            elif event.name == 'StatusComplete':
                # _LOGGER.info(self.tmp_events)
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
            _LOGGER.error(traceback.format_exc())

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
                lines_status.append(f"{filtered_event['chan_re']}({filtered_event['ChannelStateDesc']})")
                for link in linked:
                    lines_status.append(f"{link['chan_re']}({link['ChannelStateDesc']})")

                calls_from.append(filtered_event['CallerIDNum'])
                calls_to.append(filtered_event['Exten'])
                cids_from.append(cid_from)
                cids_to.append(cid_to)
                channels.append(filtered_event['chan_re'])
                contexts.append(filtered_event['Context'])

                lines_status_txt = ','.join(lines_status)

                out_print = f"{cid_from}->{cid_to} [{lines_status_txt}]"
                all_event_prints.append(out_print)

            if len(all_event_prints) > 0:
                topublish = ', '.join(all_event_prints)
            else:
                topublish = 'idle'
            self.result = {
                "status": topublish,
                "calls_from": calls_from,
                "calls_to": calls_to,
                "cids_from": cids_from,
                "cids_to": cids_to,
                "channels": channels,
                "contexts": contexts
            }
            _LOGGER.info(self.result)
            self.save_results(self.result)

        except Exception:
            _LOGGER.error(traceback.format_exc())
