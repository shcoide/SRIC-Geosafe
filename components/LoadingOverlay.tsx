import React, { useState } from 'react';
import { View, Text, ActivityIndicator, StyleSheet } from 'react-native';
import { Colors } from '../constants/colors';
import { Type } from '../constants/typography';
import { Space } from '../constants/spacing';
import { useSlowRequest } from '../hooks/useSlowRequest';
import { SLOW_REQUEST_THRESHOLD_MS, isBackendWarmed } from '../services/api';

interface Props {
  message?: string;
  slowMessage?: string;
}

export const LoadingOverlay: React.FC<Props> = ({
  message = 'Analysing location…',
  slowMessage = 'Waking up the server — first request after a while can take up to a minute…',
}) => {
  // This component only ever mounts while its caller's request is in
  // flight, so "always active" is the right signal — the timer restarts
  // fresh every time a new request begins.
  const isSlow = useSlowRequest(true, SLOW_REQUEST_THRESHOLD_MS);

  // Snapshotted once, at mount — not read live — so the decision made for
  // *this* request stays fixed even though isBackendWarmed() itself flips
  // to true the instant this request's response arrives (which happens
  // right before this component unmounts anyway). Only the first request
  // of the session, made while the backend hasn't proven itself awake yet,
  // is plausibly a cold start; every later slow request just gets the
  // plain message, not a repeated (and by then likely wrong) cold-start
  // explanation.
  const [wasLikelyColdStart] = useState(() => !isBackendWarmed());

  return (
    <View style={styles.container}>
      <ActivityIndicator size="large" color={Colors.primary} />
      <Text style={styles.text}>{isSlow && wasLikelyColdStart ? slowMessage : message}</Text>
    </View>
  );
};

const styles = StyleSheet.create({
  container: { alignItems: 'center', justifyContent: 'center', paddingVertical: Space.xl + Space.lg + 4, gap: Space.md - 2 },
  text: { ...Type.body, color: Colors.textSecondary },
});
