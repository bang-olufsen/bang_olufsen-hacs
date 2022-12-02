# Home Assistant integration for Bang & Olufsen products

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/bang-olufsen/BangOlufsen-HACS)

[![Balance stereo](https://raw.githubusercontent.com/bang-olufsen/mozart-open-api/main/docs/media/balance_stereo.png)](https://www.bang-olufsen.com/en/dk/speakers/beosound-balance-stereo-set?variant=beosound-balance-gva-naturaloak-bundle)

This integration enables control of some of the features of a Bang & Olufsen device through Home Assistant.

This integration uses the [Mozart open API](https://github.com/bang-olufsen/mozart-open-api)

## Compatible devices

Devices that have been tested and _should_ work without any trouble are:

- [Beolab 28](https://www.bang-olufsen.com/en/dk/speakers/beolab-28)
- [Beosound Balance](https://www.bang-olufsen.com/en/dk/speakers/beosound-balance)
- [Beosound Emerge](https://www.bang-olufsen.com/en/dk/speakers/beosound-emerge)
- [Beosound Level](https://www.bang-olufsen.com/en/dk/speakers/beosound-level)
- [Beosound Theatre](https://www.bang-olufsen.com/en/dk/soundbars/beosound-theatre) (Audio only for now)

## Configuration

This device can be added to your Home Assistant installation manually by using the UI or by auto-discovery.

## Entities

This integration adds an array of different useful entities that are generated and added automatically upon setup, customized for the supported features of the device.

```python
SUPPORTS_PROXIMITY_SENSOR = (
    "Beosound Balance",
    "Beosound Level",
    "BeoLab 28",
    "Beosound Theatre",
)
```

### Media Player entity

- Playback control: play/pause/stop/previous/next
- Adjust volume: set volume/step volume/mute
- Clear playlist
- Enable shuffle / repeat
- Select playback source
- Display artwork from currently playing music
- Displaying currently playing artist and track
- Displaying playback progress
- Media seeking (Currently only when using Deezer)
- Device triggers for automations by using device buttons such as Preset1, Bluetooth etc.
- Device triggers for automations by using the Beoremote One Control and Light events
- Events fired upon WebSocket events received
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
  - Favourites
  - Current netradio station:
    - Station name
    - Station ID
  - Current Deezer track ID (if available)
  - Bluetooth devices:
    - Currently connected bluetooth devices such as phones (if available)
    - Paired remotes (if available)
- Using the play_media service:
  - Activate a favourite
  - Play from a URI
  - Play a Deezer flow
  - Play an album from Deezer (with optional starting position)
  - Play a playlist from Deezer (with optional starting position)
  - Play a track from Deezer
- Custom services:
  - Overlay
    - overlay_audio: Overlaying audio over any currently playing audio.
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

Some entities are added according to lists of supported devices. These are currently:

### Binary Sensor entity

- Battery Charging (If available)
- Proximity sensor (If available)

### Button entity

- Favourite entities

### Number entity

- Treble
- Bass

### Sensor entity

- Battery Level (If available)
- Battery Charging Time (If available)
- Battery Playing Time (If available)

### Switch entity

- Loudness

## Device triggers and events

This integration provides device triggers for the physical controls such as Preset1, Bluetooth etc.

Device triggers for the [Beoremote One](https://www.bang-olufsen.com/en/dk/accessories/beoremote-one) are supported and will be available once the integration detects that it has been paired with the device. To trigger these triggers, enter the "Control" or "Light" submenu, and press any of the compatible buttons, each button press will send a "press" and a "release" event and therefore also a "press" and a "release" device trigger.

These can be received by listening to "bangolufsen_event" event types.

Additionally the "raw" WebSocket notifications received from the device are fired as events in Home Assistant. These can be received by listening to "bangolufsen_websocket_event" event types.

## Getting Deezer URIs

In order to find Deezer playlist, album URIs and user IDs for Deezer flows, the Deezer website has to be accessed. When navigating to an album, the URL will look something like: "https://www.deezer.com/en/album/ALBUM_ID", and this simply needs to be converted to: "album:ALBUM_ID" and the same applies to playlist, which have the format: "playlist:PLAYLIST_ID".

Additionally a Deezer user ID can be found at "https://www.deezer.com/en/profile/USER_ID" by selecting the active user in a web browser.

Deezer track IDs can currently only easily be found by playing the track on the speaker and looking at the extra state attributes, where it is shown with the key "deezer_track_id". Tracks do not have a prefix so the ID needs to be used directly.

## Automation

An array of automations can be defined using the integration.

### Physical buttons and sensors

The "shortPress" of all the buttons, except for the volume control, are available as device triggers.

If the device has a proximity sensor, then a proximity sensor binary sensor will be available in Home Assistant.

### Beoremote One

The `Control` and `Light` menus in the [Beoremote One](https://www.bang-olufsen.com/en/dk/accessories/beoremote-one) can be used as a device triggers once it has been paired with a device that has been added to Home Assistant.

The favourite buttons correspond to the physical favourite buttons on the device.

Each of the available buttons will send a device trigger upon keypress and release.

### Automation examples

#### Using the overlay custom service as doorbell

```yaml
description: Play doorbell sound overlay on doorbell press.
mode: single
trigger:
  - platform: device
    device_id: 1234567890abcdef1234567890abcdef
    domain: example
    type: doorbell
condition: []
action:
  - service: bangolufsen.overlay_audio
    data:
      uri: media-source://media_source/local/doorbell.mp3
      absolute_volume: 60
    target:
      entity_id: media_player.beosound_balance_12345678
```

#### Using the Beoremote One to control lights

```yaml
description: Use the Beoremote One to control living room lights.
mode: single
trigger:
  - platform: device
    device_id: 234567890abcdef1234567890abcdef1
    domain: bangolufsen
    type: Light/Digit1_KeyPress
condition: []
action:
  - service: light.toggle
    target:
      entity_id: light.living_room
```

## Services

### play_media services

The Bang & Olufsen integration supports different playback types in the `media_player.play_media` service: playback from URL, activating a favourite, playback from a local file, activating a Deezer flow and Deezer playlists, albums and tracks.

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
  entity_id: media_player.bangolufsen
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

### Custom services

The Bang & Olufsen integration additionally supports different custom services

### Service `bangolufsen.beolink_join`

Join a Beolink experience.

| Service data attribute | Optional | Description                           |
| ---------------------- | -------- | ------------------------------------- |
| `beolink_jid`          | yes      | Manually specify Beolink JID to join. |

### Service `bangolufsen.beolink_expand`

Expand current Beolink experience.

| Service data attribute | Optional | Description                                                      |
| ---------------------- | -------- | ---------------------------------------------------------------- |
| `beolink_jids`         | no       | Specify which Beolink JIDs will join current Beolink experience. |

### Service `bangolufsen.beolink_unexpand`

Unexpand from current Beolink experience.

| Service data attribute | Optional | Description                                                            |
| ---------------------- | -------- | ---------------------------------------------------------------------- |
| `beolink_jids`         | no       | Specify which Beolink JIDs will leave from current Beolink experience. |

### Service `bangolufsen.beolink_leave`

Leave a Beolink experience.

### Service `bangolufsen.beolink_allstandby`

Set all Connected Beolink devices to standby.

### Service `bangolufsen.beolink_set_volume`

Set a volume level for all connected Beolink devices.

| Service data attribute | Optional | Description               |
| ---------------------- | -------- | ------------------------- |
| `volume_level`         | no       | Specify the volume level. |

### Service `bangolufsen.beolink_leader_command`

Send a media_player command to Beolink leader.

| Service data attribute | Optional | Description                                   |
| ---------------------- | -------- | --------------------------------------------- |
| `command`              | no       | Specify the media_player command.             |
| `parameter`            | yes      | Specify the media_player command's parameter. |

### Service `bangolufsen.overlay_audio`

Overlay audio over any currently playing audio.

| Service data attribute | Optional | Description                                 |
| ---------------------- | -------- | ------------------------------------------- |
| `uri`                  | no       | Specify the audio to play.                  |
| `absolute_volume`      | yes      | Specify an absolute volume for the overlay. |
