/*
- type: module
  url: /local/community/au190-irrig_card/au190-irrig_card.js


entity: switch.x_1
name: Test
icon: 'mdi:lightbulb'
type: 'custom:au190-irrig_card.js'


*/

import {cssData} from './styles.js?v=0.1.1';

class au190_IrrigCard extends HTMLElement {
  
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this.run = 0;
  }

  setConfig(config){
    
    if (!config.entity) {
      throw new Error('Please define an entity');
    }

    const root = this.shadowRoot;
    if (root.lastChild) root.removeChild(root.lastChild);

    const cardConfig = Object.assign({}, config);
    const card = document.createElement('ha-card');
    const content = document.createElement('div');
    const style = document.createElement('style');
    style.textContent = cssData();

    content.innerHTML = `
      <ha-card>
        <header>
          <paper-icon-button icon="mdi:dots-vertical" id="pr" class="c_icon clickable" role="button" tabindex="0" aria-disabled="false"></paper-icon-button>
          <div id="name" class="c_title">${this.name}</div>
        </header>
        <div id="btns" class="ctrl status">
        </div>
        <div class="sep"></div>
        <div class="status">
          <paper-icon-button id="i_0" class="OFF" icon=${"mdi:engine-outline"}></paper-icon-button>
					<paper-icon-button id="i_1" class="OFF" icon=${"mdi:water-pump-off"}></paper-icon-button>
          <paper-icon-button id="i_2" class="OFF" icon=${"mdi:weather-pouring"}></paper-icon-button>
					<paper-icon-button id="i_3" class="OFF" icon=${"mdi:motion-sensor"}></paper-icon-button>
          <paper-icon-button id="i_4" class="OFF" icon=${"mdi:timetable"}></paper-icon-button>
        </div>
        <div class="sep"></div>
        <div class="info">
          <div class="ibox">
            <p>Power</p>
            <p id="t_d" class="mtxt">0W</p>
          </div>
          <div class="ibox">
            <p>P daily</p>
            <p id="t_w" class="mtxt">0kWh</p>
          </div>
          <div class="ibox">
            <p>P monthly</p>
            <p id="t_m" class="mtxt">0kWh</p>
          </div>
        </div>
      </ha-card>
    `;
    card.appendChild(style);
    card.appendChild(content);
    root.appendChild(card)
    
    const pr = root.getElementById('pr')
    pr.addEventListener('click', () => this._openProp(cardConfig.entity));
    
    this._config = cardConfig;
  }
  
  set hass(hass) {

    const config = this._config;
    const root = this.shadowRoot;
    this.stateObj = hass.states[config.entity]
    
    if(this.stateObj === undefined || !this._isChanged()){
      return
    }
    
    this._hass = hass;
    //console.log(this.stateObj.attributes.au190);
    
    if(typeof config.name === 'string'){
      this.name = config.name
    }else if (config.name === false){
      this.name = false
    }else{
      this.name = this.stateObj.attributes.friendly_name
    }


    this._updateName(root.getElementById('name'), this.name);
    this._updateButtons(root);
    
    this.run =+1;
  }

  _isChanged(){
    try{
      var r = false;
      
      const new_state = {
        status: (this.stateObj.attributes.au190) ? this.stateObj.attributes.au190.status : [],
        md_st: (this.stateObj.attributes.au190) ? this.stateObj.attributes.au190.md_status : [],
        enable_irrig_sys: (this.stateObj.attributes.au190) ? this.stateObj.attributes.au190.enable_irrig_sys : false,
        enable_scheduler: (this.stateObj.attributes.au190) ? this.stateObj.attributes.au190.enable_scheduler : false,
        enable_md: (this.stateObj.attributes.au190) ? this.stateObj.attributes.au190.enable_md : false,
        enable_protection: (this.stateObj.attributes.au190) ? this.stateObj.attributes.au190.enable_protection : false,
        enable_motorRunningToL: (this.stateObj.attributes.au190) ? this.stateObj.attributes.au190.enable_motorRunningToL : false,
        enable_waterL: (this.stateObj.attributes.au190) ? this.stateObj.attributes.au190.enable_waterL : false,
        enable_rainL: (this.stateObj.attributes.au190) ? this.stateObj.attributes.au190.enable_rainL : false,
        irrig_sys_status: (this.stateObj.attributes.au190) ? this.stateObj.attributes.au190.irrig_sys_status : false,
        waterLimLogic: (this.stateObj.attributes.au190) ? this.stateObj.attributes.au190.waterLimLogic : false,
        pow: (this.stateObj.attributes.au190) ? this.stateObj.attributes.au190.P : 0,
      }
      
      if( (this._old_state === undefined) ||
        JSON.stringify(this._old_state.status) !== JSON.stringify(new_state.status) 
        || JSON.stringify(this._old_state.md_st) !== JSON.stringify(new_state.md_st) 
        || this._old_state.enable_irrig_sys !== new_state.enable_irrig_sys
        || this._old_state.enable_scheduler !== new_state.enable_scheduler
        || this._old_state.enable_md !== new_state.enable_md
        || this._old_state.enable_protection !== new_state.enable_protection
        || this._old_state.enable_motorRunningToL !== new_state.enable_motorRunningToL
        || this._old_state.enable_waterL !== new_state.enable_waterL
        || this._old_state.enable_rainL !== new_state.enable_rainL
        || this._old_state.irrig_sys_status !== new_state.irrig_sys_status
        || this._old_state.waterLimLogic !== new_state.waterLimLogic
        || this._old_state.pow !== new_state.pow

      ){

        if(this.run == 1){
          if(this._old_state.state !== new_state.state){
            this.run = 0;
          }
        }
        
        this._old_state = new_state;
        r =  true;
        //console.log('<-- _isChanged:' + r)
      }

    }catch(e){
      console.error('_isChanged: ' + e);
    }

    return r;
  }
  
  _openProp(entityId){
    this.fire('hass-more-info', { entityId });
  }
  
  fire(type, detail, options) {
  
    options = options || {}
    detail = detail === null || detail === undefined ? {} : detail
    const e = new Event(type, {
      bubbles: options.bubbles === undefined ? true : options.bubbles,
      cancelable: Boolean(options.cancelable),
      composed: options.composed === undefined ? true : options.composed,
    })
    
    e.detail = detail
    this.dispatchEvent(e)
    return e
  }
  
  _zoneSwitch(zone) {
    if(zone == ""){
      return;
    }
    this._hass.callService("au190_mqtt_irrigation", "sw_zone", 
      {
      "entity_id": this.stateObj.entity_id,
      "zone": zone
      }
    );

  }
  
  _updateName(el, attr) {
    el.innerHTML = attr;
  }

  _updateButtons(root) {
    //console.log(this.stateObj.attributes.au190)
    
    var el = root.getElementById('btns');
    
    if(this.stateObj.state !== 'unavailable'){
      
      if(!this.stateObj.attributes.au190.enable_irrig_sys || !this.stateObj.attributes.au190.irrig_sys_status){
        el.innerHTML = `<button class="OFF err">Turned OFF</button>`;
      }else{
        el.innerHTML = `
          ${Object.keys(this.stateObj.attributes.au190.status).map(item => `
            <button id="${item}" class="${this.stateObj.attributes.au190.status[item]}">Zone${(parseInt(item) + 1)}</button>
          `).join('')}
        `;
      
        if(this.run == 0){
          el.addEventListener('click', (e) => this._zoneSwitch(e.target.id));
        }
      }

      for(let i=0;i<5;i++){
        root.getElementById('i_'+i).removeAttribute("class");
      }
      
      if((!this.stateObj.attributes.au190.enable_motorRunningToL || !this.stateObj.attributes.au190.enable_protection) && this.stateObj.attributes.au190.irrig_sys_status){
        root.getElementById('i_0').classList.add('OFF');
      }else if(this.stateObj.attributes.au190.enable_motorRunningToL && this.stateObj.attributes.au190.irrig_sys_status){
        root.getElementById('i_0').classList.add('ON');
      }else if(this.stateObj.attributes.au190.enable_irrig_sys && !this.stateObj.attributes.au190.irrig_sys_status){
        root.getElementById('i_0').classList.add('err');
      }

      if(!this.stateObj.attributes.au190.enable_waterL || !this.stateObj.attributes.au190.enable_protection){
        root.getElementById('i_1').classList.add('OFF');
      }else if(this.stateObj.attributes.au190.enable_waterL && !this.stateObj.attributes.au190.waterLimLogic){
        root.getElementById('i_1').classList.add('ON');
      }else if(this.stateObj.attributes.au190.enable_waterL && this.stateObj.attributes.au190.waterLimLogic){
        root.getElementById('i_1').classList.add('err');
      }

      if(!this.stateObj.attributes.au190.enable_rainL || !this.stateObj.attributes.au190.enable_protection){
        root.getElementById('i_2').classList.add('OFF');
      }else if(this.stateObj.attributes.au190.enable_rainL){
        root.getElementById('i_2').classList.add('ON');
      }else if(this.stateObj.attributes.au190.enable_rainL && this.stateObj.attributes.au190.enable_irrig_sys && !this.stateObj.attributes.au190.irrig_sys_status){
        root.getElementById('i_2').classList.add('err');
      }
      
      if(this.stateObj.attributes.au190.md_status[0] == 2 || this.stateObj.attributes.au190.md_status[1] == 2 || this.stateObj.attributes.au190.md_status[2] == 2 ){
        root.getElementById('i_3').classList.add('err');
      }else{
        if(!this.stateObj.attributes.au190.enable_md){
          root.getElementById('i_3').classList.add('OFF');
        }else if(this.stateObj.attributes.au190.enable_md){
          root.getElementById('i_3').classList.add('ON');
        }
      }
      
      if(!this.stateObj.attributes.au190.enable_scheduler){
        root.getElementById('i_4').classList.add('OFF');
      }else if(this.stateObj.attributes.au190.enable_scheduler){
        root.getElementById('i_4').classList.add('ON');
      }

      root.getElementById('t_d').classList.remove('g');
      if(this.stateObj.attributes.au190.motor){
        root.getElementById('t_d').classList.add('g');
      }
      var el = root.getElementById('t_d');
      el.innerHTML = `${this.stateObj.attributes.au190.P}W`;
      
      var el = root.getElementById('t_w');
      el.innerHTML = `${this.stateObj.attributes.au190.PD}kWh`;
      
      var el = root.getElementById('t_m');
      el.innerHTML = `${this.stateObj.attributes.au190.PM}kWh`;

      
    }else{
      
      el.innerHTML = `<button class="OFF">Unavailable</button>`;
      
    }

  }
  
  getCardSize() {
    3;
  }
  
}
customElements.define("au190-irrig_card", au190_IrrigCard);