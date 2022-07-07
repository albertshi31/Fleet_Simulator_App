/* global window */
import React, {useState, useEffect} from 'react';
import {render} from 'react-dom';
import {StaticMap} from 'react-map-gl';
import {AmbientLight, PointLight, LightingEffect} from '@deck.gl/core';
import DeckGL from '@deck.gl/react';
import {TripsLayer} from '@deck.gl/geo-layers';

function updateTime(time) {
  var period = "AM";
  if (time / 3600 >= 12) {
    period = "PM";
  }
  if (time / 3600 <= 6 || time / 3600 >= 18) {
    $('#time').css('background-color', 'black');
    $('#time').css('color', 'white');
  }
  else {
    $('#time').css('background-color', 'white');
    $('#time').css('color', 'black');
  }

  var hours = Math.floor(time / 3600) % 12;
  var minutes = Math.floor(time / 60) % 60;
  var seconds = time % 60;

  if (hours == 0) hours = 12;
  hours = hours < 10 ? `0${hours}` : hours;
  minutes = minutes < 10 ? `0${minutes}` : minutes;
  seconds = seconds < 10 ? `0${seconds}` : seconds;

  var display_time = `${hours}:${minutes}:${seconds} ${period}`;
  $('#time').text(display_time);
};

const ambientLight = new AmbientLight({
  color: [255, 255, 255],
  intensity: 1.0
});

const pointLight = new PointLight({
  color: [255, 255, 255],
  intensity: 2.0,
  position: [-74.762758, 40.226667, 8000]
});

const lightingEffect = new LightingEffect({ambientLight, pointLight});

const material = {
  ambient: 0.1,
  diffuse: 0.6,
  shininess: 32,
  specularColor: [60, 64, 70]
};

const DEFAULT_THEME = {
  buildingColor: [175, 175, 175], // gray
  trailColor0: [255, 0, 0], // red
  trailColor1: [252, 186, 3], // orange/gold
  trailColor2: [0, 0, 139], // dark blue
  trailColor3: [144, 238, 144], // light green
  trailColor4: [0, 100, 0], // dark green
  material,
  effects: [lightingEffect]
};

const INITIAL_VIEW_STATE = {
  longitude: -74.753789,
  latitude: 40.227492,
  zoom: 12,
  pitch: 45,
  bearing: 0
};

const MAP_STYLE = 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json';

function App({
  trips = TRIPS,
  trailLength = 10,
  initialViewState = INITIAL_VIEW_STATE,
  mapStyle = MAP_STYLE,
  theme = DEFAULT_THEME,
  loopLength = 86995, // unit corresponds to the timestamp in source data
  startingAnimationSpeed = 1,
  startTime = 0
}) {
  // States that decide which vehicle occupancy to show
  const [occupancyHideArray, setOccupancyHideArray] = useState([]);

  const [animationSpeed, setAnimationSpeed] = useState(startingAnimationSpeed);
  const [prevAnimationSpeed, setPrevAnimationSpeed] = useState(animationSpeed);
  const [time, setTime] = useState(startTime);
  updateTime(time);
  const [animation] = useState({});

  const animate = () => {
    setTime(t => (t + animationSpeed) % loopLength);
    animation.id = window.requestAnimationFrame(animate);
  };

  useEffect(
    () => {
      animation.id = window.requestAnimationFrame(animate);
      return () => window.cancelAnimationFrame(animation.id);
    },
    [animation, animationSpeed, time, prevAnimationSpeed, occupancyHideArray]
  );

  const trailColors = [theme.trailColor0, theme.trailColor1, theme.trailColor2, theme.trailColor3, theme.trailColor4];
  const layers = [
    new TripsLayer({
      id: 'trips',
      data: trips,
      getPath: d => d.lnglats,
      getTimestamps: d => d.timestamps,
      getColor: d => {
        let num = d.num_passengers;
        if (!(occupancyHideArray.includes(num))) {
          return trailColors[num];
        }
        else {
          return [0, 0, 0, 0];
        }
      },
      updateTriggers: {
        getColor: occupancyHideArray
      },
      opacity: 1,
      widthMinPixels: 10,
      rounded: true,
      trailLength,
      currentTime: time,
      shadowEnabled: false,
      // Enable picking
      pickable: true
    }),
  ];

  return (
    <div>
    <div id="topright" style={{position: 'absolute', bottom: '10px', right: '0', zIndex: '1'}}>
      <div class='my-legend'>
        <div class='legend-title'>Car Occupancy</div>
        <div class='legend-scale'>
          <ul class='legend-labels'>
            <li>
              <input type="checkbox" id="zeroPax" value="0" onClick={() => {
              let id_str="#zeroPax";
              const copyArray = [...occupancyHideArray];
              var result = [];
              if ($(id_str).prop('checked')) {
                result = copyArray.filter(num => num != parseInt($(id_str).val()));
              }
              else {
                result = copyArray.concat(parseInt($(id_str).val()));
              }
              console.log(result);
              setOccupancyHideArray(result);
            }} />
                <label for="zeroPax">
                  <span style={{background: '#FF0000'}}></span>Zero Passengers
                </label>
            </li>
            <li>
              <input type="checkbox" id="onePax" value="1" onClick={() => {
              let id_str="#onePax";
              const copyArray = [...occupancyHideArray];
              var result = [];
              if ($(id_str).prop('checked')) {
                result = copyArray.filter(num => num != parseInt($(id_str).val()));
              }
              else {
                result = copyArray.concat(parseInt($(id_str).val()));
              }
              console.log(result);
              setOccupancyHideArray(result);
            }} />
                <label for="onePax">
                  <span style={{background: '#FCBA03'}}></span>One Passenger
                </label>
            </li>
            <li>
              <input type="checkbox" id="twoPax" value="2" onClick={() => {
              let id_str="#twoPax";
              const copyArray = [...occupancyHideArray];
              var result = [];
              if ($(id_str).prop('checked')) {
                result = copyArray.filter(num => num != parseInt($(id_str).val()));
              }
              else {
                result = copyArray.concat(parseInt($(id_str).val()));
              }
              console.log(result);
              setOccupancyHideArray(result);
            }} />
                <label for="twoPax">
                  <span style={{background: '#00008B'}}></span>Two Passengers
                </label>
            </li>
            <li>
              <input type="checkbox" id="threePax" value="3" onClick={() => {
              let id_str="#threePax";
              const copyArray = [...occupancyHideArray];
              var result = [];
              if ($(id_str).prop('checked')) {
                result = copyArray.filter(num => num != parseInt($(id_str).val()));
              }
              else {
                result = copyArray.concat(parseInt($(id_str).val()));
              }
              console.log(result);
              setOccupancyHideArray(result);
            }} />
                <label for="threePax">
                  <span style={{background: '#90EE90'}}></span>Three Passengers
                </label>
            </li>
            <li>
              <input type="checkbox" id="fourPax" value="4" onClick={() => {
              let id_str="#fourPax";
              const copyArray = [...occupancyHideArray];
              var result = [];
              if ($(id_str).prop('checked')) {
                result = copyArray.filter(num => num != parseInt($(id_str).val()));
              }
              else {
                result = copyArray.concat(parseInt($(id_str).val()));
              }
              console.log(result);
              setOccupancyHideArray(result);
            }} />
                <label for="fourPax">
                  <span style={{background: '#006400'}}></span>Four Passengers
                </label>
            </li>
          </ul>
        </div>
      </div>
    </div>

    <div style={{position: 'absolute', bottom: '0', left: '30%', width: '40%', textAlign: 'center', zIndex: '2'}}>
    <button onClick={() => {setTime(Math.max(0, time-1));}}>
        <i class="fas fa-step-backward" />
    </button>
    <button onClick={() => {setAnimationSpeed(prevAnimationSpeed);}}>
        <i class="fa fa-play" />
    </button>
    <button onClick={() => {setPrevAnimationSpeed(animationSpeed); setAnimationSpeed(0);}}>
        <i class="fa fa-stop" />
    </button>
    <button onClick={() => {setTime((time+1) % loopLength);}}>
        <i class="fas fa-step-forward" />
    </button>
    <button onClick={() => {setPrevAnimationSpeed(1); setAnimationSpeed(1); setTime(0);}}>
        <i class="fas fa-redo" />
    </button>
    <br />
    <label for="speedInput">Speed: {animationSpeed}x</label>
    <input style={{paddingTop: '5px', width:"70%", float:"right"}} id="speedInput" onChange={() => {setAnimationSpeed(parseInt(document.getElementById("speedSelector").value)); setPrevAnimationSpeed(parseInt(document.getElementById("speedSelector").value));}} type="range" value={animationSpeed} min="0" max="50" id="speedSelector" />
    <br />
    <label for="timeInput">Time: {time} sec</label>
    <input style={{width:"70%", float: "right"}} id="timeInput" onChange={() => {setTime(parseInt(document.getElementById("timeSelector").value) % loopLength);}} type="range" value={time} min="0" max={loopLength} id="timeSelector" />
    </div>

    <DeckGL
      layers={layers}
      effects={theme.effects}
      initialViewState={initialViewState}
      controller={true}
    >
      <StaticMap reuseMaps mapStyle={mapStyle} preventStyleDiffing={true} />
    </DeckGL>
    </div>
  );
};

export default App;
