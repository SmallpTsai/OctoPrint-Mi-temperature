# coding=utf-8
from __future__ import absolute_import

import time
import struct
import octoprint.plugin

from octoprint.events import Events
from octoprint.util import RepeatedTimer

import bluetooth._bluetooth as bluez
from .bluetooth_utils import (toggle_device,
                            enable_le_scan, parse_le_advertising_events,
                            disable_le_scan, raw_packet_to_str)


scan_timeout = 30

dev_id = 0  # hci0

class Mi_temperaturePlugin(octoprint.plugin.StartupPlugin,
                           octoprint.plugin.ShutdownPlugin,
                           octoprint.plugin.SettingsPlugin,
                           octoprint.plugin.AssetPlugin,
                           octoprint.plugin.TemplatePlugin,
                           octoprint.plugin.EventHandlerPlugin):

    readings = {}

    def ble_scan_timer(self):
        try:
            sensors = self._settings.get(["sensors"])
            mac_set = set((s["mac"] for s in sensors))
            result = {}

            t_start = time.time()

            def packet_handler(mac, adv_type, data, rssi):
                if time.time() - t_start > scan_timeout:
                    return True # timeout, stop scan

                if mac not in mac_set:
                    return

                data_str = raw_packet_to_str(data)
                atcIdentifier = data_str[6:10].upper()
                if atcIdentifier != "1A18":
                    return

                temp = struct.unpack("H", data[11:13])[0] / 100
                humid = struct.unpack("H", data[13:15])[0] / 100
                battery = struct.unpack("B", data[17:18])[0]

                result[mac] = (temp, humid, battery)

                self._logger.info("[{}] T: {:.2f}, H: {:.2f}, B: {}".format(mac, temp, humid, battery))

                if len(mac_set) == len(result.keys()):
                    return True # found all entries, stop scan

            toggle_device(dev_id, True, logger=self._logger)
            sock = bluez.hci_open_dev(dev_id)
            enable_le_scan(sock, filter_duplicates=False, logger=self._logger)
            parse_le_advertising_events(sock,
                                        handler=packet_handler,
                                        debug=False, 
                                        logger=self._logger)
            disable_le_scan(sock, logger=self._logger)

            if result:
                for mac in result:
                    self.readings[mac] = result[mac]
                self._plugin_manager.send_plugin_message(self._identifier, dict(readings=self.readings))
        except Exception as ex:
            self._logger.error(ex)

    def update_ui(self):
        sensors = self._settings.get(["sensors"])
        for sensor in sensors:
            mac = sensor["mac"]
            if mac in self.readings:
                sensor["readings"] = self.readings[mac]
        self._plugin_manager.send_plugin_message(self._identifier, dict(sensors=sensors))

    # ~~ StartupPlugin mixin

    def on_after_startup(self):
        # emulated check
        self.ble_timer = RepeatedTimer(60, self.ble_scan_timer, None, None, True)
        self.ble_timer.start()
        self._logger.info("MI temp: start timer")

    # ~~ ShutdownPlugin mixin

    def on_shutdown(self):
        self.ble_timer.cancel()
        self._logger.info("MI temp: stop timer")

    ##~~ SettingsPlugin mixin

    def get_settings_defaults(self):
        return dict(
            # put your plugin's default settings here
            sensors=[]
        )

    ##~~ AssetPlugin mixin

    def get_assets(self):
        # Define your plugin's asset files to automatically include in the
        # core UI here.
        return dict(
            js=["js/mi_temperature.js"],
            css=["css/mi_temperature.css"],
            less=["less/mi_temperature.less"]
        )

    ##~~ TemplatePlugin mixin

    def get_template_vars(self):
        return dict(sensors=self._settings.get(["sensors"]))

    def get_template_configs(self):
        return [
            dict(type="navbar", custom_bindings=True, classes=["dropdown"]),
            dict(type="settings", custom_bindings=False)
        ]
        
    ##~~ EventHandlerPlugin mixin

    def on_event(self, event, payload):
        if event == Events.CONNECTED:
            self.update_ui()

        if event == Events.CLIENT_OPENED:
            self.update_ui()


    ##~~ Softwareupdate hook

    def get_update_information(self):
        # Define the configuration for your plugin to use with the Software Update
        # Plugin here. See https://docs.octoprint.org/en/master/bundledplugins/softwareupdate.html
        # for details.
        return dict(
            mi_temperature=dict(
                displayName="Mi_temperature Plugin",
                displayVersion=self._plugin_version,

                # version check: github repository
                type="github_release",
                user="smallptsai",
                repo="OctoPrint-Mi-temperature",
                current=self._plugin_version,

                # update method: pip
                pip="https://github.com/smallptsai/OctoPrint-Mi-temperature/archive/{target_version}.zip"
            )
        )


# If you want your plugin to be registered within OctoPrint under a different name than what you defined in setup.py
# ("OctoPrint-PluginSkeleton"), you may define that here. Same goes for the other metadata derived from setup.py that
# can be overwritten via __plugin_xyz__ control properties. See the documentation for that.
__plugin_name__ = "Mi_temperature Plugin"

# Starting with OctoPrint 1.4.0 OctoPrint will also support to run under Python 3 in addition to the deprecated
# Python 2. New plugins should make sure to run under both versions for now. Uncomment one of the following
# compatibility flags according to what Python versions your plugin supports!
#__plugin_pythoncompat__ = ">=2.7,<3" # only python 2
__plugin_pythoncompat__ = ">=3,<4" # only python 3
#__plugin_pythoncompat__ = ">=2.7,<4" # python 2 and 3

def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = Mi_temperaturePlugin()

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
    }

