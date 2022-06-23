/* global window */
import React, {useState, useEffect} from 'react';
import {render} from 'react-dom';
import {StaticMap} from 'react-map-gl';
import {AmbientLight, PointLight, LightingEffect} from '@deck.gl/core';
import DeckGL from '@deck.gl/react';
import {PolygonLayer, TextLayer, ScatterplotLayer} from '@deck.gl/layers';
import {TripsLayer} from '@deck.gl/geo-layers';

function updateMetricAnimations(time) {
  let num_active_vehicles = METRIC_ANIMATIONS["NumOfActiveVehicles"][time];
  let num_active_passengers = METRIC_ANIMATIONS["NumOfActivePassengers"][time];
  let avo = METRIC_ANIMATIONS["AVO"][time];
  let passengers_left = METRIC_ANIMATIONS["PassengersLeft"][time];
  let served_passengers = METRIC_ANIMATIONS["ServedPassengers"][time];
  $('#AVO').html(avo.toFixed(2).toString());
  $('#NumOfActiveVehicles').html(num_active_vehicles.toString());
  $('#NumOfActivePassengers').html(num_active_passengers.toString());
  $('#PassengersLeft').html(passengers_left.toString());
  $('#ServedPassengers').html(served_passengers.toString());
};

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
  trailColor1: [173, 216, 230], // lightblue
  trailColor2: [0, 0, 139], // dark blue
  trailColor3: [144, 238, 144], // light green
  trailColor4: [0, 100, 0], // dark green
  material,
  effects: [lightingEffect]
};

const INITIAL_VIEW_STATE = {
  longitude: VIEWSTATE_COORDINATES[1],
  latitude: VIEWSTATE_COORDINATES[0],
  zoom: 12,
  pitch: 45,
  bearing: 0
};

const MAP_STYLE = 'https://basemaps.cartocdn.com/gl/positron-nolabels-gl-style/style.json';

function App({
  buildings = BUILDINGS,
  depot_locations = DEPOT_LOCATIONS,
  trips = TRIPS,
  missed_passengers = MISSED_PASSENGERS,
  waiting = WAITING,
  trailLength = 15,
  initialViewState = INITIAL_VIEW_STATE,
  mapStyle = MAP_STYLE,
  theme = DEFAULT_THEME,
  loopLength = LOOP_LENGTH, // unit corresponds to the timestamp in source data
  startingAnimationSpeed = ANIMATION_SPEED,
  startTime = START_TIME
}) {
  // States that decide which vehicle occupancy to show
  const [occupancyHideArray, setOccupancyHideArray] = useState([]);

  const [animationSpeed, setAnimationSpeed] = useState(startingAnimationSpeed);
  const [prevAnimationSpeed, setPrevAnimationSpeed] = useState(animationSpeed);
  const [time, setTime] = useState(startTime);
  updateTime(time);
  updateMetricAnimations(time);
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

  const depotLocations = depot_locations;
  const trailColors = [theme.trailColor0, theme.trailColor1, theme.trailColor2, theme.trailColor3, theme.trailColor4];
  const layers = [
    new TripsLayer({
      id: 'trips',
      data: trips,
      getPath: d => d.path,
      getTimestamps: d => d.timestamps,
      getColor: d => {
        let num = d.vendor;
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
    new PolygonLayer({
      id: 'buildings',
      data: buildings,
      extruded: true,
      wireframe: false,
      opacity: 0.5,
      getPolygon: f => f.polygon,
      getElevation: f => f.height,
      getFillColor: theme.buildingColor,
      material: theme.material,
      // Enable picking
      pickable: true
    }),
    new TextLayer({
      id: 'waiting_passengers',
      data: waiting[time],
      getPosition: d => depotLocations[d.c.split(" ")[0]],
      getText: d => d.c.split(" ")[1],
      getSize: 20,
      getColor: [255, 0, 0],
      getTextAnchor: 'start',
      getAlignmentBaseline: 'bottom',
      getPixelOffset: [5, 5],
      parameters: {depthTest: false}
    }),
    new TextLayer({
      id: 'waiting_vehicles',
      data: waiting[time],
      getPosition: d => depotLocations[d.c.split(" ")[0]],
      getText: d => d.c.split(" ")[2],
      getSize: 20,
      getColor: [79, 130, 247],
      getTextAnchor: 'end',
      getAlignmentBaseline: 'bottom',
      getPixelOffset: [-5, 5],
      parameters: {depthTest: false}
    }),
    new ScatterplotLayer({
      id: 'missed_passengers',
      data: missed_passengers[time],
      getPosition: d => depotLocations[d.c],
      getRadius: 100,
      filled: true,
      getFillColor: [255, 0, 0],
      opacity: 0.5,
      radiusMinPixels: 1,
      radiusMaxPixels: 200,
      parameters: {depthTest: false},
      pickable: true
    })
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
                  <span style={{background: '#ADD8E6'}}></span>One Passenger
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
      getTooltip={({object}) => object && object.m}
    >
      <StaticMap reuseMaps mapStyle={mapStyle} preventStyleDiffing={true} />
    </DeckGL>
    </div>
  );
};

export default App;
