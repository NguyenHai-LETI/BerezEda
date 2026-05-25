import { NextRequest, NextResponse } from 'next/server';

const API_KEY = process.env.NEXT_PUBLIC_GOOGLE_MAPS_KEY || '';

// GET /api/places?action=autocomplete&input=...
// GET /api/places?action=details&place_id=...
// GET /api/places?action=geocode&lat=...&lng=...
export async function GET(req: NextRequest) {
  const { searchParams } = req.nextUrl;
  const action = searchParams.get('action');

  if (!API_KEY) {
    return NextResponse.json({ error: 'No API key' }, { status: 500 });
  }

  try {
    if (action === 'autocomplete') {
      const input = searchParams.get('input') || '';
      if (input.length < 2) return NextResponse.json({ predictions: [] });
      const url = `https://maps.googleapis.com/maps/api/place/autocomplete/json?input=${encodeURIComponent(input)}&key=${API_KEY}&language=ru`;
      const res = await fetch(url);
      const data = await res.json();
      return NextResponse.json({
        predictions: (data.predictions || []).map((p: any) => ({
          place_id: p.place_id,
          description: p.description,
        })),
      });
    }

    if (action === 'details') {
      const placeId = searchParams.get('place_id') || '';
      const url = `https://maps.googleapis.com/maps/api/place/details/json?place_id=${placeId}&fields=geometry,formatted_address&key=${API_KEY}&language=ru`;
      const res = await fetch(url);
      const data = await res.json();
      if (data.status === 'OK' && data.result?.geometry?.location) {
        return NextResponse.json({
          lat: data.result.geometry.location.lat,
          lng: data.result.geometry.location.lng,
          address: data.result.formatted_address || '',
        });
      }
      return NextResponse.json({ error: 'Not found' }, { status: 404 });
    }

    if (action === 'geocode') {
      const lat = searchParams.get('lat');
      const lng = searchParams.get('lng');
      // Use OpenStreetMap Nominatim — free, no billing required
      const url = `https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lng}&format=json&accept-language=ru`;
      const res = await fetch(url, {
        headers: { 'User-Agent': 'BerezhEda-App/1.0' },
      });
      const data = await res.json();
      if (data.display_name) {
        return NextResponse.json({ address: data.display_name });
      }
      return NextResponse.json({ address: '' });
    }

    return NextResponse.json({ error: 'Invalid action' }, { status: 400 });
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
