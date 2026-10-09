export default function KpiCard({ label, value, note, variant = "", asName = false }) {
  return (
    <div className={`glass kpi ${variant}`}>
      <div className="kpi-label">{label}</div>
      <div className={`kpi-value ${asName ? "name" : ""}`}>{value}</div>
      {note ? <div className="kpi-note">{note}</div> : null}
    </div>
  );
}
