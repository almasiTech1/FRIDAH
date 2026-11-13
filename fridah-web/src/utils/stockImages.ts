/**
 * Curated real-estate photography for FRIDAH's public site.
 *
 * All images are hosted on Unsplash's CDN under the Unsplash License (free for
 * commercial use, no attribution required - https://unsplash.com/license). They are
 * used as a graceful fallback for property/listing cards that have no uploaded photo
 * yet (e.g. demo data, or a listing whose owner hasn't added photos). Real uploaded
 * photos from propertiesApi/bookingsApi always take priority; this is only the fallback.
 *
 * unsplashUrl() appends Unsplash's own image-transform params so we only request the
 * resolution we actually display.
 */

export function unsplashUrl(id: string, width: number, quality = 75): string {
  return `https://images.unsplash.com/${id}?auto=format&fit=crop&w=${width}&q=${quality}`
}

export const houseExteriors = [
  'photo-1721815693498-cc28507c0ba2',
  'photo-1628012209120-d9db7abf7eab',
  'photo-1698994705178-d244d73ea573',
  'photo-1600596542815-ffad4c1539a9',
  'photo-1633354747567-e0682586f082',
  'photo-1719887805632-de5be825f72b',
  'photo-1580587771525-78b9dba3b914',
  'photo-1691425700585-c108acad6467',
  'photo-1627141234469-24711efb373c',
  'photo-1660361339436-ddd4b85372da',
  'photo-1523217582562-09d0def993a6',
]

export const livingInteriors = [
  'photo-1522708323590-d24dbb6b0267',
  'photo-1564078516393-cf04bd966897',
  'photo-1628592102751-ba83b0314276',
  'photo-1665249934445-1de680641f50',
  'photo-1738168279272-c08d6dd22002',
  'photo-1560448204-e02f11c3d0e2',
  'photo-1606074280798-2dabb75ce10c',
  'photo-1502672260266-1c1ef2d93688',
]

export const kitchens = [
  'photo-1675279200694-8529c73b1fd0',
  'photo-1689043528099-2ba014dd7c64',
  'photo-1618221469555-7f3ad97540d6',
]

export const hotelRooms = [
  'photo-1618773928121-c32242e63f39',
  'photo-1611892440504-42a792e24d32',
  'photo-1629140727571-9b5c6f6267b4',
  'photo-1631049307264-da0ec9d70304',
  'photo-1711059985570-4c32ed12a12c',
  'photo-1582719478250-c89cae4dc85b',
  'photo-1667125095636-dce94dcbdd96',
]

/** Deterministic pick: the same id always maps to the same image (no flicker on re-render). */
function pickFor(pool: string[], seed: string, width: number): string {
  let hash = 0
  for (let i = 0; i < seed.length; i++) hash = (hash * 31 + seed.charCodeAt(i)) >>> 0
  return unsplashUrl(pool[hash % pool.length], width)
}

/** Fallback photo for a rental property card/hero with no uploaded image yet. */
export function propertyFallbackImage(propertyId: string, width = 800): string {
  return pickFor(houseExteriors, propertyId, width)
}

/** Fallback photo for a hotel/short-stay listing card/hero with no uploaded image yet. */
export function listingFallbackImage(listingId: string, width = 800): string {
  return pickFor(hotelRooms, listingId, width)
}

/** Several distinct fallback photos for a detail-page gallery (exterior, living, kitchen, room). */
export function galleryFallbackImages(seed: string, kind: 'property' | 'listing', width = 1200): string[] {
  if (kind === 'listing') {
    return [0, 1, 2, 3].map((i) => pickFor(hotelRooms, `${seed}-${i}`, width))
  }
  return [
    pickFor(houseExteriors, seed, width),
    pickFor(livingInteriors, `${seed}-a`, width),
    pickFor(kitchens, `${seed}-b`, width),
    pickFor(livingInteriors, `${seed}-c`, width),
  ]
}
