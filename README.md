# Home Assistant integration for Bang & Olufsen products

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/bang-olufsen/bang_olufsen-hacs)

[![Balance stereo](https://raw.githubusercontent.com/bang-olufsen/mozart-open-api/main/docs/media/balance_stereo.png)](https://www.bang-olufsen.com/en/dk/speakers/beosound-balance-stereo-set?variant=beosound-balance-gva-naturaloak-bundle)

The `bang_olufsen` integration enables control of some of the features of certain [Bang & Olufsen](https://www.bang-olufsen.com/) devices through Home Assistant.

This integration uses the [Mozart open API](https://bang-olufsen.github.io/mozart-open-api/)

## Compatible devices

Devices that have been tested and _should_ work without any trouble are:

- [Beoconnect Core](https://www.bang-olufsen.com/en/dk/accessories/beoconnect-core)
- [Beolab 8](https://www.bang-olufsen.com/en/dk/speakers/beolab-8)
- [Beolab 28](https://www.bang-olufsen.com/en/dk/speakers/beolab-28)
- [Beosound 2 3rd gen](https://www.bang-olufsen.com/en/dk/speakers/beosound-2)
- [Beosound A5](https://www.bang-olufsen.com/en/dk/speakers/beosound-a5)
- [Beosound A9 5th gen](https://www.bang-olufsen.com/en/dk/speakers/beosound-a9)
- [Beosound Balance](https://www.bang-olufsen.com/en/dk/speakers/beosound-balance)
- [Beoconnect Core](https://www.bang-olufsen.com/en/dk/accessories/beoconnect-core)
- [Beosound Emerge](https://www.bang-olufsen.com/en/dk/speakers/beosound-emerge)
- [Beosound Level](https://www.bang-olufsen.com/en/dk/speakers/beosound-level)
- [Beosound Theatre](https://www.bang-olufsen.com/en/dk/soundbars/beosound-theatre)

## Configuration

This integration can be added to a Home Assistant installation using [HACS](https://hacs.xyz/) by adding `https://github.com/bang-olufsen/bang_olufsen-hacs` as a [custom repository](https://hacs.xyz/docs/faq/custom_repositories/).

Afterwards, devices can be added to your Home Assistant installation manually by using the UI or by auto-discovery.

## Entities

This integration adds an array of different useful entities that are generated and added automatically upon setup, customized for the supported features of the device. Some of these features, such as `proximity sensor` and `home-control` are manually defined based on model name in the code, as they currently can't be determined in any other way.

### Media Player entity

- Playback control: play/pause/stop/previous/next
- Adjust volume: set volume/mute
- Clear playlist
- Enable shuffle / repeat
- Select playback source
- Display artwork from currently playing music
- Displaying currently playing artist and track
- Displaying playback progress
- Media seeking (For supported sources)
- Sound mode selection
- Media browsing:
  - Playback of local media
  - Radio Browsing
  - TTS
- Displaying various extra state attributes
  - Beolink:
    - Own JID
    - Beolink leader (if available)
    - Beolink listeners (if available)
    - Beolink peers (if available)
- Using the play_media service:
  - Activate a favourite
  - Play from a URI
  - Play a local file
  - Play a radio station
  - Play a Deezer flow
  - Play an album from Deezer (with optional starting position)
  - Play a playlist from Deezer (with optional starting position)
  - Play a track from Deezer
  - Play an album from Tidal (with optional starting position)
  - Play a playlist from Tidal (with optional starting position)
  - Play a track from Tidal
  - Announce using B&O TTS
- Custom services:
  - Beolink:
    - beolink_allstandby: Set all connected Beolink devices to standby
    - beolink_expand: Expand the Beolink experience with a device
    - beolink_join: Join a Beolink experience, either with specific JID or automatically
    - beolink_leave: Leave a Beolink experience
    - beolink_unexpand: Unexpand a device from a Beolink experience
    - beolink_set_volume: Set volume level on all devices in the Beolink experience
    - beolink_leader_command: Run media_player commands on the Beolink leader from anywhere in the experience:
      - set_volume_level
      - media_seek
      - mute_volume
      - select_source
      - turn_on
      - turn_off
      - volume_up
      - volume_down
      - media_play_pause
      - media_pause
      - media_play
      - media_stop
      - media_next_track
      - media_previous_track
      - toggle
  - reboot: Reboot the device.

### Binary Sensor entity

- Battery Charging (If available)

### Button entity

- Favourite entities

### Event entity

- Device button entities (If available) (Disabled by default)
- Beoremote One key entities (If available) (Disabled by default)
- Proximity (If available) (Disabled by default)

### Number entity

- Treble
- Bass

### Sensor entity

- Battery Level (If available)
- Battery Charging Time (If available)
- Battery Playing Time (If available)
- Media ID (Disabled by default)
- Input Signal (Disabled by default)

### Select entity

- Listening Position (If available)

### Switch entity

- Loudness

### Text entity

- Friendly Name
- Home Control URI (If available)

## Getting Deezer URIs

In order to find Deezer playlists, album URIs and user IDs for Deezer flows, the Deezer website has to be accessed. When navigating to an album, the URL will look something like: <https://www.deezer.com/en/album/ALBUM_ID>, and this simply needs to be converted to: `album:ALBUM_ID` and the same applies to playlist, which have the format: `playlist:PLAYLIST_ID`.

Additionally a Deezer user ID can be found at <https://www.deezer.com/en/profile/USER_ID> by selecting the active user in a web browser.

## Getting Tidal URIs

To find Tidal playlists, album URIs and track IDs, the Tidal website has to be accessed. When navigating to an album, the URL will look something like: <https://listen.tidal.com/album/ALBUM_ID/>, and this needs to be converted to: `album:ALBUM_ID` and the same applies to playlists, which have the format: `playlist:PLAYLIST_ID`. Individual tracks can also be found by sharing the track and selecting the `Copy track link` method, which should yield a link with this format: <https://tidal.com/browse/track/TRACK_ID?u>, this can be played by extracting the track id `TRACK_ID`.

## Automations

"raw" WebSocket notifications received from the device are fired as events in Home Assistant. These can be received by listening to `bang_olufsen_websocket_event` event types where `device_id` is used to differentiate devices.

### Physical buttons and sensors

Event entities are created for each of the physical "buttons" on your device. These buttons usually have their own behaviors, so using them for automations is not always ideal.

Available buttons:

- Bluetooth
- Microphone
- Next
- Play / Pause
- Favourite 1
- Favourite 2
- Favourite 3
- Favourite 4
- Previous
- Volume

All of these buttons support the following events:

- Release of short press
- Long press
- Release of long press
- Very long press
- Release of very long press

All devices except the [Beoconnect Core](https://www.bang-olufsen.com/en/dk/accessories/beoconnect-core) support device controls.

### Beoremote One

Event entities are available for each of the compatible keys on the [Beoremote One](https://www.bang-olufsen.com/en/dk/accessories/beoremote-one). To trigger these triggers, enter the "Control" or "Light" submenu, and press any of the compatible buttons. Each button press will send a "press" and a "release" event. The functions in these submenus are also supported.

The favourite buttons correspond to the physical favourite buttons on the device.

### Automation examples

#### Using the Beoremote One to control lights (OUTDATED)

```yaml
description: Use the Beoremote One to control living room lights.
mode: single
trigger:
  - platform: device
    device_id: 234567890abcdef1234567890abcdef1
    domain: bang_olufsen
    type: Light/Digit1_KeyPress
condition: []
action:
  - service: light.toggle
    target:
      entity_id: light.living_room
```

#### Setting all devices to standby when leaving home (OUTDATED)

```yaml
description: Set all Bang & Olufsen devices to standby when leaving home.
mode: single
trigger:
  - platform: zone
    entity_id: person.example
    zone: zone.home
    event: leave
condition: []
action:
  - service: bang_olufsen.beolink_allstandby
    data: {}
    target:
      entity_id: media_player.beosound_balance_32836899
```

## Services

### play_media services

The Bang & Olufsen integration supports different playback types in the `media_player.play_media` service: playback from URL, activating a favourite, playback from a local file, playing a radio station, activating a Deezer flow and Deezer/Tidal playlists, albums and tracks. Additionally `announce` can be set to `True` to play TTS or files as an overlay.

#### play_media examples

Playing [DR P1](https://www.dr.dk/lyd/p1) from a URL:

```yaml
service: media_player.play_media
target:
  entity_id: media_player.beosound_balance_12345678
data:
  media_content_type: url
  media_content_id: http://live-icy.dr.dk/A/A03H.mp3
```

Activating the first favourite:

```yaml
service: media_player.play_media
target:
  entity_id: media_player.beosound_balance_12345678
data:
  media_content_type: favourite
  media_content_id: 1
```

Playing a local file:

```yaml
service: media_player.play_media
target:
  entity_id: media_player.beosound_balance_12345678
data:
  media_content_id: media-source://media_source/local/example.mp3
  media_content_type: music
```

Playing a Deezer flow. Optionally define a Deezer user ID:

```yaml
service: media_player.play_media
target:
  entity_id: media_player.bang_olufsen
data:
  media_content_type: deezer
  media_content_id: flow
  extra:
    id: 1234567890
```

Playing a Deezer playlist. Optionally define starting position for the playlist:

```yaml
service: media_player.play_media
target:
  entity_id: media_player.beosound_balance_12345678
data:
  media_content_type: deezer
  media_content_id: playlist:1234567890
  extra:
    start_from: 123
```

Playing a Deezer album. Optionally define starting position for the album:

```yaml
service: media_player.play_media
target:
  entity_id: media_player.beosound_balance_12345678
data:
  media_content_type: deezer
  media_content_id: album:1234567890
  extra:
    start_from: 123
```

Playing a Deezer track:

```yaml
service: media_player.play_media
target:
  entity_id: media_player.beosound_balance_12345678
data:
  media_content_type: deezer
  media_content_id: 1234567890
```

Playing a Tidal playlist. Optionally define starting position for the playlist:

```yaml
service: media_player.play_media
target:
  entity_id: media_player.beosound_balance_12345678
data:
  media_content_type: tidal
  media_content_id: playlist:01234567-89ab-cdfe-0123-456789abcdef
  extra:
    start_from: 123
```

Playing a Tidal album. Optionally define starting position for the album:

```yaml
service: media_player.play_media
target:
  entity_id: media_player.beosound_balance_12345678
data:
  media_content_type: tidal
  media_content_id: album:123456789
  extra:
    start_from: 123
```

Playing a Tidal track:

```yaml
service: media_player.play_media
target:
  entity_id: media_player.beosound_balance_12345678
data:
  media_content_type: tidal
  media_content_id: 123456789
```

Playing a B&O Radio station:

```yaml
service: media_player.play_media
target:
  entity_id: media_player.beosound_balance_12345678
data:
  media_content_id: 1234567890123456
  media_content_type: radio
```

Playing a doorbell file with an absolute volume

```yaml
service: media_player.play_media
target:
  entity_id: media_player.beosound_balance_12345678
data:
  media_content_type: music
  media_content_id: media-source://media_source/local/doorbell.mp3
  announce: true
  extra:
    overlay_absolute_volume: 60
```

Playing an overlay TTS with an offset volume

TTS messages can be quiet, so an offset is useful in this scenario.

```yaml
service: media_player.play_media
target:
  entity_id: media_player.beosound_balance_12345678
data:
  media_content_type: overlay_tts
  media_content_id: This is a test
  announce: true
  extra:
    overlay_offset_volume: 10
```

Playing a Bang & Olufsen Cloud TTS message with a local language

```yaml
service: media_player.play_media
target:
  entity_id: media_player.beosound_balance_12345678
data:
  media_content_type: overlay_tts
  media_content_id: Dette er en test
  announce: true
  extra:
    overlay_tts_language: da-dk
```

_NOTE_: To easily obtain the media_content_id for a Deezer/Tidal track or B&O Radio station, you can enable the 'Media id' sensor on Mozart device in Home Assistant (disabled by default).
Once enabled, start playing the content you wish to activate in a service call - the Media id sensor will then provide the value to be used in the media_content_id field.

### Custom services

The Bang & Olufsen integration additionally supports different custom services

### Service `bang_olufsen.beolink_join`

Join a Beolink experience.

| Service data attribute | Optional | Description                           |
| ---------------------- | -------- | ------------------------------------- |
| `beolink_jid`          | yes      | Manually specify Beolink JID to join. |

### Service `bang_olufsen.beolink_expand`

Expand current Beolink experience.

| Service data attribute | Optional | Description                                                      |
| ---------------------- | -------- | ---------------------------------------------------------------- |
| `beolink_jids`         | no       | Specify which Beolink JIDs will join current Beolink experience. |

### Service `bang_olufsen.beolink_unexpand`

Unexpand from current Beolink experience.

| Service data attribute | Optional | Description                                                            |
| ---------------------- | -------- | ---------------------------------------------------------------------- |
| `beolink_jids`         | no       | Specify which Beolink JIDs will leave from current Beolink experience. |

### Service `bang_olufsen.beolink_leave`

Leave a Beolink experience.

### Service `bang_olufsen.beolink_allstandby`

Set all Connected Beolink devices to standby.

### Service `bang_olufsen.beolink_set_volume`

Set a volume level for all connected Beolink devices.

| Service data attribute | Optional | Description               |
| ---------------------- | -------- | ------------------------- |
| `volume_level`         | no       | Specify the volume level. |

### Service `bang_olufsen.beolink_leader_command`

Send a media_player command to Beolink leader.

| Service data attribute | Optional | Description                                   |
| ---------------------- | -------- | --------------------------------------------- |
| `command`              | no       | Specify the media_player command.             |
| `parameter`            | yes      | Specify the media_player command's parameter. |

### Service `bang_olufsen.reboot`

Reboot the device.

## Blueprints

### Announce where music has been joined from (Beolink)

A Blueprint for this scenario: https://youtu.be/AiZbrYQ6u48

Select the speaker you want to announce which other product it joins, when performing a long-press on the Play/Pause button.

Default phrase is “Joined {friendly name}”, but this can easily be modified to a different language, e.g: “Lytter med fra {friendly name}”.

Additionally it is possible to enable announcements when using a remote or the Bang & Olufsen app to expand.

Create an automation for each Mozart product that should announce when joining a different room.

[![Open your Home Assistant instance and show the blueprint import dialog with a specific blueprint pre-filled.](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgist.github.com%2Fcklit%2Fe7126c9fda1195bd88bcaefb45fe493e)

### Control lights using Beoremote One BT (OUTDATED)

A Blueprint to easily set up light control with Beoremote One BT and a Mozart-based product.

Select your Mozart product and the light-bulbs or groups you want to control.

This Blueprint allows for 3 light "zones". See the setup for detailed information on how to control the 3 zones.

To use Light-commands, press “List” on your Beoremote One, navigate down to “Light” and press the center-button. From here, use the described buttons on the remote below to modify brightness.

[![Open your Home Assistant instance and show the blueprint import dialog with a specific blueprint pre-filled.](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgist.github.com%2Fcklit%2F816e6fd144ff91559548e1bf0eb3bf84)

### Control shades using Beoremote One BT (OUTDATED)

A Blueprint to easily set up shade control with Beoremote One BT and a Mozart-based product.

Select your Mozart product and the shades you want to control.

This Blueprint allows for 3 "zones". See the setup for detailed information on how to control the 3 zones.

To use Control-commands, press “List” on your Beoremote One, navigate down to “Control” and press the center-button. From here, use the described buttons on the remote below to modify the position.

[![Open your Home Assistant instance and show the blueprint import dialog with a specific blueprint pre-filled.](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgist.github.com%2Fcklit%2Fd81d36c525936ab8f9309a226287ff91)

### Control scenes using Light and Control menu items on Beoremote One BT (OUTDATED)

A Blueprint to set up scene control with Beoremote One BT and a Mozart-based product.

Select your Mozart product in the dropdown menu.

Enter the function (e.g. Light/Func1) you want to trigger the scene with. All functions are described in the Blueprint.

Select the action that should be triggered by the defined function. This can be any service call, e.g. scene.turn_on.

In case you have renamed the scenes on your remote, they will not match the documentation. To find the function name of a renamed button, enable the debug mode toggle. Every time a Light or Control item is activated, a notification with the name of the selected function will show up in the Home Assistant dashboard notification panel. We recommend to disable debug mode as soon as the automation is working as expected.

To activate a scene, press “List” on your Beoremote One BT, navigate down to “Light” or "Control" and press the right-arrow key. Navigate to the function you want to activate and confirm with the center-button.

[![Open your Home Assistant instance and show the blueprint import dialog with a specific blueprint pre-filled.](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgist.github.com%2Fcklit%2Fd3ee25fa0576da38ca8dede75cf49c04)
