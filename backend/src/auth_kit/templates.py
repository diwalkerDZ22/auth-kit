"""Textes et mise en page des mails. Remplaçables en entier ou en partie :

    from dataclasses import replace
    templates = replace(EmailTemplates(), brand_color="#0f766e", login=LinkEmail("Sign-in request", ...))
    AuthKit(..., templates=templates)
"""
import html
from dataclasses import dataclass, field

from auth_kit.ports import EmailMessage


@dataclass(frozen=True)
class LinkEmail:
    subject: str
    title: str
    intro: str
    button: str
    footer: str


@dataclass(frozen=True)
class EmailTemplates:
    brand_color: str = "#4f46e5"
    signup: LinkEmail = field(default_factory=lambda: LinkEmail(
        subject="Confirmez votre adresse email",
        title="Bienvenue !",
        intro="Il ne reste qu'une étape : confirmez votre adresse email pour activer votre compte.",
        button="Activer mon compte",
        footer="Si vous n'êtes pas à l'origine de cette inscription, ignorez ce mail.",
    ))
    login: LinkEmail = field(default_factory=lambda: LinkEmail(
        subject="Confirmez cette connexion",
        title="Nouvelle connexion",
        intro="Une connexion à votre compte a été demandée. Si c'est bien vous, approuvez-la :",
        button="Examiner la demande",
        footer=(
            "Ce n'est pas vous ? Ouvrez le lien et choisissez « Ce n'est pas moi », puis changez votre "
            "mot de passe : quelqu'un d'autre le connaît."
        ),
    ))
    reset: LinkEmail = field(default_factory=lambda: LinkEmail(
        subject="Réinitialisez votre mot de passe",
        title="Mot de passe oublié",
        intro="Une réinitialisation du mot de passe a été demandée. Choisissez-en un nouveau :",
        button="Choisir un mot de passe",
        footer="Si vous n'êtes pas à l'origine de cette demande, ignorez ce mail : rien ne change.",
    ))
    account_exists_subject: str = "Tentative d'inscription avec votre adresse"
    account_exists_title: str = "Vous avez déjà un compte"
    account_exists_intro: str = (
        "Quelqu'un (peut-être vous) a essayé de créer un compte avec cette adresse email, mais un compte "
        "existe déjà. Si c'est vous, connectez-vous ou utilisez « Mot de passe oublié »."
    )
    account_exists_footer: str = (
        "Sinon, vous pouvez ignorer ce mail : aucun compte n'a été créé et le vôtre n'a pas été modifié."
    )
    context_title: str = "Détails de la demande"
    context_date: str = "Date"
    context_ip: str = "Adresse IP"
    context_browser: str = "Navigateur"
    unknown: str = "inconnu"
    link_fallback: str = "Le bouton ne fonctionne pas ? Copiez ce lien dans votre navigateur :"

    def link_email(self, purpose: str) -> LinkEmail:
        return {"signup": self.signup, "login": self.login, "reset": self.reset}[purpose]


def _layout(templates: EmailTemplates, app_name: str, title: str, body_html: str) -> str:
    """Mise en page compatible clients mail : tableaux et styles en ligne uniquement."""
    e = html.escape
    return (
        '<!doctype html><html><body style="margin:0;padding:0;background:#f4f4f7;">'
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f4f4f7;padding:32px 12px;">'
        '<tr><td align="center">'
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        'style="max-width:520px;background:#ffffff;border-radius:16px;overflow:hidden;'
        'font-family:-apple-system,BlinkMacSystemFont,\'Segoe UI\',Roboto,Helvetica,Arial,sans-serif;color:#1f2937;">'
        f'<tr><td style="background:{e(templates.brand_color)};padding:20px 32px;color:#ffffff;'
        f'font-size:16px;font-weight:600;letter-spacing:0.2px;">{e(app_name)}</td></tr>'
        f'<tr><td style="padding:32px;"><h1 style="margin:0 0 16px;font-size:22px;line-height:1.3;">{e(title)}</h1>'
        f'{body_html}</td></tr>'
        '</table></td></tr></table></body></html>'
    )


def _p(text: str, muted: bool = False) -> str:
    color = "#6b7280" if muted else "#374151"
    size = "13px" if muted else "15px"
    return f'<p style="margin:0 0 16px;font-size:{size};line-height:1.6;color:{color};">{html.escape(text)}</p>'


def render_link_email(
    templates: EmailTemplates,
    app_name: str,
    to: str,
    url: str,
    purpose: str,
    context: dict[str, str | None] | None = None,
) -> EmailMessage:
    """Mail contenant un lien (signup, login, reset). context : détails de la demande (login)."""
    t = templates.link_email(purpose)
    safe_url = html.escape(url, quote=True)
    context_rows = ""
    context_text = ""
    if context:
        labels = {"date": templates.context_date, "ip": templates.context_ip, "browser": templates.context_browser}
        values = {key: (value or templates.unknown) for key, value in context.items()}
        rows = "".join(
            f'<tr><td style="padding:4px 12px 4px 0;color:#6b7280;font-size:13px;white-space:nowrap;">{html.escape(labels[k])}</td>'
            f'<td style="padding:4px 0;font-size:13px;color:#111827;">{html.escape(v[:150])}</td></tr>'
            for k, v in values.items()
        )
        context_rows = (
            '<table role="presentation" cellpadding="0" cellspacing="0" '
            'style="width:100%;margin:0 0 20px;background:#f9fafb;border:1px solid #e5e7eb;border-radius:10px;padding:12px 16px;">'
            f'<tr><td colspan="2" style="padding-bottom:6px;font-size:13px;font-weight:600;">{html.escape(templates.context_title)}</td></tr>'
            f'{rows}</table>'
        )
        context_text = templates.context_title + " :\n" + "\n".join(
            f"{labels[k]} : {v[:150]}" for k, v in values.items()
        )

    button = (
        f'<p style="margin:8px 0 24px;"><a href="{safe_url}" style="display:inline-block;background:{html.escape(templates.brand_color)};'
        'color:#ffffff;text-decoration:none;font-weight:600;font-size:15px;padding:12px 22px;border-radius:10px;">'
        f'{html.escape(t.button)}</a></p>'
    )
    body = (
        _p(t.intro) + context_rows + button + _p(t.footer, muted=True)
        + _p(templates.link_fallback, muted=True)
        + f'<p style="margin:0;font-size:12px;word-break:break-all;"><a href="{safe_url}" style="color:#6b7280;">{safe_url}</a></p>'
    )
    text_parts = [t.intro, url] + ([context_text] if context_text else []) + [t.footer]
    return EmailMessage(
        to=to,
        subject=t.subject,
        text="\n\n".join(text_parts),   # version texte : meilleure délivrabilité
        html=_layout(templates, app_name, t.title, body),
        purpose=purpose,
    )


def render_account_exists_email(templates: EmailTemplates, app_name: str, to: str) -> EmailMessage:
    body = _p(templates.account_exists_intro) + _p(templates.account_exists_footer, muted=True)
    return EmailMessage(
        to=to,
        subject=templates.account_exists_subject,
        text=f"{templates.account_exists_intro}\n\n{templates.account_exists_footer}",
        html=_layout(templates, app_name, templates.account_exists_title, body),
        purpose="account_exists",
    )
