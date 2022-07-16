/* global window */
import React, {useState, useEffect} from 'react';
import {render} from 'react-dom';
import {StaticMap} from 'react-map-gl';
import {AmbientLight, PointLight, LightingEffect} from '@deck.gl/core';
import DeckGL from '@deck.gl/react';
import {TripsLayer} from '@deck.gl/geo-layers';
import {IconLayer, GeoJsonLayer, TextLayer} from '@deck.gl/layers';

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

function updateMetricAnimations(time) {
  let timeframe_idx = (time - (time % TIME_STEP)).toString();

  let vehicles_moving = timeframe_metrics[timeframe_idx]["vehicles_moving"];
  $('#vehicles_moving').text(vehicles_moving.toLocaleString());

  let vehicles_with_pax_moving = timeframe_metrics[timeframe_idx]["vehicles_with_pax_moving"];
  $('#vehicles_with_pax_moving').text(vehicles_with_pax_moving.toLocaleString());

  let empty_vehicles_moving = timeframe_metrics[timeframe_idx]["empty_vehicles_moving"];
  $('#empty_vehicles_moving').text(empty_vehicles_moving.toLocaleString());

  let vehicles_not_moving = timeframe_metrics[timeframe_idx]["vehicles_not_moving"];
  $('#vehicles_not_moving').text(vehicles_not_moving.toLocaleString());

  let total_pax = timeframe_metrics[timeframe_idx]["total_pax"];
  $('#total_pax').text(total_pax.toLocaleString());

  let pax_moving = timeframe_metrics[timeframe_idx]["pax_moving"];
  $('#pax_moving').text(pax_moving.toLocaleString());

  let pax_waiting = timeframe_metrics[timeframe_idx]["pax_waiting"];
  $('#pax_waiting').text(pax_waiting.toLocaleString());

  let pax_served_running_total = timeframe_metrics[timeframe_idx]["pax_served_running_total"];
  $('#pax_served_running_total').text(pax_served_running_total.toLocaleString());

  let pax_missed_running_total = timeframe_metrics[timeframe_idx]["pax_missed_running_total"];
  $('#pax_missed_running_total').text(pax_missed_running_total.toLocaleString());
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
  trailColor1: [230, 140, 0], // orange/gold
  trailColor2: [200, 200, 0], // dark blue
  trailColor3: [60, 200, 0], // light green
  trailColor4: [0, 100, 0], // dark green
  material,
  effects: [lightingEffect]
};

const INITIAL_VIEW_STATE = {
  longitude: center_coordinates["lng"],
  latitude: center_coordinates["lat"],
  zoom: 12,
  pitch: 45,
  bearing: 0
};

const MAP_STYLE = 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json';

const ICON_MAPPING = {
  marker: {x: 0, y: 0, width: 512, height: 512, anchorY: 512}
};

function App({
  kiosks = KIOSKS,
  kiosk_metrics = KIOSK_METRICS,
  road_network = ROAD_NETWORK,
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

  const trailColors = [theme.trailColor0, theme.trailColor1, theme.trailColor2, theme.trailColor3, theme.trailColor4];
  const layers = [
    new GeoJsonLayer({
      id: 'road-network',
      data: road_network,
      pickable: false,
      lineWidthScale: 20,
      getLineWidth: 1,
      lineWidthMinPixels: 2,
      getLineColor: [169, 169, 169, 100],
      parameters: {depthTest: false}
    }),
    new IconLayer({
      id: 'icon-layer',
      data: kiosks,
      pickable: true,
      // iconAtlas and iconMapping are required
      // getIcon: return a string
      iconAtlas: '/static/assets/kiosk_clipart.png',
      iconMapping: ICON_MAPPING,
      getIcon: d => 'marker',

      sizeScale: 5,
      getPosition: d => d.coordinates,
      getSize: d => 5,
      sizeMinPixels: 20,
      sizeMaxPixels: 200,
      parameters: {depthTest: false}
    }),
    new TextLayer({
      id: 'vehicle-passenger-counts',
      data: kiosk_metrics[(time-(time%TIME_STEP)).toString()],
      pickable: false,
      fontFamily: 'monospace, Material Icons',
      characterSet: ['\ue559', '\ue7fd', '\uf233', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ',', '\n'],
      getPosition: d => d.c,
      getText: d => d.n + '\n' + d.v.toLocaleString() + '\ue559 ' + d.p.toLocaleString() + '\ue7fd ' + d.g.toLocaleString() + '\uf233',
      getSize: 10,
      getAngle: 0,
      getTextAnchor: 'middle',
      getAlignmentBaseline: 'top',
      parameters: {depthTest: false}
    }),
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
              setOccupancyHideArray(result);
            }} />
                <label for="zeroPax">
                  <span style={{background: 'rgb(255, 0, 0)'}}></span>Zero Passengers
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
              setOccupancyHideArray(result);
            }} />
                <label for="onePax">
                  <span style={{background: 'rgb(230, 140, 0)'}}></span>One Passenger
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
              setOccupancyHideArray(result);
            }} />
                <label for="twoPax">
                  <span style={{background: 'rgb(200, 200, 0)'}}></span>Two Passengers
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
              setOccupancyHideArray(result);
            }} />
                <label for="threePax">
                  <span style={{background: 'rgb(60, 200, 0)'}}></span>Three Passengers
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
              setOccupancyHideArray(result);
            }} />
                <label for="fourPax">
                  <span style={{background: 'rgb(0, 100, 0)'}}></span>Four Passengers
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
      getTooltip={({object}) => object && `${object.msg}`}
    >
      <StaticMap reuseMaps mapStyle={mapStyle} preventStyleDiffing={true} />
    </DeckGL>
    </div>
  );
};

export default App;
