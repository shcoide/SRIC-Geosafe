import React from 'react';
import { View, TextInput, TouchableOpacity, StyleSheet, Text } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { Colors } from '../constants/colors';

interface Props {
  value: string;
  onChangeText: (text: string) => void;
  onGpsPress: () => void;
  loading?: boolean;
}

export const SearchBar: React.FC<Props> = ({ value, onChangeText, onGpsPress, loading }) => (
  <View style={styles.wrapper}>
    <View style={styles.inputRow}>
      <MaterialCommunityIcons name="magnify" size={18} color={Colors.text.muted} />
      <TextInput
        style={styles.input}
        value={value}
        onChangeText={onChangeText}
        placeholder="Search city, district…"
        placeholderTextColor={Colors.text.muted}
        returnKeyType="search"
        autoCorrect={false}
      />
    </View>
    <TouchableOpacity style={styles.gpsBtn} onPress={onGpsPress} disabled={loading}>
      <MaterialCommunityIcons
        name="crosshairs-gps"
        size={16}
        color={Colors.primary}
      />
      <Text style={styles.gpsBtnText}>Use GPS</Text>
    </TouchableOpacity>
  </View>
);

const styles = StyleSheet.create({
  wrapper: { gap: 8, marginBottom: 16 },
  inputRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    backgroundColor: Colors.surface.secondary,
    borderRadius: 10,
    borderWidth: 0.5,
    borderColor: Colors.surface.border,
    paddingHorizontal: 12,
    paddingVertical: 10,
  },
  input: { flex: 1, fontSize: 14, color: Colors.text.primary },
  gpsBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    backgroundColor: Colors.primaryLight,
    borderWidth: 0.5,
    borderColor: Colors.primaryBorder,
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: 10,
  },
  gpsBtnText: { fontSize: 13, fontWeight: '500', color: Colors.primary },
});
