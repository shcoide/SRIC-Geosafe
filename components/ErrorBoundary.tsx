import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { Colors, Palette } from '../constants/colors';
import { RISK_COLORS } from '../constants/riskConfig';
import { Type } from '../constants/typography';
import { Space, Radius } from '../constants/spacing';
import { getLastAnalyzeRequest } from '../services/api';

interface Props {
  children: React.ReactNode;
}

interface State {
  error: Error | null;
}

// React's componentStack is a multi-line string like:
//   "\n    in HazardCard (created by ResultsScreen)\n    in View (created by ...)"
// The first "in X" names the component the error actually originated in —
// exactly what's needed to tell "which screen crashed" apart from "the app
// crashed", which is otherwise not derivable from error.message alone.
const extractComponentName = (componentStack: string): string => {
  const match = componentStack.trim().match(/^in (\S+)/);
  return match ? match[1] : 'unknown';
};

export class ErrorBoundary extends React.Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    // This app has no crash-reporting SDK (deliberately — see README); this
    // is a research prototype, and the frontend runs on a user's own
    // device, not on Render, so this line lands in the Metro/device
    // console, not Render's log viewer (only the backend's GEOSAFE_ERROR
    // lines do — see backend/main.py). The [GEOSAFE_CRASH] prefix and flat
    // key=value shape keep it grep-able wherever it's read from, and
    // including the last analyzeLocation() request (if any) means a report
    // of "it crashed" carries enough context to debug without asking the
    // user to reproduce it.
    const componentStack = info.componentStack ?? '';
    const component = extractComponentName(componentStack);
    const lastAnalyzeRequest = getLastAnalyzeRequest();
    console.error(
      `[GEOSAFE_CRASH] component=${component} message=${JSON.stringify(error.message)} ` +
      `lastAnalyzeRequest=${JSON.stringify(lastAnalyzeRequest)} stack=${JSON.stringify(componentStack)}`
    );
  }

  handleReset = () => this.setState({ error: null });

  render() {
    if (this.state.error) {
      return (
        <View style={styles.container}>
          <MaterialCommunityIcons name="alert-circle-outline" size={40} color={RISK_COLORS['Very High'].dot} />
          <Text style={styles.title}>Something went wrong</Text>
          <Text style={styles.message}>{this.state.error.message || 'An unexpected error occurred.'}</Text>
          <TouchableOpacity style={styles.actionBtn} onPress={this.handleReset}>
            <Text style={styles.actionBtnText}>Try again</Text>
          </TouchableOpacity>
        </View>
      );
    }
    return this.props.children;
  }
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: Space.lg + 8,
    backgroundColor: Palette.white,
    gap: Space.sm - 2,
  },
  title: { ...Type.heading, color: Colors.textPrimary, marginTop: Space.sm + 2 },
  message: { ...Type.bodySmall, color: Colors.textSecondary, textAlign: 'center' },
  actionBtn: {
    marginTop: Space.sm + 6,
    borderWidth: 1,
    borderColor: Colors.primaryBorder,
    borderRadius: Radius.md,
    paddingHorizontal: Space.lg - 6,
    paddingVertical: Space.sm + 4,
    backgroundColor: Colors.primaryLight,
  },
  actionBtnText: { ...Type.bodySmall, fontWeight: '500', color: Colors.primary },
});
