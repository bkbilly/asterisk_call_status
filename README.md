[![GitHub Release](https://img.shields.io/github/release/bkbilly/asterisk_call_status.svg?style=flat-square)](https://github.com/bkbilly/asterisk_call_status/releases)
[![License](https://img.shields.io/github/license/bkbilly/asterisk_call_status.svg?style=flat-square)](LICENSE)
[![hacs](https://img.shields.io/badge/HACS-default-orange.svg?style=flat-square)](https://hacs.xyz)

# ASTERISK_CALL_STATUS
This custom addon is inspired for the use with Home Assistant as a sensor for monitoring the call status on the VoIP server Asterisk.
The information is taken from the Asterisk Manager Interface (AMI) and publishes the call status to the MQTT server.

The result will be something like this `caller -> 541 [voips.modulus.gr (Up), 541 (Up)]`.
The caller and the callee are both checked on the database of Asterisk and if found, they are replaced by the appropriate name.

## AMI Config
This `manager.conf` configuration will allow connections from the localhost `127.0.0.1` and the host `192.168.1.5`:
```
[general]
enabled = yes
webenabled = yes
displayconnects = yes   

port = 5038
bindaddr = 0.0.0.0


[admin]
secret = mysecret
deny = 0.0.0.0/0.0.0.0
permit = 127.0.0.1/255.255.255.255
permit = 192.168.1.5/255.255.255.255
read = system,call,log,verbose,command,agent,user,config,command,dtmf,reporting,cdr,dialplan,originate,message
write = system,call,log,verbose,command,agent,user,config,command,dtmf,reporting,cdr,dialplan,originate,message
writetimeout = 5000
```

Restart manager:
```bash
sudo asterisk -rvvv
module reload manager
manager reload
quit
```

## Installation
Easiest install is via [HACS](https://hacs.xyz/):

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=bkbilly&repository=asterisk_call_status&category=integration)

`HACS -> Explore & Add Repositories -> Asterisk Call Status`

HACS does not "configure" the integration for you. You must go to `Configuration > Integrations` and add `Asterisk Call Status` after installing via HACS.


## Old version
The older version that was using a dedicated service and was sending information via MQTT is not maintained anymore and it's stored on it's own branch `mqtt`.