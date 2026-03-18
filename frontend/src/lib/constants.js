export const COLORS = [
  "#E8915A","#5B9BD5","#7BC67E","#D4A0D9","#E06C75",
  "#C9B458","#6CC1C8","#F28B82","#A4C9A4","#B8A9C9","#D4956B","#8BB8D0"
];

export const SC = (s) => s >= 0.7 ? "#4ade80" : s >= 0.5 ? "#facc15" : s >= 0.3 ? "#fb923c" : "#f87171";
export const SL = (s) => s >= 0.7 ? "Strong" : s >= 0.5 ? "Moderate" : s >= 0.3 ? "Weak" : "Poor";

export const SS = {
  candidate: { bg: "#facc1522", c: "#facc15", l: "Candidate" },
  confirmed:  { bg: "#4ade8022", c: "#4ade80", l: "Confirmed" },
  rejected:   { bg: "#f8717122", c: "#f87171", l: "Rejected"  },
};
