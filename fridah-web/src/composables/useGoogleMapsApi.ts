import { setOptions, importLibrary } from '@googlemaps/js-api-loader'

let optionsSet = false
let placesPromise: Promise<google.maps.PlacesLibrary> | null = null
let geometryPromise: Promise<google.maps.GeometryLibrary> | null = null

function ensureOptionsSet() {
  if (optionsSet) return
  const apiKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY as string | undefined
  if (!apiKey) return
  setOptions({ key: apiKey })
  optionsSet = true
}

/** Loads the Places library once, shared across every caller (Autocomplete widgets, etc). */
export function usePlacesLibrary(): Promise<google.maps.PlacesLibrary> | null {
  const apiKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY as string | undefined
  if (!apiKey) return null
  ensureOptionsSet()
  if (!placesPromise) placesPromise = importLibrary('places')
  return placesPromise
}

/** Loads the Geometry library once, used for distance calculations ("near me" sorting). */
export function useGeometryLibrary(): Promise<google.maps.GeometryLibrary> | null {
  const apiKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY as string | undefined
  if (!apiKey) return null
  ensureOptionsSet()
  if (!geometryPromise) geometryPromise = importLibrary('geometry')
  return geometryPromise
}

export function hasGoogleMapsApiKey(): boolean {
  return Boolean(import.meta.env.VITE_GOOGLE_MAPS_API_KEY)
}
