interface Props {
  value: string;
}

// The one recurring visual motif across the app: role/status rendered as
// a small rotated "stamp", echoing the admit/reject ledger the app
// actually implements. Modifier class matches the value directly.
export default function Badge({ value }: Props) {
  return <span className={`stamp stamp--${value}`}>{value}</span>;
}