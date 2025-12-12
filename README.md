# kaleidescape_volume
Minimal Home Assistant custom integration to enable a Kaleidescape remote to control another components volume.  Your Kaleidescape's remote must have volume buttons, of course.  This is built off the latest release of [PyKaleidescape](https://github.com/SteveEasley/pykaleidescape), and is hopefully temporary until that release is merged into the HA core Kaleidescape integration, making it available to all.  Until that happens, you can enjoy controlling volume using this repo.

## Installation
1). Install via HACS: [![Open this repository in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=kevinlester&repository=kaleidescape_volume&category=integration)

2). Add the IP or hostname of your Kaleidescape to the configuration.yaml like so [you can also tweak how
    fast the volume changes when holding down the volume up/down button]:

```
kaleidescape_volume:
  host: 192.168.X.X     # Kaleidescape IP/hostname
  port: 10000           # [Optional]
  repeat_interval: .25  # [Optional] seconds between volume steps when holding up/down button
```

3). If you wish to enable logs for it, then add the following to your configuration.yaml
```
logger:
  logs:
    custom_components.kaleidescape_volume: debug
    kaleidescape: debug
```

4). Add an automation to control volume:
```
alias: Kaleidescape → Denon Volume Control
description: "Enables Kaleidescape remote to control receiver volume"
mode: single
triggers:
  - event_type: kaleidescape_volume_button
    trigger: event
actions:
  - choose:
      - conditions:
          - condition: template
            value_template: "{{ trigger.event.data.event == 'VOLUME_UP_PRESS' }}"
        sequence:
          - target:
              entity_id: media_player.denon_receiver
            action: media_player.volume_up
      - conditions:
          - condition: template
            value_template: "{{ trigger.event.data.event == 'VOLUME_DOWN_PRESS' }}"
        sequence:
          - target:
              entity_id: media_player.denon_receiver
            action: media_player.volume_down
```

5). Enjoy being able to control volume on your receiver using the Kaleidescape remote!
