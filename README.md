# Dynamic mqtt Irrigation for Homeassistant


You can use a lot of cool features for your Irrigation using just Homeassistant GUI.
This component contains the server componenet and the client component.
You can use different sensors and switches, power meter, motion detection sensors, infra senzors, based on MQTT protocol. These sensors can be conbined together in a singel logic working as a Smart MQTT Irrigation System.
Working with Tasmota software on the devices.
https://github.com/au190/au190_mqtt_irrigation
<br>Forum for questions, issues: https://community.home-assistant.io/t/dynamic-mqtt-irrigation-for-homeassistant/310401


**Example**
Lovelace UI:<br />
<img src='https://raw.githubusercontent.com/au190/au190_mqtt_irrigation/master/1.jpg'/>
[![Watch the video](https://img.youtube.com/vi/-5QZi2_nNfk/0.jpg)](https://www.youtube.com/watch?v=-5QZi2_nNfk "Watch the video")


### Irrigation system
Number of maximum Zones not limited. Number of Zones can be set in yaml.
Switching ON|OFF the system. By swiching ON resetting all the logic do default.
You can set Zone Duration. 
Duration: Can be set from (10 sec - 18 hours).
Each Zone can be enable or disabled. 
If the Zone is disabled the Scheduler will skip that Zone on the autmatic irrigation. 
If the Zone is enabled automatic irrigation will run on that Zone for that specific duration. 
For the manual irrigation same duration is applied.



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
- [ ] ⚠️ The output will be ON only the time what is in configuraiton, even if the Ha is crashing druring the output is ON, or even if the Wifi router is crashing druring the output is ON.
- [ ] ⚠️ Working only with MQTT
- [ ] ⚠️ Working only with Tasmota(https://github.com/arendst/Tasmota) software.

```
Tested:
Home Assistant version: 2021.9.7
Python_version	3.9.7
Tasmota v7.1.2

```


#### Installation
1.  Copy the au190_mqtt_irrigation dir into $homeassistant_config_dir/custom_components/ <br/>
2.  Copy the au190-irrig_card dir into $homeassistant_config_dir/www/community/ <br/>


#### 1. Server side configuration:

Tasmota config:
```
Backlog Module 18; SSID1 Wifi_name; Password1 Wifi_pw; MqttHost 192.168.1.11; MqttUser user; MqttPassword mqtt_pw; DeviceName Irrigation; MqttClient Irrigation; Topic irrig; SetOption65 1; Setoption13 1; SerialLog 0; PowerOnState 0; GPIO4 22; GPIO5 21; GPIO12 24; GPIO13 35; GPIO14 25; GPIO15 23; GPIO16 26;
```

**Options**

| Name | Type | Default | Accepted input values | Description
| ---- | ---- | ------- | ----------- | -----------
| platform | string | **Required** | `au190_mqtt_irrigation` |  
| name | string | optional |  |  
| icon | string | optional |  |  
| z_cmnd | string | **Required** |  |  These are the commands for zones.
| z_stat | string | **Required** | ON or OFF |  These are the status message for zones.
| md_stat | string | optional | ON or OFF |  These are the status message for md.
| md_template | string | optional |  |  If I have special json or "".
| md_assign | string | optional |  |  The number in this array, maps Md number to Zone index. Rerender md inputs to zone (values in *md_assign* assignments have to be equal elements as in *md_stat*). The first number represents the Md1 activates that number of Zone.
| m_cmnd | string | optional |  |   Enable or disable power for the Motor.
| m_stat | string | optional | ON or OFF |   Status message if the power is enabled or disabled for the Motor.
| m_template | string | optional |  |  If I have special json or "".
| m_power_stat | string | optional | int or float |  Power of the motor - form this info I know if the motor is running or not. If the power is above 100 W it considering running.
| m_power_template | string | optional |  |  If I have special json or ""
| m_powerdaily_template | string | optional |  |  If I have special json or ""
| m_powermonthly_template | string | optional |  |  If I have special json or ""
| waterLim_stat | string | optional | ON or OFF | 
| waterLim_template | string | optional |  |   If I have special json or "".
| rainLim_stat | string | optional | ON or OFF |  
| rainLim_template | string | optional |  |   If I have special json or ""


**configuration.yaml**

In the yaml there are some dependent configuration if you are using *md_stat* in config you must define the *md_template* and *md_template*.

The stat configuratons is allways the input for Irrigation System logic. These values specified above. After the config allways check the logs, if some issue with the config you will find more info there.

All the config is saved in the $homeassistant_config_dir/au190/ directory.
If you change the yaml configuration of this entity, delete the $homeassistant_config_dir/au190/switch.irrigation_data.json and restart the HA.




**1 Basic config**

If you have more zones, you can add more Sonoff 4CH or any other MQTT devices.

1.  WEMOS-D1-MINI with Tasmota software

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
    "cmnd/irrig/PWMIR1",
    "cmnd/irrig/PWMIR2",
    "cmnd/irrig/PWMIR3",
    "cmnd/irrig/PWMIR4"
    ]
    z_stat: [
    "stat/irrig/POWER1",
    "stat/irrig/POWER2",
    "stat/irrig/POWER3",
    "stat/irrig/POWER4",
    ]

    qos: 1


```


**2 Full config**


In this example Iam using 

1.  WEMOS-D1-MINI with Tasmota software
2.  Sonoff basic with Tasmota software
3.  Ir for Motion Detection with Tasmota software 
4.  Enable disable the power for the Motor and also measuring current consumption with blitzwolf device and Tasmota software.
(I have also dedicated hardware for all of this)



md_assign - The number in this array, maps Md number to Zone index. Rerender md inputs to zone (values in *md_assign* assignments have to be equal elements as in *md_stat*). The first number represents the Md1 activates that number of Zone.

It depends on z_cmnd and md_stat.
In the below example:
The values in the md_assign can not be bigger then the (number of elements - 1) in z_cmnd. In this case 3 becasue we have 4 elements in z_cmnd.
The number of elemnts in md_assign must be equal to number of elemnts in md_stat.
If the value is good you have to use empty string in template.

You can assign multiple Md to the same zone.

You can use the below config in Tasmota:
```
Backlog Module 18; SSID1 Wifi_name; Password1 Wifi_pw; MqttHost 192.168.1.11; MqttUser user; MqttPassword mqtt_pw; DeviceName Irrigation; MqttClient Irrigation; Topic irrig; SetOption65 1; Setoption13 1; SerialLog 0; PowerOnState 0; GPIO4 22; GPIO5 21; GPIO12 24; GPIO13 35; GPIO14 25; GPIO15 23; GPIO16 26;
```

For Motion detection - you can use input switch and you can use example rules.
```
Rule1 
ON switch1#state=1 DO publish stat/irrig/md_1 OFF ENDON 
ON switch1#state=0 DO publish stat/irrig/md_1 ON ENDON
Rule1 1
```


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
    "cmnd/basic/PWMIR",
    "cmnd/irrig/PWMIR1",
    "cmnd/irrig/PWMIR2",
    "cmnd/irrig/PWMIR3",
    ]
    z_stat: [
    "stat/basic/POWER",
    "stat/irrig/POWER1",
    "stat/irrig/POWER2",
    "stat/irrig/POWER3",
    ]

    md_stat: [
    "stat/irrig/md_1",
    "stat/irrig/md_2",
    "stat/irrig/md_3",
    "stat/irrig/md_4",
    "stat/irrig/md_5",
    "stat/irrig/md_6"
    ]
    md_template: [
    "",
    "",
    "",
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
    
    waterLim_stat: "stat/irrig/waterL"
    #waterLim_template: "{{ value_json.waterLim }}"
    
    rainLim_stat: "tele/irrig/precip"
    #rainLim_template: "{{ value_json.rainLim }}"

    qos: 1


```


#### 2. Client side configuration:

Lovelace UI configuration


Adding the resource to Client:

```
resources:

  - type: module
    url: /local/community/au190-irrig_card/au190-irrig_card.js
```


Card configuration:

```    
  entity: switch.irrigation
  type: 'custom:au190-irrig_card'

```


