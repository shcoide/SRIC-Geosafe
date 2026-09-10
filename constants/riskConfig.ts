import { Palette } from './colors';
import { SiteDataSource, HazardSource } from '../types';

export const RISK_COLORS = {
  'Low':       { bg: Palette.risk_low_bg,  border: Palette.risk_low_border,  text: Palette.risk_low_text,  dot: Palette.risk_low_dot },
  'Moderate':  { bg: Palette.risk_mod_bg,  border: Palette.risk_mod_border,  text: Palette.risk_mod_text,  dot: Palette.risk_mod_dot },
  'High':      { bg: Palette.risk_hi_bg,   border: Palette.risk_hi_border,   text: Palette.risk_hi_text,   dot: Palette.risk_hi_dot },
  'Very High': { bg: Palette.risk_vhi_bg,  border: Palette.risk_vhi_border,  text: Palette.risk_vhi_text,  dot: Palette.risk_vhi_dot },
};

// Provenance tiers, in decreasing order of confidence. The token system only
// names three source-confidence pairs (measured/interpolated/assumed) plus
// regional_bbox — the four gaps below (modeled, shapefile, approximate) are
// filled by grouping each with the nearest-confidence named tier rather than
// inventing new colours:
//  - "shapefile" (a real surveyed IS 1893 zone boundary) reads as trustworthy
//    as "measured" (a real calibrated survey point), so it shares that tier.
//  - "modeled" (a global raster) and "approximate" (a lat/lon zone bounding
//    box) both sit below "interpolated" in confidence, same as "assumed" and
//    "regional_bbox" — grouped with them rather than the closer-to-real-data
//    tiers above.
// `dot` is not part of the CoverageBadge redesign (background + text carry
// the badge; see the component) but stays populated here because
// app/(tabs)/map.tsx's coverage-polygon and calibrated-point circle colours
// are semantic map overlay colours, not decorative — they must keep reading
// as the same green->amber->ochre->red confidence gradient the app always
// used, so `dot` reuses the risk-scale dot colours at the equivalent tier.
export const SOURCE_COLORS: Record<SiteDataSource | HazardSource, { bg: string; text: string; dot: string }> = {
  measured:      { bg: Palette.src_measured_bg,      text: Palette.src_measured_text,      dot: Palette.risk_low_dot },
  interpolated:  { bg: Palette.src_interpolated_bg,  text: Palette.src_interpolated_text,  dot: Palette.risk_mod_dot },
  modeled:       { bg: Palette.src_assumed_bg,       text: Palette.src_assumed_text,       dot: Palette.risk_hi_dot },
  assumed:       { bg: Palette.src_assumed_bg,       text: Palette.src_assumed_text,       dot: Palette.risk_vhi_dot },
  shapefile:     { bg: Palette.src_measured_bg,      text: Palette.src_measured_text,      dot: Palette.risk_low_dot },
  approximate:   { bg: Palette.stone100,             text: Palette.stone500,               dot: Palette.risk_vhi_dot },
  regional_bbox: { bg: Palette.stone100,             text: Palette.stone500,               dot: Palette.risk_vhi_dot },
};

export const SOURCE_LABELS: Record<SiteDataSource | HazardSource, string> = {
  measured: 'Measured — calibrated survey point',
  interpolated: 'Interpolated — city-scale estimate',
  modeled: 'Modeled — global raster',
  assumed: 'Assumed — regional default',
  shapefile: 'Shapefile — surveyed zone boundary',
  approximate: 'Approximate — bounding-box zone rule',
  regional_bbox: 'Regional bounding box — location only, not surveyed',
};

// Same tiers as SOURCE_LABELS, condensed to 1-2 words for CoverageBadge's
// `compact` mode — small grid tiles (e.g. HazardCard) don't have room for
// the full sentence, but still need enough text that the confidence tier
// reads on its own, not just from background colour.
export const SOURCE_LABELS_COMPACT: Record<SiteDataSource | HazardSource, string> = {
  measured: 'Measured',
  interpolated: 'Interpolated',
  modeled: 'Modeled',
  assumed: 'Assumed',
  shapefile: 'Shapefile',
  approximate: 'Approximate',
  regional_bbox: 'Regional est.',
};

export const ZONE_LABELS: Record<string, string> = {
  II: 'Low seismic activity',
  III: 'Moderate seismic activity',
  IV: 'High seismic activity',
  V: 'Very high seismic activity',
};

export const ZONE_RISK: Record<string, string> = {
  II: 'Low',
  III: 'Moderate',
  IV: 'High',
  V: 'Very High',
};

export const HAZARD_ICONS: Record<string, string> = {
  earthquake: 'alert-circle',
  flood: 'water',
  landslide: 'terrain',
  cyclone: 'weather-windy',
};
