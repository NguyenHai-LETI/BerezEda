export interface PlaceSuggestion {
  place_id: string;
  description: string;
}

export async function getPlaceSuggestions(input: string): Promise<PlaceSuggestion[]> {
  if (input.length < 2) return [];
  try {
    const res = await fetch(`/api/places?action=autocomplete&input=${encodeURIComponent(input)}`);
    const data = await res.json();
    return data.predictions || [];
  } catch {
    return [];
  }
}

export async function getPlaceDetails(placeId: string): Promise<{ lat: number; lng: number; address: string } | null> {
  try {
    const res = await fetch(`/api/places?action=details&place_id=${encodeURIComponent(placeId)}`);
    const data = await res.json();
    if (data.lat !== undefined) return data;
    return null;
  } catch {
    return null;
  }
}

export async function reverseGeocode(lat: number, lng: number): Promise<string> {
  try {
    const res = await fetch(`/api/places?action=geocode&lat=${lat}&lng=${lng}`);
    const data = await res.json();
    return data.address || '';
  } catch {
    return '';
  }
}
