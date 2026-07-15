import axios from 'axios';
import { SearchResult } from '../types';

const OPENCAGE_KEY = process.env.EXPO_PUBLIC_OPENCAGE_KEY || 'demo';
const BASE = 'https://api.opencagedata.com/geocode/v1/json';

export const searchLocations = async (query: string): Promise<SearchResult[]> => {
  if (query.length < 3) return [];

  try {
    const response = await axios.get(BASE, {
      params: {
        q: query,
        key: OPENCAGE_KEY,
        limit: 5,
        no_annotations: 1,
        countrycode: 'in',
      },
    });

    return response.data.results.map((r: any) => ({
      name: r.components.city || r.components.town || r.components.state || query,
      displayName: r.formatted,
      lat: r.geometry.lat,
      lon: r.geometry.lng,
    }));
  } catch {
    return [{
      name: query,
      displayName: query + ', India',
      lat: 20.5937,
      lon: 78.9629,
    }];
  }
};
