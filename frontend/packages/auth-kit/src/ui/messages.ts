/**
 * Textes de l'interface. Remplaçables par section, partiellement :
 *   <AuthUIProvider messages={{ login: { title: 'Sign in' } }}>
 * Les messages d'erreur du backend s'affichent tels quels (ils se traduisent côté backend).
 */
export const FR = {
  common: {
    backToLogin: 'Retour à la connexion',
    loading: 'Chargement…',
    unexpectedError: 'Une erreur inattendue est survenue.',
  },
  theme: {
    label: 'Thème',
    light: 'Clair',
    system: 'Système',
    dark: 'Sombre',
  },
  validation: {
    required: 'Champ obligatoire.',
    email: 'Adresse email invalide.',
    passwordMin: (n: number) => `Le mot de passe doit contenir au moins ${n} caractères.`,
    passwordMaxBytes: (n: number) => `Le mot de passe ne doit pas dépasser ${n} octets.`,
    username: 'De 3 à 30 caractères : lettres, chiffres, « _ », « . » ou « - ».',
    mismatch: 'Les deux mots de passe ne correspondent pas.',
    tooLong: 'Trop long.',
  },
  fields: {
    username: "Nom d'utilisateur",
    email: 'Email',
    fullName: 'Nom complet',
    fullNameOptional: 'Nom complet (facultatif)',
    password: 'Mot de passe',
    passwordConfirm: 'Confirmer le mot de passe',
    currentPassword: 'Mot de passe actuel',
    newPassword: 'Nouveau mot de passe',
    showPassword: 'Afficher le mot de passe',
    hidePassword: 'Masquer le mot de passe',
  },
  strength: {
    levels: ['Trop court', 'Faible', 'Correct', 'Bon', 'Excellent'],
    hint: 'Une phrase de plusieurs mots est plus sûre et plus facile à retenir.',
  },
  login: {
    title: 'Bon retour parmi nous',
    subtitle: 'Connectez-vous : un lien de confirmation vous sera envoyé par email.',
    subtitleDirect: 'Connectez-vous à votre compte.',
    forgot: 'Mot de passe oublié ?',
    submit: 'Se connecter',
    noAccount: 'Pas encore de compte ?',
    createAccount: 'Créer un compte',
    resendLink: "Renvoyer l'email de vérification",
    waitingTitle: 'Vérifiez vos emails',
    waitingSteps: [
      'Ouvrez le mail « Confirmez cette connexion ».',
      'Vérifiez l’heure, l’adresse IP et le navigateur indiqués.',
      'Cliquez sur « Oui, c’est moi » : cette page se connecte toute seule.',
    ],
    waitingHint: "Le lien peut être ouvert sur n'importe quel appareil, votre téléphone par exemple.",
    cancel: 'Annuler et recommencer',
    expired: 'Le lien de connexion a expiré, recommencez.',
  },
  register: {
    title: 'Créer un compte',
    subtitle: 'Quelques secondes suffisent. Vous confirmerez votre adresse par email.',
    usernameHint: '3 à 30 caractères : lettres, chiffres, « _ », « . » ou « - ».',
    submit: 'Créer mon compte',
    haveAccount: 'Déjà inscrit ?',
    signIn: 'Se connecter',
    closedTitle: 'Inscriptions fermées',
    closedText: "La création de compte n'est pas ouverte au public. Contactez un administrateur.",
    inboxTitle: 'Vérifiez votre boîte mail',
    inboxText: (email: string) => `Nous avons envoyé un email à ${email}. Suivez ses instructions pour continuer.`,
    resend: "Renvoyer l'email",
  },
  forgot: {
    title: 'Mot de passe oublié',
    subtitle: 'Saisissez votre email : vous recevrez un lien pour choisir un nouveau mot de passe.',
    submit: 'Envoyer le lien',
  },
  resend: {
    title: "Renvoyer l'email de vérification",
    subtitle: "Saisissez l'adresse utilisée à l'inscription.",
    submit: 'Renvoyer',
  },
  reset: {
    title: 'Nouveau mot de passe',
    subtitle: 'Choisissez un mot de passe solide. Toutes vos sessions ouvertes seront fermées.',
    submit: 'Enregistrer le mot de passe',
    missingTitle: 'Lien incomplet',
    missingText: 'Ce lien ne contient pas de jeton de réinitialisation.',
    requestNew: 'Demander un nouveau lien',
    doneTitle: 'Mot de passe modifié',
    signIn: 'Se connecter',
  },
  verify: {
    missingTitle: 'Lien incomplet',
    missingText: 'Ce lien ne contient pas de jeton de vérification.',
    confirmTitle: 'Confirmer votre adresse',
    confirmSubtitle: 'Un clic pour activer votre compte.',
    confirm: 'Confirmer mon adresse',
    loginTitle: 'Approuver cette connexion ?',
    loginSubtitle:
      "N'approuvez que si vous venez de vous connecter vous-même. Le mail indique l'heure, l'adresse IP et le navigateur de la demande.",
    approve: "Oui, c'est moi",
    deny: "Ce n'est pas moi",
    signupDoneTitle: 'Adresse confirmée',
    loginDoneTitle: 'Connexion approuvée',
    loginDoneText: "Vous pouvez fermer cet onglet : la page de connexion d'origine s'ouvre toute seule.",
    deniedTitle: 'Connexion bloquée',
    changePassword: 'Changer mon mot de passe',
    signIn: 'Se connecter',
  },
  profile: {
    role: 'Rôle',
    logout: 'Se déconnecter',
    profileTitle: 'Profil',
    profileDesc: 'Le nom affiché dans l’application.',
    save: 'Enregistrer',
    saved: 'Profil enregistré.',
    passwordTitle: 'Mot de passe',
    passwordDesc: 'Vos autres appareils seront déconnectés.',
    passwordSubmit: 'Changer le mot de passe',
    passwordSaved: 'Mot de passe modifié. Vos autres appareils ont été déconnectés.',
    devicesTitle: 'Appareils connectés',
    devicesDesc: 'Déconnectez un appareil que vous ne reconnaissez pas, puis changez votre mot de passe.',
    thisDevice: 'Cet appareil',
    unknownDevice: 'Appareil inconnu',
    unknownIp: 'IP inconnue',
    activeOn: (date: string) => `Actif le ${date}`,
    signedInOn: (date: string) => `connecté le ${date}`,
    disconnect: 'Déconnecter',
    disconnectOthers: 'Déconnecter tous les autres appareils',
  },
  admin: {
    title: 'Utilisateurs',
    count: (n: number) => `${n} compte${n > 1 ? 's' : ''}`,
    search: 'Rechercher par username ou email',
    columns: { user: 'Utilisateur', email: 'Email', role: 'Rôle', status: 'Statut', action: 'Action' },
    roleOf: (username: string) => `Rôle de ${username}`,
    active: 'Actif',
    disabled: 'Désactivé',
    unverified: 'Email non vérifié',
    you: 'Vous',
    disable: 'Désactiver',
    enable: 'Réactiver',
    empty: 'Aucun utilisateur trouvé.',
    page: (page: number, count: number) => `Page ${page} sur ${count}`,
    previous: 'Précédent',
    next: 'Suivant',
    deniedTitle: 'Accès refusé',
    deniedText: 'Votre rôle ne donne pas accès à cette page.',
  },
}

export type Messages = typeof FR
export type MessagesOverride = { [K in keyof Messages]?: Partial<Messages[K]> }

export function mergeMessages(base: Messages, override?: MessagesOverride): Messages {
  if (!override) return base
  const merged = { ...base } as Record<string, unknown>
  for (const [section, values] of Object.entries(override)) {
    merged[section] = { ...(base as Record<string, object>)[section], ...values }
  }
  return merged as Messages
}
