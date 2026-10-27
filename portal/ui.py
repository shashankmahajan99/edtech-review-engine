"""Shared workspace layout, introduced with the Studio redesign.

Other pages can adopt this shell in later UI stages without changing their
routes or application behavior.
"""
from html import escape

ASSET_VERSION = "20261026-turnitout"


def icon(name: str, size: int = 20) -> str:
    paths = {
        "logo": '<path d="m5 17 7-12 7 12M8 12h8M4 20h16"/>',
        "document": '<path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><path d="M14 3v6h6M8 13h8M8 17h5"/>',
        "queue": '<rect x="4" y="4" width="16" height="16" rx="3"/><path d="M8 9h8M8 13h8M8 17h4"/>',
        "home": '<path d="m3 10 9-7 9 7M5 9v11h14V9M9 20v-7h6v7"/>',
        "guide": '<path d="M12 6c-3-2-6-2-9-1v14c3-1 6-1 9 1 3-2 6-2 9-1V5c-3-1-6-1-9 1v14"/>',
        "arrow": '<path d="M5 12h14m-5-5 5 5-5 5"/>',
        "menu": '<path d="M4 6h16M4 12h16M4 18h16"/>',
    }
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
            f'stroke="currentColor" stroke-width="1.6" stroke-linecap="round" '
            f'stroke-linejoin="round" aria-hidden="true">{paths[name]}</svg>')


def workspace_page(title: str, content: str, user: dict | None = None,
                   active: str = "studio", scripts: tuple[str, ...] = ()) -> str:
    user = user or {}
    email = str(user.get("email") or "")
    display = str(user.get("full_name") or email or "Guest workspace")
    account_href = "/logout" if email else "/login"
    account_label = "Sign out" if email else "Sign in"
    links = [
        ("studio", "/thinkingstorm", "ThinkingStorm Studio", "document"),
        ("queue", "/reviewer", "Reviewer desk", "queue"),
        ("home", "/", "Apex home", "home"),
        ("guide", "/docs/capabilities", "Platform guide", "guide"),
    ]
    navigation = ""
    for key, href, label, symbol in links:
        current = ' aria-current="page"' if key == active else ''
        class_name = 'workspace-link is-current' if key == active else 'workspace-link'
        navigation += (f'<a class="{class_name}" href="{href}"{current}>'
                       f'{icon(symbol)}<span>{label}</span></a>')
    script_tags = "".join(f'<script src="/assets/{escape(name)}?v={ASSET_VERSION}" defer></script>' for name in scripts)
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="theme-color" content="#222536">
  <title>{escape(title)} · Apex Review</title>
  <link rel="stylesheet" href="/assets/workspace.css?v={ASSET_VERSION}">
  <script src="/assets/workspace.js?v={ASSET_VERSION}" defer></script>
  {script_tags}
</head>
<body class="apex-app">
  <a class="skip-link" href="#mainContent">Skip to content</a>
  <button id="navBackdrop" class="nav-backdrop" aria-label="Close navigation" hidden></button>
  <aside id="workspaceSidebar" class="workspace-sidebar" aria-label="Workspace navigation">
    <button id="navClose" class="nav-close" aria-label="Close navigation">×</button>
    <a class="workspace-brand" href="/thinkingstorm"><span class="brand-mark">{icon("logo", 25)}</span><span>Apex<span class="brand-subtitle">REVIEW DESK</span></span></a>
    <div class="nav-section-label">YOUR WORKSPACE</div>
    <nav class="workspace-navigation" aria-label="Main navigation">{navigation}</nav>
    <div class="sidebar-note"><span class="sidebar-note-icon">{icon("guide")}</span><strong>A little guidance?</strong><p>Find your way around the review desk.</p><a href="/docs/capabilities">Explore the guide {icon("arrow", 15)}</a></div>
    <div class="sidebar-account"><span class="account-avatar">{escape(display[:1].upper())}</span><div><span class="account-name" title="{escape(display, quote=True)}">{escape(display)}</span><a href="{account_href}">{account_label}</a></div></div>
  </aside>
  <div class="workspace-body">
    <header class="workspace-topbar"><div class="topbar-location"><button id="navToggle" class="icon-button nav-toggle" aria-controls="workspaceSidebar" aria-expanded="false" aria-label="Open navigation">{icon("menu")}</button><a href="/thinkingstorm">Workspace</a><span aria-hidden="true">/</span><span>{escape(title)}</span></div><a class="topbar-help" href="/docs/capabilities">{icon("guide", 17)} Help &amp; guide</a></header>
    <main id="mainContent" class="workspace-main" tabindex="-1">{content}</main>
    <footer class="workspace-footer"><span>Apex Academic Review Desk</span><span>Thoughtful feedback. A clearer next draft.</span></footer>
  </div>
</body>
</html>'''
