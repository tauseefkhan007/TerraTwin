/* NAKSH cinematic intro: the user's scroll position scrubs the video timeline.
   Self-contained and defensive: if anything fails, the landing falls back to a
   static scene with working call-to-action buttons so the app is never blocked. */
(function () {
    'use strict';

    const landing = document.getElementById('terratwin-landing');
    const track = document.getElementById('tt-intro-track');
    const stage = document.getElementById('tt-intro-stage');
    const video = document.getElementById('tt-intro-video');
    if (!landing || !track || !stage || !video) return;

    const hint = document.getElementById('tt-intro-hint');
    const loader = document.getElementById('tt-intro-loader');
    const loaderFill = document.getElementById('tt-intro-loader-fill');
    const railFill = document.getElementById('tt-intro-rail-fill');
    const cta = document.getElementById('tt-intro-cta');
    const fallback = document.getElementById('tt-intro-fallback');
    const missionBtn = document.getElementById('tt-intro-mission-btn');
    const mission = document.getElementById('tt-intro-mission');

    const CTA_AT = 0.86;      // scroll progress at which the call to action appears
    const EASE = 0.28;        // faster catch-up keeps the scroll response close to 60/65 Hz
    const SEEK_THRESHOLD = 0.025;
    const FAST_SEEK_THRESHOLD = 0.75;
    const reducedMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    let duration = 0;
    let target = 0;           // scroll progress 0..1
    let current = 0;          // eased progress 0..1
    let raf = 0;
    let wantedTime = 0;
    let ready = false;
    let failed = false;
    let primed = false;

    function pickSource() {
        return 'assets/video/naksh-intro-scrub.mp4';
    }

    function showCta(on) {
        if (cta) cta.classList.toggle('is-on', on);
    }

    function fail(reason) {
        if (failed) return;
        failed = true;
        if (window.console) console.warn('NAKSH intro video unavailable, using static scene.', reason || (video.error && video.error.message) || '');
        landing.classList.add('tt-intro-static');
        video.hidden = true;
        if (fallback) fallback.hidden = false;
        if (loader) loader.hidden = true;
        showCta(true);
    }

    function hideLoader() {
        if (!loader || loader.classList.contains('is-done')) return;
        if (loaderFill) loaderFill.style.transform = 'scaleX(1)';
        loader.classList.add('is-done');
        window.setTimeout(function () { loader.hidden = true; }, 450);
    }

    function updateLoadProgress() {
        if (!duration || !loaderFill) return;
        try {
            const b = video.buffered;
            if (b.length) {
                const frac = Math.min(1, b.end(b.length - 1) / duration);
                loaderFill.style.transform = 'scaleX(' + frac.toFixed(3) + ')';
                if (frac >= 0.995) hideLoader();
            }
        } catch (e) { /* ignore */ }
    }

    function scrollProgress() {
        const span = track.offsetHeight - stage.offsetHeight;
        if (span <= 0) return 1;
        return Math.min(1, Math.max(0, landing.scrollTop / span));
    }

    function applyFrame() {
        if (!ready || !duration) return;
        // Stay just inside the last frame so the video never flips to its ended state.
        wantedTime = Math.min(duration - 0.04, Math.max(0, current * duration));
        const distance = Math.abs(video.currentTime - wantedTime);
        if (video.seeking || distance <= SEEK_THRESHOLD) return;
        if (distance >= FAST_SEEK_THRESHOLD && typeof video.fastSeek === 'function') {
            video.fastSeek(wantedTime);
        } else {
            video.currentTime = wantedTime;
        }
    }

    function pausePlayback() {
        if (!video.paused) video.pause();
        video.playbackRate = 1;
    }

    function paintUi() {
        if (hint) hint.style.opacity = String(Math.max(0, 1 - target * 28));
        if (railFill) railFill.style.transform = 'scaleY(' + target.toFixed(4) + ')';
        showCta(target >= CTA_AT);
    }

    function tick() {
        raf = 0;
        current += (target - current) * EASE;
        if (Math.abs(target - current) < 0.0004) current = target;
        applyFrame();
        if (current !== target) raf = window.requestAnimationFrame(tick);
    }

    function onScroll() {
        if (failed || reducedMotion) return;
        pausePlayback();
        target = scrollProgress();
        paintUi();
        if (!raf) raf = window.requestAnimationFrame(tick);
    }

    // iOS/Safari only let a video seek reliably after a user gesture has "touched" it.
    function prime() {
        if (primed) return;
        primed = true;
        try {
            const p = video.play();
            if (p && typeof p.then === 'function') {
                p.then(function () { video.pause(); applyFrame(); }).catch(function () { /* autoplay blocked: seeking still works */ });
            } else {
                video.pause();
            }
        } catch (e) { /* ignore */ }
    }

    function onMetadata() {
        duration = video.duration;
        if (!isFinite(duration) || duration <= 0) { fail('invalid duration'); return; }
        ready = true;
        video.pause();
        video.defaultPlaybackRate = 1;
        video.playbackRate = 1;
        if (reducedMotion) {
            // No scrubbing: show the closing frame and the call to action immediately.
            landing.classList.add('tt-intro-static');
            showCta(true);
            hideLoader();
            return;
        }
        target = scrollProgress();
        current = target;
        applyFrame();
        paintUi();
    }

    video.addEventListener('loadedmetadata', onMetadata);
    video.addEventListener('progress', updateLoadProgress);
    function showEndFrame() {
        if (!reducedMotion || !ready || !duration) return;
        const end = Math.max(0, duration - 0.05);
        if (Math.abs(video.currentTime - end) > 0.1) video.currentTime = end;
    }
    video.addEventListener('loadeddata', function () { updateLoadProgress(); showEndFrame(); window.setTimeout(hideLoader, 2500); });
    video.addEventListener('canplay', showEndFrame);
    video.addEventListener('canplaythrough', hideLoader);
    video.addEventListener('timeupdate', function () {
        if (video.paused || failed || reducedMotion || !duration) return;
        target = Math.min(1, Math.max(0, video.currentTime / duration));
        current = target;
        wantedTime = video.currentTime;
        paintUi();
    });
    video.addEventListener('ended', function () {
        video.pause();
        video.playbackRate = 1;
        target = 1;
        current = 1;
        paintUi();
    });
    video.addEventListener('seeked', function () {
        if (Math.abs(video.currentTime - wantedTime) > SEEK_THRESHOLD) applyFrame();
    });
    video.addEventListener('error', function () { fail(); });

    landing.addEventListener('scroll', onScroll, { passive: true });
    ['pointerdown', 'touchstart', 'keydown', 'wheel'].forEach(function (name) {
        landing.addEventListener(name, prime, { once: true, passive: true });
    });
    window.addEventListener('resize', onScroll, { passive: true });

    if (missionBtn && mission) {
        missionBtn.addEventListener('click', function () {
            prime();
            landing.scrollTo({ top: mission.offsetTop, behavior: reducedMotion ? 'auto' : 'smooth' });
        });
    }

    // When the landing is shown again (log out) restart from the beginning of the journey.
    new MutationObserver(function () {
        if (!landing.hidden) {
            pausePlayback();
            landing.scrollTop = 0;
            target = 0;
            current = 0;
            paintUi();
            applyFrame();
        }
    }).observe(landing, { attributes: true, attributeFilter: ['hidden'] });

    // Safety nets: slow/blocked media must never trap the visitor.
    window.setTimeout(function () { if (!ready && !failed) fail('timeout'); }, 12000);

    // Download the whole clip first and play it from memory. Scrubbing needs instant random
    // seeks, which do not work on servers without HTTP Range support (e.g. python -m http.server).
    function attachDirect(url) {
        video.src = url;
        video.load();
    }

    function loadVideo(url) {
        if (!window.fetch || !window.URL || location.protocol === 'file:') { attachDirect(url); return; }
        const type = /\.webm$/.test(url) ? 'video/webm' : 'video/mp4';
        fetch(url).then(function (res) {
            if (!res.ok) throw new Error('HTTP ' + res.status);
            const total = Number(res.headers.get('content-length')) || 0;
            if (!res.body || !res.body.getReader || !total) return res.blob();
            const reader = res.body.getReader();
            const chunks = [];
            let received = 0;
            function pump() {
                return reader.read().then(function (r) {
                    if (r.done) return new Blob(chunks, { type: type });
                    chunks.push(r.value);
                    received += r.value.length;
                    if (loaderFill) loaderFill.style.transform = 'scaleX(' + Math.min(1, received / total).toFixed(3) + ')';
                    return pump();
                });
            }
            return pump();
        }).then(function (blob) {
            video.src = URL.createObjectURL(new Blob([blob], { type: type }));
            video.load();
        }).catch(function () { attachDirect(url); });
    }

    loadVideo(pickSource());
    if (reducedMotion) showCta(true);
    paintUi();
})();
