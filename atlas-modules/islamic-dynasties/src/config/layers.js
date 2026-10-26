/* ═══ Layer Configuration ═══ */

export const LAYER_KEYS = ['dynasties', 'battles', 'events', 'scholars', 'monuments', 'cities', 'routes', 'rulers', 'madrasas', 'salibiyyat'];

export const FILTER_KEYS = ['religion', 'ethnic', 'government', 'period', 'zone'];

export const DEFAULT_LAYERS = {
  dynasties: true, battles: true, events: true,
  scholars: true, monuments: true, cities: true, routes: true, rulers: true, madrasas: true, salibiyyat: true
};

export const DEFAULT_FILTERS = {
  religion: '', ethnic: '', government: '', period: '', zone: ''
};

const IS_OFFLINE_OR_FILE =
  typeof window !== 'undefined' &&
  (window.location.protocol === 'file:' || (typeof navigator !== 'undefined' && navigator.onLine === false));

const OFFLINE_DARK_TILE =
  "data:image/svg+xml;utf8," +
  encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256"><rect width="256" height="256" fill="#0b1220"/><path d="M0 0h256v256H0z" fill="none" stroke="rgba(201,168,76,0.09)" stroke-width="1"/></svg>'
  );

const OFFLINE_LIGHT_TILE =
  "data:image/svg+xml;utf8," +
  encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256"><rect width="256" height="256" fill="#f3ede0"/><path d="M0 0h256v256H0z" fill="none" stroke="rgba(120,95,55,0.12)" stroke-width="1"/></svg>'
  );

export const MAP_CONFIG = {
  center: [30, 42],
  zoom: 4,
  minZoom: 3,
  maxZoom: 10,
  tileUrl: IS_OFFLINE_OR_FILE ? OFFLINE_DARK_TILE : 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
  tileUrlLight: IS_OFFLINE_OR_FILE ? OFFLINE_LIGHT_TILE : 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
};
