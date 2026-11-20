import { useState } from 'react';

export default function TeamSearch({ value, onChange }) {
  const [editing, setEditing] = useState(false);
  const [field, setField] = useState({ source: value, text: value });
  // URL navigation may finish between keystrokes. Keep the active edit intact;
  // accept URL/back-navigation values when the user is not editing this field.
  if (field.source !== value) setField({ source: value, text: editing ? field.text : value });
  return <label className="search-field"><span className="sr-only">Search teams</span><input
    type="search" placeholder="Search a team…" value={field.text}
    onFocus={() => setEditing(true)}
    onBlur={() => { setEditing(false); setField({ source: value, text: value }); }}
    onChange={event => {
      const text = event.target.value;
      setField({ source: value, text });
      onChange(text);
    }}
  /></label>;
}
