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
- [Beosound Premiere](https://www.bang-olufsen.com/en/dk/soundbars/beosound-premiere)
- [Beosound Theatre](https://www.bang-olufsen.com/en/dk/soundbars/beosound-theatre)
- [Beoremote Halo](https://www.bang-olufsen.com/en/dk/accessories/beoremote-halo)
- [Beoremote One](https://www.bang-olufsen.com/en/dk/accessories/beoremote-one)

### Beoremote One

Beoremote One remotes are added to Home Assistant through Mozart devices as they are paired.

Event entities are available for each of the compatible keys on the remote. To trigger these Event entities, enter the "Control" or "Light" submenu, and press any of the compatible buttons. Each button press will send a "press" and a "release" event. The functions in these submenus are also supported.

The favourite buttons correspond to the physical favourite buttons on the device.

### Beoremote Halo

Beoremote Halo support is still in active development, so several features are missing, and current features may change without any warning.

Do note that the Beoremote Halo can only be connected to one platform at a time, if two platforms try to connect to the Beoremote Halo at the same time, then none of the connections will be stable and usable. This means that the Halo can't be used with [Beoliving Intelligence](https://www.bang-olufsen.com/en/dk/accessories/beoliving-intelligence) and Home Assistant at the same time.

Feel free to open an [issue](https://github.com/bang-olufsen/bang_olufsen-hacs/issues) to request a feature or comment on an existing one.

The Halo can be added through Zeroconf discovery, or manually by entering both the IP address and the serial number. Afterwards, add a configuration to the Halo by entering the options by pressing the `CONFIGURE` button.

All actions have to be manually defined for each entity type, which is why not all entities work at this point.

Generally "wheel" events are handled by counting the number of detents in a "rotation" with a resetting timeout of currently 250ms and acting accordingly. This means that an action is called only when the wheel has been stationary for 250ms. This seems to be the most stable way to handle entities that are "slow" to change states.

#### Current features

- Add pages containing Home Assistant Entities as buttons. Currently support for:
  - Binary Sensor
  - Button / Input Button
  - Cover
  - Light
  - Number / Input Number
  - Scene
  - Script
  - Sensor
  - Switch / Input Boolean
- Entity state is shown as subtitle
- "Preview" value shown in the middle of buttons for wheel actions
- Modify pages:
  - Modify page name
  - Add / remove button(s)
  - Modify button
    - Title
    - Icon
- Select or remove a default Halo button
- Delete page(s)
- Halo entities:
  - Battery charging Binary Sensor Entity
  - Battery Level Sensor Entity
  - System status Event entity (Can be used as a proximity sensor)
- Custom actions:
  - Get Halo configuration
  - Send notification to Halo
  - Display a page and button on the Halo

#### Missing features

These features have to evaluated further and are in no particular order.

- Support for more Entity types (These are the missing ones):
  - Calender
  - Climate
  - Device tracker
  - Event
  - Fan
  - Humidifier
  - Lawn mower
  - Lock
  - Media player
  - Notify
  - Remote
  - Select
  - Siren
  - Text
  - Update
  - Vacuum
  - Valve
  - Water heater
  - Weather
- Create Event entity for button instead of selecting an existing entity
- Home Assistant diagnostics

## Configuration

This integration can be added to a Home Assistant installation using [HACS](https://hacs.xyz/) by adding `https://github.com/bang-olufsen/bang_olufsen-hacs` as a [custom repository](https://hacs.xyz/docs/faq/custom_repositories/).

Afterwards, devices can be added to your Home Assistant installation manually by using the UI or by auto-discovery.

## Example setup and blueprints

Christian Klit has made a setup video for Home Assistant which includes this integration.
[![Setup video](https://img.youtube.com/vi/ju_gQDIme0w/0.jpg)](https://www.youtube.com/watch?v=ju_gQDIme0w)

As can be seen in the video, Christian also provides several [automation blueprints](https://cklit.dk/index.php/category/blueprints/mozart/) for this integration on his website.

These include:

- Control lights using Beoremote One
- Control shades using Beoremote One
- Announce where music has been joined from (Beolink)
- Control scenes using Light and Control menu items on BR1 BT
- Trigger a scene, when alarm starts
- Show active Listening position and Sound mode on LG screen

Go to his website [cklit.dk](https://cklit.dk/) to see more information on the useful blueprints for Mozart and ASE based Bang & Olufsen products.

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
  - Media ID (if available)
  - Input Signal (if available)
  - Beolink:
    - Own JID
    - Beolink leader (if available)
    - Beolink listeners (if available)
    - Beolink peers (if available)
    - Beolink remote source (if available)
  - Favourites:
    - Source name (if available)
    - Title (if available)
    - Content ID (if available)
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

- Battery Charging for Mozart devices (If available)
- Battery Charging for Halo (If available)

### Event entity

- Device button entities (If available) (Disabled by default)
- Beoremote One key entities (If available) (Disabled by default)
- Proximity (If available) (Disabled by default)
- Halo system status (If available) (Disabled by default)

### Sensor entity

- Battery Level for Mozart devices (If available)
- Battery Level for Halo (If available)
- Remote Battery Level (If available)
- Battery Charging Time (If available)
- Battery Playing Time (If available)

### Select entity

- Listening Position (If available)

### Text entity

- Home Control URI (If available)

## Getting Deezer URIs

To find Deezer playlist, album URIs, and user IDs for Deezer flows, the Deezer website has to be accessed. When navigating to an album, the URL will look something like: <https://www.deezer.com/en/album/ALBUM_ID>, and this needs to be converted to: `album:ALBUM_ID` and the same applies to playlists, which have the format: `playlist:PLAYLIST_ID`.

Deezer user IDs can be found at <https://www.deezer.com/en/profile/USER_ID> by selecting the active user in a web browser.

Additionally Deezer IDs for a currently playing tracks can be found in the `media_content_id` attribute in the `media_player` entity.

## Getting Tidal URIs

Tidal playlists, album URIs and track IDs are available via the Tidal website. When navigating to an album, the URL will look something like <https://listen.tidal.com/album/ALBUM_ID/>, and this needs to be converted to `album:ALBUM_ID`. The same applies to playlists, which have the format `playlist:PLAYLIST_ID`. Individual tracks can be found by sharing the track and selecting the `Copy track link` method, which should yield a link of the format <https://tidal.com/browse/track/TRACK_ID?u>, this can be played by extracting the track id `TRACK_ID`.

Additionally Tidal IDs for currently playing tracks can be found in the `media_content_id` attribute in the `media_player` entity.

### Getting B&O Radio station IDs

Radio station IDs for currently playing stations can be found in the `media_content_id` attribute in the `media_player` entity.

## Automations

"raw" WebSocket notifications received from the device are fired as events in Home Assistant. These can be received by listening to `bang_olufsen_websocket_event` and `bang_olufsen_halo_websocket_event` event types where `device_id` is used to differentiate devices.

### Physical buttons and sensors

Event entities are created for each of the physical "buttons" on your device. These buttons usually have their own behaviors, so using them for automations is not always ideal.

Available buttons:

- Bluetooth (Not available on Beosound Premiere)
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

## Actions

### play_media actions

The Bang & Olufsen integration supports different playback types in the `media_player.play_media` action: playback from URL, activating a favourite, playback from a local file, playing a radio station, activating a Deezer flow and Deezer/Tidal playlists, albums and tracks. Additionally `announce` can be set to `True` to play TTS or files as an overlay.

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

### Custom Mozart actions

The Bang & Olufsen integration supports different custom actions for Mozart-based devices

#### Action `bang_olufsen.beolink_join`

Join a Beolink experience.

| Action data attribute | Optional | Description                                                                                                                                                                                                                                                                                                                                            |
| --------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `beolink_jid`         | yes      | Manually specify Beolink JID to join.                                                                                                                                                                                                                                                                                                                  |
| `source_id`           | yes      | Specify which source to join, behavior varies between hardware platforms. Source names prefaced by a platform name can only be used when connecting to that platform. For example \"ASE Beoradio\" can only be used when joining an ASE device, while ”ASE / Mozart Deezer” can be used with ASE or Mozart devices. A defined Beolink JID is required. |

#### Action `bang_olufsen.beolink_expand`

Expand current Beolink experience.

| Action data attribute | Optional | Description                                                      |
| --------------------- | -------- | ---------------------------------------------------------------- |
| `beolink_jids`        | no       | Specify which Beolink JIDs will join current Beolink experience. |

#### Action `bang_olufsen.beolink_unexpand`

Unexpand from current Beolink experience.

| Action data attribute | Optional | Description                                                            |
| --------------------- | -------- | ---------------------------------------------------------------------- |
| `beolink_jids`        | no       | Specify which Beolink JIDs will leave from current Beolink experience. |

#### Action `bang_olufsen.beolink_leave`

Leave a Beolink experience.

#### Action `bang_olufsen.beolink_allstandby`

Set all Connected Beolink devices to standby.

#### Action `bang_olufsen.beolink_set_volume`

Set a volume level for all connected Beolink devices.

| Action data attribute | Optional | Description               |
| --------------------- | -------- | ------------------------- |
| `volume_level`        | no       | Specify the volume level. |

#### Action `bang_olufsen.beolink_leader_command`

Send a media_player command to Beolink leader.

| Action data attribute | Optional | Description                                   |
| --------------------- | -------- | --------------------------------------------- |
| `command`             | no       | Specify the media_player command.             |
| `parameter`           | yes      | Specify the media_player command's parameter. |

#### Action `bang_olufsen.reboot`

Reboot the device.

### Custom Halo actions

The Bang & Olufsen integration additionally supports different custom actions for the Beoremote Halo

#### Action `bang_olufsen.halo_configuration`

Get the raw Halo configuration.

#### Action `bang_olufsen.halo_notification`

Send a notification to the Halo.

| Action data attribute | Optional | Description                                                                                    |
| --------------------- | -------- | ---------------------------------------------------------------------------------------------- | -------------------------------------------- |
| `title`               | no       | The title of the notification.                                                                 |
| `subtitle`            | no       | The subtitle of the notification. 6 lines are supported before formatting starts to break. Use | in yaml mode to construct multiline strings. |

#### Action `bang_olufsen.halo_display_page`

Focus on a Page and Button on a Halo.

| Action data attribute | Optional | Description           |
| --------------------- | -------- | --------------------- |
| `page_id`             | no       | The UUID of a Page.   |
| `button_id`           | no       | The UUID of a Button. |
