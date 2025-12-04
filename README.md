# kaleidescape_volume
Minimal Home Assistant custom integration to test out volume control for a Kaleidescape whose remote has volume buttons.

## Installation
1). Install via HACS.  
2). Add the IP or hostname of your Kaleidescape to the configuration.yaml like so

kaleidescape_volume:
  host: 192.168.X.X  # Strato V IP
  port: 10000 

3). If you wish to enable logs for it, then add the following to your configuration.yaml

logger:
  logs:
    custom_components.kaleidescape_volume: debug
    kaleidescape: debug

