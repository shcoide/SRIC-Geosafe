export const Palette = {
  // Base surfaces — warm stone, not clinical white
  stone50:  '#F7F5F1',   // page background
  stone100: '#EDEAE4',   // card / panel background
  stone200: '#DDD9D1',   // subtle border
  stone300: '#C4BFB5',   // divider lines
  stone400: '#9A9388',   // muted text
  stone500: '#6B6560',   // secondary text
  stone900: '#1C1917',   // primary text — warm near-black, not cold

  // Instrument blue — the primary brand colour
  blue50:  '#EBF2FB',
  blue100: '#C9DEFA',
  blue500: '#2563A8',   // primary actions, links
  blue600: '#1A4F8C',   // pressed states
  blue900: '#0F2E52',   // dark blue text on light

  // Risk scale — geological hazard convention
  // Low: measured slate — calm, not dismissive
  risk_low_bg:     '#EEF2EE',
  risk_low_border: '#9AB89A',
  risk_low_text:   '#2D4A2D',
  risk_low_dot:    '#4A7C4A',

  // Moderate: warm amber — notable, not alarming
  risk_mod_bg:     '#FBF4E8',
  risk_mod_border: '#D4A843',
  risk_mod_text:   '#5C3D0A',
  risk_mod_dot:    '#B8860B',

  // High: deep ochre — serious
  risk_hi_bg:      '#FBF0E8',
  risk_hi_border:  '#C47A35',
  risk_hi_text:    '#5C2E08',
  risk_hi_dot:     '#A0521A',

  // Very High: deep red — not garish, not orange
  risk_vhi_bg:     '#F9EDED',
  risk_vhi_border: '#B03A3A',
  risk_vhi_text:   '#5C1A1A',
  risk_vhi_dot:    '#8B2020',

  // Source confidence tiers — semantic, not decorative
  src_measured_bg:      '#EBF5F0',
  src_measured_text:    '#1A4A32',
  src_interpolated_bg:  '#EBF2FB',
  src_interpolated_text:'#0F2E52',
  src_assumed_bg:       '#F5F0EB',
  src_assumed_text:     '#4A3520',

  white: '#FFFFFF',
};

export const Colors = {
  background: Palette.stone50,
  surface:    Palette.stone100,
  border:     Palette.stone200,
  divider:    Palette.stone300,
  textMuted:  Palette.stone400,
  textSecondary: Palette.stone500,
  textPrimary:   Palette.stone900,
  primary:    Palette.blue500,
  primaryDark: Palette.blue600,
  primaryLight: Palette.blue50,
  primaryBorder: Palette.blue100,
};
