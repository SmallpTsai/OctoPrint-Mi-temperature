/*
 * View model for OctoPrint-Mi-temperature
 *
 * Author: Smallp Tsai
 * License: AGPLv3
 */
$(function() {
    function Mi_temperatureViewModel(parameters) {
        var self = this;

        // assign the injected parameters, e.g.:
        self.settingsViewModel = parameters[0];

        self.sensors = ko.observableArray();

        self.onDataUpdaterPluginMessage = (plugin, data) => {
            if (typeof plugin === 'undefined')
                return;
        
            if (plugin !== "mi_temperature")
                return;

            if (data.hasOwnProperty("readings")) {
                self.sensors().forEach(sensor => {
                    const r = data.readings[sensor.mac()];
                    if(r) {
                        sensor.temp(r[0])
                        sensor.humid(r[1])
                        sensor.bat(r[2])
                    }
                })
            }

            if (data.hasOwnProperty("sensors")) {
                self.sensors.removeAll()
                data.sensors.forEach(sensor => {
                    self.sensors.push({
                        name: ko.observable(sensor["name"]),
                        mac: ko.observable(sensor["mac"]),
                        temp: ko.observable(sensor["readings"] && sensor["readings"][0]), 
                        humid: ko.observable(sensor["readings"] && sensor["readings"][1]), 
                        bat: ko.observable(sensor["readings"] && sensor["readings"][2]), 
                    })
                })
            }
        }
    }

    /* view model class, parameters for constructor, container to bind to
     * Please see http://docs.octoprint.org/en/master/plugins/viewmodels.html#registering-custom-viewmodels for more details
     * and a full list of the available options.
     */
    OCTOPRINT_VIEWMODELS.push({
        construct: Mi_temperatureViewModel,
        // ViewModels your plugin depends on, e.g. loginStateViewModel, settingsViewModel, ...
        dependencies: [ "settingsViewModel", ],
        // Elements to bind to, e.g. #settings_plugin_mi_temperature, #tab_plugin_mi_temperature, ...
        elements: [ "#navbar_plugin_mi_temperature" ]
    });
});
