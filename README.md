# Dynamic mqtt Irrigation for Homeassistant


You can use a lot of cool features for your Irrigation using just Homeassistant GUI.
This component contains the server componenet and the client component.
You can use different sensors and switches, power meter, motion detection sensors, infra senzors, based on MQTT protocol. These sensors can be conbined together in a singel logic working as a Smart MQTT Irrigation System.
Working with Tasmota software on the devices.
https://github.com/au190/au190_mqtt_irrigation


**Example**
Lovelace UI:<br />
<img src='https://raw.githubusercontent.com/au190/au190_mqtt_irrigation/master/1.jpg'/>
[![Watch the video](https://img.youtube.com/vi/-5QZi2_nNfk/0.jpg)](https://www.youtube.com/watch?v=-5QZi2_nNfk "Watch the video")


### Irrigation system
```
Number of maximum Zones not limited. Number of Zones can be set in yaml.
Switching ON|OFF the system. By swiching ON resetting all the logic do default.
You can set Zone Duration. 
Duration: Can be set from (10 sec - 18 hours).
Each Zone can be enable or disabled. 
If the Zone is disabled the Scheduler will skip that Zone on the autmatic irrigation. 
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
Number of maximum motion detection is 6.
Switching ON|OFF you can Enable|Disable Md settings.
If you attach IR sensor or Md sensor you can trigger irrigation on a specific Zone.
Md on time - irrigation will turn ON for this specific time. Duration: Can be set from (10 sec - 10 min).
You can specify Start time|End time when will be active.If is not set the Start time|End time allways will be active.
If the Zone is triggerd 10 times in 5 minutes, it will be suspended until manual intervention(Manual Switching ON|OFF all the system).
```

### Protection

```
Switching ON|OFF you can Enable|Disable all the Protections or you can Enable|Disable one by one.
MotorRunTout  - This information is getting form the motor power consuption. If the motor is running more then scecified, Irrigation system will be suspended until manual intervention(Switching ON|OFF the system). Can be set from (60 sec - 18 hours).
WaterLimTout  - If the water in the well ran out of water, Irrigation system will be suspended for the specified time, after that automaticaly return to normal wrok. Can be set from (60 sec - 18 hours).
RainLimTout   - If rainy day, automatic irrigation will be suspended for the specific time. This info can be get from weather station (OpenWeatherMap).
```



#### Info
```
- [ ] ⚠️ Working only with MQTT
- [ ] ⚠️ Working only with Tasmota(https://github.com/arendst/Tasmota) software.

Tested:
Home Assistant version: 0.105.1
Tasmota v7.1.2
Python_version	3.7.5

```


#### Installation
1.  Copy the au190_mqtt_irrigation dir into $homeassistant_config_dir/custom_components/ <br/>
2.  To update the frontend use: https://github.com/au190/au190_homeassistant_frontend <br/> (Needs for popup menu)
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
| z_cmnd | string | **Required** | [cmnd/irrig/POWER1] |  These are the command message for each zone.
| z_stat | string | **Required** | [stat/irrig/POWER1] |  These are the status message for each zone.
| md_stat | string | **Required** | "stat/irrig_test/md_1" |  
| md_template | string | **Required** | "{{ value_json.md1 }}" |  If I have special json or "".
| md_assign | string | **Required** | [1,2,3] |  The number in this array, maps Md number to Zone index. Rerender md inputs to zone (values in *md_assign* assignments have to be equal elements as in *md_stat*). The first number represents the Md1 activates that number of Zone.
| m_cmnd | string | optional | "cmnd/irrig_test/POWER7" |   Motor command message.
| m_stat | string | optional | "stat/irrig_test/POWER7" |   Motor status message.
| m_template | string | optional | "{{ value_json.M }}"" |  If I have special json or "".
| waterLim_stat | string | **Required** | "stat/irrig_test/POWER8" | 
| waterLim_template | string | optional | "{{ value_json.rainLim }}" |   I have special circuit serial - arduino.
| rainLim_stat | string | optional | "stat/irrig_test/precip" |  
| rainLim_template | string | **Required** | "{{ value_json.waterLim }}" |   I have special circuit serial - arduino.
| power_value_template | string | optional | "{{ value_json.P }}" |  I have special circuit serial - arduino.
| powdaily_value_template | string | optional | "{{ value_json.PD }}" |  I have special circuit serial - arduino.
| powmontly_value_template | string | optional | "{{ value_json.PM }}" |  I have special circuit serial - arduino.

configuration.yaml

```
switch:


#****************************
#    
#   Do not use the same topic in the configuration !!!
#
#   md_assign   - the index number from the z_cmnd, rerender md inputs to zone
#****************************    
  - platform: au190_mqtt_irrigation
    name: "Irrigation"
    icon: mdi:power
    z_cmnd: [
    "cmnd/basic/POWER",
    "cmnd/irrig_test/POWER1",
    "cmnd/irrig_test/POWER2",
    "cmnd/irrig_test/POWER3",
    ]
    z_stat: [
    "stat/basic/POWER",
    "stat/irrig_test/POWER1",
    "stat/irrig_test/POWER2",
    "stat/irrig_test/POWER3",
    ]

    md_stat: [
    "stat/irrig_test/md_1",
    "stat/irrig_test/md_2",
    "stat/irrig_test/md_3",
    "stat/irrig_test/md_4",
    "stat/irrig_test/md_5",
    "stat/irrig_test/md_6"
    ]
    md_template: [
    "",
    "{{ value_json.md2 }}",
    "{{ value_json.md3 }}",
    "",
    "",
    "",
    ]
    md_assign: [0,2,1,3,3,3]
    
    m_cmnd: "cmnd/blitzwolf/POWER"
    m_stat: "stat/blitzwolf/POWER"
    #m_template: "{{ value_json.M }}"
    
    m_power_stat: "tele/blitzwolf/SENSOR"
    m_power_template: "{{ value_json.ENERGY.Power }}"
    m_powerdaily_template: "{{ value_json.ENERGY.Today }}"
    m_powermonthly_template: "{{ value_json.ENERGY.Total }}"
    
    rainLim_stat: "tele/irrig_test/precip"
    rainLim_template: "{{ value_json.rainLim }}"
    
    waterLim_stat: "stat/irrig_test/POWER8"
    waterLim_template: "{{ value_json.waterLim }}"
    
    availability_topic: "tele/irrig_test/LWT"
    payload_available: "Online"
    payload_not_available: "Offline"
    qos: 1
    



```


#### 2. Client side configuration:
For the popup menu I had to create new fronted. You have to replace the with this: https://github.com/au190/au190_homeassistant_frontend

#### 3. Client side configuration:
Lovelace UI configuration

```
resources:

  - type: module
    url: /local/community/au190-irrig_card/au190-irrig_card.js

    
  entity: switch.irrigation
  type: 'custom:au190-irrig_card'

```


