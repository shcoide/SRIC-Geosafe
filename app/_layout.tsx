import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { ErrorBoundary } from '../components/ErrorBoundary';

export default function RootLayout() {
  return (
    // react-native-gesture-handler is present in the dependency tree
    // (pulled in transitively, e.g. by react-native-screens/expo-router for
    // native-stack transition gestures) but this root wrapper was missing —
    // without it, RNGH can end up intercepting touches app-wide on Android
    // instead of just the screens that actually use it, which is why the
    // MapLibre MapView on the map tab wasn't receiving pan gestures. Must be
    // the outermost element per RNGH's own setup docs.
    <GestureHandlerRootView style={{ flex: 1 }}>
      <ErrorBoundary>
        <SafeAreaProvider>
          <StatusBar style="auto" />
          <Stack>
            <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
            <Stack.Screen
              name="results/[locationId]"
              options={{ title: 'Hazard overview', headerBackTitle: 'Back' }}
            />
            <Stack.Screen
              name="results/earthquake"
              options={{ title: 'Earthquake analysis', headerBackTitle: 'Back' }}
            />
            <Stack.Screen
              name="results/materials"
              options={{ title: 'Material recommendations', headerBackTitle: 'Back' }}
            />
            <Stack.Screen
              name="results/guidelines"
              options={{ title: 'Design guidelines', headerBackTitle: 'Back' }}
            />
          </Stack>
        </SafeAreaProvider>
      </ErrorBoundary>
    </GestureHandlerRootView>
  );
}
