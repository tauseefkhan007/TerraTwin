/* TerraTwin landing interaction and OAuth-backed authentication gate. */
(function () {
    'use strict';

    const landing = document.getElementById('terratwin-landing');
    const auth = document.getElementById('terratwin-auth');
    if (!landing || !auth) return;

    const closeButton = document.getElementById('terratwin-auth-close');
    const demoButton = document.getElementById('terratwin-demo-auth');
    const githubButton = document.getElementById('terratwin-github-auth');
    const googleButton = document.getElementById('terratwin-google-auth');
    const status = document.getElementById('terratwin-auth-status');
    const workspace = document.getElementById('tab-home');
    const logoutButton = document.getElementById('terratwin-logout');
    const defaultApiBase = window.location.hostname
        ? `${window.location.protocol}//${window.location.hostname}:8001`
        : 'http://localhost:8001';
    const apiBase = (window.TERRATWIN_API_BASE || defaultApiBase).replace(/\/$/, '');

    function setStatus(message) {
        if (status) status.textContent = message;
    }

    function openAuth() {
        if (landing.hidden || !auth.hidden) return;
        auth.hidden = false;
        landing.setAttribute('aria-hidden', 'true');
        document.body.classList.add('tt-landing-locked');
        closeButton?.focus();
    }

    function closeAuth() {
        auth.hidden = true;
        landing.setAttribute('aria-hidden', 'false');
        document.body.classList.add('tt-landing-locked');
        landing.focus({ preventScroll: true });
    }

    function unlockSession(kind) {
        sessionStorage.setItem('terratwin-authenticated', kind);
        auth.hidden = true;
        landing.hidden = true;
        document.body.classList.remove('tt-landing-locked');
        if (logoutButton) logoutButton.hidden = false;
        workspace?.focus();
    }

    function unlockDemo() {
        unlockSession('demo');
    }

    function logout() {
        const kind = sessionStorage.getItem('terratwin-authenticated');
        if (kind === 'oauth') {
            fetch(`${apiBase}/auth/logout`, { method: 'POST', credentials: 'include' }).catch(() => {});
        }
        sessionStorage.removeItem('terratwin-authenticated');
        auth.hidden = true;
        landing.hidden = false;
        document.body.classList.add('tt-landing-locked');
        if (logoutButton) logoutButton.hidden = true;
        window.scrollTo({ top: 0, behavior: 'smooth' });
        landing.focus({ preventScroll: true });
    }

    async function startOAuth(provider) {
        setStatus(`Connecting to ${provider}…`);
        try {
            const health = await fetch(`${apiBase}/health`, { credentials: 'include' });
            if (!health.ok) throw new Error('Auth service unavailable');
            const config = await fetch(`${apiBase}/api/auth/config`, { credentials: 'include' });
            const configured = config.ok && (await config.json()).providers?.[provider];
            if (!configured) {
                setStatus(`${provider} OAuth is not configured yet. Add its client ID and secret to the backend environment.`);
                return;
            }
            const next = encodeURIComponent(window.location.href.split('?')[0]);
            window.location.assign(`${apiBase}/auth/${provider}?next_url=${next}`);
        } catch (error) {
            setStatus('The TerraTwin auth service is offline. Start the backend on port 8001, or use demo access.');
        }
    }

    async function syncOAuthSession() {
        try {
            const response = await fetch(`${apiBase}/api/me`, { credentials: 'include' });
            if (!response.ok) return;
            const payload = await response.json();
            if (payload.authenticated) unlockSession('oauth');
        } catch (error) {
            // The static dashboard remains usable in demo mode when the API is not running.
        }
    }

    landing.tabIndex = -1;
    landing.addEventListener('pointerdown', openAuth, { passive: true });
    landing.addEventListener('keydown', event => {
        if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            openAuth();
        }
    });
    closeButton?.addEventListener('click', closeAuth);
    auth.addEventListener('click', event => {
        if (event.target === auth) closeAuth();
    });
    demoButton?.addEventListener('click', unlockDemo);
    logoutButton?.addEventListener('click', logout);
    githubButton?.addEventListener('click', () => startOAuth('github'));
    googleButton?.addEventListener('click', () => startOAuth('google'));

    const existingSession = sessionStorage.getItem('terratwin-authenticated');
    if (existingSession === 'demo' || existingSession === 'oauth') {
        landing.hidden = true;
        document.body.classList.remove('tt-landing-locked');
        if (logoutButton) logoutButton.hidden = false;
    } else {
        document.body.classList.add('tt-landing-locked');
    }

    const query = new URLSearchParams(window.location.search);
    if (query.get('auth') === 'error') {
        auth.hidden = false;
        setStatus(`Authentication failed or is not configured (${query.get('reason') || 'unknown error'}).`);
        closeButton?.focus();
    } else if (existingSession !== 'demo') {
        syncOAuthSession();
    }
})();
