import React from 'react';
import { View, Text, ActivityIndicator, StyleSheet } from 'react-native';
import { Colors } from '../constants/colors';

interface Props {
  message?: string;
}

export const LoadingOverlay: React.FC<Props> = ({ message = 'Analysing location…' }) => (
  <View style={styles.container}>
    <ActivityIndicator size="large" color={Colors.primary} />
    <Text style={styles.text}>{message}</Text>
  </View>
);

const styles = StyleSheet.create({
  container: { alignItems: 'center', justifyContent: 'center', paddingVertical: 60, gap: 14 },
  text: { fontSize: 14, color: Colors.text.secondary },
});
