import { useState, useEffect, useRef, useCallback, useMemo } from "react";
import * as d3 from "d3";

// ─── DEMO DATA ─────────────────────────────────────────────────────────────
// Replace this block with: const DEMO_DATA = <contents of frontend_data.json>
const DEMO_DATA = {
  metadata: {
    total_companies: 6, total_streams: 24, total_candidates: 18,
    unique_company_pairs: 9, min_score_threshold: 0.15,
  },
  companies: [
    { company_id: "C001", name: "Acme Steel", sector: "Metallurgy", location: "Zone A" },
    { company_id: "C002", name: "GreenChem", sector: "Chemicals", location: "Zone B" },
    { company_id: "C003", name: "EcoCement", sector: "Building Materials", location: "Zone A" },
    { company_id: "C004", name: "BioFuel Co", sector: "Energy", location: "Zone C" },
    { company_id: "C005", name: "AquaPure", sector: "Water Treatment", location: "Zone B" },
    { company_id: "C006", name: "PolymerTech", sector: "Plastics", location: "Zone C" },
  ],
  streams: [
    { stream_id: "S001", company_id: "C001", stream_name: "Iron Ore Feed", stream_type: "raw_material", direction: "input", flow_kton_per_year: 850, temperature_c: 25, pressure_bar: 1, composition_raw: "Fe2O3 (92%), SiO2 (5%), Al2O3 (3%)", components: [{ component_id: "CM001", name: "Fe2O3", category: "oxide", fraction: 0.92, is_trace: 0, hazardous: 0 }, { component_id: "CM002", name: "SiO2", category: "oxide", fraction: 0.05, is_trace: 0, hazardous: 0 }, { component_id: "CM003", name: "Al2O3", category: "oxide", fraction: 0.03, is_trace: 0, hazardous: 0 }] },
    { stream_id: "S002", company_id: "C001", stream_name: "Blast Furnace Slag", stream_type: "waste", direction: "output", flow_kton_per_year: 280, temperature_c: 1400, pressure_bar: 1, composition_raw: "CaO (40%), SiO2 (35%), Al2O3 (15%), MgO (10%)", components: [{ component_id: "CM004", name: "CaO", category: "oxide", fraction: 0.40, is_trace: 0, hazardous: 0 }, { component_id: "CM002", name: "SiO2", category: "oxide", fraction: 0.35, is_trace: 0, hazardous: 0 }, { component_id: "CM003", name: "Al2O3", category: "oxide", fraction: 0.15, is_trace: 0, hazardous: 0 }, { component_id: "CM005", name: "MgO", category: "oxide", fraction: 0.10, is_trace: 0, hazardous: 0 }] },
    { stream_id: "S003", company_id: "C001", stream_name: "Blast Furnace Gas", stream_type: "waste", direction: "output", flow_kton_per_year: 120, temperature_c: 200, pressure_bar: 1.5, composition_raw: "N2 (55%), CO (25%), CO2 (18%), H2 (2%)", components: [{ component_id: "CM006", name: "N2", category: "other", fraction: 0.55, is_trace: 0, hazardous: 0 }, { component_id: "CM007", name: "CO", category: "other", fraction: 0.25, is_trace: 0, hazardous: 1 }, { component_id: "CM008", name: "CO2", category: "other", fraction: 0.18, is_trace: 0, hazardous: 0 }, { component_id: "CM009", name: "H2", category: "other", fraction: 0.02, is_trace: 0, hazardous: 0 }] },
    { stream_id: "S004", company_id: "C001", stream_name: "Steel Product", stream_type: "product", direction: "output", flow_kton_per_year: 600, temperature_c: 900, pressure_bar: 1, composition_raw: "Fe (98%), C (1.5%), Mn (0.5%)", components: [{ component_id: "CM010", name: "Fe", category: "metal", fraction: 0.98, is_trace: 0, hazardous: 0 }, { component_id: "CM011", name: "C", category: "other", fraction: 0.015, is_trace: 0, hazardous: 0 }, { component_id: "CM012", name: "Mn", category: "metal", fraction: 0.005, is_trace: 0, hazardous: 0 }] },
    { stream_id: "S005", company_id: "C002", stream_name: "Methanol Feed", stream_type: "raw_material", direction: "input", flow_kton_per_year: 45, temperature_c: 25, pressure_bar: 1, composition_raw: "CH3OH (99.5%), H2O (0.5%)", components: [{ component_id: "CM013", name: "CH3OH", category: "organic", fraction: 0.995, is_trace: 0, hazardous: 1 }, { component_id: "CM014", name: "H2O", category: "other", fraction: 0.005, is_trace: 0, hazardous: 0 }] },
    { stream_id: "S006", company_id: "C002", stream_name: "CO2 Feed", stream_type: "raw_material", direction: "input", flow_kton_per_year: 30, temperature_c: 25, pressure_bar: 10, composition_raw: "CO2 (99%), N2 (1%)", components: [{ component_id: "CM008", name: "CO2", category: "other", fraction: 0.99, is_trace: 0, hazardous: 0 }, { component_id: "CM006", name: "N2", category: "other", fraction: 0.01, is_trace: 0, hazardous: 0 }] },
    { stream_id: "S007", company_id: "C002", stream_name: "Formaldehyde Product", stream_type: "product", direction: "output", flow_kton_per_year: 35, temperature_c: 40, pressure_bar: 1, composition_raw: "HCHO (37%), H2O (52%), CH3OH (11%)", components: [{ component_id: "CM015", name: "HCHO", category: "organic", fraction: 0.37, is_trace: 0, hazardous: 1 }, { component_id: "CM014", name: "H2O", category: "other", fraction: 0.52, is_trace: 0, hazardous: 0 }, { component_id: "CM013", name: "CH3OH", category: "organic", fraction: 0.11, is_trace: 0, hazardous: 1 }] },
    { stream_id: "S008", company_id: "C002", stream_name: "Wastewater", stream_type: "waste", direction: "output", flow_kton_per_year: 15, temperature_c: 35, pressure_bar: 1, composition_raw: "H2O (97%), CH3OH (2%), HCHO (trace)", components: [{ component_id: "CM014", name: "H2O", category: "other", fraction: 0.97, is_trace: 0, hazardous: 0 }, { component_id: "CM013", name: "CH3OH", category: "organic", fraction: 0.02, is_trace: 0, hazardous: 1 }, { component_id: "CM015", name: "HCHO", category: "organic", fraction: 0, is_trace: 1, hazardous: 1 }] },
    { stream_id: "S009", company_id: "C003", stream_name: "Calcium Silicate Feed", stream_type: "raw_material", direction: "input", flow_kton_per_year: 400, temperature_c: 25, pressure_bar: 1, composition_raw: "CaO (42%), SiO2 (33%), Al2O3 (15%), MgO (6%), Fe2O3 (4%)", components: [{ component_id: "CM004", name: "CaO", category: "oxide", fraction: 0.42, is_trace: 0, hazardous: 0 }, { component_id: "CM002", name: "SiO2", category: "oxide", fraction: 0.33, is_trace: 0, hazardous: 0 }, { component_id: "CM003", name: "Al2O3", category: "oxide", fraction: 0.15, is_trace: 0, hazardous: 0 }, { component_id: "CM005", name: "MgO", category: "oxide", fraction: 0.06, is_trace: 0, hazardous: 0 }, { component_id: "CM001", name: "Fe2O3", category: "oxide", fraction: 0.04, is_trace: 0, hazardous: 0 }] },
    { stream_id: "S010", company_id: "C003", stream_name: "Cement Product", stream_type: "product", direction: "output", flow_kton_per_year: 500, temperature_c: 60, pressure_bar: 1, composition_raw: "CaO (63%), SiO2 (22%), Al2O3 (6%), Fe2O3 (3%), MgO (2%), SO3 (3%)", components: [{ component_id: "CM004", name: "CaO", category: "oxide", fraction: 0.63, is_trace: 0, hazardous: 0 }, { component_id: "CM002", name: "SiO2", category: "oxide", fraction: 0.22, is_trace: 0, hazardous: 0 }, { component_id: "CM003", name: "Al2O3", category: "oxide", fraction: 0.06, is_trace: 0, hazardous: 0 }, { component_id: "CM001", name: "Fe2O3", category: "oxide", fraction: 0.03, is_trace: 0, hazardous: 0 }, { component_id: "CM005", name: "MgO", category: "oxide", fraction: 0.02, is_trace: 0, hazardous: 0 }, { component_id: "CM016", name: "SO3", category: "sulfate", fraction: 0.03, is_trace: 0, hazardous: 0 }] },
    { stream_id: "S011", company_id: "C003", stream_name: "Kiln CO2 Exhaust", stream_type: "waste", direction: "output", flow_kton_per_year: 320, temperature_c: 350, pressure_bar: 1, composition_raw: "CO2 (25%), N2 (65%), H2O (8%), SO2 (trace)", components: [{ component_id: "CM008", name: "CO2", category: "other", fraction: 0.25, is_trace: 0, hazardous: 0 }, { component_id: "CM006", name: "N2", category: "other", fraction: 0.65, is_trace: 0, hazardous: 0 }, { component_id: "CM014", name: "H2O", category: "other", fraction: 0.08, is_trace: 0, hazardous: 0 }, { component_id: "CM017", name: "SO2", category: "other", fraction: 0, is_trace: 1, hazardous: 1 }] },
    { stream_id: "S012", company_id: "C004", stream_name: "Biomass Feed", stream_type: "raw_material", direction: "input", flow_kton_per_year: 200, temperature_c: 25, pressure_bar: 1, composition_raw: "Cellulose (45%), Hemicellulose (25%), Lignin (20%), H2O (10%)", components: [{ component_id: "CM018", name: "Cellulose", category: "organic", fraction: 0.45, is_trace: 0, hazardous: 0 }, { component_id: "CM019", name: "Hemicellulose", category: "organic", fraction: 0.25, is_trace: 0, hazardous: 0 }, { component_id: "CM020", name: "Lignin", category: "organic", fraction: 0.20, is_trace: 0, hazardous: 0 }, { component_id: "CM014", name: "H2O", category: "other", fraction: 0.10, is_trace: 0, hazardous: 0 }] },
    { stream_id: "S013", company_id: "C004", stream_name: "Syngas Feed", stream_type: "raw_material", direction: "input", flow_kton_per_year: 60, temperature_c: 250, pressure_bar: 25, composition_raw: "CO (45%), H2 (45%), CO2 (8%), CH4 (2%)", components: [{ component_id: "CM007", name: "CO", category: "other", fraction: 0.45, is_trace: 0, hazardous: 1 }, { component_id: "CM009", name: "H2", category: "other", fraction: 0.45, is_trace: 0, hazardous: 0 }, { component_id: "CM008", name: "CO2", category: "other", fraction: 0.08, is_trace: 0, hazardous: 0 }, { component_id: "CM021", name: "CH4", category: "organic", fraction: 0.02, is_trace: 0, hazardous: 0 }] },
    { stream_id: "S014", company_id: "C004", stream_name: "Bioethanol Product", stream_type: "product", direction: "output", flow_kton_per_year: 80, temperature_c: 78, pressure_bar: 1, composition_raw: "C2H5OH (95%), H2O (5%)", components: [{ component_id: "CM022", name: "C2H5OH", category: "organic", fraction: 0.95, is_trace: 0, hazardous: 1 }, { component_id: "CM014", name: "H2O", category: "other", fraction: 0.05, is_trace: 0, hazardous: 0 }] },
    { stream_id: "S015", company_id: "C004", stream_name: "Fermentation CO2", stream_type: "waste", direction: "output", flow_kton_per_year: 75, temperature_c: 35, pressure_bar: 1, composition_raw: "CO2 (98%), H2O (1.5%), C2H5OH (0.5%)", components: [{ component_id: "CM008", name: "CO2", category: "other", fraction: 0.98, is_trace: 0, hazardous: 0 }, { component_id: "CM014", name: "H2O", category: "other", fraction: 0.015, is_trace: 0, hazardous: 0 }, { component_id: "CM022", name: "C2H5OH", category: "organic", fraction: 0.005, is_trace: 0, hazardous: 1 }] },
    { stream_id: "S016", company_id: "C005", stream_name: "Raw Water Intake", stream_type: "raw_material", direction: "input", flow_kton_per_year: 500, temperature_c: 15, pressure_bar: 3, composition_raw: "H2O (99.5%), dissolved solids (0.5%)", components: [{ component_id: "CM014", name: "H2O", category: "other", fraction: 0.995, is_trace: 0, hazardous: 0 }, { component_id: "CM023", name: "dissolved solids", category: "other", fraction: 0.005, is_trace: 0, hazardous: 0 }] },
    { stream_id: "S017", company_id: "C005", stream_name: "H2SO4 Feed", stream_type: "raw_material", direction: "input", flow_kton_per_year: 5, temperature_c: 25, pressure_bar: 1, composition_raw: "H2SO4 (98%), H2O (2%)", components: [{ component_id: "CM024", name: "H2SO4", category: "sulfate", fraction: 0.98, is_trace: 0, hazardous: 1 }, { component_id: "CM014", name: "H2O", category: "other", fraction: 0.02, is_trace: 0, hazardous: 0 }] },
    { stream_id: "S018", company_id: "C005", stream_name: "Treated Water", stream_type: "product", direction: "output", flow_kton_per_year: 480, temperature_c: 20, pressure_bar: 4, composition_raw: "H2O (99.99%)", components: [{ component_id: "CM014", name: "H2O", category: "other", fraction: 0.9999, is_trace: 0, hazardous: 0 }] },
    { stream_id: "S019", company_id: "C005", stream_name: "Sludge", stream_type: "waste", direction: "output", flow_kton_per_year: 20, temperature_c: 20, pressure_bar: 1, composition_raw: "H2O (75%), Fe2O3 (8%), SiO2 (7%), Al2O3 (5%), organics (5%)", components: [{ component_id: "CM014", name: "H2O", category: "other", fraction: 0.75, is_trace: 0, hazardous: 0 }, { component_id: "CM001", name: "Fe2O3", category: "oxide", fraction: 0.08, is_trace: 0, hazardous: 0 }, { component_id: "CM002", name: "SiO2", category: "oxide", fraction: 0.07, is_trace: 0, hazardous: 0 }, { component_id: "CM003", name: "Al2O3", category: "oxide", fraction: 0.05, is_trace: 0, hazardous: 0 }, { component_id: "CM025", name: "organics", category: "organic", fraction: 0.05, is_trace: 0, hazardous: 0 }] },
    { stream_id: "S020", company_id: "C006", stream_name: "Ethylene Feed", stream_type: "raw_material", direction: "input", flow_kton_per_year: 150, temperature_c: 25, pressure_bar: 30, composition_raw: "C2H4 (99.5%), C2H6 (0.5%)", components: [{ component_id: "CM026", name: "C2H4", category: "organic", fraction: 0.995, is_trace: 0, hazardous: 0 }, { component_id: "CM027", name: "C2H6", category: "organic", fraction: 0.005, is_trace: 0, hazardous: 0 }] },
    { stream_id: "S021", company_id: "C006", stream_name: "Process Water", stream_type: "raw_material", direction: "input", flow_kton_per_year: 40, temperature_c: 20, pressure_bar: 4, composition_raw: "H2O (99.9%)", components: [{ component_id: "CM014", name: "H2O", category: "other", fraction: 0.999, is_trace: 0, hazardous: 0 }] },
    { stream_id: "S022", company_id: "C006", stream_name: "Polyethylene Product", stream_type: "product", direction: "output", flow_kton_per_year: 145, temperature_c: 80, pressure_bar: 1, composition_raw: "PE pellets (100%)", components: [{ component_id: "CM028", name: "PE", category: "organic", fraction: 1.0, is_trace: 0, hazardous: 0 }] },
    { stream_id: "S023", company_id: "C006", stream_name: "Off-gas", stream_type: "waste", direction: "output", flow_kton_per_year: 8, temperature_c: 120, pressure_bar: 1, composition_raw: "C2H4 (40%), N2 (35%), CO2 (15%), H2 (10%)", components: [{ component_id: "CM026", name: "C2H4", category: "organic", fraction: 0.40, is_trace: 0, hazardous: 0 }, { component_id: "CM006", name: "N2", category: "other", fraction: 0.35, is_trace: 0, hazardous: 0 }, { component_id: "CM008", name: "CO2", category: "other", fraction: 0.15, is_trace: 0, hazardous: 0 }, { component_id: "CM009", name: "H2", category: "other", fraction: 0.10, is_trace: 0, hazardous: 0 }] },
    { stream_id: "S024", company_id: "C006", stream_name: "Process Wastewater", stream_type: "waste", direction: "output", flow_kton_per_year: 38, temperature_c: 45, pressure_bar: 1, composition_raw: "H2O (99%), dissolved organics (1%)", components: [{ component_id: "CM014", name: "H2O", category: "other", fraction: 0.99, is_trace: 0, hazardous: 0 }, { component_id: "CM025", name: "organics", category: "organic", fraction: 0.01, is_trace: 0, hazardous: 0 }] },
  ],
  candidates: [
    { from_company_id: "C001", to_company_id: "C003", from_stream_id: "S002", to_stream_id: "S009", from_stream_name: "Blast Furnace Slag", to_stream_name: "Calcium Silicate Feed", from_stream_type: "waste", to_stream_type: "raw_material", composite_score: 0.82, component_overlap: 0.80, fraction_similarity: 0.92, flow_compatibility: 0.70, temperature_proximity: 0.07, pressure_proximity: 1.0, shared_components: [{ name: "CaO", hazardous: 0, fraction_out: 0.40, fraction_in: 0.42 }, { name: "SiO2", hazardous: 0, fraction_out: 0.35, fraction_in: 0.33 }, { name: "Al2O3", hazardous: 0, fraction_out: 0.15, fraction_in: 0.15 }, { name: "MgO", hazardous: 0, fraction_out: 0.10, fraction_in: 0.06 }], has_hazardous: false, available_flow_kton: 280, required_flow_kton: 400 },
    { from_company_id: "C004", to_company_id: "C002", from_stream_id: "S015", to_stream_id: "S006", from_stream_name: "Fermentation CO2", to_stream_name: "CO2 Feed", from_stream_type: "waste", to_stream_type: "raw_material", composite_score: 0.76, component_overlap: 0.67, fraction_similarity: 0.96, flow_compatibility: 0.40, temperature_proximity: 0.91, pressure_proximity: 0.53, shared_components: [{ name: "CO2", hazardous: 0, fraction_out: 0.98, fraction_in: 0.99 }, { name: "N2", hazardous: 0, fraction_out: 0.0, fraction_in: 0.01 }], has_hazardous: false, available_flow_kton: 75, required_flow_kton: 30 },
    { from_company_id: "C003", to_company_id: "C002", from_stream_id: "S011", to_stream_id: "S006", from_stream_name: "Kiln CO2 Exhaust", to_stream_name: "CO2 Feed", from_stream_type: "waste", to_stream_type: "raw_material", composite_score: 0.51, component_overlap: 0.50, fraction_similarity: 0.64, flow_compatibility: 0.094, temperature_proximity: 0.24, pressure_proximity: 0.53, shared_components: [{ name: "CO2", hazardous: 0, fraction_out: 0.25, fraction_in: 0.99 }, { name: "N2", hazardous: 0, fraction_out: 0.65, fraction_in: 0.01 }], has_hazardous: false, available_flow_kton: 320, required_flow_kton: 30 },
    { from_company_id: "C005", to_company_id: "C006", from_stream_id: "S018", to_stream_id: "S021", from_stream_name: "Treated Water", to_stream_name: "Process Water", from_stream_type: "product", to_stream_type: "raw_material", composite_score: 0.74, component_overlap: 1.0, fraction_similarity: 1.0, flow_compatibility: 0.083, temperature_proximity: 1.0, pressure_proximity: 1.0, shared_components: [{ name: "H2O", hazardous: 0, fraction_out: 0.9999, fraction_in: 0.999 }], has_hazardous: false, available_flow_kton: 480, required_flow_kton: 40 },
    { from_company_id: "C001", to_company_id: "C004", from_stream_id: "S003", to_stream_id: "S013", from_stream_name: "Blast Furnace Gas", to_stream_name: "Syngas Feed", from_stream_type: "waste", to_stream_type: "raw_material", composite_score: 0.58, component_overlap: 0.60, fraction_similarity: 0.68, flow_compatibility: 0.50, temperature_proximity: 0.84, pressure_proximity: 0.04, shared_components: [{ name: "CO", hazardous: 1, fraction_out: 0.25, fraction_in: 0.45 }, { name: "H2", hazardous: 0, fraction_out: 0.02, fraction_in: 0.45 }, { name: "CO2", hazardous: 0, fraction_out: 0.18, fraction_in: 0.08 }], has_hazardous: true, available_flow_kton: 120, required_flow_kton: 60 },
    { from_company_id: "C006", to_company_id: "C004", from_stream_id: "S023", to_stream_id: "S013", from_stream_name: "Off-gas", to_stream_name: "Syngas Feed", from_stream_type: "waste", to_stream_type: "raw_material", composite_score: 0.42, component_overlap: 0.50, fraction_similarity: 0.55, flow_compatibility: 0.133, temperature_proximity: 0.44, pressure_proximity: 0.04, shared_components: [{ name: "CO2", hazardous: 0, fraction_out: 0.15, fraction_in: 0.08 }, { name: "H2", hazardous: 0, fraction_out: 0.10, fraction_in: 0.45 }], has_hazardous: false, available_flow_kton: 8, required_flow_kton: 60 },
    { from_company_id: "C005", to_company_id: "C004", from_stream_id: "S018", to_stream_id: "S012", from_stream_name: "Treated Water", to_stream_name: "Biomass Feed", from_stream_type: "product", to_stream_type: "raw_material", composite_score: 0.28, component_overlap: 0.20, fraction_similarity: 0.10, flow_compatibility: 0.42, temperature_proximity: 0.95, pressure_proximity: 0.75, shared_components: [{ name: "H2O", hazardous: 0, fraction_out: 0.9999, fraction_in: 0.10 }], has_hazardous: false, available_flow_kton: 480, required_flow_kton: 200 },
    { from_company_id: "C001", to_company_id: "C002", from_stream_id: "S003", to_stream_id: "S006", from_stream_name: "Blast Furnace Gas", to_stream_name: "CO2 Feed", from_stream_type: "waste", to_stream_type: "raw_material", composite_score: 0.44, component_overlap: 0.50, fraction_similarity: 0.50, flow_compatibility: 0.25, temperature_proximity: 0.15, pressure_proximity: 0.53, shared_components: [{ name: "CO2", hazardous: 0, fraction_out: 0.18, fraction_in: 0.99 }, { name: "N2", hazardous: 0, fraction_out: 0.55, fraction_in: 0.01 }], has_hazardous: false, available_flow_kton: 120, required_flow_kton: 30 },
  ],
  flows: [],
};

// ─── CONSTANTS & HELPERS ────────────────────────────────────────────────────

const COLORS = ["#E8915A", "#5B9BD5", "#7BC67E", "#D4A0D9", "#E06C75", "#C9B458", "#6CC1C8", "#F28B82", "#A4C9A4", "#B8A9C9", "#D4956B", "#8BB8D0"];
const SC = (s) => s >= 0.7 ? "#4ade80" : s >= 0.5 ? "#facc15" : s >= 0.3 ? "#fb923c" : "#f87171";
const SL = (s) => s >= 0.7 ? "Strong" : s >= 0.5 ? "Moderate" : s >= 0.3 ? "Weak" : "Poor";
const SS = { candidate: { bg: "#facc1522", c: "#facc15", l: "Candidate" }, confirmed: { bg: "#4ade8022", c: "#4ade80", l: "Confirmed" }, rejected: { bg: "#f8717122", c: "#f87171", l: "Rejected" } };

function scorePair(out, inp) {
  const oC = {}, iC = {};
  (out.components || []).forEach(c => { if (!c.is_trace) oC[c.component_id] = c; });
  (inp.components || []).forEach(c => { if (!c.is_trace) iC[c.component_id] = c; });
  const oK = new Set(Object.keys(oC)), iK = new Set(Object.keys(iC));
  const shared = [...oK].filter(k => iK.has(k)), union = new Set([...oK, ...iK]);
  const co = union.size > 0 ? shared.length / union.size : 0;
  let fs = 0;
  if (shared.length) { const d = shared.map(k => Math.abs((oC[k].fraction||0) - (iC[k].fraction||0))); fs = 1 - d.reduce((a,b)=>a+b,0)/d.length; }
  const fO = out.flow_kton_per_year||0, fI = inp.flow_kton_per_year||0;
  const fc = (fO > 0 && fI > 0) ? Math.min(fO,fI)/Math.max(fO,fI) : 0;
  const tp = (out.temperature_c!=null && inp.temperature_c!=null) ? 1/(1+Math.abs(out.temperature_c-inp.temperature_c)/100) : 0.5;
  const pp = (out.pressure_bar!=null && inp.pressure_bar!=null) ? 1/(1+Math.abs(out.pressure_bar-inp.pressure_bar)/10) : 0.5;
  const cs = co*0.35 + fs*0.25 + fc*0.20 + tp*0.10 + pp*0.10;
  const sc = shared.map(k => ({ name: oC[k].name, hazardous: oC[k].hazardous, fraction_out: oC[k].fraction, fraction_in: iC[k].fraction })).sort((a,b)=>(b.fraction_out||0)-(a.fraction_out||0));
  const r = v => Math.round(v*10000)/10000;
  return { composite_score:r(cs), component_overlap:r(co), fraction_similarity:r(fs), flow_compatibility:r(fc), temperature_proximity:r(tp), pressure_proximity:r(pp), shared_components:sc, has_hazardous:sc.some(c=>c.hazardous===1) };
}

// ─── FORCE GRAPH ────────────────────────────────────────────────────────────

function Graph({ companies, candidates, flows, active, cMap, onEdge }) {
  const ref = useRef(null);
  const fCands = useMemo(() => candidates.filter(c => active.has(c.from_company_id) && active.has(c.to_company_id)), [candidates, active]);
  const fConf = useMemo(() => flows.filter(f => f.status==="confirmed" && active.has(f.from_company_id) && active.has(f.to_company_id)), [flows, active]);
  const fComps = useMemo(() => companies.filter(c => active.has(c.company_id)), [companies, active]);

  useEffect(() => {
    if (!ref.current) return;
    const svg = d3.select(ref.current); svg.selectAll("*").remove();
    const w = ref.current.clientWidth, h = ref.current.clientHeight;
    const defs = svg.append("defs");
    defs.append("marker").attr("id","ac").attr("viewBox","0 -5 10 10").attr("refX",28).attr("refY",0).attr("markerWidth",6).attr("markerHeight",6).attr("orient","auto").append("path").attr("d","M0,-5L10,0L0,5").attr("fill","#5f6577");
    defs.append("marker").attr("id","af").attr("viewBox","0 -5 10 10").attr("refX",28).attr("refY",0).attr("markerWidth",7).attr("markerHeight",7).attr("orient","auto").append("path").attr("d","M0,-5L10,0L0,5").attr("fill","#4ade80");
    const g = svg.append("g");
    svg.call(d3.zoom().scaleExtent([0.3,4]).on("zoom",e=>g.attr("transform",e.transform)));

    const eMap = new Map();
    fCands.forEach(c => { const k=`${c.from_company_id}→${c.to_company_id}`; if(!eMap.has(k)||c.composite_score>eMap.get(k).composite_score)eMap.set(k,c); });
    const cfMap = new Set(); fConf.forEach(f => cfMap.add(`${f.from_company_id}→${f.to_company_id}`));

    const nodes = fComps.map(c => ({...c, id:c.company_id}));
    const links = [];
    eMap.forEach((c,k) => { if(!cfMap.has(k)) links.push({source:c.from_company_id,target:c.to_company_id,score:c.composite_score,type:"cand",data:c}); });
    fConf.forEach(f => links.push({source:f.from_company_id,target:f.to_company_id,score:1,type:"conf",data:f}));

    const sim = d3.forceSimulation(nodes).force("link",d3.forceLink(links).id(d=>d.id).distance(160)).force("charge",d3.forceManyBody().strength(-600)).force("center",d3.forceCenter(w/2,h/2)).force("collision",d3.forceCollide(50));

    const link = g.append("g").selectAll("line").data(links).join("line")
      .attr("stroke",d=>d.type==="conf"?"#4ade80":SC(d.score)).attr("stroke-width",d=>d.type==="conf"?4:1.5+d.score*3)
      .attr("stroke-opacity",d=>d.type==="conf"?0.85:0.45).attr("stroke-dasharray",d=>d.type==="conf"?"none":"6 3")
      .attr("marker-end",d=>d.type==="conf"?"url(#af)":"url(#ac)").style("cursor","pointer")
      .on("click",(_,d)=>{if(d.type==="cand")onEdge(d.data);});

    const lbl = g.append("g").selectAll("text").data(links).join("text")
      .text(d=>d.type==="conf"?"✓":`${(d.score*100).toFixed(0)}%`)
      .attr("font-size",d=>d.type==="conf"?"12px":"10px").attr("fill",d=>d.type==="conf"?"#4ade80":"#5f6577")
      .attr("text-anchor","middle").attr("dy",-8).style("pointer-events","none");

    const node = g.append("g").selectAll("g").data(nodes).join("g").style("cursor","grab")
      .call(d3.drag().on("start",(e,d)=>{if(!e.active)sim.alphaTarget(0.3).restart();d.fx=d.x;d.fy=d.y;}).on("drag",(e,d)=>{d.fx=e.x;d.fy=e.y;}).on("end",(e,d)=>{if(!e.active)sim.alphaTarget(0);d.fx=null;d.fy=null;}));
    node.append("circle").attr("r",24).attr("fill",d=>cMap[d.company_id]).attr("stroke","#181b23").attr("stroke-width",2.5);
    node.append("text").text(d=>d.name.split(" ").map(w=>w[0]).join("")).attr("text-anchor","middle").attr("dy","0.35em").attr("font-size","11px").attr("font-weight","700").attr("fill","#fff").style("pointer-events","none");
    node.append("text").text(d=>d.name).attr("text-anchor","middle").attr("dy",40).attr("font-size","11px").attr("fill","#e8eaed").style("pointer-events","none");

    sim.on("tick",()=>{link.attr("x1",d=>d.source.x).attr("y1",d=>d.source.y).attr("x2",d=>d.target.x).attr("y2",d=>d.target.y);lbl.attr("x",d=>(d.source.x+d.target.x)/2).attr("y",d=>(d.source.y+d.target.y)/2);node.attr("transform",d=>`translate(${d.x},${d.y})`);});
    return ()=>sim.stop();
  }, [fComps, fCands, fConf, cMap, onEdge]);

  return <svg ref={ref} style={{width:"100%",height:"100%"}} />;
}

// ─── REUSABLE COMPONENTS ────────────────────────────────────────────────────

function Bar({label,value}){const p=Math.round(value*100);return(<div style={{marginBottom:6}}><div style={{display:"flex",justifyContent:"space-between",fontSize:11,marginBottom:2}}><span style={{color:"#5f6577"}}>{label}</span><span style={{fontWeight:600,fontVariantNumeric:"tabular-nums"}}>{(value*100).toFixed(1)}%</span></div><div style={{height:6,borderRadius:3,background:"#0f1117",overflow:"hidden"}}><div style={{height:"100%",width:`${p}%`,borderRadius:3,background:SC(value),transition:"width 0.3s"}}/></div></div>);}

function Scores({r,children}){return(<><div style={{display:"flex",alignItems:"center",gap:8,marginBottom:12}}><span style={{fontSize:22,fontWeight:700,color:SC(r.composite_score)}}>{(r.composite_score*100).toFixed(0)}%</span><span style={{fontSize:12,padding:"2px 8px",borderRadius:9999,background:SC(r.composite_score)+"22",color:SC(r.composite_score),fontWeight:600}}>{SL(r.composite_score)}</span>{r.has_hazardous&&<span style={{fontSize:11,padding:"2px 6px",borderRadius:4,background:"#f871711a",color:"#f87171",fontWeight:600}}>HAZARDOUS</span>}</div><Bar label="Component Overlap" value={r.component_overlap}/><Bar label="Fraction Similarity" value={r.fraction_similarity}/><Bar label="Flow Compatibility" value={r.flow_compatibility}/><Bar label="Temperature Match" value={r.temperature_proximity}/><Bar label="Pressure Match" value={r.pressure_proximity}/>{(r.shared_components||[]).length>0&&<div style={{marginTop:10}}><div style={{fontSize:11,color:"#5f6577",textTransform:"uppercase",letterSpacing:1,marginBottom:4}}>Shared Components</div>{r.shared_components.map((sc,i)=>(<div key={i} style={{display:"flex",justifyContent:"space-between",padding:"3px 0",borderBottom:"1px solid #2a2e3a",fontSize:12}}><span>{sc.name}{sc.hazardous===1&&<span style={{color:"#f87171",marginLeft:4}}>⚠</span>}</span><span style={{color:"#5f6577",fontVariantNumeric:"tabular-nums"}}>{((sc.fraction_out||0)*100).toFixed(1)}% → {((sc.fraction_in||0)*100).toFixed(1)}%</span></div>))}</div>}{children}</>);}

function AiEval({outStream,inStream,fromCo,toCo}){const[res,setRes]=useState(null);const[loading,setLoading]=useState(false);const ask=useCallback(async()=>{setLoading(true);setRes(null);const p=`You are an industrial ecology expert evaluating a potential industrial symbiosis connection.\n\n**Supplier:** ${fromCo?.name} (${fromCo?.sector||"unknown sector"})\n**Output stream:** ${outStream.stream_name} (${outStream.stream_type})\n- Flow: ${outStream.flow_kton_per_year} kton/year\n- Temperature: ${outStream.temperature_c??"unknown"}°C, Pressure: ${outStream.pressure_bar??"unknown"} bar\n- Composition: ${outStream.composition_raw||outStream.components?.map(c=>`${c.name} (${(c.fraction*100).toFixed(1)}%)`).join(", ")}\n\n**Receiver:** ${toCo?.name} (${toCo?.sector||"unknown sector"})\n**Input stream:** ${inStream.stream_name} (${inStream.stream_type})\n- Flow: ${inStream.flow_kton_per_year} kton/year\n- Temperature: ${inStream.temperature_c??"unknown"}°C, Pressure: ${inStream.pressure_bar??"unknown"} bar\n- Composition: ${inStream.composition_raw||inStream.components?.map(c=>`${c.name} (${(c.fraction*100).toFixed(1)}%)`).join(", ")}\n\nProvide a concise evaluation (200 words max) covering:\n1. **Compatibility** — compositional match\n2. **Practical concerns** — temperature/pressure gaps, purification, hazards, contaminants\n3. **Flow balance** — can supply meet demand?\n4. **Recommendation** — viable, conditionally viable, or not viable`;try{const r=await fetch("https://api.anthropic.com/v1/messages",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({model:"claude-sonnet-4-20250514",max_tokens:1000,messages:[{role:"user",content:p}]})});const d=await r.json();setRes(d.content?.map(b=>b.text||"").join("\n")||"No response.");}catch(e){setRes(`Error: ${e.message}`);}finally{setLoading(false);};},[outStream,inStream,fromCo,toCo]);return(<><button onClick={ask} disabled={loading} style={{marginTop:14,width:"100%",padding:"10px 16px",borderRadius:8,border:"1px solid #5B9BD5",background:loading?"#0f1117":"#5B9BD5",color:loading?"#5f6577":"#fff",fontWeight:600,fontSize:13,cursor:loading?"not-allowed":"pointer",fontFamily:"inherit"}}>{loading?"Evaluating...":"Ask Claude for Evaluation"}</button>{res&&<div style={{marginTop:12,padding:12,borderRadius:8,background:"#0f1117",fontSize:12,lineHeight:1.6,whiteSpace:"pre-wrap",color:"#9aa0ad"}}>{res}</div>}</>);}

// ─── FLOWS MANAGER ──────────────────────────────────────────────────────────

function FlowsMgr({flows,companies,onUpdate,onRemove,onExport}){
  const[editId,setEditId]=useState(null);const[note,setNote]=useState("");
  const cn=id=>companies.find(c=>c.company_id===id)?.name||id;
  const cycle={candidate:"confirmed",confirmed:"rejected",rejected:"candidate"};
  const ct={candidate:flows.filter(f=>f.status==="candidate").length,confirmed:flows.filter(f=>f.status==="confirmed").length,rejected:flows.filter(f=>f.status==="rejected").length};

  return(<div style={{padding:12}}>
    <div style={{display:"flex",gap:8,marginBottom:12,flexWrap:"wrap"}}>{["candidate","confirmed","rejected"].map(s=><div key={s} style={{padding:"4px 10px",borderRadius:6,background:SS[s].bg,color:SS[s].c,fontSize:11,fontWeight:600}}>{ct[s]} {SS[s].l}</div>)}</div>

    {flows.length===0&&<div style={{padding:24,textAlign:"center",color:"#5f6577",fontSize:12,lineHeight:1.6}}>No flows yet. Add stream pairs from the Candidates or Manual Pair tabs.</div>}

    {flows.map(f=>{const s=SS[f.status];return(<div key={f.flow_id} style={{padding:12,borderRadius:8,marginBottom:8,background:"#181b23",border:`1px solid ${f.status==="confirmed"?"#4ade8044":f.status==="rejected"?"#f8717133":"#2a2e3a"}`}}>
      <div style={{display:"flex",justifyContent:"space-between",alignItems:"start",marginBottom:6}}>
        <div style={{flex:1}}>
          <div style={{fontSize:11,fontWeight:600}}><span>{cn(f.from_company_id)}</span><span style={{color:"#5f6577"}}> → </span><span>{cn(f.to_company_id)}</span></div>
          <div style={{fontSize:10,color:"#9aa0ad",marginTop:2}}>{f.from_stream_name} → {f.to_stream_name}</div>
          <div style={{fontSize:10,color:"#5f6577",marginTop:2}}>{f.flow_kton_per_year} kt/yr · Score: {((f.composite_score||0)*100).toFixed(0)}%</div>
        </div>
        <div style={{display:"flex",gap:4,alignItems:"center",flexShrink:0}}>
          <button onClick={()=>onUpdate(f.flow_id,{status:cycle[f.status]})} style={{padding:"3px 10px",borderRadius:9999,border:"none",background:s.bg,color:s.c,fontSize:10,fontWeight:600,cursor:"pointer",fontFamily:"inherit"}} title={`Click → ${SS[cycle[f.status]].l}`}>{s.l}</button>
          <button onClick={()=>onRemove(f.flow_id)} style={{padding:"3px 8px",borderRadius:6,border:"none",background:"#f871711a",color:"#f87171",fontSize:10,cursor:"pointer",fontFamily:"inherit"}} title="Remove">✕</button>
        </div>
      </div>
      {editId===f.flow_id?(<div style={{marginTop:6}}><textarea value={note} onChange={e=>setNote(e.target.value)} placeholder="Add notes..." style={{width:"100%",padding:8,borderRadius:6,border:"1px solid #2a2e3a",background:"#0f1117",color:"#e8eaed",fontSize:11,fontFamily:"inherit",resize:"vertical",minHeight:50,boxSizing:"border-box"}}/><div style={{display:"flex",gap:4,marginTop:4}}><button onClick={()=>{onUpdate(f.flow_id,{notes:note});setEditId(null);}} style={{padding:"4px 12px",borderRadius:6,border:"none",background:"#5B9BD5",color:"#fff",fontSize:10,fontWeight:600,cursor:"pointer",fontFamily:"inherit"}}>Save</button><button onClick={()=>setEditId(null)} style={{padding:"4px 12px",borderRadius:6,border:"none",background:"#2a2e3a",color:"#9aa0ad",fontSize:10,cursor:"pointer",fontFamily:"inherit"}}>Cancel</button></div></div>):(<div onClick={()=>{setEditId(f.flow_id);setNote(f.notes||"");}} style={{marginTop:6,fontSize:10,color:f.notes?"#9aa0ad":"#5f6577",cursor:"pointer",fontStyle:f.notes?"normal":"italic",padding:"4px 0"}}>{f.notes||"Click to add notes..."}</div>)}
    </div>);})}

    {flows.length>0&&<button onClick={onExport} style={{marginTop:12,width:"100%",padding:"10px 16px",borderRadius:8,border:"1px solid #5B9BD5",background:"transparent",color:"#5B9BD5",fontWeight:600,fontSize:12,cursor:"pointer",fontFamily:"inherit"}}>Export Flows as JSON</button>}
  </div>);
}

// ─── MAIN APP ───────────────────────────────────────────────────────────────

export default function App(){
  const data=DEMO_DATA;
  const[active,setActive]=useState(()=>new Set(data.companies.map(c=>c.company_id)));
  const[sel,setSel]=useState(null);
  const[tab,setTab]=useState("candidates");
  const[sf,setSf]=useState(0.15);
  const[flows,setFlows]=useState(()=>data.flows.map((f,i)=>({...f,flow_id:f.flow_id||`F${String(i+1).padStart(3,"0")}`})));
  const[nf,setNf]=useState(data.flows.length+1);
  const[scales,setScales]=useState(()=>{const m={};data.companies.forEach(c=>{m[c.company_id]=1.0;});return m;});
  const setScale=(id,v)=>setScales(p=>({...p,[id]:v}));
  const scaledFlow=(companyId,flow)=>(flow||0)*( scales[companyId]||1);

  const cMap=useMemo(()=>{const m={};data.companies.forEach((c,i)=>{m[c.company_id]=COLORS[i%COLORS.length];});return m;},[data.companies]);
  const fCands=useMemo(()=>data.candidates.filter(c=>active.has(c.from_company_id)&&active.has(c.to_company_id)).filter(c=>c.composite_score>=sf).sort((a,b)=>b.composite_score-a.composite_score),[data.candidates,active,sf]);

  const toggle=id=>setActive(p=>{const n=new Set(p);n.has(id)?n.delete(id):n.add(id);return n;});
  const addFlow=useCallback(fd=>{const id=`F${String(nf).padStart(3,"0")}`;setFlows(p=>[...p,{flow_id:id,status:"candidate",notes:"",...fd}]);setNf(n=>n+1);setTab("flows");},[nf]);
  const updateFlow=useCallback((id,u)=>setFlows(p=>p.map(f=>f.flow_id===id?{...f,...u}:f)),[]);
  const removeFlow=useCallback(id=>setFlows(p=>p.filter(f=>f.flow_id!==id)),[]);
  const exportFlows=useCallback(()=>{const b=new Blob([JSON.stringify(flows,null,2)],{type:"application/json"});const u=URL.createObjectURL(b);const a=document.createElement("a");a.href=u;a.download="flows_export.json";a.click();URL.revokeObjectURL(u);},[flows]);

  const inFlows=useCallback((fromSid,toSid)=>flows.some(f=>f.from_stream_id===fromSid&&f.to_stream_id===toSid),[flows]);
  const cc=flows.filter(f=>f.status==="confirmed").length;
  const cn=id=>data.companies.find(c=>c.company_id===id)?.name||id;

  // Manual pair state
  const[outSid,setOutSid]=useState("");const[inSid,setInSid]=useState("");const[mResult,setMResult]=useState(null);
  const outStreams=useMemo(()=>data.streams.filter(s=>s.direction==="output"&&active.has(s.company_id)),[data.streams,active]);
  const inStreams=useMemo(()=>data.streams.filter(s=>s.direction==="input"&&active.has(s.company_id)),[data.streams,active]);
  const doEval=useCallback(()=>{const o=data.streams.find(s=>s.stream_id===outSid),i=data.streams.find(s=>s.stream_id===inSid);if(!o||!i)return;setMResult({...scorePair(o,i),from_stream_name:o.stream_name,to_stream_name:i.stream_name,available_flow_kton:o.flow_kton_per_year,required_flow_kton:i.flow_kton_per_year});},[outSid,inSid,data.streams]);
  const mOut=data.streams.find(s=>s.stream_id===outSid),mIn=data.streams.find(s=>s.stream_id===inSid);
  const mFromCo=mOut?data.companies.find(c=>c.company_id===mOut.company_id):null;
  const mToCo=mIn?data.companies.find(c=>c.company_id===mIn.company_id):null;

  const selStyle={width:"100%",padding:"8px 10px",borderRadius:6,border:"1px solid #2a2e3a",background:"#0f1117",color:"#e8eaed",fontSize:12,fontFamily:"inherit"};

  return(
  <div style={{background:"#0f1117",color:"#e8eaed",fontFamily:"'JetBrains Mono','SF Mono','Fira Code',monospace",height:"100vh",display:"flex",flexDirection:"column",overflow:"hidden"}}>
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet"/>

  {/* Header */}
  <div style={{padding:"12px 20px",borderBottom:"1px solid #2a2e3a",display:"flex",justifyContent:"space-between",alignItems:"center",flexShrink:0}}>
    <div><h1 style={{margin:0,fontSize:16,fontWeight:700,letterSpacing:-0.3}}>SYMBIOSIS MATCHER</h1><span style={{fontSize:11,color:"#5f6577"}}>{data.metadata.total_companies} companies · {fCands.length} candidates · {cc} confirmed flow{cc!==1?"s":""}</span></div>
    <div style={{display:"flex",gap:6,alignItems:"center"}}><span style={{fontSize:10,color:"#5f6577",marginRight:4}}>MIN SCORE</span><input type="range" min="0" max="0.9" step="0.05" value={sf} onChange={e=>setSf(parseFloat(e.target.value))} style={{width:80,accentColor:"#5B9BD5"}}/><span style={{fontSize:11,fontVariantNumeric:"tabular-nums",width:32}}>{(sf*100).toFixed(0)}%</span></div>
  </div>

  {/* Body */}
  <div style={{flex:1,display:"flex",overflow:"hidden"}}>
    {/* Left — Companies */}
    <div style={{width:200,borderRight:"1px solid #2a2e3a",flexShrink:0,display:"flex",flexDirection:"column",overflow:"hidden"}}>
      <div style={{padding:"10px 12px",borderBottom:"1px solid #2a2e3a",display:"flex",justifyContent:"space-between",alignItems:"center"}}>
        <span style={{fontSize:10,color:"#5f6577",textTransform:"uppercase",letterSpacing:1,fontWeight:600}}>Companies</span>
        <div style={{display:"flex",gap:4}}><button onClick={()=>setActive(new Set(data.companies.map(c=>c.company_id)))} style={{fontSize:10,background:"none",border:"none",color:"#5B9BD5",cursor:"pointer",padding:"2px 4px",fontFamily:"inherit"}}>All</button><button onClick={()=>setActive(new Set())} style={{fontSize:10,background:"none",border:"none",color:"#5f6577",cursor:"pointer",padding:"2px 4px",fontFamily:"inherit"}}>None</button><button onClick={()=>{const m={};data.companies.forEach(c=>{m[c.company_id]=1.0;});setScales(m);}} style={{fontSize:10,background:"none",border:"none",color:"#5f6577",cursor:"pointer",padding:"2px 4px",fontFamily:"inherit"}}>×1</button></div>
      </div>
      <div style={{flex:1,overflow:"auto",padding:"6px 0"}}>
        {data.companies.map(c=><div key={c.company_id} style={{padding:"7px 12px",transition:"background 0.1s",background:active.has(c.company_id)?"#181b23":"transparent",opacity:active.has(c.company_id)?1:0.4}}>
          <div onClick={()=>toggle(c.company_id)} style={{display:"flex",alignItems:"center",gap:8,cursor:"pointer"}}>
            <div style={{width:10,height:10,borderRadius:"50%",background:active.has(c.company_id)?cMap[c.company_id]:"#2a2e3a",flexShrink:0}}/>
            <div><div style={{fontSize:12,fontWeight:500}}>{c.name}</div><div style={{fontSize:10,color:"#5f6577"}}>{c.sector||c.company_id}</div></div>
          </div>
          {active.has(c.company_id)&&<div style={{marginTop:4,marginLeft:18,display:"flex",alignItems:"center",gap:4}} onClick={e=>e.stopPropagation()}>
            <span style={{fontSize:9,color:"#5f6577",width:14,textAlign:"right",flexShrink:0}}>×</span>
            <input type="range" min="0.1" max="5" step="0.05" value={scales[c.company_id]||1} onChange={e=>setScale(c.company_id,parseFloat(e.target.value))} style={{width:80,accentColor:cMap[c.company_id],height:12}}/>
            <span style={{fontSize:10,color:scales[c.company_id]!==1?"#e8eaed":"#5f6577",fontVariantNumeric:"tabular-nums",width:32,fontWeight:scales[c.company_id]!==1?600:400}}>{(scales[c.company_id]||1).toFixed(2)}</span>
            {scales[c.company_id]!==1&&<button onClick={()=>setScale(c.company_id,1)} style={{fontSize:8,background:"none",border:"1px solid #2a2e3a",color:"#5f6577",borderRadius:3,cursor:"pointer",padding:"1px 4px",fontFamily:"inherit",lineHeight:1}}>↺</button>}
          </div>}
        </div>)}
      </div>
    </div>

    {/* Center — Graph */}
    <div style={{flex:1,position:"relative",background:"#0f1117"}}>
      <Graph companies={data.companies} candidates={fCands} flows={flows} active={active} cMap={cMap} onEdge={e=>{setSel(e);setTab("candidates");}}/>
      <div style={{position:"absolute",bottom:12,left:12,display:"flex",gap:10,fontSize:10,color:"#5f6577"}}>
        {[{c:"#4ade80",l:"Confirmed"},{c:"#facc15",l:">50%"},{c:"#fb923c",l:">30%"},{c:"#f87171",l:"<30%"}].map(x=><div key={x.l} style={{display:"flex",alignItems:"center",gap:4}}><div style={{width:14,height:x.l==="Confirmed"?4:2,borderRadius:2,background:x.c}}/>{x.l}</div>)}
        <div style={{display:"flex",alignItems:"center",gap:4}}><div style={{width:14,height:0,borderTop:"2px dashed #5f6577"}}/> Candidate</div>
      </div>
    </div>

    {/* Right — Tabs */}
    <div style={{width:340,borderLeft:"1px solid #2a2e3a",flexShrink:0,display:"flex",flexDirection:"column",overflow:"hidden"}}>
      <div style={{display:"flex",borderBottom:"1px solid #2a2e3a",flexShrink:0}}>
        {[["candidates","Candidates"],["manual","Manual Pair"],["flows",`Flows (${flows.length})`]].map(([k,l])=><button key={k} onClick={()=>{setTab(k);setSel(null);}} style={{flex:1,padding:"10px 0",fontSize:11,fontWeight:600,background:"none",border:"none",cursor:"pointer",color:tab===k?"#5B9BD5":"#5f6577",borderBottom:tab===k?"2px solid #5B9BD5":"2px solid transparent",fontFamily:"inherit"}}>{l}</button>)}
      </div>

      <div style={{flex:1,overflow:"auto"}}>
        {/* CANDIDATES */}
        {tab==="candidates"&&!sel&&<div style={{padding:12}}>
          {fCands.map((c,i)=>{const inf=inFlows(c.from_stream_id,c.to_stream_id);return(<div key={i} onClick={()=>setSel(c)} style={{padding:"10px 12px",borderRadius:8,marginBottom:6,cursor:"pointer",background:"#181b23",border:"1px solid #2a2e3a",transition:"border-color 0.15s"}} onMouseEnter={e=>e.currentTarget.style.borderColor=SC(c.composite_score)} onMouseLeave={e=>e.currentTarget.style.borderColor="#2a2e3a"}>
            <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:4}}><span style={{fontSize:13,fontWeight:600,color:SC(c.composite_score)}}>{(c.composite_score*100).toFixed(0)}%</span><div style={{display:"flex",gap:4,alignItems:"center"}}>{inf&&<span style={{fontSize:9,padding:"1px 6px",borderRadius:9999,background:"#4ade8022",color:"#4ade80"}}>in flows</span>}{c.has_hazardous&&<span style={{fontSize:10,color:"#f87171"}}>⚠</span>}</div></div>
            <div style={{fontSize:11}}><span style={{color:cMap[c.from_company_id],fontWeight:500}}>{cn(c.from_company_id)}</span><span style={{color:"#5f6577"}}> → </span><span style={{color:cMap[c.to_company_id],fontWeight:500}}>{cn(c.to_company_id)}</span></div>
            <div style={{fontSize:10,color:"#5f6577",marginTop:2}}>{c.from_stream_name} → {c.to_stream_name}</div>
            <div style={{fontSize:10,color:"#5f6577",marginTop:2}}>{c.shared_components.map(sc=>sc.name).join(", ")}</div>
          </div>);})}
          {fCands.length===0&&<div style={{padding:20,textAlign:"center",color:"#5f6577",fontSize:12}}>No candidates match current filters.</div>}
        </div>}

        {tab==="candidates"&&sel&&<div>
          <button onClick={()=>setSel(null)} style={{padding:"8px 16px",fontSize:11,background:"none",border:"none",color:"#5B9BD5",cursor:"pointer",fontFamily:"inherit"}}>← Back to list</button>
          <div style={{padding:16}}>
            {(()=>{
              const sAvail=scaledFlow(sel.from_company_id,sel.available_flow_kton);
              const sReq=scaledFlow(sel.to_company_id,sel.required_flow_kton);
              const fromScale=scales[sel.from_company_id]||1;
              const toScale=scales[sel.to_company_id]||1;
              const matchSupplierFactor=sel.available_flow_kton>0?(sel.required_flow_kton*(toScale))/sel.available_flow_kton:1;
              const matchReceiverFactor=sel.required_flow_kton>0?(sel.available_flow_kton*(fromScale))/sel.required_flow_kton:1;
              return <>
            <div style={{display:"grid",gridTemplateColumns:"1fr auto 1fr",gap:8,alignItems:"center",marginBottom:12,padding:12,borderRadius:8,background:"#0f1117"}}>
              <div><div style={{fontSize:10,color:"#5f6577",textTransform:"uppercase",letterSpacing:1}}>Output</div><div style={{fontWeight:600,fontSize:13}}>{cn(sel.from_company_id)}</div><div style={{fontSize:12,color:"#9aa0ad"}}>{sel.from_stream_name}</div><div style={{fontSize:11,color:"#5f6577"}}>{fromScale!==1?<><span style={{textDecoration:"line-through",opacity:0.5}}>{sel.available_flow_kton}</span> <span style={{color:"#e8eaed",fontWeight:600}}>{sAvail.toFixed(1)}</span></>:sel.available_flow_kton} kt/yr</div></div>
              <div style={{fontSize:20,color:"#5f6577"}}>→</div>
              <div style={{textAlign:"right"}}><div style={{fontSize:10,color:"#5f6577",textTransform:"uppercase",letterSpacing:1}}>Input</div><div style={{fontWeight:600,fontSize:13}}>{cn(sel.to_company_id)}</div><div style={{fontSize:12,color:"#9aa0ad"}}>{sel.to_stream_name}</div><div style={{fontSize:11,color:"#5f6577"}}>{toScale!==1?<><span style={{textDecoration:"line-through",opacity:0.5}}>{sel.required_flow_kton}</span> <span style={{color:"#e8eaed",fontWeight:600}}>{sReq.toFixed(1)}</span></>:sel.required_flow_kton} kt/yr</div></div>
            </div>
            <div style={{display:"flex",gap:6,marginBottom:14}}>
              <button onClick={()=>setScale(sel.from_company_id,Math.round(matchSupplierFactor*100)/100)} style={{flex:1,padding:"7px 6px",borderRadius:6,border:"1px solid #2a2e3a",background:"#181b23",color:"#e8eaed",fontSize:10,cursor:"pointer",fontFamily:"inherit",lineHeight:1.3,textAlign:"center"}} title={`Set ${cn(sel.from_company_id)} scale to ×${matchSupplierFactor.toFixed(2)}`}>Scale supplier<br/><span style={{color:"#5B9BD5",fontWeight:600}}>×{matchSupplierFactor.toFixed(2)}</span></button>
              <button onClick={()=>setScale(sel.to_company_id,Math.round(matchReceiverFactor*100)/100)} style={{flex:1,padding:"7px 6px",borderRadius:6,border:"1px solid #2a2e3a",background:"#181b23",color:"#e8eaed",fontSize:10,cursor:"pointer",fontFamily:"inherit",lineHeight:1.3,textAlign:"center"}} title={`Set ${cn(sel.to_company_id)} scale to ×${matchReceiverFactor.toFixed(2)}`}>Scale receiver<br/><span style={{color:"#5B9BD5",fontWeight:600}}>×{matchReceiverFactor.toFixed(2)}</span></button>
            </div>
            </>;})()}
            <Scores r={sel}>
              <button onClick={()=>!inFlows(sel.from_stream_id,sel.to_stream_id)&&addFlow({from_company_id:sel.from_company_id,to_company_id:sel.to_company_id,from_stream_id:sel.from_stream_id,to_stream_id:sel.to_stream_id,from_stream_name:sel.from_stream_name,to_stream_name:sel.to_stream_name,flow_kton_per_year:Math.min(sel.available_flow_kton||0,sel.required_flow_kton||0),composite_score:sel.composite_score})} disabled={inFlows(sel.from_stream_id,sel.to_stream_id)} style={{marginTop:14,width:"100%",padding:"10px 16px",borderRadius:8,border:"none",background:inFlows(sel.from_stream_id,sel.to_stream_id)?"#181b23":"#4ade80",color:inFlows(sel.from_stream_id,sel.to_stream_id)?"#5f6577":"#0f1117",fontWeight:600,fontSize:13,cursor:inFlows(sel.from_stream_id,sel.to_stream_id)?"default":"pointer",fontFamily:"inherit"}}>{inFlows(sel.from_stream_id,sel.to_stream_id)?"Already in Flows":"Add to Flows"}</button>
              {(()=>{const o=data.streams.find(s=>s.stream_id===sel.from_stream_id),i=data.streams.find(s=>s.stream_id===sel.to_stream_id);return o&&i?<AiEval outStream={o} inStream={i} fromCo={data.companies.find(c=>c.company_id===sel.from_company_id)} toCo={data.companies.find(c=>c.company_id===sel.to_company_id)}/>:null;})()}
            </Scores>
          </div>
        </div>}

        {/* MANUAL PAIR */}
        {tab==="manual"&&<div style={{padding:16}}>
          <div style={{marginBottom:12}}><label style={{fontSize:11,color:"#5f6577",textTransform:"uppercase",letterSpacing:1,display:"block",marginBottom:4}}>Output Stream (supplier)</label><select value={outSid} onChange={e=>{setOutSid(e.target.value);setMResult(null);}} style={selStyle}><option value="">Select an output stream...</option>{outStreams.map(s=><option key={s.stream_id} value={s.stream_id}>{cn(s.company_id)} — {s.stream_name} ({s.stream_type})</option>)}</select></div>
          <div style={{marginBottom:12}}><label style={{fontSize:11,color:"#5f6577",textTransform:"uppercase",letterSpacing:1,display:"block",marginBottom:4}}>Input Stream (receiver)</label><select value={inSid} onChange={e=>{setInSid(e.target.value);setMResult(null);}} style={selStyle}><option value="">Select an input stream...</option>{inStreams.map(s=><option key={s.stream_id} value={s.stream_id}>{cn(s.company_id)} — {s.stream_name} ({s.stream_type})</option>)}</select></div>
          <button onClick={doEval} disabled={!outSid||!inSid} style={{width:"100%",padding:"10px 16px",borderRadius:8,border:"none",background:(!outSid||!inSid)?"#181b23":"#5B9BD5",color:(!outSid||!inSid)?"#5f6577":"#fff",fontWeight:600,fontSize:13,cursor:(!outSid||!inSid)?"not-allowed":"pointer",fontFamily:"inherit"}}>Evaluate Fit</button>
          {mResult&&<div style={{marginTop:16}}>
            <Scores r={mResult}>
              {mResult.shared_components.length===0&&<div style={{marginTop:10,padding:12,borderRadius:8,background:"#f871711a",fontSize:12,color:"#f87171"}}>No shared components found.</div>}
              <button onClick={()=>!inFlows(outSid,inSid)&&mOut&&mIn&&addFlow({from_company_id:mOut.company_id,to_company_id:mIn.company_id,from_stream_id:outSid,to_stream_id:inSid,from_stream_name:mOut.stream_name,to_stream_name:mIn.stream_name,flow_kton_per_year:Math.min(mOut.flow_kton_per_year||0,mIn.flow_kton_per_year||0),composite_score:mResult.composite_score})} disabled={inFlows(outSid,inSid)||!outSid||!inSid} style={{marginTop:14,width:"100%",padding:"10px 16px",borderRadius:8,border:"none",background:inFlows(outSid,inSid)?"#181b23":"#4ade80",color:inFlows(outSid,inSid)?"#5f6577":"#0f1117",fontWeight:600,fontSize:13,cursor:inFlows(outSid,inSid)?"default":"pointer",fontFamily:"inherit"}}>{inFlows(outSid,inSid)?"Already in Flows":"Add to Flows"}</button>
              {mOut&&mIn&&<AiEval outStream={mOut} inStream={mIn} fromCo={mFromCo} toCo={mToCo}/>}
            </Scores>
          </div>}
        </div>}

        {/* FLOWS */}
        {tab==="flows"&&<FlowsMgr flows={flows} companies={data.companies} onUpdate={updateFlow} onRemove={removeFlow} onExport={exportFlows}/>}
      </div>
    </div>
  </div>
  </div>);
}
