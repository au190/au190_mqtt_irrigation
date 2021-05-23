/*
- type: module
  url: /local/community/au190-irrig_card/au190-irrig_card.js


entity: switch.x_1
name: Test
icon: 'mdi:lightbulb'
type: 'custom:au190-irrig_card.js'


*/

import {cssData} from './styles.js?v=0.1.1';



var au190   = {};
const _wdn = ['M','T','W','T','F','S','S'];
/*******************************************************

  Dlg fc

*******************************************************/

/*******************************************************

  Convert cDown time to Tasmota PulseTime1
  
  f = 0 - Time to Tasmota PulseTime1
  f = 1 - Tasmota PulseTime1 to Time
  f = 2 - Force seconds to 0
  f = 3 - Time to sec
  f = 4 - Sec to Time
  
*******************************************************/
function _cfc(f, d){

  var r = null;
  try{
    
    if(f==0){
      var a = d.split(':'); // split it at the colons
      if(a.length == 2){
        r = ( (+a[0]) * 60 * 60 + (+a[1]) * 60 );
      }else if(a.length == 3){
        r = ( (+a[0]) * 60 * 60 + (+a[1]) * 60 + (+a[2]) );
      }
      if(r==0){
        
      }else if(r<12){
        r = r * 10;
      }else{
        r = r + 100;
      }
      if(r>64900){
        r = 64900;
      }
      
    }else if(f==1){
      
      if(d==0){

      }else if(d<=111){
        d = d/10;
      }else if(d>111){
        d = d - 100;
      }
    
      var sec_num = parseInt(d, 10);
      var hours   = Math.floor(sec_num / 3600);
      var minutes = Math.floor((sec_num - (hours * 3600)) / 60);
      var seconds = sec_num - (hours * 3600) - (minutes * 60);

      if (hours   < 10) {hours   = "0"+hours;}
      if (minutes < 10) {minutes = "0"+minutes;}
      if (seconds < 10) {seconds = "0"+seconds;}
      
      r = hours+':'+minutes+':'+seconds;
      
    }else if(f==2){
      var a = d.split(':'); // split it
      if(a.length == 1){
        r = "00:00";
      }else if(a.length == 3){
        r = a[0] + ":" + a[1];
      }else{
        r = d;
      }
    
    }else if(f==3){
      var a = d.split(':'); // split it at the colons
      if(a.length == 2){
        r = ( (+a[0]) * 60 * 60 + (+a[1]) * 60 );
      }else if(a.length == 3){
        r = ( (+a[0]) * 60 * 60 + (+a[1]) * 60 + (+a[2]) );
      }
    }else if(f==4){
      
      var sec_num = parseInt(d, 10);
      var hours   = Math.floor(sec_num / 3600);
      var minutes = Math.floor((sec_num - (hours * 3600)) / 60);
      var seconds = sec_num - (hours * 3600) - (minutes * 60);

      if (hours   < 10) {hours   = "0"+hours;}
      if (minutes < 10) {minutes = "0"+minutes;}
      if (seconds < 10) {seconds = "0"+seconds;}
      
      r = hours+':'+minutes+':'+seconds;
    }
    
  }catch(e){
    console.error('_cfc: ' + e);
  }
  //console.log('<-- _cfc: [' + f + '][' + d + '][' + r + ']');
  return r;
}
/*******************************************************

  Event form card
  
*******************************************************/
function _evC(o){
  
  if(o.entity_id != au190.o.stateObj.entity_id){
    return;
  }
  try{
    //console.log('--> _evC: ' + o.entity_id);

    if(o.attributes._state == true){
      
      var el = document.getElementById('btn_sys');
      el.removeAttribute('class');
      el.classList.add('ck');
      var ir_st = false;
      if(o.attributes.au190.irrig_sys_status == 1 || o.attributes.au190.irrig_sys_status == 3){
        ir_st = true;
      }
      
      el.classList.add(ir_st);
      
      el = document.getElementById('irig_system_tab');
      el.removeAttribute('class');
      if(!ir_st){
        el.classList.add('h_w');
      }
      
      Object.keys(o.attributes.au190.pulsetime).map(idx => {
        
        el = document.getElementById('enzone_' + idx);
        el.removeAttribute('class');
        el.classList.add('ck_id');
        el.classList.add(o.attributes.au190.enable_zone[idx]);

        el = document.getElementById('pulsetime_' + idx);
        el.value = _cfc(1, o.attributes.au190.pulsetime[idx]);
      })
      
      el = document.getElementById('sch_en');
      el.removeAttribute('class');
      el.classList.add('ck');
      el.classList.add(o.attributes.au190.enable_scheduler);

      el = document.getElementById('sch_tab');
      el.removeAttribute('class');
      if(!o.attributes.au190.enable_scheduler){
        el.classList.add('h_w');
      }

      Object.keys(o.attributes.au190.irrigdays).map(idx => {
        document.getElementById('wdays_' + idx).checked = o.attributes.au190.irrigdays[idx];
      })
             
      el = document.getElementById('sch_da');
      el.innerHTML = Object.keys(o.attributes.au190.scheduler).map(idx => `
      <div class='m'>
          <div class='t1'>Start time${(parseInt(idx) + 1)}</div>
          <div class='t1'><input type='time' id='schtime_${(idx)}' class='ch_id' step='1' value='${o.attributes.au190.scheduler[idx]}'></div>
          <paper-icon-button id='schdel_${(idx)}' class='ck_id false' icon=${'mdi:delete'}></paper-icon-button>
        </div>
      `).join('');

      el = document.getElementById('md_en');
      el.removeAttribute('class');
      el.classList.add('ck');
      el.classList.add(o.attributes.au190.enable_md); 
       
      el = document.getElementById('md_tab');
      el.removeAttribute('class');
      if(!o.attributes.au190.enable_md){
        el.classList.add('h_w');
      }
      
      Object.keys(o.attributes.au190.md_status).map(idx => {
        el = document.getElementById('md_' + idx);
        el.removeAttribute('class');
        el.classList.add(o.attributes.au190.md_status[idx]);
      }); 
       
      el = document.getElementById('md_time');
      el.value = _cfc(1, o.attributes.au190.md_on_time);
                  
      el = document.getElementById('md_da');
      el.innerHTML = Object.keys(o.attributes.au190.md).map(idx => `
        <div class='m'>
          <div class='t1'><input type='time' id='mdsttime_${(idx)}' class='ch_id' step='1' value='${o.attributes.au190.md[idx].start_time}'></div>
          <div class='t1'><input type='time' id='mdentime_${(idx)}' class='ch_id' step='1' value='${o.attributes.au190.md[idx].end_time}'></div>
          <paper-icon-button id='mddel_${(idx)}' class='ck_id false' icon=${'mdi:delete'}></paper-icon-button>
        </div>
      `).join('');

      el = document.getElementById('pro_en');
      el.removeAttribute('class');
      el.classList.add('ck');
      el.classList.add(o.attributes.au190.enable_protection);
       
      el = document.getElementById('pro_tab');
      el.removeAttribute('class');
      if(!o.attributes.au190.enable_protection){
        el.classList.add('h_w');
      }

      el = document.getElementById('pro_motors');
      el.removeAttribute('class');
      el.classList.add(o.attributes.au190.motorPower);
      
      el = document.getElementById('pro_waterLs');
      el.removeAttribute('class');
      el.classList.add(o.attributes.au190.waterLim);
      
      el = document.getElementById('pro_RainLs');
      el.removeAttribute('class');
      el.classList.add(o.attributes.au190.rainLim);
      
      el = document.getElementById('pro_enmotor');
      el.removeAttribute('class');
      el.classList.add('ck');
      el.classList.add(o.attributes.au190.enable_motorRunningToL);

      el = document.getElementById('pro_motortime');
      el.value = _cfc(4, o.attributes.au190.motorRunningTout);
      
      el = document.getElementById('pro_enwaterL');
      el.removeAttribute('class');
      el.classList.add('ck');
      el.classList.add(o.attributes.au190.enable_waterL);        
       
      el = document.getElementById('pro_waterL');
      el.value = _cfc(4, o.attributes.au190.waterLimTout);
      
      el = document.getElementById('pro_enrainL');
      el.removeAttribute('class');
      el.classList.add('ck');
      el.classList.add(o.attributes.au190.enable_rainL);   
      
      el = document.getElementById('pro_rainL');
      el.value = _cfc(4, o.attributes.au190.rainLimTout);
      
    }
    
    el = document.getElementById('inf');
    el.innerHTML = Object.keys(o.attributes.i).map(idx => `
      <div class='m2'>
        <div class="t1">Topic:</div>
        <div class="t5">${idx}</div>
      </div>
      <div class='m2'>
        <div class="t1">IpAddress:</div>
        <div class="t5"><a href="http://${o.attributes.i[idx].IpAddress}" target="_blank" class="flase">${o.attributes.i[idx].IpAddress}</a></div>
      </div>
      <div class='m2'>
        <div class="t1">SSId:</div>
        <div class="t5">${o.attributes.i[idx].SSId}</div>
      </div>
      <div class='m2'>
        <div class="t1">Uptime:</div>
        <div class="t5">${o.attributes.i[idx].Uptime}</div>
      </div>
      <div class='m2'>
        <div class="t1">Time:</div>
        <div class="t5">${o.attributes.i[idx].Time}</div>
      </div>
      <div class='m2'>
        <div class="sep"></div>
      </div>
    `).join('');
    
  }catch(e){
    console.error('<-- _evC: ' + e);
  }
}
/*******************************************************

  Event form dialog
  o - card object
  e - event object
  f - type of event click change ....
*******************************************************/
function _ev(o, e, f){

  if(e.classList.contains('ck') || e.classList.contains('ck_id') || f == 2 && e.classList.contains('ch_id')){
    
    //console.log('--> _ev: [' + f + '][' + e.id + '] ' + e.className);

    var fc = '';
    var id = '';
    var el = '';
    if(e.classList.contains('ck_id') || e.classList.contains('ch_id')){//has more info
    
      const a = e.id.split('_');
      if(a.length == 2){
        fc = a[0];
        id = a[1];
      }
    }

    
    if(e.id == 'c_w' || e.id == 'r_dlg'){
      
      const d = document.getElementById('r_dlg');
      document.body.removeChild(d);
      
      /*
      if(o.offsetTop > 1000){
        au190.o.scrollIntoView(true);
      }else{
        au190.o.scrollIntoView(false);
      }
      */
      
      au190   = {};
      return;
      
    }else if(e.id == 'btn_sys'){
      
      if(o.stateObj.attributes.au190.irrig_sys_status != 1){
        o.stateObj.attributes.au190.irrig_sys_status = 1;
      }else{
        o.stateObj.attributes.au190.irrig_sys_status = 0;
      }
      
    }else if(fc == 'enzone'){
      
      o.stateObj.attributes.au190['enable_zone'][id] = !o.stateObj.attributes.au190['enable_zone'][id];

    }else if(fc == 'pulsetime'){
      
      o.stateObj.attributes.au190['pulsetime'][id] = _cfc(0, e.value);

    }else if(e.id == 'sch_en'){

      o.stateObj.attributes.au190.enable_scheduler = !o.stateObj.attributes.au190.enable_scheduler;
      
    }else if(fc == 'wdays'){
      
      o.stateObj.attributes.au190['irrigdays'][id] = !o.stateObj.attributes.au190['irrigdays'][id];
    
    }else if(e.id == 'sch_add'){

      el = document.getElementById('start_time');
      o.stateObj.attributes.au190.scheduler.push(_cfc(2, el.value));
      
    }else if(fc == 'schdel'){

      o.stateObj.attributes.au190.scheduler.splice(id,1)
      
    }else if(fc == 'schtime'){
      
      o.stateObj.attributes.au190.scheduler[id] = _cfc(2, e.value);
      
    }else if(e.id == 'md_en'){
      
      o.stateObj.attributes.au190.enable_md = !o.stateObj.attributes.au190.enable_md;
    
    }else if(e.id == 'md_time'){
      
      o.stateObj.attributes.au190.md_on_time = _cfc(0, e.value);

    }else if(e.id == 'md_add'){
      
      var u = {};
      el = document.getElementById('md_sttime');
      u['start_time'] = _cfc(2, el.value);
      
      el = document.getElementById('md_entime');
      u['end_time'] = _cfc(2, el.value);

      o.stateObj.attributes.au190.md.push(u);

    }else if(fc == 'mddel'){
      
      o.stateObj.attributes.au190.md.splice(id,1);

    }else if(fc == 'mdsttime'){
      
      o.stateObj.attributes.au190.md[id]['start_time'] = _cfc(2, e.value);
      
    }else if(fc == 'mdentime'){
      
      o.stateObj.attributes.au190.md[id]['end_time'] = _cfc(2, e.value);
      
    }else if(e.id == 'pro_en'){
      
      o.stateObj.attributes.au190.enable_protection = !o.stateObj.attributes.au190.enable_protection;
            
    }else if(e.id == 'pro_enmotor'){
      
      o.stateObj.attributes.au190.enable_motorRunningToL = !o.stateObj.attributes.au190.enable_motorRunningToL;
      
    }else if(e.id == 'pro_motortime'){
      
      o.stateObj.attributes.au190.motorRunningTout = _cfc(3, e.value);
      
    }else if(e.id == 'pro_enwaterL'){

      o.stateObj.attributes.au190.enable_waterL = !o.stateObj.attributes.au190.enable_waterL;
    
    }else if(e.id == 'pro_waterL'){

      o.stateObj.attributes.au190.waterLimTout = _cfc(3, e.value);
    
    }else if(e.id == 'pro_enrainL'){

      o.stateObj.attributes.au190.enable_rainL = !o.stateObj.attributes.au190.enable_rainL;
      
    }else if(e.id == 'pro_rainL'){

      o.stateObj.attributes.au190.rainLimTout = _cfc(3, e.value);
    
    }

    
    if(e.id == 'btn_i'){
      o._au190fc(3);
    }else{
      o._au190fc(2, o.stateObj.attributes.au190);
    }
  }
}

function _openProp(o, c){

  //console.log('--> _openProp: ' + c.entity);
  au190.o = o;

  const dlg     = document.createElement('r_dialog');
  const style   = document.createElement('style');
  style.textContent = cssData();

  if(typeof o.stateObj === 'undefined'){
    return;
  }
  
  var ir_st = false;
  if(o.stateObj.attributes.au190.irrig_sys_status == 1 || o.stateObj.attributes.au190.irrig_sys_status == 3){
    ir_st = true;
  }
  var tab_1 = ir_st ? '' : 'h_w';
  var tab_2 = o.stateObj.attributes.au190.enable_scheduler ? '' : 'h_w';
  var tab_3 = o.stateObj.attributes.au190.enable_md ?        '' : 'h_w';
  var tab_4 = o.stateObj.attributes.au190.enable_protection ?'' : 'h_w';
  
  dlg.innerHTML = `
    <div class='mw'>
      <div class='menu1'>
        <paper-icon-button icon='mdi:close' id='c_w' class='ck d_icon clickable' role='button' tabindex='0' aria-disabled='false'></paper-icon-button>
        <div id='name' class='d_title'>${o.name}</div>
      </div>
      <div class='wr_dlg'>
        <div class='m'>
          <div class='sep'></div>
        </div>
        ${o.stateObj.attributes._state == true ? `
        <div class='m1'>
          <div class='t3'>Irrigation system</div>
          <div class='t1'></div>
          <paper-icon-button id='btn_sys' class='ck ${ir_st}' icon=${'mdi:power'}></paper-icon-button>
        </div>
        <div id='irig_system_tab' class='${tab_1}'>
          ${Object.keys(o.stateObj.attributes.au190.pulsetime).map(idx => `
            <div class='m'>
              <div class='t1'>Zone${(parseInt(idx) + 1)}</div>
              <div class='t1'><input type='time' id='pulsetime_${(idx)}' class='ch_id' step='1' value='${_cfc(1, o.stateObj.attributes.au190.pulsetime[idx])}'></div>
              <paper-icon-button id='enzone_${(idx)}' class='ck_id ${o.stateObj.attributes.au190.enable_zone[idx]}' icon=${'mdi:power'}></paper-icon-button>
            </div>
          `).join('')}
          <div class='m'>
            <div class='sep'></div>
          </div>
          <div class='m1'>
            <div class='t3'>Scheduler</div>
            <div class='t1'></div>
            <paper-icon-button id='sch_en' class='ck ${o.stateObj.attributes.au190.enable_scheduler}' icon=${'mdi:power'}></paper-icon-button>
          </div>
          <div id='sch_tab' class='${tab_2}'>
            <div class='m1 w_s'>
              ${Object.keys(o.stateObj.attributes.au190.irrigdays).map(idx => `
              <input type='checkbox' id='wdays_${(idx)}' class='ch_id' ${(o.stateObj.attributes.au190.irrigdays[idx]) ? `checked` : ``}><label for='wdays_${idx}'>${_wdn[idx]}</label>
              `).join('')}
            </div>
            <div class='m'>
              <div class='t1'>Start time</div>
              <div class='t1'><input type='time' id='start_time' step='1' value='01:00'></div>
              <paper-icon-button id='sch_add' class='ck g' icon=${'mdi:plus-box'}></paper-icon-button>
            </div>
            <div id='sch_da'>
              ${Object.keys(o.stateObj.attributes.au190.scheduler).map(idx => `
                <div class='m'>
                  <div class='t1'>Start time${(parseInt(idx) + 1)}</div>
                  <div class='t1'><input type='time' id='schtime_${(idx)}' class='ch_id' step='1' value='${o.stateObj.attributes.au190.scheduler[idx]}'></div>
                  <paper-icon-button id='schdel_${(idx)}' class='ck_id false' icon=${'mdi:delete'}></paper-icon-button>
                </div>
              `).join('')}
            </div>
          </div>
          <div class='m'>
            <div class='sep'></div>
          </div>
          <div class='m1'>
            <div class='t3'>Md settings</div>
            <div class='t1'></div>
            <paper-icon-button id='md_en' class='ck ${o.stateObj.attributes.au190.enable_md}' icon=${'mdi:power'}></paper-icon-button>
          </div>
          <div id='md_tab' class='${tab_3}'>
            <div class='m1'>
              ${Object.keys(o.stateObj.attributes.au190.md_status).map(idx => `
                <paper-icon-button id='md_${(idx)}' class='${o.stateObj.attributes.au190.md_status[idx]}' icon=${'mdi:motion-sensor'}></paper-icon-button>
              `).join('')}
            </div>
            <div class='m'>
              <div class='t1'>Md on time</div>
              <div class='t1'><input type='time' id='md_time' class='ch_id' step='1' value='${_cfc(1, o.stateObj.attributes.au190.md_on_time)}'></div>
              <div class='t2'></div>
            </div>
            <div class='m'>
              <div class='t1'>Start time</div>
              <div class='t1'>End time</div>
              <div class='t2'></div>
            </div>
            <div class='m'>
              <div class='t1'><input type='time' id='md_sttime' step='1' value='21:00'></div>
              <div class='t1'><input type='time' id='md_entime' step='1' value='07:00'></div>
              <paper-icon-button id='md_add' class='ck g' icon=${'mdi:plus-box'}></paper-icon-button>
            </div>
            <div id='md_da'>
              ${Object.keys(o.stateObj.attributes.au190.md).map(idx => `
                <div class='m'>
                  <div class='t1'><input type='time' id='mdsttime_${(idx)}' class='ch_id' step='1' value='${o.stateObj.attributes.au190.md[idx].start_time}'></div>
                  <div class='t1'><input type='time' id='mdentime_${(idx)}' class='ch_id' step='1' value='${o.stateObj.attributes.au190.md[idx].end_time}'></div>
                  <paper-icon-button id='mddel_${(idx)}' class='ck_id false' icon=${'mdi:delete'}></paper-icon-button>
                </div>
              `).join('')}
            </div>
          </div>
          <div class='m'>
            <div class='sep'></div>
          </div>
          <div class='m1'>
            <div class='t3'>Protection</div>
            <div class='t1'></div>
            <paper-icon-button id='pro_en' class='ck ${o.stateObj.attributes.au190.enable_protection}' icon=${'mdi:power'}></paper-icon-button>
          </div>
          <div id='pro_tab' class='${tab_4}'>
            <div class='m'>
              <paper-icon-button id='pro_motors' class='${o.stateObj.attributes.au190.motorPower}' icon=${'mdi:engine-outline'}></paper-icon-button>
              <paper-icon-button id='pro_waterLs' class='${o.stateObj.attributes.au190.waterLim}' icon=${'mdi:water-pump-off'}></paper-icon-button>
              <paper-icon-button id='pro_RainLs' class='${o.stateObj.attributes.au190.rainLim}' icon=${'mdi:weather-pouring'}></paper-icon-button>
            </div>
            <div class='m'>
              <div class='t1'>MotorRunTout</div>
              <div class='t1'><input type='time' id='pro_motortime' class='ch_id' step='1' value='${_cfc(4, o.stateObj.attributes.au190.motorRunningTout)}'></div>
              <paper-icon-button id='pro_enmotor' class='ck ${o.stateObj.attributes.au190.enable_motorRunningToL}' icon=${'mdi:power'}></paper-icon-button>
            </div>
            <div class='m'>
              <div class='t1'>WaterLimTout</div>
              <div class='t1'><input type='time' id='pro_waterL' class='ch_id' step='1' value='${_cfc(4, o.stateObj.attributes.au190.waterLimTout)}'></div>
              <paper-icon-button id='pro_enwaterL' class='ck ${o.stateObj.attributes.au190.enable_waterL}' icon=${'mdi:power'}></paper-icon-button>
            </div>
            <div class='m'>
              <div class='t1'>RainLimTout</div>
              <div class='t1'><input type='time' id='pro_rainL' class='ch_id' step='1' value='${_cfc(4, o.stateObj.attributes.au190.rainLimTout)}'></div>
              <paper-icon-button id='pro_enrainL' class='ck ${o.stateObj.attributes.au190.enable_rainL}' icon=${'mdi:power'}></paper-icon-button>
            </div>
          </div>
        </div>
        `:`<div class='mst'>
            <button class='off'>Unavailable</button>
          </div>`
        }
        <div class='m'>
          <div class='sep'></div>
        </div>
        <div class='m1'>
          <div class='t3'>Info</div>
          <div></div>
          <paper-icon-button id='btn_i' class='ck false' icon=${'mdi:refresh'}></paper-icon-button>
        </div>
        <div id='inf'>
          ${Object.keys(o.stateObj.attributes.i).map(idx => `
            <div class='m2'>
              <div class='t1'>Topic:</div>
              <div class='t5'>${idx}</div>
            </div>
            <div class='m2'>
              <div class='t1'>IpAddress:</div>
              <div class='t5'><a href='http://${o.stateObj.attributes.i[idx].IpAddress}' target='_blank' class='flase'>${o.stateObj.attributes.i[idx].IpAddress}</a></div>
            </div>
            <div class='m2'>
              <div class='t1'>SSId:</div>
              <div class='t5'>${o.stateObj.attributes.i[idx].SSId}</div>
            </div>
            <div class='m2'>
              <div class='t1'>Uptime:</div>
              <div class='t5'>${o.stateObj.attributes.i[idx].Uptime}</div>
            </div>
            <div class='m2'>
              <div class='t1'>Time:</div>
              <div class='t5'>${o.stateObj.attributes.i[idx].Time}</div>
            </div>
            <div class='m'>
              <div class='sep'></div>
            </div>
          `).join('')}
        </div>
      </div>
    </div>
  `;
  
  dlg.appendChild(style);
  dlg.setAttribute('id', 'r_dlg');
  dlg.setAttribute('class', 'ck');
  document.body.appendChild(dlg);


  dlg.addEventListener('click', function(e){
    if(e.target){
      _ev(o, e.target, 1);
    }
  });
  
  dlg.addEventListener('change', function(e){
    if(e.target){
      _ev(o, e.target, 2);
    }
  });

}


class au190_IrrigCard extends HTMLElement {
  
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
  }

  setConfig(config){
    
    if (!config.entity) {
      throw new Error('Please define an entity');
    }

    const root = this.shadowRoot;
    if (root.lastChild) root.removeChild(root.lastChild);

    const cardConfig = Object.assign({}, config);
    const card = document.createElement('div');
    const style = document.createElement('style');
    style.textContent = cssData();

    card.innerHTML = `
      <ha-card class='m_c'>
        <div class='m'>
          <div id='name' class='c_title'>${this.name}</div>
          <paper-icon-button icon='mdi:dots-vertical' id='m_1' class='c_icon off clickable' role='button' tabindex='0' aria-disabled='false'></paper-icon-button>
        </div>
        <div id='btn_st' class='mst'>
        </div>
        <div class='sep'></div>
        <div class='mst'>
          <paper-icon-button id='i_0' class='OFF' icon=${'mdi:engine-outline'}></paper-icon-button>
					<paper-icon-button id='i_1' class='OFF' icon=${'mdi:water-pump-off'}></paper-icon-button>
          <paper-icon-button id='i_2' class='OFF' icon=${'mdi:weather-pouring'}></paper-icon-button>
					<paper-icon-button id='i_3' class='OFF' icon=${'mdi:motion-sensor'}></paper-icon-button>
          <paper-icon-button id='i_4' class='OFF' icon=${'mdi:timetable'}></paper-icon-button>
        </div>
        <div class='sep'></div>
        <div class='mst'>
          <div class='ibox'>
            <p>Power</p>
            <p id='t_d' class='mtxt'>0W</p>
          </div>
          <div class='ibox'>
            <p>P daily</p>
            <p id='t_w' class='mtxt'>0kWh</p>
          </div>
          <div class='ibox'>
            <p>P monthly</p>
            <p id='t_m' class='mtxt'>0kWh</p>
          </div>
        </div>
      </ha-card>
    `;
    card.appendChild(style);
    root.appendChild(card)
    
    var el = root.getElementById('m_1');
    el.addEventListener('click', () => _openProp(this, config));
    
    el = root.getElementById('btn_st');
    el.addEventListener('click', (e) => this._cck(e.target.id));
    
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
    
    if(typeof config.name === 'string'){
      this.name = config.name
    }else if (config.name === false){
      this.name = false
    }else{
      this.name = this.stateObj.attributes.friendly_name
    }


    this._updateName(root.getElementById('name'), this.name);
    this._updateButtons(root);
  }

  _isChanged(){
    try{
      var r = false;
      
      const new_state = {
        state: this.stateObj.state,
        au190: (this.stateObj.attributes.au190) ? this.stateObj.attributes.au190 : {},
      }
      
     if( (this._old_state === undefined)
        || this._old_state.state !== new_state.state
        || this._old_state.au190 !== new_state.au190
      ){
        
        this._old_state = new_state;
        r =  true;
        //console.log('<-- _isChanged:' + r)
      }

    }catch(e){
      console.error('_isChanged: ' + e);
    }

    return r;
  }
  
  _au190fc(f, o){
    
    if(typeof this._hass === 'undefined'){
      return;
    }

    this._hass.callService('au190_mqtt_irrigation', 'au190_fc', {
      entity_id: this.stateObj.entity_id,
      fc: f,
      au190: o,
    });
  }
  
  _cck(o){
    if(!isNaN(o)){
      this._au190fc(1, {'zone': o});
    }else if(o == 'm_on'){
      this.stateObj.attributes.au190.irrig_sys_status = 1;
      this._au190fc(2, this.stateObj.attributes.au190);
    }
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
  
  _updateName(el, attr) {
    el.innerHTML = attr;
  }

  _updateButtons(root){

    try{
      _evC(this.stateObj);
    }catch{}
    
    var el    = root.getElementById('0');
    
    if(this.stateObj.attributes._state == true){
      
      if(this.stateObj.attributes.au190.irrig_sys_status == 0){
        el = root.getElementById('btn_st').innerHTML = `<button id='m_on' class='OFF error'>Turn ON</button>`;
      }else if(this.stateObj.attributes.au190.irrig_sys_status == 2){
        el = root.getElementById('btn_st').innerHTML = `<button id='m_on' class='OFF error'>Error Motor Running too long</button>`;
      }else if(this.stateObj.attributes.au190.irrig_sys_status == 3){
        el = root.getElementById('btn_st').innerHTML = `<button id='m_on' class='OFF error'>Water Limit</button>`;
      }else{
        
        if(el == null){
          el = root.getElementById('btn_st');
          el.innerHTML = `
            ${Object.keys(this.stateObj.attributes.au190.status).map(idx => `
              <button id='${idx}' class='${this.stateObj.attributes.au190.status[idx]}'>Zone${(parseInt(idx) + 1)}</button>
            `).join('')}
          `;
        }
    
        el = root.getElementById('btn_st');
        el.removeAttribute('class');
        el.classList.add('mst');
        
        Object.keys(this.stateObj.attributes.au190.status).map(idx => {
          el = root.getElementById(idx);
          el.removeAttribute('class');
          el.classList.add(this.stateObj.attributes.au190.status[idx]);
        })        
      }
      
      for(let i=0;i<5;i++){
        root.getElementById('i_'+i).removeAttribute('class');
      }
      
      el = root.getElementById('i_0');
      if(!this.stateObj.attributes.au190.enable_motorRunningToL || !this.stateObj.attributes.au190.enable_protection){
        el.classList.add('OFF');
      }else if(this.stateObj.attributes.au190.irrig_sys_status == 2){
        el.classList.add('error');
      }else if(this.stateObj.attributes.au190.motorPower){
        el.classList.add('g');
      }else if(this.stateObj.attributes.au190.enable_motorRunningToL){
        el.classList.add('ON');
      }

      el = root.getElementById('i_1');
      if(!this.stateObj.attributes.au190.enable_waterL || !this.stateObj.attributes.au190.enable_protection){
        el.classList.add('OFF');
      }else if(!this.stateObj.attributes.au190.waterLimLogic){
        el.classList.add('ON');
      }else if(this.stateObj.attributes.au190.waterLimLogic){
        el.classList.add('error');
      }

      el = root.getElementById('i_2');
      if(!this.stateObj.attributes.au190.enable_rainL || !this.stateObj.attributes.au190.enable_protection){
        el.classList.add('OFF');
      }else if(!this.stateObj.attributes.au190.rainLimLogic){
        el.classList.add('ON');
      }else if(this.stateObj.attributes.au190.rainLimLogic){
        el.classList.add('error');
      }
      
      var tcl = '';
      el = root.getElementById('i_3');
      if(!this.stateObj.attributes.au190.enable_md){
        el.classList.add('OFF');
      }else{
        el.removeAttribute('class');
          
        Object.keys(this.stateObj.attributes.au190.md_status).map(idx => {
          if(this.stateObj.attributes.au190.md_status[idx] == 'error'){
            tcl = 'error';
          }else if(this.stateObj.attributes.au190.md_status[idx] && tcl != 'error'){
            tcl = 'g';
          }
        });
        
        if(tcl != ''){
          el.classList.add(tcl);
        }else{
          el.classList.add('ON');
        }
      
      }
      
      el = root.getElementById('i_4');
      if(this.stateObj.attributes.au190.enable_scheduler){
        el.classList.add('ON');
      }else{
        el.classList.add('OFF');
      }

      root.getElementById('t_d').classList.remove('g');
      if(this.stateObj.attributes.au190.motorPower){
        root.getElementById('t_d').classList.add('g');
      }
      var el = root.getElementById('t_d');
      el.innerHTML = `${this.stateObj.attributes.au190.P}W`;
      
      el = root.getElementById('t_w');
      el.innerHTML = `${this.stateObj.attributes.au190.PD}kWh`;
      
      el = root.getElementById('t_m');
      el.innerHTML = `${this.stateObj.attributes.au190.PM}kWh`;
    
    }else{
      
      el = root.getElementById('btn_st');
      el.innerHTML = `<button id='mu' class='OFF'>Unavailable</button>`;
      
    }

  }
  
  getCardSize() {
    3;
  }
  
}
customElements.define('au190-irrig_card', au190_IrrigCard);