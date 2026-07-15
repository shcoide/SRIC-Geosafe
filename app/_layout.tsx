import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';

export default function RootLayout() {
  return (
    <>
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
    </>
  );
}
