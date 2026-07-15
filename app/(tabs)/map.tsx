import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import MapView, { Marker, Circle } from 'react-native-maps';
import { useLocationStore } from '../../store/useLocationStore';
import { Colors } from '../../constants/colors';

export default function MapScreen() {
  const result = useLocationStore((s) => s.currentResult);

  const initialRegion = result
    ? {
        latitude: result.coordinates.lat,
        longitude: result.coordinates.lon,
        latitudeDelta: 5,
        longitudeDelta: 5,
      }
    : { latitude: 22.5, longitude: 80, latitudeDelta: 20, longitudeDelta: 20 };

  return (
    <View style={styles.container}>
      <MapView style={styles.map} initialRegion={initialRegion}>
        {result && (
          <>
            <Marker
              coordinate={{ latitude: result.coordinates.lat, longitude: result.coordinates.lon }}
              title={result.name}
              description={`Zone ${result.seismicZone} · ${result.overallRisk} risk`}
            />
            <Circle
              center={{ latitude: result.coordinates.lat, longitude: result.coordinates.lon }}
              radius={300000}
              fillColor="rgba(24,95,165,0.08)"
              strokeColor="rgba(24,95,165,0.3)"
              strokeWidth={1}
            />
          </>
        )}
      </MapView>
      {!result && (
        <View style={styles.hint}>
          <Text style={styles.hintText}>Search a location first to see it on the map</Text>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  map: { flex: 1 },
  hint: {
    position: 'absolute', bottom: 30, left: 20, right: 20,
    backgroundColor: '#fff', borderRadius: 10, padding: 14,
    borderWidth: 0.5, borderColor: Colors.surface.border,
    alignItems: 'center',
  },
  hintText: { fontSize: 13, color: Colors.text.secondary },
});
