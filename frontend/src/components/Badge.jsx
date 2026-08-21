// Coloured pills for request priority and status values.
const TONES = {
  CRITICAL: "bg-[#fce7df] text-[#a5452d]",
  HIGH: "bg-[#fff0ce] text-[#a16312]",
  MEDIUM: "bg-[#e8eef1] text-[#49616b]",
  LOW: "bg-[#e6f0e8] text-[#39704c]",

  PENDING: "bg-[#f6eee1] text-[#906c3a]",
  ASSIGNED: "bg-[#e6eef1] text-[#416271]",
  IN_PROGRESS: "bg-[#e7effc] text-[#315b96]",
  RESOLVED: "bg-[#e3f0e5] text-[#39704c]",
  CANCELLED: "bg-[#ece7e0] text-[#8a8175]",
};

export default function Badge({ value }) {
  const tone = TONES[value] || TONES.MEDIUM;
  const label = value === "IN_PROGRESS" ? "In progress" : value.charAt(0) + value.slice(1).toLowerCase();
  return (
    <span className={`rounded-full px-2.5 py-1 text-[10px] font-semibold ${tone}`}>{label}</span>
  );
}
