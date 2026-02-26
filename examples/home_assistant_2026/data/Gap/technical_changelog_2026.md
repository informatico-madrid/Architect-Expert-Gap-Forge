## 2026.2.1

- Fix device_class of backup reserve sensor (tesla_fleet docs)
- Bump evohome-async to 1.1.3 (evohome docs) (dependency)
- Bump google_air_quality_api to 3.0.1 (google_air_quality docs) (dependency)
- Bump denonavr to 1.3.2 (denonavr docs) (dependency)
- Fix multipart upload to use consistent part sizes for R2/S3 (cloudflare_r2 docs)
- Add mapping for stopped state to denonavr media player (denonavr docs)
- Fix unicode escaping in MCP server tool response (mcp_server docs)
- Bump pyenphase to 2.4.5 (enphase_envoy docs) (dependency)
- Fix Shelly Linkedgo Thermostat status update (shelly docs)
- Update pynintendoparental requirement to version 2.3.2.1 (nintendo_parental_controls docs) (dependency)
- Fix conversion of data for todo.* actions (todoist docs)
- Bump python-smarttub to 0.0.47 (smarttub docs) (dependency)
- Add missing config flow strings to SmartTub (smarttub docs)
- Remove entity id overwrite for ambient station (ambient_station docs)
- Bump librehardwaremonitor-api to version 1.9.1 (libre_hardware_monitor docs) (dependency)
- Remove double unit of measurement for yardian (yardian docs)
- Fix invalid yardian snaphots (yardian docs)

### BREAKING CHANGES

- Fix redundant off preset in Tuya climate (tuya docs)

## 2026.2.0b5

- Bump fressnapftracker to 0.2.2
- Fix evohome not updating scheduled setpoints in state attrs
- Add guard for Apple TV text focus state
- Fix logic and tests for Alexa Devices utils module

## 2026.2.0b4

- Add missing OUI to Axis integration, discovery would abort with unsup…
- Fix template weather humidity
- Bump bleak-esphome to 3.6.0
- Update compit-inext-api to 0.7.0
- Bump compit-inext-api to 0.8.0
- Bump python-otbr-api to 2.8.0
- Bump growattServer to 1.9.0
- Bump denonavr to 1.3.1
- Bump ZHA to 0.0.89
- Bump yt-dlp to 2026.02.04
- Bump intents
- Add missing codes for Miele coffe systems
- Update frontend to 20260128.6

## 2026.2.0b3

- Remove invalid notification sensors for Alexa devices
- Remove coffee machine's hot water sensor's state class at Home Connect
- Update Senz temperature sensor
- Bump pyhik to 0.4.2
- Fix Shelly xpercent sensor state_class
- Update title and description of YAML dashboard repair
- Add Heiman virtual brand
- Add Heatit virtual brand
- Update frontend to 20260128.5

## 2026.2.0b2

- Fix mired warning in template light
- Bump pyotgw to 2.2.3
- Fix OpenTherm Gateway button availability
- Bump opower to 0.17.0
- Bump uiprotect to version 10.1.0
- Fix Shelly CoIoT repair issue
- Bump reolink-aio to 0.18.2
- Fix KNX fan unique_id for switch-only fans
- Add integration type of hub to vesync
- Fix parse_mode for Telegram bot actions
- Update ical requirement version to 12.1.3
- Remove file description dependency in onedrive
- Bump pymeteoclimatic to 0.1.1
- Bump incomfort-client to 0.6.12
- Fix Miele dishwasher PowerDisk filling level sensor not showing up
- Add learn more data for Analytics in labs
- Update frontend to 20260128.4

## 2026.2.0b1

- Fix validation of actions config in intent_script
- Bump pydexcom to 0.5.1
- Fix use of ambiguous units for reactive power and energy
- Update todoist-api-python to 3.1.0
- Bump intents to 2026.1.28
- Fix string in Namecheap DynamicDNS integration
- Fix action descriptions of alarm_control_panel
- Fix incorrect entity_description class in radarr
- Bump renault-api to 0.5.3
- Bump nibe to 2.22.0
- Update frontend to 20260128.2
- Update fritzconnection to 1.15.1
- Update translations for Telegram bot
- Bump ZHA to 0.0.88
- Fix Control4 HVAC state-to-action mapping
- Update frontend to 20260128.3

## 2026.1.3

- Bump uiprotect to 8.1.1 (unifiprotect docs) (dependency)
- Update list of supported locations for London Air (london_air docs)
- Bump onedrive-personal-sdk to 0.1.0 (onedrive docs) (dependency)
- Fix color temperature attributes in wiz (wiz docs)
- Bump xiaomi-ble to 1.4.3 (xiaomi_ble docs)
- Bump opower to 0.16.4 (opower docs) (dependency)
- Fix detection of multiple smart object types in single event (unifiprotect docs)
- Fix icons for 'moving' state (binary_sensor docs)
- Bump onedrive-personal-sdk to 0.1.1 (onedrive docs) (dependency)
- Bump uiprotect to 10.0.0 (unifiprotect docs) (dependency)
- Bump uiprotect to 10.0.1 (unifiprotect docs) (dependency)
- Bump Insteon panel to 0.6.1 (insteon docs) (dependency)
- Bump music-assistant-client to 1.3.3 (music_assistant docs) (dependency)
- Bump opower to 0.16.5 (opower docs) (dependency)

## 2026.1.2

- Fix Airzone Q-Adapt select entities (airzone docs)
- Bump opower to 0.16.2 (opower docs) (dependency)
- Add support for packaging version >= 26 on the version bump script
- Update PyNaCl to 1.6.2 (owntracks docs) (mobile_app docs) (dependency)
- Bump pyenphase from 2.4.2 to 2.4.3 (enphase_envoy docs) (dependency)
- Bump opower to 0.16.3 (opower docs) (dependency)
- Bump PySrDaliGateway from 0.18.0 to 0.19.3 (sunricher_dali docs) (dependency)
- Add descriptions to openai_conversation (openai_conversation docs)
- Update knx-frontend to 2026.1.15.112308 (knx docs) (dependency)
- Bump aiomealie to 1.2.0 (mealie docs) (dependency)
- Update frontend to 20260107.2 (frontend docs) (dependency)
- Update aioairzone to v1.0.5 (airzone docs) (dependency) 2026.1.0

## 2026.1.0b5

- Fix Ring integration log flooding for accounts without subscription
- Bump ZHA to 0.0.83
- Fix IndexError in Israel Rail sensor when no departures available
- Fix schema validation error in Telegram
- Add SSL support in Bravia TV
- Bump pyTibber to 0.34.1
- Bump solarlog_cli to 0.7.0
- Bump uiprotect to 8.0.0
- Bump intents to 2026.1.6
- Bump python-roborock to 4.2.1
- Remove q7 total cleaning time for Roborock

## 2026.1.0b4

- Fix rain count sensors' state class of Ecowitt
- Add Resideo X2S Smart Thermostat to Matter fan-only mode list
- Fix unit for Tibber sensor
- Bump pyTibber to 0.34.0
- Fix missing state class to solaredge
- Bump opower to 0.16.0
- Fix number or entity choose schema
- Bump pybravia to 0.4.1
- Update frontend to 20251229.1

## 2026.1.0b3

- Add support for health_overview API endpoint to Tractive integration
- Fix Tesla update showing scheduled updates as installing
- Add schema validation for set_hot_water_schedule service
- add description to string vesync
- Update voluptuous and voluptuous-openapi
- Bump total_connect_client to 2025.12.2
- Bump velbusaio to 2026.1.0
- Bump intents to 2026.1.1
- Fix reolink brightness scaling
- Bump velbusaio to 2026.1.1
- Bump pyairobotrest to 0.2.0
- bump pyvlx version to 0.2.27
- Bump python-roborock to 4.2.0
- Remove referral link from fish_audio
- Bump aiohttp 3.13.3
- Bump aiowebdav2 to 0.5.0
- Fix Tuya light color data wrapper
- Add connection check before registering cloudhook URL
- Fix humidifier trigger turned on icon

## 2026.1.0b2

- Update knx-frontend to 2025.12.30.151231
- Bump eternalegypt to 0.0.18
- Fix netgear_lte unloading
- Bump portainer 1.0.19
- Bump aioamazondevices to 11.0.2
- Fix Hikvision thread safety issue when calling async_write_ha_state

## 2026.1.0b1

- Add translation of exceptions in met
- Add integration_type device to netgear
- Add integration_type service to nuheat
- Add integration_type hub to permobil
- Add integration_type hub to pooldose
- Add integration_type hub to poolsense
- Add integration_type device to ps4
- bump xiaomi-ble to 1.4.1
- Fix KNX translation references
- Bump aioesphomeapi to 43.9.1
- Bump Python-Roborock to 4.1.0

## 2025.12.5

- Fix ZeroDivisionError for inverse unit conversions
- Add openid scope and update OAuth2 url:s in senz integration (senz docs)
- Bump insteon panel to 0.6.0 to fix dialog button issues (insteon docs) (dynalite docs) (dependency)
- Bump yalexs-ble to 3.2.2 (august docs) (yalexs_ble docs) (yale docs) (dependency)
- Bump yalexs-ble to 3.2.4 (august docs) (yalexs_ble docs) (yale docs) (dependency)
- Bump melissa to 3.0.3 (melissa docs) (dependency)
- Bump valbusaio to 2025.12.0 (velbus docs) (dependency)
- Bump uiprotect to 7.33.3 (unifiprotect docs) (dependency)
- Fix Ecoforest unknown alarm translation key (ecoforest docs)
- Bump axis to v66 fixing an issue with latest xmltodict (axis docs) (dependency)
- Bump python-roborock to 3.20.1 (roborock docs) (dependency)
- Bump python-roborock to 3.21.1 (roborock docs) (dependency)
- Fix Roborock repair issue behavior (roborock docs)
- Add state_class to Nuki battery sensor (nuki docs)

## 2025.12.4

- Update pynintendoparental to 2.0.0 (nintendo_parental_controls docs)
- Update pynintendoparental to 2.1.0 (nintendo_parental_controls docs)
- Fix Sonos speaker async_offline assertion failure (sonos docs)
- Bump pynintendoparental to 2.1.1 (nintendo_parental_controls docs)
- Bump aioasuswrt 1.5.3 (asuswrt docs)
- Bump aiomealie to 1.1.1 and statically define mealplan entry types (mealie docs)
- Update systembridgeconnector to 5.2.4, fix media source (system_bridge docs)
- Bump ical to 12.1.2 (google docs) (local_calendar docs) (local_todo docs) (remote_calendar docs)
- Update unnecessary error logging of unknown and unavailable source states from mold indicator (mold_indicator docs)
- Add exception handling for rate limited or unauthorized MQTT requests (roborock docs)
- Bump aioasuswrt to 1.5.4 (asuswrt docs)
- Bump blinkpy to 0.25.2 (blink docs)
- Fix slow event state updates for remote calendar (remote_calendar docs)
- Bump aiodns to 3.6.1 (dnsip docs)
- Bump pysmlight to v0.2.13 (smlight docs)
- Bump pynintendoparental 2.1.3 (nintendo_parental_controls docs)
- Bump soco to 0.30.13 for Sonos (sonos docs)
- Bump ekey-bionyxpy to version 1.0.1 (ekeybionyx docs)
- Fix incorrect status updates for lcn (lcn docs)
- Bump python-roborock to 3.18.0 (roborock docs)
- Bump pypck to 0.9.8 (lcn docs)
- Fix AttributeError in Roborock Empty Mode entity (roborock docs)
- Add missing strings for Shelly voltmeter sensor (shelly docs)
- Bump ZHA to 0.0.81 (zha docs)
- Bump python-roborock to 3.19.0 (roborock docs)
- Remove users refresh tokens when the user get's deactivated
- Update frontend to 20251203.3 (frontend docs)

## 2025.12.3

- Fix Tuya BitmapTypeInformation parsing (tuya docs)
- Bump pypck to 0.9.7 (lcn docs)
- Bump blinkpy to 0.25.1 (blink docs) (dependency)
- Fix webhook exception when empty json data is sent (webhook docs)
- Fix roborock off peak electricity timer (roborock docs)
- Add Tuya local_strategy to Tuya diagnostic (tuya docs)
- Fix Matter Door Lock Operating Mode select entity (matter docs)
- Bump asusrouter to 1.21.3 (asuswrt docs)
- Bump hanna-cloud to version 0.0.7 (hanna docs) (dependency)
- Add measurement state class to ohme sensors (ohme docs)
- Bump python-roborock to 3.12.2 (roborock docs) (dependency)
- Add state_class to Growatt power and energy sensors (growatt_server docs)
- Update advanced_options display text for MQTT (mqtt docs)
- Bump google air quality api to 2.0.2 (google_air_quality docs) (dependency)
- Bump ical to 12.1.1 (google docs) (local_calendar docs) (local_todo docs) (remote_calendar docs) (dependency)
- Bump pylamarzocco to 2.2.3 (lamarzocco docs) (dependency)
- Bump pylamarzocco to 2.2.4 (lamarzocco docs) (dependency)
- Bump pySmartThings to 3.5.1 (smartthings docs) (dependency)
- Bump aioasuswrt to 1.5.2 (asuswrt docs) (dependency) 2025.12.2
- fix Lutron Caseta smart away subscription (lutron_caseta docs)
- Fix legacy template entity_id field in migration (template docs)
- Fix secure URLs for promotional game media in Xbox integration (xbox docs)
- Add program id codes for Miele WQ1000 (miele docs)
- Bump pymiele dependency to 0.6.1 (miele docs) (dependency)
- Bump asusrouter to 1.21.1 (asuswrt docs)
- Bump HueBLE to 2.1.0 (hue_ble docs) (dependency)
- Bump python-roborock to 3.10.10 (roborock docs) (dependency)
- Fix description placeholders for system_bridge (system_bridge docs)
- Bump google air quality api to 2.0.0 (google_air_quality docs) (dependency)
- Fix zwave_js service description placeholders (zwave_js docs)
- Fix yeelight service description placeholders (yeelight docs)
- Fix teslemetry service description placeholders (teslemetry docs)
- Fix multiple top-level support for template integration (template docs)
- Bump yt-dlp to 2025.12.08 (media_extractor docs) (dependency)
- Update frontend to 20251203.2 (frontend docs)

## 2025.12.1

- Fix Rituals Perfume Genie (rituals_perfume_genie docs)
- Fix Starlink's ever updating uptime (starlink docs)
- Fix VeSync binary sensor discovery (vesync docs)
- Bump reolink_aio to 0.17.1 (reolink docs) (dependency)
- Add pyanglianwater to Anglian Water loggers (anglian_water docs)
- Fix template migration errors (template docs)
- Fix unit parsing in Tuya climate entities (tuya docs)
- Update template deprecation to be more explicit (template docs)
- Add subscribe preview feature endpoint to labs (labs docs)
- Bump python-Roborock to 3.10.0 (roborock docs) (dependency)
- Bump oralb-ble to 1.0.2 (oralb docs) (dependency)
- Bump evohome-async to 1.0.6 (evohome docs)
- Fix doorbird duplicate unique ID generation (doorbird docs)
- Bump python-roborock to 3.10.2 (roborock docs) (dependency)
- Fix missing template key in deprecation repair (template docs)
- Fix inverted kelvin issue (template docs)
- Bump uiprotect to 7.33.2 (unifiprotect docs) (dependency)
- Update frontend to 20251203.1 (frontend docs)

## 2025.12.0b9

- Bump deebot-client to 17.0.0
- Bump reolink_aio to 0.17.0
- Update frontend to 20251203.0
- Bump Roborock to 3.9.3
- Add retry logic to docker.io image push step

## 2025.12.0b8

- bump iometer to v0.3.0
- Add integration_type to Oralb
- Add final learn more and feedback links for purpose-specific triggers and conditions preview feature

## 2025.12.0b7

- Fix bug in group notify entities when title is missing
- Add storage link to low disk space repair issue
- Fix ping TypeError when killing the process
- Update release URL in WLED
- Bump google-nest-sdm to 9.1.2
- Bump python-roborock to 3.9.2

## 2025.12.0b6

- Fix orphaned devices not being removed during integration startup
- Fix ZHA network formation
- Add integration_type for tedee
- Bump hassil to 3.5.0
- Bump letpot to 0.6.4

## 2025.12.0b5

- Fix Anglian Water sensor setup
- Add occupancy binary sensor triggers
- Add integration_type to Teslemetry manifest
- Add integration_type to Tesla Fleet manifest
- Add integration type to google_translate
- Add integration type to speedtestdotnet
- Add integration type to rest
- Add integration type to ping
- Update frontend to 20251202.0
- Bump intents to 2025.12.2
- Add integration_type for Fronius

## 2025.12.0b4

- Add labs_updated event to subscription allowlist
- Add program id:s and phases to new Miele WQ1000
- Add integration_type to Apple TV manifest
- Add integration_type to Ecowitt manifest
- Add integration_type to Home Connect manifest
- Add integration_type to HomeKit Device manifest
- Add integration_type to Reolink manifest
- Add integration_type to SmartThings manifest
- Add integration_type to Sonos manifest
- Add integration_type to SwitchBot Bluetooth manifest
- Add integration_type to Tessie manifest
- Add integration_type to HomeWizard Energy manifest
- Add integration_type to Konnected.io manifest
- Add integration_type to Motionblinds manifest
- Add integration_type to Nuki Bridge manifest
- Bump pyvesync to 3.3.3
- Add integration type to met
- Add integration type to dlna_dms
- Add integration type to music_assistant
- Add integration type to google
- Add integration type to dlna_dmr
- Add integration type to ibeacon
- Add integration type to tplink
- Add integration type to webostv
- Add integration type to roborock
- Add integration type to ring
- Add integration type to broadlink
- Add integration type to xiaomi_ble

## 2025.12.0b3

- Fix strings in Google Air Quality
- Add tools in default agent also in fallback pipeline
- bump: youtubeaio to 2.1.1
- Remove unnecessary instanciating in Tuya find_dpcode
- Fix blocking call in Tuya initialisation
- Add loggers to senz manifest
- Add missing string for Shelly away mode switch
- Remove name for Shelly gas valve (gen1) entity
- Remove name from Shelly RGBCCT sensors
- Fix subentry ID is not updated when renaming the entity ID
- Bump pyenphase to 2.4.2
- Bump ESPHome stable BLE version to 2025.11.0
- Bump python-roborock to 3.8.3
- Fix UniFi Protect RTSP repair warnings when globally disabled
- Bump python-roborock to 3.8.4
- Fix MQTT entity cannot be renamed
- Bump uiprotect to 7.31.0
- Bump google air quality api to 1.1.3
- Bump aioesphomeapi to 42.9.0
- Bump google-nest-sdm to 9.1.1
- Bump bosch-alarm-mode2 to v0.4.10
- Fix spelling of "to set up" in hue_ble
- Fix spelling of "to log in" in anglian_water
- Bump pyvesync to 3.3.2
- Bump thinqconnect to 1.0.9
- Bump floor registry to version 1.3 and sort floors
- Fix user store not loaded on restart
- Remove description_configured from condition and trigger translations
- Remove cover triggers
- Bump aioshelly to version 13.22.0
- Bump area registry to version 1.9 and sort areas
- Update frontend to 20251201.0
- Add code mappings for Miele WQ1000
- bump yt-dlp to 2025.11.12

## 2025.12.0b2

- Fix MAC address mix-ups between WLED devices
- Bump python-roborock to 3.8.1
- Fix Anthropic init with incorrect model
- Fix Shelly support for button5 trigger
- Update frontend to 20251127.0
- Update roborock test typing
- Fix regression in roborock image entity naming

## 2025.12.0b1

- Add climate started_cooling and started_drying triggers
- Fix parsing of Tuya electricity RAW values
- Remove old roborock map storage
- Bump reolink-aio to 0.16.6
- Bump hass-nabucasa from 1.6.1 to 1.6.2
- Fix state classes of Ecowitt rain sensors
- Bump renault-api to 0.5.1

## 2025.11.3

- Bump version of python_awair to 0.2.5 (awair docs) (dependency)
- Fix args passed to check_config script
- update methods to non deprecated methods in vesync (vesync docs)
- Fix wrong BrowseError module in Kode (kodi docs)
- Bump universal-silabs-flasher to v0.1.0 (homeassistant_yellow docs) (homeassistant_sky_connect docs) (homeassistant_hardware docs) (homeassistant_connect_zbt2 docs) (dependency)
- Bump pyiCloud to 2.2.0 (icloud docs) (dependency)
- Fix is_matching in samsungtv config flow (samsungtv docs)
- Bump async-upnp-client to 0.46.0 (upnp docs) (yeelight docs) (dlna_dmr docs) (samsungtv docs) (ssdp docs) (dlna_dms docs) (dependency)
- Bump tplink-omada-api to 1.5.3 (tplink_omada docs) (dependency)
- Fix missing description placeholders in MQTT subentry flow (mqtt docs)
- Fix missing temperature_delta device class translations (mqtt docs) (template docs) (sql docs) (scrape docs) (random docs)
- Fix blocking call in cync (cync docs)
- Fix hvv_departures to pass config_entry explicitly to DataUpdateCoordinator (hvv_departures docs)
- Bump aioautomower to 2.7.1 (husqvarna_automower docs) (dependency)
- Bump pySmartThings to 3.3.4 (smartthings docs)
- Bump universal-silabs-flasher to 0.1.2 (homeassistant_hardware docs)
- Bump onedrive-personal-sdk to 0.0.17 (onedrive docs) (dependency)
- Bump aiounifi to 88 (unifi docs)
- Bump go2rtc to 1.9.12 and go2rtc-client to 0.3.0 (go2rtc docs) (dependency)
- Update frontend to 20251105.1 (frontend docs) (dependency)

### BREAKING CHANGES

- Bump ohmepy and remove advanced_settings_coordinator (ohme docs) (dependency)

## 2025.11.2

- Bump cronsim to 2.7 ([utility_meter docs]) (backup docs) (dependency)
- Remove arbitrary forecast limit for meteo_lt (meteo_lt docs)
- Fix progress step bugs
- Bump pyportainer 1.0.13 (portainer docs) (dependency)
- Bump pyportainter 1.0.14 (portainer docs) (dependency)
- Bump aio-ownet to 0.0.5 (onewire docs) (dependency)
- Fix MFA Notify setup flow schema
- Update xknx to 3.10.1 (knx docs) (dependency)
- Fix set_absolute_position angle (motion_blinds docs)
- Fix config flow reconfigure for Comelit (comelit docs)
- Bump pyvesync to 3.2.1 ([vesync docs]) (dependency)
- Fix Climate state reproduction when target temperature is None (climate docs)
- Bump pypalazzetti lib from 0.1.19 to 0.1.20 (palazzetti docs) (dependency)
- Bump pySmartThings to 3.3.2 ([smartthings docs]) (dependency)
- Fix support for Hyperion 2.1.1 (hyperion docs)
- Update pyMill to 0.14.1 (mill docs) (dependency)
- Fix update progress in Teslemetry ([teslemetry docs])
- Bump pyvesync to 3.2.2 ([vesync docs]) (dependency)
- Fix lamarzocco update status (lamarzocco docs)
- Add firmware flashing debug loggers to hardware integrations (homeassistant_yellow docs) (homeassistant_sky_connect docs) (homeassistant_connect_zbt2 docs)
- Update Home Assistant base image to 2025.11.0 (dependency)
- Bump pySmartThings to 3.3.3 ([smartthings docs]) (dependency)
- Update bsblan to python-bsblan version 3.1.1 (bsblan docs) (dependency)
- Bump reolink-aio to 0.16.5 (reolink docs) (dependency)
- Bump python-open-router to 0.3.3 (open_router docs) (dependency)
- Bump ZHA to 0.0.78 ([zha docs]) (dependency)
- Bump ZHA to 0.0.79 ([zha docs]) (dependency)
- Fix sfr_box entry reload (sfr_box docs)
- Fix model_id in Husqvarna Automower (husqvarna_automower docs)
- Add debounce to Alexa Devices coordinator (alexa_devices docs)

## 2025.11.1

- Remove decorator from ZHA and Hardware integration (zha docs) (homeassistant_hardware docs)
- Fix KNX Climate humidity DPT (knx docs)
- Fix for corrupt restored state in miele consumption sensors (miele docs)
- Fix SolarEdge unload failing when there are no sensors (solaredge docs)
- Bump aioamazondevices to 8.0.1 (alexa_devices docs) (dependency)
- Fix Growatt integration authentication error for legacy config entries (growatt_server docs)
- Bump tuya-device-sharing-sdk to 0.2.5 (tuya docs) (dependency)
- Bump onedrive-personal-sdk to 0.0.16 (onedrive docs) (dependency)
- Fix the exception caused by the missing Foscam integration key (foscam docs)
- Bump intents to 2025.11.7 (conversation docs) (dependency)

## 2025.11.0b6

- Update frontend to 20251105.0

## 2025.11.0b5

- Add progress to ZHA migration steps
- Bump holidays to 0.84
- Bump pylitterbot to 2025.0.0
- Bump libpyfoscamcgi to 0.0.9
- Fix ESPHome config entry unload

## 2025.11.0b4

- Fix non-unique ZHA serial port paths and migrate USB integration to always list unique paths
- Remove Enmax Energy virtual integration
- Add ZHA migration retry steps for unplugged adapters
- Fix ZBT-2 Thread to Zigbee migration discovery failing
- Fix Ambient Weather incorrect state classes
- Bump Tesla Fleet API to v1.2.5
- Bump ZHA to 0.0.77
- Update python-smarttub to 0.0.45
- Bump reolink-aio to 0.16.4
- Update frontend to 20251104.0

## 2025.11.0b3

- Bump aioamazondevices to 6.5.6
- Update frontend to 2025110.0

## 2025.11.0b2

- Fix Shelly irrigation zone ID retrieval with Sleepy devices
- Bump uv to 0.9.6
- Bump pyvesync to 3.1.4
- Bump eheimdigital to 1.4.0
- Bump onedrive-personal-sdk to 0.0.15
- Update pynintendoparental to version 1.1.3
- Update knx-frontend to 2025.10.31.195356
- Bump deebot-client to 16.2.0
- Fix device tracker name & icon for Volvo integration
- Bump deebot-client to 16.3.0
- Fix KNX climate loading min/max temp from UI config
- Bump reolink_aio to 0.16.3
- fix vesync mist level value
- Bump python-open-router to 0.3.2

## 2025.11.0b1

- Bump pyportainer 1.0.12
- Bump PyCync to 0.4.3
- Bump librehardwaremonitor-api to 1.5.0
- Update frontend to 20251029.1

## 2025.10.4

- Bump aioautomower to v2.3.1 (husqvarna_automower docs)
- Fix history coordinator in Tesla Fleet and Teslemetry (teslemetry docs) (tesla_fleet docs)
- Bump pyprobeplus to 1.1.1 (probe_plus docs) (dependency)
- Fix units for Shelly TopAC EVE01-11 sensors (shelly docs)
- Fix pterodactyl server config link (pterodactyl docs)
- Remove opower violation from hassfest requirements check
- Bump opower to 0.15.8 (opower docs) (dependency)
- Bump bring-api to v1.1.1 (bring docs) (dependency)
- Bump PyCync to 0.4.2 (cync docs) (dependency)
- Bump aioamazondevices to 6.4.6 (alexa_devices docs) (dependency)
- Fix BrowseError import in yamaha_musiccast media_player.py ([yamaha_musiccast docs])
- Remove async-modbus exception from hassfest requirements check
- Add SensorDeviceClass and unit for LCN humidity sensor. (lcn docs)
- Add shared BleakScanner to probe_plus (probe_plus docs) (dependency)
- Update aioairzone to v1.0.2 (airzone docs) (dependency)
- Bump pydroplet version to 2.3.4 (droplet docs) (dependency)
- Bump holidays to 0.83 ([workday docs]) (holiday docs) (dependency)

## 2025.10.3

- Bump aioasuswrt to 1.5.1 (asuswrt docs) (dependency)
- Remove redudant state write in Smart Meter Texas (smart_meter_texas docs)
- Fix state class for Overkiz water consumption (overkiz docs)
- Bump frontend 20251001.4 (frontend docs)
- Bump aioamazondevices to 6.4.1 (alexa_devices docs) (dependency)
- Remove URL from ViCare strings.json ([vicare docs])
- Fix August integration to handle unavailable OAuth implementation at startup (august docs)
- Fix Yale integration to handle unavailable OAuth implementation at startup ([yale docs])
- Add description placeholders in Uptime Kuma config flow ([uptime_kuma docs])
- Add description placeholders to pyLoad config flow (pyload docs)
- Fix home wiziard total increasing sensors returning 0 (homewizard docs)
- Bump pyprobeplus to 1.1.0 (probe_plus docs) (dependency)
- Update Snoo strings.json to include weaning_baseline (snoo docs)
- Bump aioamazondevices to 6.4.3 (alexa_devices docs) (dependency)
- Fix Bluetooth discovery for devices with alternating advertisement names (bluetooth docs)
- Bump opower to 0.15.7 (opower docs) (dependency)
- update pysqueezebox lib to 0.13.0 (squeezebox docs) (dependency)
- Bump aioairq to 0.4.7 (airq docs) (dependency)
- Bump aiocomelit to 1.1.2 (comelit docs) (dependency)
- Add missinglong_press entry for trigger_type in strings.json for Hue (hue docs)
- Bump aioamazondevices to 6.4.4 (alexa_devices docs) (dependency)
- Bump pyvesync version to 3.1.2 ([vesync docs]) (dependency)

## 2025.10.2

- Fix power device classes for system bridge ([system_bridge docs])
- Bump PyCync to 0.4.1 ([cync docs]) (dependency)
- Bump python-roborock to 2.50.2 ([roborock docs]) (dependency)
- Bump aioamazondevices to 6.2.8 ([alexa_devices docs]) (dependency)
- Fix MQTT Lock state reset to unknown when a reset payload is received ([mqtt docs])
- Fix ViCare pressure sensors missing unit of measurement ([vicare docs])
- Bump pyvesync to 3.1.0 ([vesync docs]) (dependency)
- Bump opower to 0.15.6 ([opower docs]) (dependency)
- Fix missing google_assistant_sdk.send_text_command ([google_assistant_sdk docs])
- Bump airOS to 0.5.5 using formdata for v6 firmware ([airos docs]) (dependency)
- Fix sensors availability check for Alexa Devices ([alexa_devices docs])
- Bump aioamazondevices to 6.2.9 ([alexa_devices docs])
- Remove stale entities from Alexa Devices ([alexa_devices docs])
- Fix Tuya cover position when only control is available ([tuya docs])
- Bump pySmartThings to 3.3.1 ([smartthings docs]) (dependency)
- Add motion presets to SmartThings AC ([smartthings docs])
- Fix delay_on and auto_off with multiple triggers ([template docs])
- Fix PIN validation for Comelit SimpleHome ([comelit docs])
- Bump aiocomelit to 1.1.1 ([comelit docs]) (dependency)
- Add plate_count for Miele KM7575 ([miele docs])
- Fix restore cover state for Comelit SimpleHome ([comelit docs])
- fix typo in icon assignment of AccuWeather integration ([accuweather docs])
- Add missing translation string for Satel Integra subentry type ([satel_integra docs])
- Fix HA hardware configuration message for Thread without HAOS ([homeassistant_hardware docs])
- Bump pylamarzocco to 2.1.2 ([lamarzocco docs]) (dependency)
- Bump holidays to 0.82 ([workday docs]) ([holiday docs]) (dependency)
- Fix update interval for AccuWeather hourly forecast ([accuweather docs])
- Bump env-canada to 0.11.3 ([environment_canada docs])
- Fix empty llm api list in chat log ([conversation docs])
- Bump aioamazondevices to 6.4.0 ([alexa_devices docs]) (dependency)
- Bump brother to version 5.1.1 ([brother docs]) (dependency)
- Fix for multiple Lyrion Music Server on a single Home Assistant server for Squeezebox ([squeezebox docs])
- Add missing entity category and icons for smlight integration ([smlight docs])
- Update frontend to 20251001.2 ([frontend docs]) (dependency)
- Bump deebot-client to 15.1.0 ([ecovacs docs]) (dependency)
- Fix Shelly RPC cover update when the device is not initialized ([shelly docs])
- Fix shelly remove orphaned entities ([shelly docs])

## 2025.10.1

- Bump airOS dependency (airos docs) (dependency)
- Bump airOS module for alternative login url (airos docs) (dependency)
- Bump aiohasupervisor to 0.3.3 (hassio docs) (dependency)
- Fix Nord Pool 15 minute interval (nordpool docs)
- Add Roborock mop intensity translations (roborock docs)
- Bump python-roborock to 2.49.1 (roborock docs) (dependency)
- Bump pyportainer 1.0.2 (portainer docs) (dependency)
- Bump pyportainer 1.0.3 (portainer docs) (dependency)
- Fix Satel Integra creating new binary sensors on YAML import (satel_integra docs)
- Update markdown field description in ntfy integration (ntfy docs)
- Fix Z-Wave RGB light turn on causing rare ZeroDivisionError (zwave_js docs)
- Bump aiohomekit to 3.2.19 (homekit_controller docs) (dependency)
- Fix sentence-casing in user-facing strings of slack (slack docs)
- Add missing translation for media browser default title (media_source docs)
- Fix missing powerconsumptionreport in Smartthings (smartthings docs)
- Update Home Assistant base image to 2025.10.0 (dependency)
- Add translation for turbo fan mode in SmartThings (smartthings docs)
- Fix next event in workday calendar (workday docs)
- Update OVOEnergy to 3.0.1 (ovo_energy docs) (dependency)
- Fix missing parameter pass in onedrive (onedrive docs)
- Bump pyTibber to 0.32.2 (tibber docs) (dependency)
- Bump reolink-aio to 0.16.1 (reolink docs) (dependency)
- Fix VeSync zero fan speed handling (vesync docs)
- Bump universal-silabs-flasher to 0.0.35 (homeassistant_hardware docs) (dependency)

## 2025.10.0b7

- Bump intents to 2025.10.1

## 2025.10.0b6

- Fix Sonos Dialog Select type conversion part II
- Fix ZHA unable to select "none" flow control
- Bump yt-dlp to 2025.09.26
- Add analytics platform to wled
- Bump aioecowitt to 2025.9.2
- Add Eltako brand
- Add Level brand
- Add Konnected brand
- Fix Bayesian ConfigFlow templates in 2025.10
- Update frontend to 20251001.0
- Add analytics platform to esphome

## 2025.10.0b5

- Add Shelly EV charger sensors
- Fix: Set EPH climate heating as on only when boiler is actively heating
- Add consumed energy sensor for Shelly pm1 and switch components
- Fix for Hue Integration motion aware areas
- Fix can exclude optional holidays in workday
- Remove redundant code for Alexa Devices
- Add timeout to dnsip (to handle stale connections)
- Bump deebot-client to 15.0.0
- Fix event range in workday calendar
- Fix entities not being created when adding subentries for Satel Integra
- Add missing translations for Model Context Protocol integration
- Bump reolink-aio to 0.16.0
- Add newly added cpu temperatures to diagnostics in FRITZ!Tools
- Bump aioamazondevices to 6.2.7
- Add hardware Zigbee flow strategy
- Add missing translation strings for added sensor device classes pm4 and reactive energy

## 2025.10.0b4

- Update Home Assistant base image to 2025.09.3

## 2025.10.0b3

- Add SSL options during config_flow for airOS
- Fix EZVIZ devices merging due to empty MAC addr
- Fix PIN failure if starting with 0 for Comelit SimpleHome
- Bump aiorussound to 4.8.2
- Bump ZHA to 0.0.73
- Bump aioesphomeapi to 41.11.0
- Bump to home-assistant/wheels
- Bump pylamarzocco to 2.1.1
- Update Home Assistant base image to 2025.09.2
- Fix Thread flow abort on multiple flows
- Update frontend to 20250926.0
- Add None-check for VeSync fan device.state.display_status

## 2025.10.0b2

- Update mvglive component
- Remove deprecated sensors and update remaining for Alexa Devices
- Bump accuweather to version 4.2.2
- Bump aioesphomeapi to 41.10.0
- Bump pySmartThings to 3.3.0
- Fix incorrect Roborock test
- Update frontend to 20250925.1

## 2025.10.0b1

- Fix logical error when user has no Roborock maps
- Update IQS to platinum for Alexa Devices
- Update IQS to platinum for Comelit SimpleHome
- Fix ESPHome reauth not being triggered on incorrect password
- Bump aioesphomeapi to 41.9.3 to fix segfault
- Bump to home-assistant/wheels
- Bump aioesphomeapi to 41.9.4
- Remove some more domains from common controls
- Bump librehardwaremonitor-api to version 1.4.0
- Update frontend to 20250925.0

### BREAKING CHANGES

- Add block Spook < 4.0.0 as breaking Home Assistant

## 2025.9.4

- Bump habiticalib to v0.4.4 (habitica docs) (dependency)
- Bump habiticalib to v0.4.5 (habitica docs) (dependency)
- Fix bug with the hardcoded configuration_url (asuswrt) (asuswrt docs)
- Fix HomeKit Controller overwhelming resource-limited devices by batching characteristic polling (homekit_controller docs)
- Bump aiohomekit to 3.2.16 (homekit_controller docs) (dependency)
- Bump bluetooth-auto-recovery to 1.5.3 (bluetooth docs) (dependency)
- Add proper error handling for /actions endpoint for miele (miele docs)
- Bump aiohomekit to 3.2.17 (homekit_controller docs) (dependency)
- Update authorization server to prefer absolute urls (auth docs)
- Bump imeon_inverter_api to 0.4.0 (imeon_inverter docs) (dependency)
- Bump pylamarzocco to 2.1.0 (lamarzocco docs) (dependency)
- Add La Marzocco specific client headers (lamarzocco docs)
- Fix KNX UI schema missing DPT (knx docs)
- Bump pyemoncms to 0.1.3 (emoncms docs) (emoncms_history docs) (dependency)
- Fix Sonos set_volume float precision issue (sonos docs)
- Bump opower to 0.15.5 (opower docs) (dependency)
- Bump holidays to 0.80 (workday docs) (holiday docs) (dependency)
- Bump holidays to 0.81 (workday docs) (holiday docs) (dependency)
- Bump asusrouter to 1.21.0 (asuswrt docs) (dependency)

## 2025.9.3

- Bump habluetooth to 5.6.4 (bluetooth docs)

## 2025.9.2

- Fix XMPP not working with non-TLS servers ([xmpp docs])
- Update SharkIQ authentication method ([sharkiq docs]) (dependency)
- Add event entity on websocket ready in Husqvarna Automower ([husqvarna_automower docs])
- Fix Aladdin Connect state not updating ([aladdin_connect docs])
- Fix support for Ecowitt soil moisture sensors ([ecowitt docs])
- Fix update of the entity ID does not clean up an old restored state
- Remove device class for Matter NitrogenDioxideSensor ([matter docs])
- Bump habluetooth to 5.3.1 ([bluetooth docs]) (dependency)
- Fix KNX BinarySensor config_store data ([knx docs])
- Fix KNX Light - individual color initialisation from UI config ([knx docs])
- Bump pydrawise to 2025.9.0 ([hydrawise docs])
- Bump aioharmony to 0.5.3 ([harmony docs]) (dependency)
- Update pysmarty2 to 0.10.3 ([smarty docs])
- fix rain sensor for Velux GPU windows ([velux docs])
- Bump aioecowitt to 2025.9.1 ([ecowitt docs]) (dependency)
- Bump aiontfy to v0.5.5 ([ntfy docs]) (dependency)
- Bump aiolifx-themes to 1.0.2 to support newer LIFX devices ([lifx docs]) (dependency)
- Bump aiovodafone to 1.2.1 ([vodafone_station docs]) (dependency)
- Fix _is_valid_suggested_unit in sensor platform ([sensor docs]) ([tuya docs])
- Bump habluetooth to 5.5.1 ([bluetooth docs]) (dependency)
- Bump bleak-esphome to 3.3.0 ([esphome docs]) ([eq3btsmart docs]) ([bluetooth docs]) (dependency)
- Bump habluetooth to 5.6.0 ([bluetooth docs]) (dependency)
- Fix invalid logger in Tuya ([tuya docs])
- Fix for squeezebox track content_type ([squeezebox docs])
- Fix playlist media_class_filter in search_media for squeezebox ([squeezebox docs])
- Bump habluetooth to 5.6.2 ([bluetooth docs]) (dependency)
- Bump yt-dlp to 2025.09.05 ([media_extractor docs]) (dependency)
- Bump accuweather to version 4.2.1 ([accuweather docs]) (dependency)
- Fix HomeKit Controller stale values at startup ([homekit_controller docs])
- Fix duplicated IP port usage in Govee Light Local ([govee_light_local docs])
- Fix DoorBird being updated with wrong IP addresses during discovery ([doorbird docs])
- Fix supported _color_modes attribute not set for on/off MQTT JSON light ([mqtt docs])
- Fix reauth for Alexa Devices ([alexa_devices docs])
- Bump hass-nabucasa from 1.1.0 to 1.1.1 ([cloud docs]) (dependency)
- Update frontend to 20250903.5 ([frontend docs]) (dependency)

## 2025.9.1

- Add support for migrated Hue bridge (hue docs)
- Add missing device trigger duration localizations (fan docs) (switch docs) (light docs) (remote docs) (update docs)
- Fix Sonos Dialog Select type conversion (sonos docs)
- Fix WebSocket proxy for add-ons not forwarding ping/pong frame data (hassio docs)
- Fix, entities stay unavailable after timeout error, Imeon inverter integration (imeon_inverter docs)
- Bump aiohue to 4.7.5 (hue docs) (dependency)
- Update frontend to 20250903.3 (frontend docs) (dependency)
- Bump ohmepy version to 1.5.2 (ohme docs) (dependency)
- Update Mill library 0.13.1 (mill docs) (dependency)
- Bump pyschlage to 2025.9.0 (schlage docs)
- Bump bimmer_connected to 0.17.3 (bmw_connected_drive docs) (dependency)
- Fix recognition of entity names in default agent with interpunction (conversation docs)
- Fix enable/disable entity in modbus (modbus docs)

## 2025.9.0b6

- Fix for deCONZ issue - Detected that integration 'deconz' calls device_registry.async_get_or_create referencing a non existing via_device
- Fix naming of "State of charge" sensor in growatt_server
- Bump intents
- Update frontend to 20250903.2

## 2025.9.0b5

- Fix racing bug in slave entities in Modbus
- Bump hass-nabucasa from 1.0.0 to 1.1.0
- Bump aioecowitt to 2025.9.0
- Update frontend to 20250903.0
- Bump device registry version to 1.12
- Update frontend to 20250903.1

## 2025.9.0b4

- Remove config entry from device instead of deleting in Uptime robot
- Bump volvocarsapi to v0.4.2
- Update Home Assistant base image to 2025.09.0
- Update frontend to 20250902.1

## 2025.9.0b3

- Fix sort order in media browser for music assistant integration
- Fix wrong description for numeric_state observation in bayesian
- Fix add checks for None values and check if DHW is available
- Bump pyiskra to 0.1.26
- Update Pooldose quality scale
- Remove the vulcan integration
- Bump aiomealie to 0.10.2
- Fix typo in const.py for Imeon inverter integration
- Update frontend to 20250901.0
- Remove mac address from Pooldose device
- Add back missing controller cleanup to Govee Light Local

## 2025.9.0b2

- Fix bug with the wrong temperature scale on new router firmware (asuswrt)
- Fix typo in Meteo France mappings
- Update frontend to 20250829.0
- Bump habluetooth to 5.2.1
- Fix play media example data
- Bump intents to 2025.8.29
- Bump aiopurpleair to 2025.08.1
- Bump aioautomower to 2.2.1
- Fix Yale Access Bluetooth key discovery timing issues
- Fix history startup failures
- Bump opower to 0.15.4
- Bump bluetooth-adapters to 2.1.0 and habluetooth to 5.3.0
- Fix backup manager delete backup error filter

## 2025.9.0b1

- Add multiple NICs in govee_light_local
- Fix direct message notifiers in PlayStation Network
- Fix spelling in bayesian strings
- Fix endpoint deprecation warning in Mastodon
- Remove uv.lock
- Fix ONVIF not displaying sensor and binary_sensor entity names
- Fix exception countries migration for Alexa Devices
- Add missing state class to Alexa Devices sensors
- Fix Reolink duplicates due to wrong merge
- Fix Z-Wave duplicate notification binary sensors
- Bump asusrouter to 1.20.1
- Fix restoring disabled_by flag of deleted devices
- Bump nexia to 2.11.0
- Update frontend to 20250828.0
- Bump deebot-client to 13.7.0
- Bump habluetooth to 5.2.0
- Bump bleak-retry-connector to 4.4.3
- Bump airOS to 0.4.4
- Bump reolink-aio to 0.15.0
- Bump nexia to 2.11.1
- Bump bleak-esphome to 3.2.0
- Bump aioesphomeapi to 39.0.1

## 2025.8.3

- Bump to zcc-helper==3.6 (zimi docs)
- fix(amberelectric): add request timeouts (amberelectric docs)
- Bump renault-api to 0.4.0 (renault docs)
- Update hassfest package exceptions
- Bump boschshcpy to 0.2.107 (bosch_shc docs)
- Fix for bosch_shc: 'device_registry.async_get_or_create' referencing a non existing 'via_device' (bosch_shc docs)
- Fix volume step error in Squeezebox media player (squeezebox docs)
- Bump opower to 0.15.2 (opower docs)
- Bump yt-dlp to 2025.08.11 (media_extractor docs)
- Bump holidays to 0.79 (workday docs) (holiday docs)
- Bump aiorussound to 4.8.1 (russound_rio docs)
- Add missing unsupported reasons to list (hassio docs)
- Fix icloud service calls (icloud docs)
- Bump pysmartthings to 3.2.9 (smartthings docs)
- Fix PWA theme color to match darker blue color scheme in 2025.8 (frontend docs)
- Bump bleak-retry-connector to 4.0.2 (bluetooth docs)
- update pyatmo to v9.2.3 (netatmo docs)
- Fix structured output object selector conversion for OpenAI (openai_conversation docs)
- Bump ESPHome minimum stable BLE version to 2025.8.0 (esphome docs)
- Bump imgw-pib to version 1.5.4 (imgw_pib docs)
- Fix update retry for Imeon inverter integration (imeon_inverter docs)
- Bump python-mystrom to 2.5.0 (mystrom docs)
- Bump onvif-zeep-async to 4.0.4 (onvif docs)
- Update frontend to 20250811.1 (frontend docs)

## 2025.8.2

- Add pymodbus to package constraints
- Fix enphase_envoy non existing via device warning at first config. (enphase_envoy docs)
- Bump habiticalib to version 0.4.2 (habitica docs) (dependency)
- Fix optimistic set to false for template entities (template docs)
- Fix error of the Powerfox integration in combination with the new Powerfox FLOW adapter (powerfox docs)
- Bump python-snoo to 0.7.0 (snoo docs) (dependency)
- Fix brightness command not sent when in white color mode (tuya docs)
- Bump cookidoo-api to 0.14.0 (cookidoo docs) (dependency)
- Fix YoLink valve state when device running in class A mode (yolink docs)
- Fix re-auth flow for Volvo integration (volvo docs)
- Add missing boost2 code for Miele hobs (miele docs)
- Bump airOS to 0.2.8 (airos docs) (dependency)
- Bump aiowebostv to 0.7.5 (webostv docs) (dependency)
- Bump bleak-retry-connector to 4.0.1 (bluetooth docs) (dependency)
- Bump aiodhcpwatcher to 1.2.1 (dhcp docs) (dependency)
- Bump python-snoo to 0.8.1 (snoo docs) (dependency)
- Bump uv to 0.8.9 (dependency)
- Bump python-snoo to 0.8.2 (snoo docs) (dependency)
- Bump pymiele to 0.5.3 (miele docs) (dependency)
- Bump pymiele to 0.5.4 (miele docs) (dependency)
- Bump airOS to 0.2.11 (airos docs) (dependency)
- Bump uiprotect to 7.21.1 (unifiprotect docs) (dependency)
- Bump onvif-zeep-async to 4.0.3 (onvif docs) (dependency)
- Bump python-snoo to 0.8.3 (snoo docs) (dependency)
- Fix missing labels for subdiv in workday (workday docs)

## 2025.8.1

- Fix Enigma2 startup hang (enigma2 docs)
- Fix dialog enhancement switch for Sonos Arc Ultra (sonos docs)
- Bump ZHA to 0.0.67 (zha docs) (dependency)
- Bump airOS to 0.2.6 improving device class matching more devices (airos docs) (dependency)
- Fix Progettihwsw config flow (progettihwsw docs)
- Bump imgw_pib to version 1.5.3 (imgw_pib docs) (dependency)
- Fix description of button.press action (button docs)
- Bump ZHA to 0.0.68 (zha docs) (dependency)
- Bump hass-nabucasa from 0.111.1 to 0.111.2 (cloud docs) (dependency)
- Fix JSON serialization for ZHA diagnostics download (zha docs)
- Fix Tibber coordinator ContextVar warning (tibber docs)
- Fix handing for zero volume error in Squeezebox (squeezebox docs)
- Fix error on startup when no Apps or Radio plugins are installed for Squeezebox (squeezebox docs)
- Add GPT-5 support (openai_conversation docs)
- Remove misleading "the" from Launch Library configuration (launch_library docs)
- Bump airOS to 0.2.7 supporting firmware 8.7.11 (airos docs) (dependency)
- Update knx-frontend to 2025.8.9.63154 (knx docs) (dependency)
- Update frontend to 20250811.0 (frontend docs) (dependency)
- Fix issue with Tuya suggested unit (tuya docs)

## 2025.8.0b5

- Fix zero-argument functions with as_function
- Fix update coordinator ContextVar log for custom integrations
- Bump holidays to 0.78
- Update frontend to 20250806.0

## 2025.8.0b4

- Fix PG&E and Duquesne Light Company in Opower
- Add missing translations for unhealthy Supervisor issues
- Update frontend to 20250805.0
- Bump reolink-aio to 0.14.6
- Fix template sensor uom string
- Remove matter vacuum battery level attribute
- Bump axis to v65
- Bump soco to 0.30.11
- Bump yalexs to 8.11.1
- Bump habluetooth to 4.0.2
- Bump pyswitchbot to 0.68.3
- Bump ZHA to 0.0.66
- Bump hass-nabucasa from 0.111.0 to 0.111.1
- Update knx-frontend to 2025.8.6.52906
- Remove tuya vacuum battery level attribute
- Add Tuya debug logging for new devices
- Fix hassio tests by only mocking supervisor id

## 2025.8.0b3

- Update sensor icons in Volvo integration
- Add translation strings for unsupported OS version
- Bump python-airos to 0.2.4
- Bump aiomealie to 0.10.1
- Fix options for error sensor in Husqvarna Automower
- Bump yt-dlp to 2025.07.21
- Fix credit sensor when there are no vehicles in Teslemetry
- Fix DeviceEntry.suggested_area deprecation warning
- Bump hass-nabucasa from 0.110.0 to 0.110.1
- Fix optimistic covers
- Fix Tuya fan speeds with numeric values
- Bump zwave-js-server-python to 0.67.1
- Bump hass-nabucasa from 0.110.1 to 0.111.0
- Bump deebot-client to 13.6.0
- Bump icalendar from 6.1.0 to 6.3.1 for CalDav
- Update knx-frontend to 2025.8.4.154919
- Bump aioautomower to 2.1.2
- Bump wyoming to 1.7.2
- Fix Z-Wave duplicate provisioned device

## 2025.8.0b2

- Fix ZHA ContextVar deprecation by passing config_entry
- Bump aioesphomeapi to 37.2.2
- Bump pylitterbot to 2024.2.3
- Bump motionblinds to 0.6.30
- Bump VoIP utils to 0.3.4
- Fix tuya light supported color modes
- Fix descriptions for template number fields
- Add scopes in config flow auth request for Volvo integration
- Add translation for absolute_humidity device class to template
- Add translation for absolute_humidity device class to random
- Add translation for absolute_humidity device class to mqtt
- Update reference for volatile_organic_compounds_parts in template
- Fix initialisation of Apps and Radios list for Squeezebox
- Fix Z-Wave config entry state conditions in listen task
- Update denonavr to 1.1.2
- Fix Miele hob translation keys
- Bump python-open-router to 0.3.1
- Fix Z-Wave handling of driver ready event
- Bump imgw_pib to version 1.5.2
- Bump yalexs-ble to 3.1.2
- Bump aiodiscover to 2.7.1
- Bump dbus-fast to 2.44.3
- Bump ZHA to 0.0.65
- Fix flaky velbus test
- Fix add_suggested_values_to_schema when the schema has sections
- Add diagnostics to UISP AirOS

## 2025.8.0b1

- Fix translation string reference for MQTT climate subentry option
- Bump intents to 2025.7.30
- Bump ZHA to 0.0.64
- Fix KeyError in friends coordinator
- Fix ContextVar deprecation warning in homeassistant_hardware integration
- Add translations for all fields in template integration
- Bump reolink-aio to 0.14.5
- Add missing translations for miele dishwasher
- Fix inconsistent use of the term 'target' and a typo in MQTT translation strings
- Fix typo in backup log message
- Fix Miele induction hob empty state
- Fix bug when interpreting miele action response
- Fix ESPHome unnecessary probing on DHCP discovery
- Bump aioesphomeapi to 37.1.6
- Bump aioesphomeapi to 37.2.0
- Fix unique_id in config validation for legacy weather platform
- Update frontend to 20250731.0
- Fix kitchen_sink option flow

## 2025.7.4

- Fix warning about failure to get action during setup phase (wmspro docs)
- Fix a bug in rainbird device migration that results in additional devices (rainbird docs)
- Fix multiple webhook secrets for Telegram bot (telegram_bot docs)
- Bump pyschlage to 2025.7.2 (schlage docs) (dependency)
- Fix Matter light get brightness (matter docs)
- Fix brightness_step and brightness_step_pct via lifx.set_state (lifx docs)
- Add Z-Wave USB migration confirm step (zwave_js docs)
- Add fan off mode to the supported fan modes to fujitsu_fglair (fujitsu_fglair docs)
- Update Tesla OAuth Server in Tesla Fleet (tesla_fleet docs)
- Update slixmpp to 1.10.0 (xmpp docs) (dependency)
- Bump aioamazondevices to 3.5.1 (alexa_devices docs) (dependency)
- Bump pysuezV2 to 2.0.7 (suez_water docs) (dependency)
- Bump habiticalib to v0.4.1 (habitica docs) (dependency)

## 2025.7.3

- Fix Shelly n_current sensor removal condition (shelly docs)
- Bump pySmartThings to 3.2.8 (smartthings docs) (dependency)
- Bump Tesla Fleet API to 1.2.2 (tessie docs) (teslemetry docs) (tesla_fleet docs) (dependency)
- Add guard to prevent exception in Sonos Favorites (sonos docs)
- Fix button platform parent class in Teslemetry (teslemetry docs)
- Bump pyenphase to 2.2.2 (enphase_envoy docs) (dependency)
- Bump gios to version 6.1.1 (gios docs) (dependency)
- Bump gios to version 6.1.2 (gios docs) (dependency)
- Bump async-upnp-client to 0.45.0 (upnp docs) (yeelight docs) (dlna_dmr docs) (samsungtv docs) (ssdp docs) (dlna_dms docs) (dependency)
- Update frontend to 20250702.3 (frontend docs) (dependency)
- Bump PySwitchbot to 0.68.2 (switchbot docs) (dependency)
- Bump aioamazondevices to 3.5.0 (alexa_devices docs) (dependency)

## 2025.7.2

- Bump pysmlight to v0.2.7 ([smlight docs]) (dependency)
- Fix REST sensor charset handling to respect Content-Type header (rest docs)
- Fix UTF-8 encoding for REST basic authentication (rest docs)
- Bump pylamarzocco to 2.0.10 (lamarzocco docs) (dependency)
- Bump sharkiq to 1.1.1 (sharkiq docs) (dependency)
- bump motionblinds to 0.6.29 (motion_blinds docs) (dependency)
- Bump aiowebostv to 0.7.4 ([webostv docs]) (dependency)
- Bump gios to version 6.1.0 (gios docs) (dependency)
- Bump pyenphase to 2.2.1 (enphase_envoy docs) (dependency)
- Add lamp states to smartthings selector (smartthings docs)
- Fix Switchbot cloud plug mini current unit Issue ([switchbot_cloud docs])
- Bump pyswitchbot to 0.68.1 ([switchbot docs]) (dependency)
- Bump aioamazondevices to 3.2.8 (alexa_devices docs) (dependency)
- Bump pylamarzocco to 2.0.11 (lamarzocco docs) (dependency)
- Bump pySmartThings to 3.2.7 (smartthings docs) (dependency)
- Bump uiprotect to version 7.14.2 ([unifiprotect docs]) (dependency)
- Bump hass-nabucasa from 0.105.0 to 0.106.0 (cloud docs) (dependency)
- Fix entity_id should be based on object_id the first time an entity is added (mqtt docs)
- Bump aioimmich to 0.10.2 (immich docs) (dependency)
- Add workaround for sub units without main device in AVM Fritz!SmartHome (fritzbox docs)
- Add Home Connect resume command button when an appliance is paused (home_connect docs)
- Fix for Renson set Breeze fan speed (renson docs)
- Remove vg argument from miele auth flow (miele docs)
- Bump aiohttp to 3.12.14 (dependency)
- Update frontend to 20250702.2 (frontend docs) (dependency)
- Fix Google Cloud 504 Deadline Exceeded (google_cloud docs)
- Fix - only enable AlexaModeController if at least one mode is offered (alexa docs)
- Bump nyt_games to 0.5.0 (nyt_games docs) (dependency)
- Fix Charge Cable binary sensor in Teslemetry ([teslemetry docs])
- Bump PyViCare to 2.50.0 (dependency)
- Fix hide empty sections in mqtt subentry flows (mqtt docs)
- Bump aioshelly to 13.7.2 (shelly docs) (dependency)
- Bump aioamazondevices to 3.2.10 (alexa_devices docs) (dependency)

## 2025.7.1

- Fix missing port in samsungtv (samsungtv docs)
- Bump ZHA to 0.0.62 (zha docs) (dependency)
- Bump aiounifi to v84 (unifi docs)
- Fix state being incorrectly reported in some situations on Music Assistant players (music_assistant docs) (dependency)
- Bump hass-nabucasa from 0.104.0 to 0.105.0 (cloud docs) (dependency)
- Fix Telegram bots using plain text parser failing to load on restart (telegram_bot docs)
- Bump pyenphase to 2.2.0 (enphase_envoy docs) (dependency)
- Bump aioamazondevices to 3.2.3 (alexa_devices docs) (dependency)
- Update frontend to 20250702.1 (frontend docs) (dependency)
- Bump venstarcolortouch to 0.21 (venstar docs) (dependency)

## 2025.7.0b9

- Bump thermopro-ble to 0.13.1
- Bump deebot-client to 13.5.0
- Update frontend to 20250702.0
- Bump aioamazondevices to 3.2.2

## 2025.7.0b8

- Bump aioamazondevices to 3.2.1
- Bump bluetooth-data-tools to 1.28.2

## 2025.7.0b7

- Fix station name sensor for metoffice
- Bump VoIP utils to 0.3.3
- Bump Music Assistant Client to 1.2.3

## 2025.7.0b6

- Fix wrong state in Husqvarna Automower
- Fix Meteo france Ciel clair condition mapping
- Add more mac address prefixes for discovery to PlayStation Network
- fix state_class for water used today sensor
- Bump Nettigo Air Monitor backend library to version 5.0.0
- fix yamaha_musiccast by creating new aiohttp session
- Fix invalid configuration of MQTT device QoS option in subentry flow
- Update frontend to 20250701.0

## 2025.7.0b5

- Bump aioshelly to 13.7.1
- Update pywmspro to 0.3.0 to wait for short-lived actions
- Fix Telegram bot proxy URL not initialized when creating a new bot
- Fix sensor displaying unknown when getting readings from heat meters in ista EcoTrend
- Fix Vesync set_percentage error
- Bump reolink_aio to 0.14.2

## 2025.7.0b4

- Fix Shelly Block entity removal
- Bump pytibber to 0.31.6
- Fix error if cover position is not available or unknown
- bump pypaperless to 4.1.1

## 2025.7.0b3

- Add previously missing state classes to dsmr sensors
- Remove dweet.io integration
- Fix energy history in Teslemetry
- Bump jellyfin-apiclient-python to 1.11.0
- Fix: Unhandled NoneType sessions in jellyfin
- Fix Shelly entity removal
- Update frontend to 20250627.0
- Fix sentence-casing and spacing of button in thermopro
- Bump aiosomecomfort to 0.0.33
- Add codeowner for Telegram bot
- Bump aioamazondevices to 3.1.22

## 2025.7.0b2

- Fix Telegram bot yaml import for webhooks containing None value for URL
- Fix config schema to make credentials optional in NUT flows
- Add Diagnostics to PlayStation Network
- Bump pynecil to v4.1.1

## 2025.7.0b1

- Fix playing TTS and local media source over DLNA
- Fix Telegram bot default target when sending messages
- Bump dependency on pyW215 for DLink integration to 0.8.0
- Fix wind direction state class sensor for AEMET
- Add action exceptions to Alexa Devices
- Fix unload for Alexa Devices
- Bump zwave-js-server-python to 0.65.0
- Fix sending commands to Matter vacuum
- Remove obsolete routing info when migrating a Z-Wave network
- Add default conversation name for OpenAI integration
- Add default title to migrated Claude entry
- Add default title to migrated Ollama entry
- Update frontend to 20250626.0
- Remove default icon for wind direction sensor for Buienradar
- Fix asset url in Habitica integration
- Fix meaters not being added after a reload

## 2025.6.3

- Update frontend to 20250531.4 (frontend docs) (dependency)

## 2025.6.2

- Bump uiprotect to 7.12.0 (unifiprotect docs) (dependency)
- Bump uiprotect to 7.13.0 (unifiprotect docs) (dependency)
- Bump reolink-aio to 0.14.0 (reolink docs) (dependency)
- Bump pypck to 0.8.7 (lcn docs) (dependency)
- Update rokuecp to 0.19.5 (roku docs) (dependency)
- Fix blocking open in Minecraft Server (minecraft_server docs)
- Bump aioamazondevices to 3.1.3 (alexa_devices docs) (dependency)
- Bump aiohttp to 3.12.13 (dependency)
- Bump motion blinds to 0.6.28 (motion_blinds docs) (dependency)
- Bump pypck to 0.8.8 (lcn docs) (dependency)
- Fix missing key for ecosmart in older Wallbox models ([wallbox docs])
- Bump bthome-ble to 3.13.1 (bthome docs) (dependency)
- Bump reolink-aio to 0.14.1 (reolink docs) (dependency)
- Add debug log for update in onedrive (onedrive docs)
- Bump pySmartThings to 3.2.5 (smartthings docs) (dependency)
- Bump ical to 10.0.4 (local_calendar docs) (local_todo docs) (remote_calendar docs) (dependency)
- Fix incorrect use of zip in service.async_get_all_descriptions
- Fix Shelly entity names for gen1 sleeping devices (shelly docs)
- Fix log in onedrive (onedrive docs)
- Bump holidays lib to 0.75 ([workday docs]) (holiday docs) (dependency)
- Bump aiohomeconnect to 0.18.0 (home_connect docs) (dependency)
- Bump ZHA to 0.0.60 ([zha docs]) (dependency)
- Bump pylamarzocco to 2.0.9 (lamarzocco docs) (dependency)
- Bump aioamazondevices to 3.1.4 (alexa_devices docs) (dependency)
- Bump aioamazondevices to 3.1.12 (alexa_devices docs) (dependency)
- Bump uiprotect to version 7.14.0 (unifiprotect docs) (dependency)
- Fix Charge Cable binary sensor in Teslemetry (teslemetry docs)
- Bump homematicip to 2.0.6 (homematicip_cloud docs) (dependency)
- Bump deebot-client to 13.4.0 (ecovacs docs) (dependency)
- Bump aioamazondevices to 3.1.14 (alexa_devices docs) (dependency)
- Bump uiprotect to version 7.14.1 (unifiprotect docs) (dependency)
- Bump aioesphomeapi to 32.2.4 (esphome docs) (dependency)
- Bump aioesphomeapi to 33.0.0 (esphome docs) (dependency)
- Fix reload for Shelly devices with no script support (shelly docs)
- Add Matter protocol to Switchbot

### BREAKING CHANGES

- Remove address info from Rachio calendar events (rachio docs)

## 2025.6.1

- Fix palette handling for LIFX Ceiling SKY effect (lifx docs)
- Fix fan is_on status in xiaomi_miio (xiaomi_miio docs)
- Update frontend to 20250531.3 (frontend docs)
- Fix cookies with aiohttp >= 3.12.7 for Vodafone Station (vodafone_station docs)
- Bump wakeonlan to 3.1.0 (wake_on_lan docs) (samsungtv docs) (dependency)
- Bump hdate to 1.1.2 (jewish_calendar docs) (dependency)
- Bump linkplay to v0.2.12 (linkplay docs) (dependency)
- Bump aioamazondevices to 3.1.2 (alexa_devices docs) (dependency)
- Fix opower to work with aiohttp>=3.12.7 by disabling cookie quoting (opower docs) (dependency)
- Bump aiodns to 3.5.0 (dnsip docs) (dependency)
- Fix throttling issue in HomematicIP Cloud (homematicip_cloud docs)

## 2025.6.0b9

- Update frontend to 20250531.1
- Remove the Delete button on the ZwaveJS device page
- Update frontend to 20250531.2
- Bump yt-dlp to 2025.06.09

## 2025.6.0b8

- Fix delay_on and delay_off restarting when a new trigger occurs during the delay
- Fix stale options in here_travel_time
- Remove stale Shelly BLU TRV devices
- Add guide for Honeywell Lyric application credentials setup
- Fix solax state class of Today's Generated Energy
- Remove Z-Wave useless reconfigure options
- Bump linkplay to v0.2.11
- Bump hdate to 1.1.1

## 2025.6.0b7

- Bump homematicip to 2.0.4
- Add color_temp_kelvin to set_temperature action variables
- Fix Jewish calendar not updating
- Remove DHCP discovery from Amazon Devices
- Bump apsystems to 2.7.0
- Bump intents to 2025.6.10
- Bump deebot-client to 13.3.0

## 2025.6.0b6

- fix possible mac collision in enphase_envoy
- Add evaporate water program id for Miele oven
- Bump aiohttp to 3.12.8
- Bump env-canada to v0.11.1
- Bump aioimmich to 0.9.0
- Bump pyiskra to 0.1.21
- Bump uiprotect to 7.11.0
- Bump aiohttp to 3.12.9
- Fix Export Rule Select Entity in Tessie
- Remove zeroconf discovery from Spotify
- Bump aioimmich to 0.9.1
- Add missing write state to Teslemetry
- Bump aiohttp-fast-zlib to 0.3.0
- Bump holidays to 0.74
- Bump aiohttp to 3.12.11
- Fix bosch alarm areas not correctly subscribing to alarms
- Bump py-synologydsm-api to 2.7.3
- Bump aioesphomeapi to 32.2.0
- Bump python-linkplay to v0.2.10
- Bump pydrawise to 2025.6.0
- Bump env-canada to v0.11.2
- Bump aioesphomeapi to 32.2.1
- Bump aioamazondevices to 3.0.6
- Fix switch_as_x entity_id tracking
- Update switch_as_x to handle wrapped switch moved to another device
- Bump pynordpool to 0.3.0
- Fix CO concentration unit in OpenWeatherMap
- Fix initial state of UV protection window
- Bump propcache to 0.3.2
- Bump yarl to 1.20.1
- Bump aiohttp to 3.12.12
- Fix typo at application credentials string at Home Connect integration
- Update requests to 2.32.4
- Update wording deprecated system package integration repair
- Update caldav to 1.6.0
- Bump pySmartThings to 3.2.4
- Fix incorrect categories handling in holiday
- Fix EntityCategory for binary_sensor platform in Amazon Devices

## 2025.6.0b5

- Fix removal of devices during Z-Wave migration
- Bump aioimmich to 0.8.0
- Bump pysmlight to v0.2.5
- Bump ical to 10.0.0
- Bump python-picnic-api2 to 1.3.1
- Add diagnostics to Amazon devices
- Bump aioamazondevices to 3.0.4
- Bump reolink-aio to 0.13.5
- Bump grpcio to 1.72.1
- Fix Shelly BLU TRV calibrate button
- Bump aioamazondevices to 3.0.5
- Add state class measurement to Freebox temperature sensors
- Fix nightlatch option for all switchbot locks
- Fix BMS and Charge states in Teslemetry
- Bump bleak-esphome to 2.16.0
- Bump habluetooth to 3.49.0
- Bump protobuf to 6.31.1
- Bump aioesphomeapi to 32.0.0

## 2025.6.0b4

- Add more Amazon Devices DHCP matches
- Bump switchbot-api to 2.4.0
- Bump tesla-fleet-api to 1.1.1.
- Add streaming to charge cable connected in Teslemetry
- Bump pyiskra to 0.1.19
- Bump python-linkplay to v0.2.9
- Bump pyprobeplus to 1.0.1
- Bump opower to 0.12.3
- Bump aiohttp to 3.12.6
- Update frontend to 20250531.0
- Bump pylamarzocco to 2.0.8

## 2025.6.0b3

- Fix language selections in workday
- Bump aiotedee to 0.2.23
- Fix Tessie volume max and step
- Bump pyaprilaire to 0.9.1
- Bump aiohttp to 3.12.3
- Bump aiohttp to 3.12.4
- Bump aioimmich to 0.7.0
- Bump aiohomeconnect to 0.17.1

## 2025.6.0b2

- Update otp description for amazon_devices
- Add level of collections in Immich media source tree
- Fix dns resolver error in dnsip config flow validation
- Bump uiprotect to version 7.10.1
- Add Shelly zwave virtual integration
- Add more Amazon Devices DHCP matches
- Bump pylamarzocco to 2.0.7
- Add more information about possible hostnames at Home Connect
- Fix uom for prebrew numbers in lamarzocco
- Bump reolink-aio to 0.13.4
- Fix HOMEASSISTANT_STOP unsubscribe in data update coordinator
- Bump intents to 2025.5.28
- Fix Immich media source browsing with multiple config entries
- Update frontend to 20250528.0

## 2025.6.0b1

- Fix translation for sensor measurement angle state class
- Fix Aquacell snapshot
- Fix Amazon devices offline handling
- Bump aiohttp to 3.12.2
- Fix justnimbus CI test
- Remove confirm screen after Z-Wave usb discovery
- Fix error stack trace for HomeAssistantError in websocket service call
- Remove static pin code length Matter sensors
- Fix unbound local variable in Acmeda config flow
- Update frontend to 20250527.0

## 2025.5.3

- Fix QNAP fail to load (qnap docs)
- Bump ESPHome stable BLE version to 2025.5.0 (esphome docs)
- Fix album and artist returning "None" rather than None for Squeezebox media player. (squeezebox docs)
- Bump aiontfy to 0.5.2 (ntfy docs) (dependency)
- Fix proberly Ecovacs mower area sensors (ecovacs docs)
- Add missing device condition translations to lock component (lock docs)
- Fix history_stats with sliding window that ends before now (history_stats docs)
- Bump sense-energy to 0.13.8 (sense docs) (emulated_kasa docs) (dependency)
- Fix Z-Wave unique id update during controller migration (zwave_js docs)
- Bump velbusaio to 2025.5.0 (velbus docs) (dependency)
- Bump aiocomelit to 0.12.3 (comelit docs) (dependency)
- Fix Z-Wave config entry unique id after NVM restore (zwave_js docs)
- Bump holidays to 0.73 (workday docs) (holiday docs) (dependency)
- Bump pyaprilaire to 0.9.0 (aprilaire docs) (dependency)
- Add cloud as after_dependency to onedrive (onedrive docs)
- Fix limit of shown backups on Synology DSM location (synology_dsm docs)
- Add initial coordinator refresh for players in Squeezebox (squeezebox docs)
- Fix: Revert Ecovacs mower total_stats_area unit to square meters (ecovacs docs)
- Bump pysqueezebox to v0.12.1 (squeezebox docs) (dependency)
- Bump pylamarzocco to 2.0.4 (lamarzocco docs) (dependency)
- Bump py-synologydsm-api to 2.7.2 (synology_dsm docs) (dependency)
- Bump yt-dlp to 2025.05.22 (media_extractor docs) (dependency)
- Bump pysmartthings to 3.2.3 (smartthings docs) (dependency)
- Bump opower to 0.12.1 (opower docs) (dependency)
- Fix strings related to Google search tool in Google AI (google_generative_ai_conversation docs)
- Bump pyfibaro to 0.8.3 (fibaro docs) (dependency)
- Bump deebot-client to 13.2.1 (ecovacs docs) (dependency)

## 2025.5.2

- Bump aiodiscover to 2.7.0 (dhcp docs) (dependency)
- Bump reolink_aio to 0.13.3 ([reolink docs]) (dependency)
- fix enphase_envoy diagnostics home endpoint name ([enphase_envoy docs])
- Bump pylamarzocco to 2.0.2 ([lamarzocco docs]) (dependency)
- bump pyenphase to 1.26.1 ([enphase_envoy docs]) (dependency)
- Bump ical to 9.2.1 ([google docs]) ([local_calendar docs]) ([local_todo docs]) ([remote_calendar docs]) (dependency)
- Bump python-linkplay to v0.2.5 ([linkplay docs]) (dependency)
- Bump holidays to 0.72 ([workday docs]) ([holiday docs]) (dependency)
- Fix strings typo for Comelit (comelit docs)
- Fix wrong state in Husqvarna Automower ([husqvarna_automower docs])
- Bump voluptuous-openapi to 0.1.0 (dependency)
- Bump ical to 9.2.2 ([google docs]) ([local_calendar docs]) ([local_todo docs]) ([remote_calendar docs]) (dependency)
- Bump gcal-sync to 7.0.1 ([google docs]) (dependency)
- Bump aiocomelit to 0.12.1 (comelit docs) (dependency)
- Fix Netgear handeling of missing MAC in device registry ([netgear docs])
- Fix blocking call in azure storage (azure_storage docs)
- Fix Z-Wave unique id after controller reset ([zwave_js docs])
- Fix blocking call in azure_storage config flow (azure_storage docs)
- Bump pylamarzocco to 2.0.3 ([lamarzocco docs]) (dependency)
- Bump python-snoo to 0.6.6 ([snoo docs]) (dependency)
- Bump ical to 9.2.4 ([google docs]) ([local_calendar docs]) ([local_todo docs]) ([remote_calendar docs]) (dependency)
- Fix wall connector states in Teslemetry ([teslemetry docs])
- Fix Reolink setup when ONVIF push is unsupported ([reolink docs])
- Fix some Home Connect translation strings ([home_connect docs])
- Update Tibber lib 0.31.2 ([tibber docs]) (dependency)
- Update mill library 0.12.5 ([mill docs]) (dependency)
- Fix unknown Pure AQI in Sensibo ([sensibo docs]) (dependency)
- Fix Home Assistant Yellow config entry data ([homeassistant_yellow docs])
- Bump deebot-client to 13.2.0 ([ecovacs docs]) (dependency)
- Fix ESPHome entities unavailable if deep sleep enabled after entry setup ([esphome docs])
- Bump pySmartThings to 3.2.2 ([smartthings docs]) (dependency)
- Fix climate idle state for Comelit (comelit docs)
- Update frontend to 20250516.0 ([frontend docs]) (dependency)
- Fix fan AC mode in SmartThings AC ([smartthings docs])
- Fix Ecovacs mower area sensors ([ecovacs docs])

## 2025.5.1

- Fix Z-Wave restore nvm command to wait for driver ready (zwave_js docs)
- fix homekit air purifier temperature sensor to convert unit (homekit docs)
- Add LAP-V102S-AUSR to VeSync (vesync docs)
- Bump pylamarzocco to 2.0.1 (lamarzocco docs) (dependency)
- Fix Z-Wave reset accumulated values button entity category (zwave_js docs)
- Fix point import error (point docs)
- Bump forecast-solar to 4.2.0 (forecast_solar docs) (dependency)
- Fix removing of smarthome templates on startup of AVM Fritz!SmartHome integration (fritzbox docs)
- Bump aiodns to 3.4.0 (dnsip docs) (dependency)
- Fix statistics coordinator subscription for lamarzocco (lamarzocco docs)
- Update frontend to 20250509.0 (frontend docs) (dependency)

## 2025.5.0b9

- Bump wh-python to 2025.4.29 for Weheat integration
- Fix Z-Wave controller hard reset
- Fix SmartThings machine operating state with no options
- Add missing device_class translations for template helper
- Bump pySmartThings to 3.2.1
- Fix variables in MELCloud

## 2025.5.0b8

- Fix field validation for mqtt subentry options in sections
- Bump renault-api to 0.3.1
- Bump uiprotect to version 7.6.0

## 2025.5.0b10

- Fix test in Husqvarna Automower
- Bump devolo_home_control_api to 0.19.0
- Bump deebot-client to 13.1.0
- Update frontend to 20250507.0
- Add more missing device_class translations for template helper

## 2025.5.0b7

- Fix Z-Wave migration flow to unload config entry before unplugging controller
- Bump bluemaestro-ble to 0.4.1
- Remove some media player intent checks for when paused
- Update frontend to 20250506.0

## 2025.5.0b6

- Bump xiaomi-ble to 0.38.0
- Fix Z-Wave USB discovery to use serial by id path
- Update Home Assistant base image to 2025.05.0
- Add endpoint validation for AWS S3
- Fix Z-Wave to reload config entry after migration nvm restore

## 2025.5.0b5

- Fix default entity name not the device default entity when no name set on MQTT subentry entity
- Fix Z-Wave config flow forms
- Fix un-/re-load of Feedreader integration
- Fix mqtt subentry device name is not required but should be
- Bump VoIP utils to 0.3.2

## 2025.5.0b4

- Fix message corruption in picotts component
- bump aiokem to 0.5.10
- Fix Office 365 calendars to be compatible with rfc5545
- Fix missing head forwarding in ingress
- Update remote calendar to do all event handling in an executor
- Update local calendar to process calendar events in the executor
- Bump ical to 9.2.0
- Fix Invalid statistic_id for Opower: National Grid
- Remove program phase sensor from miele vacuum robot
- Bump python-roborock to 2.18.2
- Bump Roborock Map Parser to 0.1.4
- Bump pylamarzocco to 2.0.0
- Update frontend to 20250502.1

## 2025.5.0b3

- Fix check for locked device in AVM Fritz!SmartHome
- Add tests to ensure ESPHome entity_ids are preserved on upgrade
- Bump habluetooth to 3.48.2
- Bump zeroconf to 0.147.0
- Bump pymiele to 0.4.3
- Fix licenses check for setuptools
- Bump homematicip to 2.0.1.1
- Add missing pollen category to AccuWeather
- Fix intent TurnOn creating stack trace for buttons

## 2025.5.0b2

- Fix brightness calculation when using brightness_step_pct
- Bump py-nextbusnext to 2.1.2
- Bump teslemetry-stream to 0.7.7
- Fix small issues with mqtt translations and improve readability
- bump aiokem to 0.5.9
- Update frontend to 20250502.0
- Bump aiodns to 3.3.0
- Bump aioautomower to 2025.5.1
- Fix intermittent unavailability for lamarzocco brew active sensor
- Update pywmspro to 0.2.2 to make error handling more robust
- Bump PyISY to 3.4.1
- Bump bleak-esphome to 2.15.1
- Bump Bluetooth deps to improve auto recovery process

## 2025.5.0b1

- Bump pushover-complete to 1.2.0
- Add units of measurement for Home Connect counter entities
- Bump pylamarzocco to 2.0.0b7
- Add translations for "energy_distance" and "wind_direction" in random
- Add connect/disconnect callbacks to lamarzocco
- Add bluetooth connection availability to diagnostics for lamarzocco
- Fix state of fan entity for Miele hobs with extractor when turned off
- Bump inkbird-ble to 0.16.1

## 2025.4.4

- Update setuptools to 78.1.1 (dependency)
- Fix licenses check for setuptools
- Add scan interval and parallel updates to LinkPlay media player (linkplay docs)
- Fix Vodafone Station config entry unload (vodafone_station docs)
- Bump aiohomekit to 3.2.14 (homekit_controller docs) (dependency)
- Bump dio-chacon-api to v1.2.2 (chacon_dio docs) (dependency)
- Bump pysmartthings to 3.0.5 (smartthings docs) (dependency)

## 2025.4.3

- Fix duke_energy data retrieval to adhere to service start date (duke_energy docs)
- Fix error in recurrence calculation of Habitica integration (habitica docs)
- Fix MQTT device discovery when using node_id (mqtt docs)
- Fix Reolink Home Hub Pro playback (reolink docs)
- Fix quality loss for LLM conversation agent question answering
- Bump Environment Canada library to 0.10.1 (environment_canada docs) (dependency)
- Bump devolo_plc_api to 1.5.1 (devolo_home_network docs) (dependency)
- Update UK Transport Integration URL (uk_transport docs)
- Bump holidays to 0.70 (workday docs) (holiday docs) (dependency)
- Fix switch state for Comelit (comelit docs)
- Bump reolink-aio to 0.13.2 (reolink docs) (dependency)
- Bump pysmhi to 1.0.2 (smhi docs) (dependency)
- Add Python-2.0 to list of approved licenses
- Bump ZHA to 0.0.56 (zha docs)
- Fix SmartThings soundbar without media playback (smartthings docs)
- Fix missing binary sensor for CoolSelect+ in SmartThings (smartthings docs)

## 2025.4.2

- Add error details in remote calendar flow ([remote_calendar docs])
- Update Roborock map more consistently on state change ([roborock docs])
- Add SensorDeviceClass and unit for LCN CO2 sensor. (lcn docs)
- Bump opower to 0.10.0 ([opower docs]) (dependency)
- Add a description for the enable_google_search_tool option in Google AI (google_generative_ai_conversation docs)
- Bump flux_led to 1.2.0 (flux_led docs) (dependency)
- Update aioairzone to v1.0.0 (airzone docs) (dependency)
- Bump aioesphomeapi to 29.9.0 (esphome docs) (dependency)
- Bump opower to 0.11.1 ([opower docs]) (dependency)
- Add exceptions translation to SamsungTV ([samsungtv docs])
- Add missing strings to Fritz (fritz docs)
- Fix reload of AVM FRITZ!Tools when new connected device is detected (fritz docs)
- Fix HKC showing hvac_action as idle when fan is active and heat cool target is off (homekit_controller docs)
- Fix Reolink smart AI sensors ([reolink docs])
- Fix kelvin parameter in light action specifications (light docs)
- Bump aioshelly to version 13.4.1 ([shelly docs]) (dependency)
- Fix range of Google Generative AI temperature (google_generative_ai_conversation docs)
- Fix small typo in Music Assistant integration causing unavailable players ([music_assistant docs])
- Fix adding devices in Husqvarna Automower (husqvarna_automower docs)
- Bump pyheos to v1.0.5 (heos docs) (dependency)
- Fix Quickmode handling in ViCare integration ([vicare docs])
- Fix Core deadlock by ensuring only one ZHA log queue handler thread is running at a time ([zha docs])
- Fix ssl_cert load from config_flow (daikin docs)
- Update growatt server dependency to 1.6.0 (growatt_server docs) (dependency)
- Bump led_ble to 1.1.7 (led_ble docs) (dependency)
- Bump livisi to 0.0.25 ([livisi docs]) (dependency)
- Fix EC certificate key not allowed in MQTT client setup ([mqtt docs])
- Bump PyViCare to 2.44.0 ([vicare docs])
- Bump reolink-aio 0.13.1 ([reolink docs]) (dependency)
- Update frontend to 20250411.0 (frontend docs) (dependency)
- Bump pySmartThings to 3.0.4 ([smartthings docs]) (dependency)
- Fix SmartThings gas meter ([smartthings docs])
- Fix Anthropic bug parsing a streaming response with no json (anthropic docs)

### BREAKING CHANGES

- Fix Shelly initialization if device runs large script ([shelly docs])

## 2025.4.1

- Fix blocking event loop - daikin (daikin docs)
- Fix humidifier platform for Comelit (comelit docs)
- Bump evohome-async to 1.0.5 (evohome docs) (dependency)
- Add translation for hassio update entity name (hassio docs)
- Bump pyenphase to 1.25.5 (enphase_envoy docs) (dependency)
- Bump pysmhi to 1.0.1 (smhi docs) (dependency)
- Bump tesla-fleet-api to v1.0.17 (tessie docs) (teslemetry docs) (tesla_fleet docs) (dependency)
- Add preset mode to SmartThings climate (smartthings docs)
- Fix fibaro setup (fibaro docs)
- Fix circular mean by always storing and using the weighted one (recorder docs) (sensor docs)
- Bump pySmartThings to 3.0.2 (smartthings docs) (dependency)
- Update frontend to 20250404.0 (frontend docs) (dependency)
- Bump forecast-solar lib to v4.1.0 (forecast_solar docs) (dependency)
- Fix skyconnect tests (zha docs)
- Fix empty actions (template docs)

## 2025.4.0b15

- Fix weather templates using new style configuration
- Bump deebot-client to 12.5.0
- Add Eve brand

## 2025.4.0b14

- Remove unused mypy ignore from google_generative_ai_conversation
- Fix warning about unfinished oauth tasks on shutdown
- Fix entity names for HA hardware firmware update entities
- Bump ZHA to 0.0.55
- Bump aiohttp to 3.11.16
- Bump bluetooth-data-tools to 1.26.5

## 2025.4.0b13

- Fix nordpool Not to return Unknown if price is exactly 0
- Fix import issues related to onboarding views
- Fix data in old SkyConnect integration config entries or delete them
- Bump aiohttp to 3.11.15
- Add LG ThinQ event bus listener to lifecycle hooks
- Update frontend to 20250401.0
- Fix train to for multiple stations in Trafikverket Train

## 2025.4.0b12

- Update frontend to 2025033.0
- Bump async-upnp-client to 0.44.0

## 2025.4.0b11

- Add switchbot cover unit tests
- Fix SmartThings climate entity missing off HAVC mode
- Bump ohmepy to 1.5.1
- Fix SmartThings being able to understand incomplete DRLC
- Add None check to azure_storage
- Add preannounce boolean for announce/start conversation
- Bump aiowebdav2 to 0.4.5

## 2025.4.0b10

- Remove sunweg integration
- Fix order of palettes, presets and playlists in WLED integration
- Bump iaqualink to 0.5.3
- Bump pySmartThings to 3.0.1
- Add helper methods to simplify USB integration testing
- Bump aiohomekit to 3.2.13
- Fix blocking late import of httpcore from httpx
- Bump PyISY to 3.1.15
- Add boost preset to AVM Fritz!SmartHome climate entities
- Bump ical to 9.0.3
- Fix System Bridge wait timeout wait condition
- Fix hardcoded UoM for total power sensor for Tuya zndb devices
- Fix the entity category for max throughput sensors in AVM Fritz!Box Tools
- Update pvo to v2.2.1
- Bump aioesphomeapi to 29.8.0
- Fix duplicate call to async_write_ha_state when adding elkm1 entities

## 2025.4.0b9

- Add unkown to uncalibrated state for tedee
- Add a common string for "country"
- Bump music assistant client to 1.2.0
- Fix Tuya tdq category to pick up temp & humid
- Fix ESPHome update entities being loaded before device_info is available
- Fix ESPHome entities not being removed when the ESPHome config removes an entire platform
- Fix immediate state update for Comelit

## 2025.4.0b8

- Bump intents and always prefer more literal text
- Update Duke Energy package to fix integration
- Fix camera proxy with sole image quality settings
- Fix grammar / sentence-casing in workday

## 2025.4.0b7

- Update frontend to 20250328.0

## 2025.4.0b6

- Fix misleading friendly names of pvoutput sensors
- Fix missing response for queued mode scripts
- Add default string and icon for light effect off
- Bump Python-Snoo to 0.6.5
- Fix zeroconf logging level not being respected
- Bump aiowebdav2 to 0.4.4
- Fix an issue with the switch preview in beta
- Fix volatile_organic_compounds_parts translation string to be referenced for MQTT subentries device class selector
- Fix sentence-casing in airvisual user strings
- Fix duplicate 'device' term in MQTT translation strings
- Fix ESPHome event entity staying unavailable

## 2025.4.0b5

- Add brand for Bosch
- Bump aiowebdav2 to 0.4.3
- Fix typing error in NMBS
- Update frontend to 20250327.1

## 2025.4.0b4

- Update frontend to 20250327.0

## 2025.4.0b3

- Add icons to hue effects

## 2025.4.0b2

- Fix wrong friendly name for storage_power in solaredge
- Add default preannounce sound to Assist satellites
- Bump linkplay to v0.2.2
- Fix sentence-casing in konnected strings, replace "override" with "custom"

## 2025.4.0b1

- Fix refresh state for Comelit alarm
- Bump deebot-client to 12.4.0
- Fix work area sensor for Husqvarna Automower
- Fix MQTT options flow QoS selector can not serialize
- Fix QoS schema issue in MQTT subentries

## 2025.3.4

- Fix initial fetch of Home Connect appliance data to handle API rate limit errors (home_connect docs)
- Add 700 RPM option to washer spin speed options at Home Connect (home_connect docs)
- Fix optional password in Velbus config flow (velbus docs)
- Fix Elk-M1 missing TLS 1.2 check (elkm1 docs)
- Bump PySwitchBot to 0.57.1 (switchbot docs) (dependency)
- Fix broken core integration Smart Meter Texas by switching it to use HA's SSL Context (smart_meter_texas docs)
- Bump pySmartThings to 2.7.4 (smartthings docs) (dependency)
- Fix SmartThings ACs without supported AC modes (smartthings docs)
- Bump pylamarzocco to 1.4.9 (lamarzocco docs) (dependency)
- Fix some Home Connect options keys (home_connect docs)
- Bump ZHA to 0.0.53 (zha docs)
- Bump Python-Snoo to 0.6.3 (snoo docs) (dependency)
- Bump python-snoo to 0.6.4 (snoo docs) (dependency)

## 2025.3.3

- Fix bug with all Roborock maps being set to the wrong map when empty (roborock docs)
- Bump pysuezV2 to 2.0.4 (suez_water docs) (dependency)
- Bump upb-lib to 0.6.1 (upb docs) (dependency)
- Bump velbusaio to 2025.3.1 (velbus docs) (dependency)
- Bump Tesla Fleet API to 0.9.13 (tessie docs) (teslemetry docs) (tesla_fleet docs)
- Update xknxproject to 3.8.2 (knx docs) (dependency)
- Fix Shelly diagnostics for devices without WebSocket Outbound support (shelly docs)
- Fix windowShadeLevel capability in SmartThings (smartthings docs)
- Fix missing UnitOfPower.MILLIWATT in sensor and number allowed units (sensor docs)

## 2025.3.2

- Bump govee_ble to 0.43.1 (govee_ble docs) (dependency)
- Bump sense-energy lib to 0.13.7 (sense docs) (emulated_kasa docs) (dependency)
- Update jinja to 3.1.6 (dependency)
- Update evohome-async to 1.0.3 (evohome docs) (dependency)
- Fix HEOS discovery error when previously ignored (heos docs)
- Fix MQTT JSON light not reporting color temp status if color is not supported (mqtt docs)
- Fix HEOS user initiated setup when discovery is waiting confirmation (heos docs)
- Fix the order of the group members attribute of the Music Assistant integration (music_assistant docs)
- Fix events without user in Bring integration (bring docs)
- Bump evohome-async to 1.0.4 to fix (evohome docs) (dependency)
- Add 900 RPM option to washer spin speed options at Home Connect (home_connect docs)
- Fix todo tool broken with Gemini 2.0 models. (google_generative_ai_conversation docs)
- Fix version not always available in onewire (onewire docs)
- Fix client_id not generated when connecting to the MQTT broker (mqtt docs)
- Bump velbusaio to 2025.3.0 (velbus docs) (dependency)
- Fix dryer operating state in SmartThings (smartthings docs)
- Bump pyheos to v1.0.3 (heos docs) (dependency)
- Bump ZHA to 0.0.52 (zha docs) (dependency)
- Bump pydrawise to 2025.3.0 (hydrawise docs)
- Bump teslemetry-stream (teslemetry docs) (dependency)
- Fix no temperature unit in SmartThings (smartthings docs)
- Fix double space quoting in WebDAV (webdav docs) (dependency)
- Bump python-roborock to 2.12.2 (roborock docs) (dependency)
- Fix browsing Audible Favorites in Sonos (sonos docs)

## 2025.3.1

- Fix Unit of Measurement for Squeezebox duration sensor entity on LMS service (squeezebox docs)
- Bump thermobeacon-ble to 0.8.1 (thermobeacon docs) (dependency)
- Bump pysmartthings to 2.6.1 (smartthings docs) (dependency)
- Bump aiowebdav2 to 0.4.0 (webdav docs) (dependency)
- Add config entry level diagnostics to SmartThings (smartthings docs)
- Bump to python-snoo 0.6.1 (snoo docs) (dependency)
- Fix SmartThings fan (smartthings docs)
- Update frontend to 20250306.0 (frontend docs) (dependency)
- Fix SmartThings dust sensor UoM (smartthings docs)
- Bump nexia to 2.2.2 (nexia docs) (dependency)
- Bump aiowebdav2 to 0.4.1 (webdav docs)
- Fix regression to evohome debug logging (evohome docs)
- Bump aiohomeconnect to 0.16.3 (home_connect docs) (dependency)
- Fix powerwall 0% in Tessie and Tesla Fleet (tessie docs) (tesla_fleet docs)
- Fix shift state default in Teslemetry and Tessie (tessie docs) (teslemetry docs)
- Add description for HomematicIP HCU1 in homematicip_cloud setup config flow (homematicip_cloud docs)
- Fix evohome to gracefully handle null schedules (evohome docs)
- Fix SmartThings disabling working capabilities (smartthings docs)
- Fix SmartThings thermostat climate check (smartthings docs)
- Bump pysmartthings to 2.7.0 (smartthings docs) (dependency)
- Bump py-synologydsm-api to 2.7.1 (synology_dsm docs) (dependency)

## 2025.3.0b8

- Bump nexia to 2.2.1
- Bump aioecowitt to 2025.3.1
- Bump onedrive-personal-sdk to 0.0.13
- Bump intents to 2025.3.5

## 2025.3.0b7

- Update frontend to 20250305.0

## 2025.3.0b6

- Bump aiowebostv to 0.7.3

## 2025.3.0b5

- Bump aiohomeconnect to 0.16.2
- Add Apollo Automation virtual integration
- Fix incorrect weather state returned by HKO
- Bump pysmartthings to 2.5.0
- Fix home connect available
- Bump nexia to 2.1.1

## 2025.3.0b4

- Fix unique identifiers where multiple IKEA Tradfri gateways are in use
- Fix vicare exception for specific ventilation device type
- Fix Homee brightness sensors reporting in percent
- Fix ability to remove orphan device in Music Assistant integration
- Fix broken link in ESPHome BLE repair
- Fix scope comparison in SmartThings
- Add additional roborock debug logging
- Bump ESPHome stable BLE version to 2025.2.2
- Bump holidays to 0.68
- Bump aiowebostv to 0.7.2
- Bump sense-energy to 0.13.6
- Add nest translation string for already_in_progress
- Bump google-nest-sdm to 7.1.4

## 2025.3.0b3

- Add missing 'state_class' attribute for Growatt plant sensors
- Bump env_canada to 0.8.0
- Fix Nederlandse Spoorwegen to ignore trains in the past
- Fix bug in derivative sensor when source sensor's state is constant
- Fix update data for multiple Gree devices
- Fix alert not respecting can_acknowledge setting
- Bump pysmartthings to 2.2.0
- Remove orphan devices on startup in SmartThings
- Bump PySwitchBot to 0.56.1
- Bump pysmartthings to 2.3.0
- Add SmartThings Viper device info
- Bump pysmartthings to 2.4.0
- Bump Tesla Fleet API to v0.9.12
- Bump aiowebdav2 to 0.3.1
- Bump aiohomekit to 3.2.8
- Fix duplicate unique id issue in Sensibo
- Fix - Allow brightness only light MQTT json light to be set up using the brightness flag or via supported_color_modes
- Fix Manufacturer naming for Squeezelite model name for Squeezebox
- Bump deebot-client to 12.3.1
- Fix handling of NaN float values for current humidity in ESPHome
- Bump aioshelly to 13.1.0
- Bump inkbird-ble to 0.7.1
- Fix body text of imap message not available in custom event data template
- Fix arm vacation mode showing as armed away in elkm1
- Bump pysmartthings to 2.4.1

## 2025.3.0b2

- Bump weatherflow4py to 1.3.1
- Add new mediatypes to Music Assistant integration
- Bump aiohomeconnect to 0.15.1
- Fix SmartThings diagnostics
- Bump pysmartthings to 2.0.1
- Bump pysmartthings to 2.1.0
- Fix shift state in Teslemetry
- Add diagnostics to onedrive
- Bump yt-dlp to 2025.02.19
- Update frontend to 20250228.0

## 2025.3.0b1

- Bump stookwijzer==1.6.1
- Bump ZHA to 0.0.51
- Bump intents to 2025.2.26
- Fix fetch options error for Home connect
- Bump onedrive to 0.0.12
- Bump pysmartthings to 2.0.0
- Bump habluetooth to 3.24.1
- Fix conversation agent fallback
- Add diagnostics to SmartThings
- Bump bleak-esphome to 2.8.0
- Bump reolink-aio to 0.12.1
- Fix Music Assistant media player entity features
- Update frontend to 20250227.0

## 2025.2.5

- Fix bug in set_preset_mode_with_end_datetime (wrong typo of frost_guard) (netatmo docs)
- Bump pyhive-integration to 1.0.2 (hive docs) (dependency)
- Bump tesla-fleet-api to v0.9.10 (tessie docs) (teslemetry docs) (tesla_fleet docs) (dependency)
- Bump pysmarty2 to 0.10.2 (smarty docs) (dependency)
- Bump pyvesync for vesync (vesync docs) (dependency)
- Bump airgradient to 0.9.2 (airgradient docs) (dependency)
- Bump pyrympro from 0.0.8 to 0.0.9 (rympro docs) (dependency)
- Fix TV input source option for Sonos Arc Ultra (sonos docs)
- Add assistant filter to expose entities list command (homeassistant docs)
- Fix playback for encrypted Reolink files (reolink docs)
- Bump pyfritzhome to 0.6.15 (fritzbox docs) (dependency)
- Fix Reolink callback id collision (reolink docs)
- Fix handling of min/max temperature presets in AVM Fritz!SmartHome (fritzbox docs)
- Bump pyprosegur to 0.0.13 (prosegur docs) (dependency)
- Bump reolink-aio to 0.12.0 (reolink docs) (dependency)
- Bump deebot-client to 12.2.0 (ecovacs docs) (dependency)
- Update frontend to 20250221.0 (frontend docs) (dependency)

## 2025.2.4

- Bump python-kasa to 0.10.2 (tplink docs) (dependency)
- Bump hass-nabucasa from 0.90.0 to 0.91.0 (cloud docs) (dependency)
- Bump aiowebostv to 0.6.2 (webostv docs) (dependency)
- Bump ZHA to 0.0.49 to fix Tuya TRV issues (zha docs) (dependency)
- Bump pyseventeentrack to 1.0.2 (seventeentrack docs) (dependency)
- Bump hass-nabucasa from 0.91.0 to 0.92.0 (cloud docs) (dependency)
- Bump py-synologydsm-api to 2.6.3 (synology_dsm docs) (dependency)
- Update frontend to 20250214.0 (dependency)

## 2025.2.3

- Bump hass-nabucasa from 0.88.1 to 0.89.0 (cloud docs) (dependency)
- Add missing thermostat state EMERGENCY_HEAT to econet (econet docs)
- Fix broken issue creation in econet (econet docs)
- Fix version extraction for APsystems (apsystems docs)
- Fix BackupManager.async_delete_backup (backup docs)
- Fix next authentication token error handling (nest docs)
- Bump pyenphase to 1.25.1 (enphase_envoy docs) (dependency)
- Bump sentry-sdk to 1.45.1 (sentry docs) (dependency)
- Bump zeroconf to 0.144.1 (zeroconf docs) (dependency)
- Bump cryptography to 44.0.1 (dependency)
- Fix tplink iot strip sensor refresh (tplink docs)
- Bump deebot-client to 12.1.0 (ecovacs docs) (dependency)
- Bump hass-nabucasa from 0.89.0 to 0.90.0 (cloud docs) (dependency)
- Update cloud backup agent to use calculate_b64md5 from lib (cloud docs)

## 2025.2.2

- Bump ohmepy to 1.2.9 (ohme docs) (dependency)
- Bump onedrive_personal_sdk to 0.0.9 (onedrive docs) (dependency)
- Fix tplink child updates taking up to 60s (tplink docs)
- Fix manufacturer_id matching for 0 (bluetooth docs)
- Fix DAB radio in Onkyo (onkyo docs)
- Fix LG webOS TV fails to setup when device is off (webostv docs)
- Fix heos migration (heos docs)
- Bump pydrawise to 2025.2.0 (hydrawise docs) (dependency)
- Bump aioshelly to version 12.4.2 (shelly docs) (dependency)
- Bump habiticalib to v0.3.7 (habitica docs) (dependency)
- Bump py-synologydsm-api to 2.6.2 (synology_dsm docs) (dependency)
- Bump onedrive-personal-sdk to 0.0.10 (onedrive docs) (dependency)
- Bump pyheos to v1.0.2 (heos docs) (dependency)
- Update frontend to 20250210.0 (frontend docs) (dependency)

## 2025.2.1

- Fix hassio test using wrong fixture (hassio docs)
- Update govee-ble to 0.42.1 (govee_ble docs) (dependency)
- Bump holidays to 0.66 (workday docs) (holiday docs) (dependency)
- Bump aiohttp-asyncmdnsresolver to 0.1.0 (dependency)
- Bump aiohttp to 3.11.12 (dependency)
- Bump govee-ble to 0.43.0 to fix compat with new H5179 firmware (govee_ble docs) (dependency)
- Bump habiticalib to v0.3.5 (habitica docs) (dependency)
- Fix Mill issue, where no sensors were shown (mill docs)
- Fix sending polls to Telegram threads (telegram_bot docs)
- Add excluded domains to broadcast intent (assist_satellite docs)
- Fix Overseerr webhook configuration JSON (overseerr docs)
- Bump eheimdigital to 1.0.6 (eheimdigital docs) (dependency)
- Bump pyfireservicerota to 0.0.46 (fireservicerota docs)
- Bump reolink-aio to 0.11.10 (reolink docs) (dependency)
- Bump aioshelly to version 12.4.1 (shelly docs) (dependency)
- Bump electrickiwi-api to 0.9.13 (electric_kiwi docs) (dependency)
- Bump ZHA to 0.0.48 (zha docs) (dependency)
- Bump Electrickiwi-api to 0.9.14 (electric_kiwi docs) (dependency)
- Update google-nest-sdm to 7.1.3 (nest docs) (dependency)
- Fix LG webOS TV turn off when device is already off (webostv docs)

## 2025.2.0b12

- Bump hassil and intents
- Update frontend to 20250205.0
- Bump dbus-fast to 2.33.0

## 2025.2.0b11

- Bump onedrive to 0.0.8
- Bump reolink_aio to 0.11.9
- Bump aiohasupervisor to version 0.3.0
- Update frontend to 20250205.0

## 2025.2.0b10

- Fix memory leak when unloading DataUpdateCoordinator
- Update led-ble to 1.1.5
- Fix sqlalchemy deprecation warning that declarative_base has moved
- Bump led-ble to 1.1.6
- Bump Tesla Fleet API to v0.9.8
- Bump pysmlight to v0.1.7

## 2025.2.0b9

- Add view to download support package to Cloud component
- Bump tololib to 1.2.2
- Bump onedrive-personal-sdk to 0.0.4
- Fix HomeWizard reconfigure flow throwing error for v2-API devices
- Update frontend to 20250204.0
- Bump uiprotect to 7.5.1
- Fix incorrect UPB service entity type
- Bump aranet4 to 2.5.1
- Bump deebot-client to 12.0.0
- Fix Tado missing await

## 2025.2.0b8

- Bump todist-api-python to 2.1.7
- Bump pypck to 0.8.5
- Fix retrieving PIN when no pin is set on mount in motionmount integration
- Fix minor issues in Homee
- Bump python-roborock to 2.11.1
- Bump onedrive-personal-sdk to 0.0.2
- Remove v2 API support for HomeWizard P1 Meter
- Update frontend to 20250203.0
- Bump pymill to 0.12.3
- Bump tesla-fleet-api to 0.9.2
- Fix data update coordinator garbage collection
- Bump onedrive-personal-sdk to 0.0.3

## 2025.2.0b7

- Bump dbus-fast to 2.30.4
- Bump bluetooth-data-tools to 1.23.3
- Bump habiticalib to v0.3.4
- Bump monarchmoney to 0.4.4
- Fix mqtt reconfigure does not use broker entry password when it is not changed
- Bump python-kasa to 0.10.1
- Bump dbus-fast to 2.31.0
- Bump aiodhcpwatcher to 1.0.3
- Bump bleak-esphome to 2.7.0
- Bump dbus-fast to 2.23.0

## 2025.2.0b6

- Bump lacrosse-view to 1.0.4
- Update RestrictedPython to 8.0
- Fix Homekit camera profiles schema
- Remove entity state from mcp-server prompt
- Bump habluetooth to 3.21.0
- Add missing brackets to ESPHome configuration URLs with IPv6 addresses
- Bump deebot-client to 12.0.0b0

## 2025.2.0b5

- Bump habluetooth to 3.20.1

## 2025.2.0b4

- Update Overseerr string to mention CSRF
- Bump bthome-ble to 3.11.0
- Bump zeroconf to 0.143.0
- Bump bthome-ble to 3.12.3
- Bump aiohttp-asyncmdnsresolver to 0.0.3
- Bump habluetooth to 3.17.1
- Bump aioimaplib to version 2.0.1

## 2025.2.0b3

- Bump total-connect-client to 2025.1.4
- Bump jellyfin-apiclient-python to 1.10.0
- Bump opower to 0.8.9
- Bump zeroconf to 0.142.0
- Bump aiohttp-asyncmdnsresolver to 0.0.2
- Update knx-frontend to 2025.1.30.194235
- Bump habluetooth to 3.15.0
- Fix missing duration translation for Swiss public transport integration
- Remove the unparsed config flow error from Swiss public transport
- Bump habluetooth to 3.17.0
- Update frontend to 20250131.0
- Bump bleak-esphome to 2.6.0
- Bump SQLAlchemy to 2.0.37
- Bump deebot-client to 11.1.0b2

## 2025.2.0b2

- Add start_conversation service to Assist Satellite
- Fix loading of SMLIGHT integration when no internet is available
- Bump ZHA to 0.0.47
- Bump nest to 7.1.1
- Add missing discovery string from onewire
- Fix handling of renamed backup files in the core writer
- Fix onedrive does not fail on delete not found
- Fix Sonos importing deprecating constant
- Fix backup related translations in Synology DSM
- Fix KeyError for Shelly virtual number component
- Update frontend to 20250130.0

## 2025.2.0b1

- Fix incorrect Bluetooth source address when restoring data from D-Bus
- Bump backup store to version 1.3

## 2025.1.4

- Update Hydrawise maximum watering duration to meet the app limits (hydrawise docs)
- Bump holidays to 0.65 (workday docs) (holiday docs) (dependency)
- Update peblar to v0.4.0 (peblar docs) (dependency)
- Update frontend to 20250109.1 (frontend docs) (dependency)
- Update frontend to 20250109.2 (frontend docs) (dependency)
- Bump aiowithings to 3.1.5 (withings docs) (dependency)
- Bump powerfox to v1.2.1 (powerfox docs) (dependency)

### BREAKING CHANGES

- Fix slave id equal to 0 (modbus docs)

## 2025.1.3

- Fix DiscoveryFlowHandler when discovery_function returns bool
- Bump pyaussiebb to 0.1.5 (aussie_broadband docs) (dependency)
- Fix Watergate Power supply mode description and MQTT/Wifi uptimes (watergate docs)
- Fix missing comma in ollama MODEL_NAMES (ollama docs)
- Bump Freebox to 1.2.2 (freebox docs) (dependency)
- Fix descriptions of send_message action of Bring! integration (bring docs)
- Bump switchbot-api to 2.3.1 (switchbot_cloud docs) (dependency)
- Fix incorrect cast in HitachiAirToWaterHeatingZone in Overkiz (overkiz docs)
- Fix referenced objects in script sequences
- Bump demetriek to 1.2.0 (lametric docs) (dependency)
- Bump elkm1-lib to 2.2.11 (elkm1 docs) (dependency)
- Fix mqtt number state validation (mqtt docs)
- Add reauthentication to SmartThings (smartthings docs)
- Update aioairzone to v0.9.9 (airzone docs) (dependency)
- Remove device_class from NFC and fingerprint event descriptions (unifiprotect docs)
- Bump onvif-zeep-async to 3.2.2 (onvif docs) (dependency)
- Update NHC lib to v0.3.4 (niko_home_control docs) (dependency)
- Update knx-frontend to 2025.1.18.164225 (knx docs) (dependency)
- Bump aiooui to 0.1.8 (nmap_tracker docs) (dependency)
- Bump aiooui to 0.1.9 (nmap_tracker docs) (dependency)
- Fix switchbot cloud library logger (switchbot_cloud docs)
- Bump aioraven to 0.7.1 (rainforest_raven docs) (dependency)
- Bump onvif-zeep-async to 3.2.3 (onvif docs) (dependency)
- Bump yt-dlp to 2025.01.15 (media_extractor docs) (dependency)
- Bump deebot-client to 11.0.0 (ecovacs docs) (dependency)

## 2025.1.2

- Fix Météo-France setup in non French cities (because of failed next rain sensor) (meteo_france docs)
- Fix ZHA "referencing a non existing via_device" warning (zha docs)
- Fix channel retrieval for Reolink DUO V1 connected to a NVR (reolink docs)
- Bump aioautomower to 2025.1.0 (husqvarna_automower docs)
- Bump cookidoo-api to 0.12.2 (cookidoo docs)
- Add jitter to backup start time to avoid thundering herd (backup docs)
- Bump pysuezV2 to 2.0.3 (suez_water docs)
- Fix Flick Electric Pricing (flick_electric docs)
- Update frontend to 20250109.0 (frontend docs)

## 2025.1.1

- Bump bleak-esphome to 2.0.0 (esphome docs) (dependency)
- Bump uiprotect to version 7.2.0 ([unifiprotect docs]) (dependency)
- Fix Flick Electric authentication (flick_electric docs)
- Fix hive color tunable light (hive docs)
- Remove call to remove slide ([slide_local docs])
- Update twentemilieu to 2.2.1 ([twentemilieu docs]) (dependency)
- Fix Reolink playback of recodings ([reolink docs])
- Update peblar to 0.3.3 ([peblar docs]) (dependency)
- Bump cookidoo-api library to 0.11.1 of for Cookidoo (cookidoo docs)
- Update demetriek to 1.1.1 (lametric docs) (dependency)
- Bump ZHA to 0.0.45 ([zha docs]) (dependency)
- Bump openwebifpy to 4.3.1 (enigma2 docs) (dependency)
- Fix swapped letter order in "°F" and "°C" temperature units (iron_os docs)
- Bump pysuezV2 to 2.0.1 ([suez_water docs]) (dependency)
- Fix missing sentence-casing etc. in several strings ([waze_travel_time docs])
- Fix a few typos or grammar issues in asus_wrt (asuswrt docs)
- Bump uiprotect to version 7.4.1 ([unifiprotect docs]) (dependency)
- Bump habluetooth to 3.7.0 (bluetooth docs) (dependency)
- Fix how function arguments are passed on actions at Home Connect (home_connect docs)
- Bump aiolifx-themes to update colors (lifx docs) (dependency)
- Update Roborock config flow message when an account is already configured ([roborock docs])
- Bump solax to 3.2.3 ([solax docs]) (dependency)
- Add extra failure exceptions during roborock setup ([roborock docs])
- Bump python-kasa to 0.9.1 ([tplink docs]) (dependency)
- Add bring_api to loggers in Bring integration (bring docs)
- Fix wrong power limit decimal place in IronOS (iron_os docs)
- Update frontend to 20250106.0 (frontend docs) (dependency)
- Bump powerfox to v1.1.0 ([powerfox docs]) (dependency)
- Bump powerfox to v1.2.0 ([powerfox docs]) (dependency)
- Bump holidays to 0.64 ([workday docs]) (holiday docs) (dependency)

## 2025.1.0b9

- Add Reolink proxy for playback
- Add backup as after_dependency of frontend
- Update frontend to 20250103.0

## 2025.1.0b8

- Fix input_datetime.set_datetime not accepting 0 timestamp value
- Bump aioacaia to 0.1.13
- Fix backup dir not existing
- Add error prints for recorder fatal errors
- Fix activating backup retention config on startup
- Update peblar to v0.3.2

## 2025.1.0b7

- Bump deebot-client to 10.1.0
- Fix a few small typos in peblar
- Update peblar to 0.3.1

## 2025.1.0b6

- Add new ID LAP-V201S-AEUR for Vital200S AirPurifier in Vesync integration
- Bump zabbix-utils to 2.0.2
- Add state attributes translations to GIOS
- Fix SQL sensor name
- Bump intents to 2025.1.1
- Bump ZHA to 0.0.44
- Bump aioacaia to 0.1.12
- Update frontend to 20250102.0

## 2025.1.0b5

- Update Flick Electric API
- Add stream preview to options flow in generic camera
- Bump aiocomelit to 0.10.1
- Bump reolink-aio to 0.11.6
- Bump pysynthru version to 0.8.0
- Bump aioshelly to 12.2.0
- Bump hassil to 2.1.0
- Update frontend to 20241231.0
- Bump pylamarzocco to 1.4.6

## 2025.1.0b4

- Bump pyvlx to 0.2.26
- Bump elmax-api
- Fix duplicate sensor disk entities in Systemmonitor
- Fix Onkyo volume rounding
- Bump opower to 0.8.7
- Bump aiopegelonline to 0.1.1
- Fix 400 This voice does not support speaking rate or pitch parameters at this time for Google Cloud Journey voices
- Bump pylamarzocco to 1.4.5
- Remove excessive period at end of action name
- Bump aiomealie to 0.9.5
- Update frontend to 20241230.0

## 2025.1.0b3

- Fix swiss public transport line field none
- Bump pylamarzocco to 1.4.3
- Fix Nord Pool empty response
- Bump aiorussound to 4.1.1
- Remove timeout from Russound RIO initialization
- Fix KNX config flow translations and add data descriptions
- Bump python-homeassistant-analytics to 0.8.1
- Bump pytile to 2024.12.0
- Bump yt-dlp to 2024.12.23
- Add missing device classes in scrape
- Update knx-frontend to 2024.12.26.233449
- Fix Wake on LAN Port input as Box instead of Slider
- Bump VoIP utils to 0.2.2
- Bump frontend to 20241229.0

## 2025.1.0b2

- Fix reload modbus component issue
- fix "Slow" response leads to "Could not find a charging station"
- Update apprise to v1.9.1
- Update Jinja2 to 3.1.5
- Update frontend to 20241224.0

## 2025.1.0b1

- Fix a history stats bug when window and tracked state change simultaneously
- Add Harvey virtual integration
- Fix duplicate call to async_register_preload_platform
- Add cronsim to default dependencies
- Fix missing % in string for generic camera
- Fix Peblar import in data coordinator

## 2024.12.5

- Bump nice-go to 1.0.0 (nice_go docs) (dependency)
- Add support for Nice G.O. HAE00080 wall station (nice_go docs)
- Bump Freebox to 1.2.1 (freebox docs) (dependency)
- Bump pyOverkiz to 1.15.3 (overkiz docs) (dependency)
- Update Roborock to 2.8.1 (roborock docs) (dependency)
- Update fjäråskupan to 2.3.1 (fjaraskupan docs) (dependency)
- Update fjäråskupan to 2.3.2 (fjaraskupan docs) (dependency)
- Bump gardena_bluetooth to 1.5.0 (gardena_bluetooth docs) (dependency)
- Bump aiohttp to 3.11.11 (dependency)
- Fix Twinkly raise on progress (twinkly docs)

## 2024.12.4

- Fix fibaro climate hvac mode (fibaro docs)
- Bump yt-dlp to 2024.12.13 (media_extractor docs) (dependency)
- Fix strptime in python_script (python_script docs)
- Bump yalexs-ble to 2.5.4 (august docs) (yalexs_ble docs) (yale docs) (dependency)
- Bump starlink-grpc-core to 1.2.1 to fix missing ping (starlink docs) (dependency)
- Bump aiolifx to 1.1.2 and add new HomeKit product prefixes (lifx docs) (dependency)
- Bump incomfort-client to v0.6.4 (incomfort docs) (dependency)
- Bump yalexs-ble to 2.5.5 (august docs) (yalexs_ble docs) (yale docs) (dependency)
- Bump imgw-pib to version 1.0.7 (imgw_pib docs) (dependency)
- Fix fan setpoints for flexit_bacnet (flexit_bacnet docs)
- Bump holidays to 0.63 (workday docs) (holiday docs) (dependency)

## 2024.12.3

- Bump python-linkplay to v0.1.1 (linkplay docs) (dependency)
- Bump pydaikin to 2.13.8 (daikin docs) (dependency)
- Fix pipeline conversation language (conversation docs) (assist_pipeline docs)
- fix AndroidTV logging when disconnected (androidtv docs)
- Bump led-ble to 1.1.1 (led_ble docs) (dependency)
- Fix LaMetric config flow for cloud import path (lametric docs)
- Update frontend to 20241127.8 (frontend docs) (dependency)
- Bump pysuezV2 to 1.3.5 (suez_water docs) (dependency)
- Bump py-aosmith to 1.0.12 (aosmith docs) (dependency)
- Bump deebot-client to 9.4.0 (ecovacs docs) (dependency)
- Bump aiowithings to 3.1.4 (withings docs)

## 2024.12.2

- Bump pydrawise to 2024.12.0 (hydrawise docs) (dependency)
- Fix API change for AC not supporting floats in SwitchBot Cloud (switchbot_cloud docs)
- Update pyrisco to 0.6.5 (risco docs) (dependency)
- Fix PyTado dependency (tado docs) (dependency)
- Bump pycups to 2.0.4 (cups docs) (dependency)
- Update debugpy to 1.8.8 (debugpy docs) (dependency)
- bump total_connect_client to 2023.12 (totalconnect docs) (dependency)
- Bump aiounifi to v81 to fix partitioned cookies on python 3.13 (unifi docs) (dependency)
- Update twentemilieu to 2.2.0 (twentemilieu docs) (dependency)
- Bump yalexs-ble to 2.5.2 (yalexs_ble docs) (dependency)
- Bump plugwise to v1.6.1 (plugwise docs) (dependency)
- Bump plugwise to v1.6.2 and adapt (plugwise docs) (dependency)
- Fix config flow in Husqvarna Automower (husqvarna_automower docs)
- Bump ZHA dependencies (zha docs) (dependency)
- Bump plugwise to v1.6.3 (plugwise docs) (dependency)
- Bump yt-dlp to 2024.12.06 (media_extractor docs) (dependency)
- Bump intents to 2024.12.9 (conversation docs) (dependency)
- Update frontend to 20241127.7 (frontend docs) (dependency)
- Bump reolink-aio to 0.11.5 (reolink docs) (dependency)
- Bump deebot-client to 9.3.0 (ecovacs docs) (dependency)
- Bump aioacaia to 0.1.11 (acaia docs) (dependency)

## 2024.12.1

- Bump elmax-api to 0.0.6.3 (elmax docs) (dependency)
- Fix deprecated call to mimetypes.guess_type in CachingStaticResource (http docs)
- Bump tesla-fleet-api to 0.8.5 (tessie docs) (teslemetry docs) (tesla_fleet docs)
- Add missing UnitOfPower to sensor (sensor docs)
- Bump upb-lib to 0.5.9 (upb docs) (dependency)
- Bump pydeako to 0.6.0 (deako docs) (dependency)
- Bump aiohttp to 3.11.10 (dependency)
- Bump aioesphomeapi to 28.0.0 (esphome docs) (dependency)
- Update exception handling for python3.13 for getpass.getuser
- Bump hass-nabucasa from 0.85.0 to 0.86.0 (cloud docs) (dependency)
- Fix nordpool dont have previous or next price (nordpool docs)
- Bump deebot-client to 9.2.0 (ecovacs docs) (dependency)
- Bump tplink python-kasa dependency to 0.8.1 (tplink docs) (dependency)
- Bump samsungtvws to 2.7.2 (samsungtv docs) (dependency)
- Update frontend to 20241127.5 (frontend docs) (dependency)
- Update frontend to 20241127.6 (frontend docs) (dependency)
- Fix google tasks due date timezone handling (google_tasks docs)

## 2024.12.0b6

- Bump knocki to 0.4.2
- Bump holidays to 0.62
- Bump thinqconnect to 1.0.2
- Fix recorder "year" period in leap year
- Fix typo in exception message in google_photos integration
- Fix blocking call in netdata
- fix: unifiprotect prevent RTSP repair for third-party cameras
- Bump yt-dlp to 2024.12.03
- Bump deebot-client to 9.1.0
- Update frontend to 20241127.4

## 2024.12.0b5

- Add support for features changing at runtime in Matter integration
- Update buienradar sensors only after being added to HA
- Add translated native unit of measurement - squeezebox
- Add translated native unit of measurement - Transmission
- Add translated native unit of measurement - PiHole
- Add translated native unit of measurement - QBitTorrent
- Fix Reolink dispatcher ID for onvif fallback
- Add translated native unit of measurement to Jellyfin
- Bump pyezviz to 0.2.2.3
- Fix imap sensor in case of alternative empty search response
- Bump hassil and intents
- Bump PyJWT to 2.10.1
- Update frontend to 20241127.2
- Bump unifi_ap to 0.0.2
- Fix bad hassil tests on CI
- Bump uiprotect to 6.6.5
- Bump pytouchlinesl to 0.3.0
- Update frontend to 20241127.3

## 2024.12.0b4

- Bump bimmer_connected to 0.17.2
- Bump propcache to 0.2.1
- Bump yarl to 1.18.3
- Bump yt-dlp to 2024.11.18
- Bump spotifyaio to 0.8.11
- Bump aiohttp to 3.11.9
- Bump psymlight v0.1.4
- Bump refoss to v1.2.5

## 2024.12.0b3

- Bump SQLAlchemy to 2.0.36
- Fix modbus state not dumped on restart
- Fix history stats count update immediately after change
- Bump denonavr to v1.0.1
- Bump aioacaia to 0.1.10
- Fix media player join action for Music Assistant integration
- Bump aiohomekit to 3.2.7
- Bump uiprotect to 6.6.4
- Fix KNX IP Secure tunnelling endpoint selection with keyfile
- Bump aiomealie to 0.9.4
- Bump reolink_aio to 0.11.4

## 2024.12.0b2

- Bump bimmer_connected to 0.17.0
- Remove Spotify featured playlists and categories from media browser
- Bump samsungtvws to 2.7.1
- Remove wrong plural "s" in 'todo.remove_item' action
- Fix more flaky translation checks
- Bump spotifyaio to 0.8.10
- Bump pyatv to 0.16.0
- Update frontend to 20241127.1
- Bump PyMetEireann to 2024.11.0
- Fix flaky test in history stats
- Add captcha to BMW ConfigFlow

## 2024.12.0b1

- Add missing data_description for lamarzocco OptionsFlow
- Bump music assistant client 1.0.8
- Add a missing rainbird data description
- Bump aiohttp to 3.11.8
- Bump orjson to 3.10.12
- Remove Spotify audio feature sensors
- Bump uiprotect to 6.6.3
- Bump pylamarzocco to 1.2.12
- Fix rounding of attributes in Habitica integration
- Bump aioesphomeapi to 27.0.3
- Bump ZHA to 0.0.41
- Fix Home Connect microwave programs

## 2024.11.3

- Fix and bump apsystems-ez1 to 2.4.0 (apsystems docs) (dependency)
- Fix file uploads in MQTT config flow not processed in executor (mqtt docs)
- Update twentemilieu to 2.1.0 (twentemilieu docs) (dependency)
- Fix unexpected stop of media playback via ffmpeg proxy for ESPhome devices (esphome docs)
- Bump homematicip to 1.1.3 (homematicip_cloud docs) (dependency)
- Bump bluetooth-adapters to 0.20.2 (bluetooth docs) (dependency)
- Update elmax_api to v0.0.6.1 (elmax docs) (dependency)
- Bump aioairq to 0.4.3 (airq docs) (dependency)
- Add more UI user-friendly description to six Supervisor actions (hassio docs)
- Add missing catholic category in workday (workday docs)
- Bump holidays to 0.61 (workday docs) (holiday docs) (dependency)
- Bump aioairzone to 0.9.6 (airzone docs) (dependency)
- Update aioairzone to v0.9.7 (airzone docs) (dependency)
- Fix typo in name of "Alarm arm home instant" action (elkm1 docs)
- Fix cast translation string (cast docs)
- Fix typo in ESPHome repair text (esphome docs)
- Fix fibaro cover state is not always correct (fibaro docs)
- Bump reolink_aio to 0.11.2 (reolink docs) (dependency)

## 2024.11.2

- Bump aiohttp to 3.10.11 (dependency)
- Fix RecursionError in Husqvarna Automower coordinator ([husqvarna_automower docs])
- Bump python-linkplay to v0.0.18 ([linkplay docs]) (dependency)
- Fix translations in ollama ([ollama docs])
- Bump nice-go to 0.3.10 ([nice_go docs]) (dependency)
- Fix wording in Google Calendar create_event strings for consistency ([google docs])
- Fix uptime sensor for Vodafone Station ([vodafone_station docs])
- Bump pyTibber ([tibber docs]) (dependency)
- Bump SoCo to 0.30.6 ([sonos docs]) (dependency)
- Bump google-nest-sdm to 6.1.5 ([nest docs]) (dependency)
- Update generic thermostat strings for clarity and accuracy ([generic_thermostat docs])
- Fix translation key for done response in conversation ([conversation docs])
- Add more f-series models to myuplink ([myuplink docs])
- Fix Homekit error handling alarm state unknown or unavailable ([homekit docs])
- Fix fan's warning TURN_ON, TURN_OFF ([lg_thinq docs])
- Bump python-linkplay to 0.0.20 ([linkplay docs])
- Add seek support to LinkPlay ([linkplay docs])
- Add Spotify and Tidal to playingmode mapping ([linkplay docs])
- Fix typo in go2rtc ([go2rtc docs])
- Bump spotifyaio to 0.8.8 ([spotify docs])
- Bump Tibber 0.30.8 ([tibber docs]) (dependency)
- Fix missing title placeholders in powerwall reauth ([powerwall docs])
- Bump ring library ring-doorbell to 0.9.9 ([ring docs]) (dependency)
- Bump ring-doorbell to 0.9.12 ([ring docs]) (dependency)
- Add title to water heater component ([water_heater docs])
- Fix translation in statistics ([statistics docs])
- Fix typo in file strings ([file docs])
- Bump aiowithings to 3.1.2 ([withings docs])
- Fix legacy _attr_state handling in AlarmControlPanel ([alarm_control_panel docs])
- Bump reolink_aio to 0.11.0 ([reolink docs]) (dependency)
- Fix translations in subaru ([subaru docs])
- Bump aioruckus to 0.42 ([ruckus_unleashed docs]) (dependency)
- Bump go2rtc-client to 0.1.1 ([go2rtc docs]) (dependency)
- Bump aiowithings to 3.1.3 ([withings docs])
- Add go2rtc recommended version ([go2rtc docs])
- fix translation in srp_energy ([srp_energy docs])
- Fix non-thread-safe operation in powerview number ([hunterdouglas_powerview docs])
- Bump ZHA dependencies ([zha docs])
- Update uptime deviation for Vodafone Station ([vodafone_station docs])
- Bump reolink-aio to 0.11.1 ([reolink docs]) (dependency)
- Fix hassfest by adding go2rtc reqs
- Add missing translation string to smarty ([smarty docs])
- Bump sense-energy to 0.13.4 ([sense docs]) ([emulated_kasa docs]) (dependency)
- Fix scene loading issue ([hue docs])
- Add missing translation string to hvv_departures ([hvv_departures docs])
- Add missing translation string to lg_netcast ([lg_netcast docs])
- Add missing translation string to philips_js ([philips_js docs])
- Bump pyplaato to 0.0.19 ([plaato docs]) (dependency)
- Remove dumping config entry to log in setup of roborock ([roborock docs])
- Fix missing translations in vilfo ([vilfo docs])
- Fix missing translations in utility_meter ([utility_meter docs])
- Fix missing translations in tradfri ([tradfri docs])
- Fix missing translations in toon ([toon docs])
- Fix missing translations in madvr ([madvr docs])
- Fix missing translations in generic ([generic docs])
- Fix missing translations in onewire ([onewire docs])
- Bump python-smarttub to 0.0.38 ([smarttub docs]) (dependency)

## 2024.11.1

- Bump intents to 2024.11.6 (conversation docs) (dependency)
- Fix Trunks in Teslemetry and Tesla Fleet (teslemetry docs) (tesla_fleet docs)
- Update sense energy library to 0.13.3 (sense docs) (emulated_kasa docs) (dependency)
- Bump google-nest-sdm to 6.1.4 (nest docs) (dependency)
- Add missing placeholder description to twitch (twitch docs)
- Bump agent-py to 0.0.24 (agent_dvr docs)
- Fix KeyError in nest integration when the old key format does not exist (nest docs)
- Add missing string to tedee plus test (tedee docs)
- Fix typo in insteon strings (insteon docs)
- Update frontend to 20241106.1 (frontend docs) (dependency)
- Bump python-roborock to 2.7.2 (roborock docs)
- Update frontend to 20241106.2 (frontend docs) (dependency)
- Fix issue when timestamp is None (seventeentrack docs)
- Add go2rtc workaround for HA managed one until upstream fixes it (go2rtc docs)
- Bump spotifyaio to 0.8.7 (spotify docs)
- Bump ha-ffmpeg to 3.2.2 (ffmpeg docs) (dependency)
- Fix volume_up not working in some cases in bluesound integration (bluesound docs)
- Fix bugs in nest stream expiration handling (nest docs)

## 2024.11.0b9

- Remove deprecation issues for LCN once entities removed
- Bump go2rtc-client to 0.1.0

## 2024.11.0b8

- Update pylutron to 0.2.16
- Bump pyTibber to 0.30.4
- Bump spotifyaio to 0.8.4
- Update Bang & Olufsen source list as availability changes
- Bump reolink_aio to 0.10.4
- Fix native sync WebRTC offer
- Bump spotifyaio to 0.8.5
- Bump intents and add HassRespond test
- Bump go2rtc-client to 0.0.1b4
- Bump go2rtc-client to 0.0.1b5
- Update frontend to 20241106.0

## 2024.11.0b7

- Update frontend to 20241105.0
- Bump holidays to 0.60

## 2024.11.0b6

- Add basic testing framework to LG ThinQ
- Bump pypalazzetti to 0.1.10
- Bump bimmer_connected to 0.16.4
- Bump pyfibaro to 0.8.0
- Add repair for add-on boot fail
- Update snapshot for lg thinq
- Remove timers from LG ThinQ

## 2024.11.0b5

- Fix source mapping in Onkyo
- Add HassRespond intent
- Fix translation in ovo energy
- Fix translations in hydrawise
- Bump reolink-aio to 0.10.3
- Fix unifiprotect supported features being set too late
- Bump uiprotect to 6.4.0

## 2024.11.0b4

- Bump lcn-frontend to 0.2.1
- Add watchdog to monitor and respawn go2rtc server
- Update Spotify state after mutation
- Add state class to precipitation_intensity in Aemet
- Bump ayla-iot-unofficial to 1.4.3
- Bump yt-dlp to 2024.11.04
- Fix stringification of discovered hassio uuid
- Fix incorrect description placeholders in azure event hub
- Update go2rtc stream if stream_source is not matching
- Fix aborting flows for single config entry integrations
- Fix create flow logic for single config entry integrations
- Fix ESPHome dashboard check
- Bump python-kasa to 0.7.7
- Remove all ice_servers on native sync WebRTC cameras
- Fix translations in homeworks
- Update frontend to 20241104.0
- Fix translations in landisgyr

## 2024.11.0b3

- Bump Airthings BLE to 0.9.2
- Bump python-linkplay to 0.0.17
- Bump bring-api to 0.9.1
- Bump DoorBirdPy to 3.0.8
- Fix nest streams broken due to CameraCapabilities change
- Add missing translation string to lamarzocco
- Bump HAP-python to 4.9.2
- Bump spotifyaio to 0.8.3
- Bump thinqconnect to 1.0.0

## 2024.11.0b2

- Fix Geniushub setup
- Bump spotifyaio to 0.8.1
- Bump aiohasupervisor to version 0.2.1
- Fix flaky camera test
- Bump aiowithings to 3.1.1
- Add go2rtc debug_ui yaml key to enable go2rtc ui
- Bump webrtc-models to 0.2.0
- Bump spotifyaio to 0.8.2
- Bump aiohomekit to 3.2.6
- Bump aioesphomeapi to 27.0.1
- Bump sensorpush-ble to 1.7.1
- Bump autarco lib to v3.1.0

## 2024.11.0b1

- Fix timeout issue on Roomba integration when adding a new device
- Fix current temperature calculation for incomfort boiler
- Bump uiprotect to 6.3.2
- Fix async_config_entry_first_refresh used after config entry is loaded in speedtestdotcom
- Bump reolink_aio to 0.10.2
- Fix bthome UnitOfConductivity
- Bump yarl to 1.17.1
- Fix "home" route in Tesla Fleet & Teslemetry
- Update frontend to 20241031.0

## 2024.10.4

- Fix evohome regression preventing helpful messages when setup fails (evohome docs)
- Bump ring-doorbell to 0.9.7 (ring docs) (dependency)
- Bump ring-doorbell library to 0.9.8 (ring docs) (dependency)
- Add diagnostics to Comelit SimpleHome (comelit docs)
- Bump pyTibber to 0.30.3 (tibber docs) (dependency)
- Add diagnostics to Vodafone Station (vodafone_station docs)
- Bump pyduotecno to 2024.10.1 (duotecno docs) (dependency)
- Fix uptime floating values for Vodafone Station (vodafone_station docs)
- Fix cancellation leaking upward from the timeout util
- Fix devolo_home_network devices not reporting a MAC address (devolo_home_network docs)
- Bump yt-dlp to 2024.10.22 (media_extractor docs) (dependency)
- Remove DHCP match from awair (awair docs)
- Update frontend to 20241002.4 (frontend docs) (dependency)
- Fix adding multiple devices simultaneously to devolo Home Network's device tracker (devolo_home_network docs)
- Fix NYT Games connection max streak (nyt_games docs)
- Bump nyt_games to 0.4.4 (nyt_games docs) (dependency)

## 2024.10.3

- Update home-assistant-bluetooth to 1.13.0 (dependency)
- Fix printer uptime fluctuations in IPP (ipp docs)
- Fix playing media via roku (roku docs)
- Bump yt-dlp to 2024.10.07 (media_extractor docs) (dependency)
- Fix daikin entities not refreshing quickly (daikin docs)
- Update aioairzone to v0.9.4 (airzone docs) (dependency)
- Update aioairzone to v0.9.5 (airzone docs) (dependency)
- Bump gcal_sync to 6.1.6 (google docs) (dependency)
- Bump solarlog_cli to 0.3.2 (solarlog docs) (dependency)
- Bump pyblu to 1.0.4 (bluesound docs)
- Bump pyotgw to 2.2.2 (opentherm_gw docs) (dependency)

## 2024.10.2

- Fix Island status in Teslemetry ([teslemetry docs])
- Bump pyblu to 1.0.3 ([bluesound docs])
- Bump aiostreammagic to 2.5.0 ([cambridge_audio docs]) (dependency)
- Bump opower to 0.8.2 ([opower docs]) (dependency)
- Fix wake up in Tesla Fleet ([tesla_fleet docs])
- Update Radarr config flow to standardize ports ([radarr docs])
- Bump fyta_cli to 0.6.7 ([fyta docs]) (dependency)
- Fix problems with automatic management of Schlage locks ([schlage docs])
- Fix typo in HDMI CEC ([hdmi_cec docs])
- Fix Withings log message ([withings docs])
- Bump NYT Games to 0.4.3 ([nyt_games docs])
- Bump airgradient to 0.9.1 ([airgradient docs])
- Add translation string for Withings wrong account ([withings docs])
- Remove stale references in squeezebox services.yaml ([squeezebox docs])
- Fix Aurora integration casts longitude and latitude to integer ([aurora docs])
- Bump python-linkplay to 0.0.15 ([linkplay docs]) (dependency)
- Fix custom account config flow setup ([ovo_energy docs])
- Bump solarlog_cli to 0.3.1 ([solarlog docs]) (dependency)
- Update DoorBirdPy to 3.0.3 ([doorbird docs]) (dependency)
- Bump DoorBirdPy to 3.0.4 ([doorbird docs]) (dependency)
- Bump pychromecast to 14.0.3 ([cast docs]) (dependency)
- Fix aurora alert sensor always Off ([aurora docs])
- Update aioairzone-cloud to v0.6.6 ([airzone_cloud docs]) (dependency)
- Bump pysmlight to v0.1.3 ([smlight docs]) (dependency)
- Fix incorrect string in amberlectric ([amberelectric docs])
- Add missing and fix incorrect translation string in alarmdecoder ([alarmdecoder docs])
- Fix incorrect translation string in analytics_insights ([analytics_insights docs])
- Add missing and fix incorrect translation string in aurora ([aurora docs])
- Fix incorrect translation string in azure event hub ([azure_event_hub docs])
- Add missing translation string in blebox ([blebox docs])
- Fix incorrect translation string in bryant_evolution ([bryant_evolution docs])
- Add missing and fix incorrect translation string in duotecno ([duotecno docs])
- Bump pytouchlinesl to 0.1.8 ([touchline_sl docs]) (dependency)
- Fix wrong DPTypes returned by Tuya's cloud ([tuya docs])
- Add missing translation string in AVM Fritz!Smarthome ([fritzbox docs])
- Fix merge_response template not mutate original object
- Bump holidays library to 0.58 ([workday docs]) ([holiday docs]) (dependency)
- Bump pyeconet to 0.1.23 ([econet docs]) (dependency)
- Add missing translation string in otbr ([otbr docs])
- Add missing translation string in yamaha_musiccast ([yamaha_musiccast docs])
- Add support of due date calculation for grey dailies in Habitica integration ([habitica docs])
- Bump imgw_pib library to version 1.0.6 ([imgw_pib docs]) (dependency)
- Bump python-kasa to 0.7.5 ([tplink docs]) (dependency)
- Fix discovery of WMS WebControl pro by using IP address ([wmspro docs])
- Update pywmspro to 0.2.1 to fix handling of unknown products ([wmspro docs]) (dependency)
- Fix europe authentication in Fujitsu FGLair ([fujitsu_fglair docs])
- Bump motionblindsble to 0.1.2 ([motionblinds_ble docs]) (dependency)
- Fix zwave_js config validation for values ([zwave_js docs])
- Fix firmware version parsing in venstar ([venstar docs])
- Bump pyduotecno to 2024.10.0 ([duotecno docs]) (dependency)
- Add missing translation string in solarlog ([solarlog docs])
- Fix missing reauth name translation placeholder in ring integration ([ring docs])
- Add missing translation string for re-auth flows
- Update xknxproject to 3.8.1 ([knx docs]) (dependency)
- Fix casing on Powerview Gen3 zeroconf discovery ([hunterdouglas_powerview docs])
- Fix ring realtime events ([ring docs])
- Update frontend to 20241002.3 ([frontend docs])
- Bump aioautomower to 2024.10.0 ([husqvarna_automower docs]) (dependency)
- Fix license script for ftfy
- Fix regression in Opower that was introduced in 2024.10.0 ([opower docs])
- Bump opower to 0.8.3 ([opower docs]) (dependency)
- Remove some redundant code in Opower's coordinator from the fix in ([opower docs])
- Fix preset handling issue in ViCare ([vicare docs])
- Fix model in Husqvarna Automower ([husqvarna_automower docs])

## 2024.10.1

- Fix device id support for alarm control panel template (template docs)
- Bump pysmlight 0.1.2 (smlight docs) (dependency)
- Remove assumption in ConfigEntryItems about unique unique_id
- Add missing number platform to init of Tesla Fleet (tesla_fleet docs)
- Bump aiomealie to 0.9.3 (mealie docs)
- Fix int value in unique_id for Tellduslive (tellduslive docs)
- Bump matrix-nio to 0.25.2 (matrix docs) (dependency)

## 2024.10.0b9

- Fix Tibber get_prices when called with aware datetime
- Remove codefences from issue titles

## 2024.10.0b12

- Update frontend to 20241002.2

## 2024.10.0b11

- Fix climate entity in ViCare integration
- Update frontend to 20241002.1

## 2024.10.0b10

- Update frontend to 20241002.0

## 2024.10.0b8

- Fix Tailwind cover exception when door is already in the requested state
- Update prometheus-client to 0.21.0
- Update gotailwind to 0.2.4
- Update log error message for Samsung TV

## 2024.10.0b7

- Add config flow validation that calibration factor is not zero
- Update assist_satellite connection test sound
- Fix Z-Wave rediscovery
- Fix reconfigure_confirm logic in madvr config flow

## 2024.10.0b6

- Bump zwave-js-server-python to 0.58.1
- Update frontend to 20240930.0
- Update RestrictedPython to 7.3

## 2024.10.0b5

- Add unique id to mold_indicator
- Bump aiohttp to 3.10.8
- Bump anyio to 4.6.0
- Bump py-synologydsm-api to 2.5.3
- Update local_calendar/todo to avoid blocking in the event loop
- Update ical to 8.2.0
- Bump gcal_sync to 6.1.5
- Fix repair when integration does not exist
- Fix timestamp isoformat in seventeentrack
- Fix removing nulls when encoding events for PostgreSQL
- Bump pylitejet to 0.6.3
- Add missing OUI to august
- Fix Roomba help URL
- Update xknxproject to 3.8.0
- Bump yt-dlp to 2024.09.27

## 2024.10.0b4

- Bump nessclient to 1.1.2
- Bump python-kasa library to 0.7.4
- Bump yarl to 1.13.1
- Bump aiohttp to 3.10.7

## 2024.10.0b3

- Bump python-linkplay to 0.0.12
- Add support for variant of Xiaomi Mi Air Purifier 3C (zhimi.airp.mb4a)
- Fix blocking call in Xiaomi Miio integration
- Update airgradient device sw_version when changed
- Fix Tado unloading
- Update pytouchlinesl to 0.1.6
- Bump pyotgw to 2.2.1
- Bump pytouchlinesl to 0.1.7
- Update frontend to 20240927.0
- Add missing icons to unifi

## 2024.10.0b2

- Update overkiz Atlantic Water Heater away mode switching
- Fix Abode integration needing to reauthenticate after core update
- Bump wolf-comm to 0.0.15
- Fix restoring state class in mobile app
- Bump yarl to 1.13.0
- Fix getting the host for the current request
- Add diagnostics platform to airgradient
- Fix getting the current host for IPv6 urls

## 2024.10.0b1

- Fix ESPHome and VoIP Assist satellite entity names
- Remove Reolink Home Hub main level switches
- Bump aiorussound to 4.0.5
- Bump reolink-aio to 0.9.11
- Fix missing template alarm control panel menu string
- Bump ring-doorbell to 0.9.6
- Bump jaraco.abode to 6.2.1
- Fix typo in Mealie integration
- Bump knocki to 0.3.5
- Add logging to NYT Games setup failures
- Bump nyt_games to 0.4.2
- Fix last played icon in NYT Games
- Fix Withings reauth title
- Bump aiohasupervisor to 0.1.0
- Update frontend to 20240926.0
- Update the Selected Pipeline entity name

## 2024.9.3

- Fix wall connector state in Teslemetry (teslemetry docs)
- Fix set brightness for Netatmo lights (netatmo docs)
- Fix qbittorrent error when torrent count is 0 (qbittorrent docs)
- Fix tibber fails if power production is enabled but no power is produced (tibber docs) (dependency)
- Bump pydaikin to 2.13.7 (daikin docs) (dependency)
- Fix Matter climate platform attributes when dedicated OnOff attribute is off (matter docs)
- Fix loading KNX UI entities with entity category set (knx docs)
- Bump airgradient to 0.9.0 (airgradient docs) (dependency)
- Fix next change (scheduler) sensors in AVM FRITZ!SmartHome (fritzbox docs)
- Bump python-holidays to 0.57 (workday docs) (holiday docs) (dependency)
- Fix surepetcare token update (surepetcare docs)
- Fix due date calculation for future dailies in Habitica integration (habitica docs)
- Bump pydrawise to 2024.9.0 (hydrawise docs) (dependency)
- Add support for new JVC Projector auth method (jvc_projector docs) (dependency)
- Fix blocking call in Bang & Olufsen API client initialization (bang_olufsen docs)
- Bump mozart_api to 3.4.1.8.8 (bang_olufsen docs) (dependency)

### BREAKING CHANGES

- Update Aseko to support new API (aseko_pool_live docs) (dependency)

## 2024.9.2

- Fix Lyric climate Auto mode (lyric docs)
- Fix Schlage removed locks (schlage docs)
- Fix mired range in blebox color temp mode lights (blebox docs)
- Update diagnostics for BSBLan (bsblan docs)
- Fix renault plug state (renault docs)
- Bump yalexs to 8.6.4 (august docs) (yale docs) (dependency)
- Bump aiolifx and aiolifx-themes to support more than 82 zones (lifx docs) (dependency)
- Fix yale_smart_alarm on missing key (yale_smart_alarm docs)
- FIx Sonos announce regression issue (sonos docs)
- Update frontend to 20240909.1 (frontend docs)
- Update tplink config to include aes keys (tplink docs)
- Bump tplink python-kasa lib to 0.7.3 (tplink docs) (dependency)
- Fix incomfort invalid setpoint if override is reported as 0.0 (incomfort docs)
- Bump to python-nest-sdm to 5.0.1 (nest docs) (dependency)
- Remove unused keys from the ZHA config schema (zha docs)
- Bump sfrbox-api to 0.0.11 (sfr_box docs) (dependency)
- Update knx-frontend to 2024.9.10.221729 (knx docs) (dependency)
- Bump russound to 0.2.0 (russound_rnet docs) (dependency)
- Fix favorite position missing for Motion Blinds TDBU devices (motion_blinds docs)
- Add missing Zigbee/Thread firmware config flow translations (homeassistant_yellow docs) (homeassistant_sky_connect docs) (homeassistant_hardware docs)
- Bump lmcloud to 1.2.3 (lamarzocco docs) (dependency)
- Bump ZHA to 0.0.33 (zha docs) (dependency)
- Bump motionblinds to 0.6.25 (motion_blinds docs) (dependency)
- Bump govee light local to 1.5.2 (govee_light_local docs) (dependency)
- Bump aiorussound to 3.0.5 (russound_rio docs) (dependency)

## 2024.9.1

- Fix BTHome validate triggers for device with multiple buttons (bthome docs)
- Fix blocking call in yale_smart_alarm (yale_smart_alarm docs)
- Bump aiorussound to 3.0.4 (russound_rio docs)
- Add follower to the PlayingMode enum (linkplay docs)
- Fix for Hue sending effect None at turn_on command while no effect is active (hue docs)
- Bump pysmlight to 0.0.14 (smlight docs)
- Bump pypck to 0.7.22 (lcn docs)
- Fix controlling AC temperature in airtouch5 (airtouch5 docs)
- Bump sfrbox-api to 0.0.10
- Update frontend to 20240906.0 (frontend docs)
- Bump pyatv to 0.15.1 (apple_tv docs)

## 2024.9.0b5

- Update gardena_bluetooth dependency to 1.4.3
- Bump yalexs to 8.6.3
- Bump python-holidays to 0.56
- Update knx-frontend to 2024.9.4.64538
- Update frontend to 20240904.0
- Bump deebot-client to 8.4.0

## 2024.9.0b4

- Fix updating insteon modem configuration while disconnected
- Add Linkplay mTLS/HTTPS and improve logging
- Update nest to only include the image attachment payload for cameras that support fetching media
- Fix blocking calls for OpenAI conversation
- Bump py-madvr2 to 1.6.32
- Fix area registry indexing when there is a name collision
- Bump aiolifx to 1.0.9 and remove unused HomeKit model prefixes
- Bump yalexs to 8.6.0
- Bump PySwitchbot to 0.48.2
- Fix unhandled exception with missing IQVIA data
- Fix Onkyo action select_hdmi_output
- Fix energy sensor for ThirdReality Matter powerplug
- Bump aiomealie to 0.9.2
- Update frontend to 20240903.1
- Bump yalexs to 8.6.2

## 2024.9.0b3

- Bump Intellifire to 4.1.9
- Fix Tado fan speed for AC
- Bump renault-api to v0.2.7
- Bump aioshelly to 11.4.1 to accomodate shelly GetStatus calls that take a few seconds to respond
- Bump python-kasa to 0.7.2
- Bump yarl to 1.9.6
- Bump aiopulse to 0.4.6
- Fix ollama blocking on load_default_certs
- Fix telegram_bot blocking on load_default_certs
- Fix BMW client blocking on load_default_certs
- Bump aiomealie to 0.9.1
- Bump python-telegram-bot to 21.5
- Add ConductivityConverter in websocket_api.py
- Add diagnostics platform to modern forms
- Bump yarl to 1.9.7
- Bump aioshelly to 11.4.2
- Bump habluetooth to 3.4.0
- Fix motionblinds_ble tests
- Bump androidtvremote2 to 0.1.2 to fix blocking event loop when loading ssl certificate chain
- Bump fyta_cli to 0.6.6
- Update frontend to 20240902.0

## 2024.9.0b2

- Bump aioruckus to v0.41 removing blocking call to load_default_certs from ruckus_unleashed integration
- Bump weatherflow4py to 0.2.23
- Bump ZHA to 0.0.32
- Bump PyTurboJPEG to 1.7.5
- Bump nice-go to 0.3.8
- Bump intents to 2024.8.29
- Fix ZHA group removal entity registry cleanup
- Bump aioesphomeapi to 25.3.1
- Bump yalexs to 8.5.5
- Add a repair issue for Yale Home users using the August integration
- Bump lmcloud to 1.2.1
- Bump lmcloud 1.2.2
- Bump aiomealie to 0.9.0

## 2024.9.0b1

- Bump pyatmo to 8.1.0
- Bump pydaikin to 2.13.5
- Fix sonos get_queue service call to restrict to sonos media_player entities
- Add missing dependencies to yale
- Update utility_account_id in Opower to be lowercase in statistic id
- Fix Mastodon migrate config entry log warning
- Bump pydaikin to 2.13.6
- Add missing translation key in Knocki
- Update frontend to 20240829.0

## 2024.8.3

- Bump yalexs to 6.5.0 (august docs)
- Bump yalexs to 8.0.2 (august docs)
- Bump aioshelly to 11.2.4 (shelly docs)
- Add Alt Core300s model to vesync integration (vesync docs)
- Bump pybravia to 0.3.4 (braviatv docs)
- Bump aiohomekit to 3.2.3 (homekit_controller docs)
- Bump nest to 4.0.7 to increase subscriber deadline (nest docs)
- Bump tplink-omada-api to 1.4.2 (tplink_omada docs)
- Bump aiohttp to 3.10.4
- Update Matter light transition blocklist to include GE Cync Undercabinet Lights (matter docs)
- Fix shelly available check when device is not initialized (shelly docs)
- Bump pyhomeworks to 1.1.2 (homeworks docs)
- Bump aiohttp to 3.10.5
- Update xknx to 3.1.1 (knx docs)
- Bump python-roborock to 2.6.0 (roborock docs)
- Bump yalexs to 8.1.2 (august docs)
- Bump python-holidays to 0.54 (workday docs) (holiday docs)
- Bump python-holidays to 0.55 (workday docs) (holiday docs)
- Add missing strings for riemann options flow (integration docs)
- Fix Spotify Media Browsing fails for new config entries (spotify docs)
- update ttn_client - fix crash with SenseCAP devices (thethingsnetwork docs)
- Add supported features for iZone (izone docs)
- Bump yalexs to 8.1.4 (august docs)
- Bump aiohue to version 4.7.3 (hue docs)
- Bump yalexs to 8.3.3 (august docs)
- Bump yalexs to 8.4.0 (august docs)
- Bump yalexs to 8.4.1 (august docs)
- Fix missing id in Habitica completed todos API response (habitica docs)

## 2024.8.2

- Fix Madvr sensor values on startup ([madvr docs])
- Bump aiohttp to 3.10.3 (dependency)
- Update knx-frontend to 2024.8.9.225351 (knx docs) (dependency)
- Fix secondary russound controller discovery failure ([russound_rio docs])
- Bump aioshelly to version 11.2.0 ([shelly docs]) (dependency)
- Bump pydaikin to 2.13.4 (daikin docs) (dependency)
- Bump aiohomekit to 3.2.2 (homekit_controller docs) (dependency)
- Fix startup block from Swiss public transport ([swiss_public_transport docs])
- Bump pyschlage to 2024.8.0 ([schlage docs]) (dependency)
- Update AEMET-OpenData to v0.5.4 (aemet docs) (dependency)
- Update aioairzone-cloud to v0.6.2 (airzone_cloud docs) (dependency)
- Update aioqsw to v0.4.1 ([qnap_qsw docs]) (dependency)
- Bump ZHA lib to 0.0.31 ([zha docs]) (dependency)
- Update wled to 0.20.2 ([wled docs]) (dependency)
- Fix error message in html5 (html5 docs)
- Bump py-nextbusnext to 2.0.4 ([nextbus docs]) (dependency)
- Bump python-nest-sdm to 4.0.6 ([nest docs]) (dependency)
- Update xknx to 3.1.0 and fix climate read only mode (knx docs) (dependency)
- Fix KNX UI Light color temperature DPT (knx docs)
- Fix status update loop in bluesound integration (bluesound docs)
- Bump py-synologydsm-api to 2.4.5 ([synology_dsm docs]) (dependency)
- Fix blocking I/O of SSLContext.load_default_certs in Ecovacs (ecovacs docs)
- Fix translation for integration not found repair issue (homeassistant docs)
- Bump pylutron_caseta to 0.21.1 (lutron_caseta docs) (dependency)
- Fix PI-Hole update entity when no update available ([pi_hole docs])
- Bump LaCrosse View to 1.0.2, fixes blocking call (lacrosse_view docs) (dependency)
- Bump pypck to 0.7.20 (lcn docs) (dependency)
- Bump pyhomeworks to 1.1.1 (homeworks docs)
- Bump openwebifpy to 4.2.7 (enigma2 docs) (dependency)
- Bump aiounifi to v80 ([unifi docs]) (dependency)
- Fix rear trunk logic in Tessie ([tessie docs])
- Bump bluetooth-adapters to 0.19.4 (bluetooth docs) (dependency)
- Fix loading KNX integration actions when not using YAML (knx docs)
- Bump aiomealie to 0.8.1 ([mealie docs]) (dependency)

## 2024.8.1

- Add support for v3 Coinbase API (coinbase docs) (dependency)
- Bump OpenWeatherMap to 0.1.1 (openweathermap docs) (dependency)
- Fix limit and order property for transmission integration (transmission docs)
- Fix doorbird with externally added events (doorbird docs)
- Bump aiorussound to 2.2.2 (russound_rio docs) (dependency)
- Bump aiohttp to 3.10.2 (dependency)
- Add missing logger to Tessie (tessie docs)
- Bump YoLink API to 0.4.7 (yolink docs) (dependency)
- Bump ZHA library to 0.0.29 (zha docs)
- Bump pyjvcprojector to 1.0.12 to fix blocking call (jvc_projector docs) (dependency)
- Bump monzopy to 1.3.2 (monzo docs)
- Fix startup blocked by bluesound integration (bluesound docs)
- Update frontend to 20240809.0 (frontend docs) (dependency)
- Bump zha lib to 0.0.30 (zha docs) (dependency)
- Fix cleanup of old orphan device entries in AVM Fritz!Tools (fritz docs)
- Bump pydaikin to 2.13.2 (daikin docs) (dependency)
- Bump AirGradient to 0.8.0 (airgradient docs) (dependency)

## 2024.8.0b9

- Bump intents to 2024.8.7

## 2024.8.0b8

- Add missing application credential to Tesla Fleet
- Update wled to 0.20.1

## 2024.8.0b7

- Fix typo on one of islamic_prayer_times calculation_method option

## 2024.8.0b6

- Bump ZHA to 0.0.28
- Update knx-frontend to 2024.8.6.211307
- Bump reolink-aio to 0.9.7
- Update ESPHome voice assistant pipeline log warning
- Fix Google Cloud TTS not respecting config values

## 2024.8.0b5

- Fix Tami4 device name is None
- Fix sense doing blocking I/O in the event loop
- Bump deebot-client to 8.3.0
- Bump mficlient to 0.5.0
- Update frontend to 20240806.1

## 2024.8.0b4

- Fix yamaha legacy receivers
- Add support for ESPHome update entities to be checked on demand
- Fix growatt server tlx battery api key
- Update greeclimate to 2.1.0
- Update knx-frontend to 2024.8.6.85349
- Bump yt-dlp to 2023.08.06
- Update frontend to 20240806.0

## 2024.8.0b3

- Add Matter Leedarson RGBTW Bulb to the transition blocklist
- Fix MPD issue creation
- Fix state icon for closed valve entities
- Update frontend to 20240805.1

## 2024.8.0b2

- Update greeclimate to 2.0.0
- Add CONTROL supported feature to Google conversation when API access
- Fix wrong DeviceInfo in bluesound integration
- Bump pyenphase to 1.22.0
- Bump ZHA lib to 0.0.27
- Bump aiohttp to 3.10.1
- Fix class attribute condition in Tesla Fleet
- Add Govee H612B to the Matter transition blocklist

## 2024.8.0b1

- Fix translation key for power exchange sensor in ViCare
- Add aliases to script llm tool description
- Update doorbird error notification to be a repair flow
- Fix yolink protocol changed
- Fix handling of directory type playlists in Plex
- Bump aioymaps to 1.2.5
- Bump yolink api to 0.4.6
- Fix and improve tedee lock states
- Fix doorbird models are missing the schedule API
- Add LinkPlay models
- Add device class
- Add additional items to REPEAT_MAP in LinkPlay
- Update frontend to 20240802.0
