/* TerraTwin landing interaction and static-MVP authentication gate. */
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

    function unlockDemo() {
        sessionStorage.setItem('terratwin-authenticated', 'demo');
        auth.hidden = true;
        landing.hidden = true;
        document.body.classList.remove('tt-landing-locked');
        workspace?.focus();
    }

    function stagedProviderMessage(provider) {
        if (status) status.textContent = `${provider} OAuth is staged for the authenticated backend integration. Choose “Enter demo workspace” for this local MVP.`;
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
    githubButton?.addEventListener('click', () => stagedProviderMessage('GitHub'));
    googleButton?.addEventListener('click', () => stagedProviderMessage('Google'));

    if (sessionStorage.getItem('terratwin-authenticated') === 'demo') {
        landing.hidden = true;
        document.body.classList.remove('tt-landing-locked');
    } else {
        document.body.classList.add('tt-landing-locked');
    }
})();
