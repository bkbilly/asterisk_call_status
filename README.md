# Asterisk-Call-Status
This service is inspired for the use with Home Assistant as a sensor for monitoring the call status on the VoIP server Asterisk.
The information is taken from the Asterisk Manager Interface (AMI) and publishes the call status to the MQTT server.

The result will be something like this `caller -> 541 [voips.modulus.gr (Up), 541 (Up)]`.
The caller and the callee are both checked on the database of Asterisk and if found, they are replaced by the appropriate name.

# Installation
You first need to download the get repository and change the configuration file:
```bash
git clone https://github.com/bkbilly/Asterisk-Call-Status.git /opt/asterisk_status
cd /opt/asterisk_status/
vi configuration.yaml
```

You will also need to install all dependencies and run it as a service:
```bash
sudo pip install -r requirements.txt
sudo cp asteriskStatus.service /etc/systemd/system/asterisk_status.service
sudo systemctl enable asterisk_status.service
sudo systemctl start asterisk_status.service
```
