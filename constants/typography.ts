import { Platform } from 'react-native';

export const Type = {
  // Risk level — the signature element, must be immediately legible
  riskDisplay: { fontSize: 36, fontWeight: '300' as const, letterSpacing: -0.5 },

  // Screen titles
  title:   { fontSize: 22, fontWeight: '500' as const, letterSpacing: -0.2 },

  // Section headings within screens
  heading: { fontSize: 15, fontWeight: '500' as const, letterSpacing: 0 },

  // Data labels (zone, PGA, etc)
  label:   { fontSize: 11, fontWeight: '400' as const, letterSpacing: 0.3 },

  // Body text — explanations, guideline text
  body:    { fontSize: 14, fontWeight: '400' as const, lineHeight: 22 },

  // Small body — reasons, subcopy
  bodySmall: { fontSize: 12, fontWeight: '400' as const, lineHeight: 18 },

  // Monospaced data values (coordinates, PGA values, Vs30)
  mono: { fontSize: 13, fontWeight: '400' as const, fontFamily: Platform.OS === 'ios' ? 'Menlo' : 'monospace' },

  // Source badge labels
  badge: { fontSize: 10, fontWeight: '500' as const, letterSpacing: 0.4 },
};
