# Dynamic mqtt Irrigation for Homeassistant


You can use a lot of cool features for your Irrigation using just Homeassistant GUI.
This component contains the server componenet and the client component.
https://github.com/au190/au190_mqtt_irrigation


**Example**
Lovelace UI:<br />
<img src='https://raw.githubusercontent.com/au190/au190_mqtt_irrigation/master/1.jpg'/>
[![Watch the video](https://img.youtube.com/vi/-5QZi2_nNfk/0.jpg)](https://www.youtube.com/watch?v=-5QZi2_nNfk "Watch the video")


### Irrigation system
```
Number of maximum Zones is 6.
Switching ON|OFF all the system. By swiching ON resetting all the logic do default.
You can set Zone Duration. Number of Zones can be set in yaml. (Number of maximum Zones is 6.)
Duration: Can be set from (12 sec - 18 hours).
Each Zone can be enable or disabled. 
If the Zone is disabled the Scheduler will skip that Zone on the aoutmatic irrigation. 
If the Zone is enabled automatic irrigation will run on that Zone for that specific duration. 
For the manual irrigation same duration is applied.
```


### Scheduler
```
Switching ON|OFF you can Enable|Disable automatic irrigation.
You can Enable|Disable weekdays for irrigation.
You can setup the time for automatic irrigation.
At that specific time will run the automatic irrigation, for a duration spcified in the Irrigation system.
```


### Md settings (Cat alarm)
```
Number of maximum motion detection is 3.
Switching ON|OFF you can Enable|Disable Md settings.
If you attach IR sensor or Md sensor you can trigger irrigation on a specific Zone.
Md on time - irrigation will turn ON for this specific time. Duration: Can be set from (10 sec - 10 min).
If there is no set Start time|End time allways will be active.
You can specify Start time|End time when will be active.
If the Zone is triggerd 10 times in 5 minutes, it will be suspended until manual intervention(Switching ON|OFF all the system).
```

### Protection

```
Switching ON|OFF you can Enable|Disable all the Protections or you can Enable|Disable one by one.
MotorRunTout  - If the motor is running more then scecified, Irrigation system will be suspended until manual intervention(Switching ON|OFF all the system). Can be set from (60 sec - 18 hours).
WaterLimTout  - If the water in the well ran out of water, Irrigation system will be suspended for the specified time, after that automaticaly return to normal wrok. Can be set from (60 sec - 18 hours).
RainLimTout   - If rainy day, irrigation will be suspended for the specific time. (under consturvtion)
```



#### Info
```
- [ ] ⚠️ Working only with MQTT
- [ ] ⚠️ Working only with Tasmota(https://github.com/arendst/Tasmota) software. 
Tested:
Tasmota v7.1.2
Os: Ubuntu 19.10

Homeassistant: 0.105.1
System Health
arch	x86_64
dev	false
docker	false
hassio	false
os_name	Linux
python_version	3.7.5
timezone	Europe/Budapest
version	0.105.1
virtualenv	true
Lovelace
mode	storage
resources	7
views	5
```


#### Installation
1.  Copy the au190_mqtt_irrigation dir into $homeassistant_config_dir/custom_components/ <br/>
2.  To update the frontend use: https://github.com/au190/au190_homeassistant_frontend <br/>
3.  Copy the au190-irrig_card dir into $homeassistant_config_dir/www/community/ <br/>


#### 1. Server side configuration:

Tasmota config:
Backlog Module 18; SSID1 Wifi_name; Password1 Wifi_pw; MqttHost 192.168.1.11; MqttUser user; MqttPassword mqtt_pw; FriendlyName1 Irrigation; MqttClient Irrigation; Topic irrig; Setoption13 1; SerialLog 0; PowerOnState 0; GPIO4 22; GPIO5 21; GPIO12 24; GPIO13 35; GPIO14 25; GPIO15 23; GPIO16 26;


**Options**

| Name | Type | Default | Example | Description
| ---- | ---- | ------- | ----------- | -----------
| platform | string | **Required** | `au190_mqtt_irrigation` |  
| name | string | optional |  |  
| icon | string | optional | mdi:power |  
| topic | string | **Required** | "irrig" |   Just use the mqtt topic here
| zones_ids | string | **Required** | [1,2,3,4,5,6] |  These are the indexes of the mqtt messages, max number is 6. (mqtt cmnd ids)
| md_ids | string | **Required** | [1,2,3] |  The index number from the zones_ids, rerender md inputs to zone (this array allways must have 3 element, I have 3 md input)
| md1 | string | **Required** | "tele/irrig/RESULT" |  
| md1_value_template | string | **Required** | "{{ value_json.md1 }}" |  I have special circuit serial - arduino.
| waterLim | string | **Required** | "tele/irrig/RESULT" |  
| rainLim_value_template | string | **Required** | "{{ value_json.waterLim }}" |   I have special circuit serial - arduino.
| rainLim | string | optional | "tele/irrig/RESULT" |  
| rainLim_value_template | string | optional | "{{ value_json.rainLim }}" |   I have special circuit serial - arduino.
| motor | string | optional | "tele/irrig/RESULT" |   I have special circuit serial - arduino.
| motor_value_template | string | optional | "{{ value_json.M }}"" |  I have special circuit serial - arduino.
| power_value_template | string | optional | "{{ value_json.P }}" |  I have special circuit serial - arduino.
| powdaily_value_template | string | optional | "{{ value_json.PD }}" |  I have special circuit serial - arduino.
| powmontly_value_template | string | optional | "{{ value_json.PM }}" |  I have special circuit serial - arduino.

configuration.yaml

```
switch:

#****************************  
# 
#****************************

  - platform: au190_mqtt_irrigation
    name: "Irrigation"
    icon: mdi:power
    topic: "irrig"
    zones_ids: [1,2,3]
    md_ids: [1,2,3]
    
    md1: "tele/irrig/RESULT"
    md1_value_template: "{{ value_json.md1 }}"
    md2: "tele/irrig/RESULT"
    md2_value_template: "{{ value_json.md2 }}"
    md3: "tele/irrig/RESULT"
    md3_value_template: "{{ value_json.md3 }}"
    waterLim: "tele/irrig/RESULT"
    waterLim_value_template: "{{ value_json.waterLim }}"
    rainLim: "tele/irrig/RESULT"
    rainLim_value_template: "{{ value_json.rainLim }}"
    motor: "tele/irrig/RESULT"
    motor_value_template: "{{ value_json.M }}"
    power_value_template: "{{ value_json.P }}"
    powdaily_value_template: "{{ value_json.PD }}"
    powmontly_value_template: "{{ value_json.PM }}"
    
    availability_topic: "tele/irrig/LWT"
    payload_available: "Online"
    payload_not_available: "Offline"
    qos: 1


```


#### Client side configuration:
For the popup menu I had to create new fronted. You have to replace the with this: https://github.com/au190/au190_homeassistant_frontend


Lovelace UI configuration

```
resources:

  - type: module
    url: /local/community/au190-irrig_card/au190-irrig_card.js

    
  entity: switch.irrigation
  type: 'custom:au190-irrig_card'

```


