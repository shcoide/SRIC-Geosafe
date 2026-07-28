import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { LocationResult, SearchResult } from '../types';

interface LocationStore {
  currentResult: LocationResult | null;
  recentSearches: SearchResult[];
  loading: boolean;
  error: string | null;
  setCurrentResult: (result: LocationResult) => void;
  addRecentSearch: (search: SearchResult) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  clearError: () => void;
}

export const useLocationStore = create<LocationStore>()(
  persist(
    (set) => ({
      currentResult: null,
      recentSearches: [],
      loading: false,
      error: null,

      setCurrentResult: (result) => set({ currentResult: result }),

      addRecentSearch: (search) =>
        set((state) => ({
          recentSearches: [
            search,
            ...state.recentSearches.filter((s) => s.name !== search.name),
          ].slice(0, 10),
        })),

      setLoading: (loading) => set({ loading }),
      setError: (error) => set({ error }),
      clearError: () => set({ error: null }),
    }),
    {
      name: 'geosafe-location-store',
      storage: createJSONStorage(() => AsyncStorage),
      partialize: (state) => ({ recentSearches: state.recentSearches }),
    }
  )
);
