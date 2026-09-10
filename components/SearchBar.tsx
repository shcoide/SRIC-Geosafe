import React from 'react';
import { View, TextInput, TouchableOpacity, StyleSheet, Text } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { Colors, Palette } from '../constants/colors';
import { Type } from '../constants/typography';
import { Space, Radius } from '../constants/spacing';

interface Props {
  value: string;
  onChangeText: (text: string) => void;
  onGpsPress: () => void;
  loading?: boolean;
}

export const SearchBar: React.FC<Props> = ({ value, onChangeText, onGpsPress, loading }) => (
  <View style={styles.wrapper}>
    <View style={styles.inputRow}>
      <MaterialCommunityIcons name="magnify" size={18} color={Colors.textMuted} />
      <TextInput
        style={styles.input}
        value={value}
        onChangeText={onChangeText}
        placeholder="Search city, district…"
        placeholderTextColor={Colors.textMuted}
        returnKeyType="search"
        autoCorrect={false}
      />
    </View>
    <TouchableOpacity style={styles.gpsBtn} onPress={onGpsPress} disabled={loading}>
      <MaterialCommunityIcons name="crosshairs-gps" size={14} color={Colors.primary} />
      <Text style={styles.gpsBtnText}>Use my location</Text>
    </TouchableOpacity>
  </View>
);

const styles = StyleSheet.create({
  wrapper: { gap: Space.sm, marginBottom: Space.md },
  inputRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Space.sm,
    backgroundColor: Palette.white,
    borderRadius: Radius.md,
    borderWidth: 1,
    borderColor: Colors.border,
    paddingHorizontal: Space.md,
    paddingVertical: Space.sm + 2,
  },
  input: { ...Type.body, flex: 1, color: Colors.textPrimary },
  gpsBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Space.xs,
    alignSelf: 'flex-start',
  },
  gpsBtnText: { ...Type.bodySmall, fontWeight: '500', color: Colors.primary },
});
