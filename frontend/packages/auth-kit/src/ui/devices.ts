/** "Firefox · Windows" à partir du user-agent (approximatif, pour l'affichage seulement). */
export function describeDevice(userAgent: string | null | undefined): { label: string | null; mobile: boolean } {
  if (!userAgent) return { label: null, mobile: false }
  const browsers: [RegExp, string][] = [
    [/Edg\//, 'Edge'],
    [/OPR\//, 'Opera'],
    [/Firefox\//, 'Firefox'],
    [/Chrome\//, 'Chrome'],
    [/Safari\//, 'Safari'],
  ]
  const systems: [RegExp, string][] = [
    [/Android/, 'Android'],
    [/iPhone|iPad/, 'iOS'],
    [/Windows/, 'Windows'],
    [/Mac OS X/, 'macOS'],
    [/Linux/, 'Linux'],
  ]
  const browser = browsers.find(([re]) => re.test(userAgent))?.[1] ?? 'Navigateur'
  const os = systems.find(([re]) => re.test(userAgent))?.[1]
  return { label: os ? `${browser} · ${os}` : browser, mobile: /Android|iPhone|iPad|Mobile/.test(userAgent) }
}
