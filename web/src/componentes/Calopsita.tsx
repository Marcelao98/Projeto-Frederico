/** O Frederico: uma calopsita robô (crista amarela, bochecha laranja). */
export function Calopsita({ tamanho = 40 }: { tamanho?: number }) {
  return (
    <svg width={tamanho} height={tamanho} viewBox="0 0 64 64" aria-hidden="true">
      <path d="M30 14c-2-6 1-11 6-12-2 4-1 7 1 9 1-5 5-8 9-8-3 3-4 7-3 11Z" fill="var(--crista)" />
      <circle cx="32" cy="34" r="20" fill="var(--corpo)" />
      <circle cx="32" cy="34" r="20" fill="none" stroke="var(--corpo-borda)" strokeWidth="2" />
      <circle cx="24" cy="40" r="5.5" fill="var(--bochecha)" />
      <circle cx="40" cy="40" r="5.5" fill="var(--bochecha)" />
      <rect x="20" y="27" width="24" height="9" rx="4.5" fill="var(--visor)" />
      <circle cx="26" cy="31.5" r="2.2" fill="var(--crista)" />
      <circle cx="38" cy="31.5" r="2.2" fill="var(--crista)" />
      <path d="M29 39h6l-3 5Z" fill="var(--bico)" />
    </svg>
  );
}
