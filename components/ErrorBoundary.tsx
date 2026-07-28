import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { Colors } from '../constants/colors';

interface Props {
  children: React.ReactNode;
}

interface State {
  error: Error | null;
}

export class ErrorBoundary extends React.Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error('Unhandled error caught by ErrorBoundary:', error, info.componentStack);
  }

  handleReset = () => this.setState({ error: null });

  render() {
    if (this.state.error) {
      return (
        <View style={styles.container}>
          <MaterialCommunityIcons name="alert-circle-outline" size={40} color={Colors.risk.veryHigh.dot} />
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
    paddingHorizontal: 32,
    backgroundColor: '#fff',
    gap: 6,
  },
  title: { fontSize: 16, fontWeight: '500', color: Colors.text.primary, marginTop: 10 },
  message: { fontSize: 13, color: Colors.text.secondary, textAlign: 'center', lineHeight: 20 },
  actionBtn: {
    marginTop: 14,
    borderWidth: 0.5,
    borderColor: Colors.primaryBorder,
    borderRadius: 10,
    paddingHorizontal: 18,
    paddingVertical: 12,
    backgroundColor: Colors.primaryLight,
  },
  actionBtnText: { fontSize: 13, fontWeight: '500', color: Colors.primary },
});
