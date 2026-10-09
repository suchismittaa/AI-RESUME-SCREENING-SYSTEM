// A verbatim resume quote (or GitHub fact) with the signal it supports and where it came from.
export default function EvidenceBlock({ item }) {
  return (
    <figure className="quote">
      <blockquote>{item.text}</blockquote>
      <figcaption>
        {item.signal ? <span className="chip chip-peach">{item.signal}</span> : null}
        <span className="muted">from {item.source || "resume"}</span>
      </figcaption>
    </figure>
  );
}
