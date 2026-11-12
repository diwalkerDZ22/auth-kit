/** Score 0 à 4, approximatif : longueur et variété (le backend reste juge). */
export function passwordScore(password: string, minLength = 8): number {
  if (!password || password.length < minLength) return 0
  const variety = [/[a-z]/, /[A-Z]/, /\d/, /[^A-Za-z0-9]/, /\s/].filter((re) => re.test(password)).length
  let score = 1
  if (password.length >= 12) score++
  if (password.length >= 16) score++
  if (variety >= 3 || password.split(/\s+/).length >= 3) score++
  return Math.min(score, 4)
}
