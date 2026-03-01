/**
 * RheXa AI — Premium Embeddable Chat Widget (Shadow DOM Isolated)
 * (c) 2024 RheXa Org. All rights reserved.
 */
(function () {
    const script = document.currentScript;
    const widgetKey = script.getAttribute('data-widget-key');
    const apiBase = script.getAttribute('data-api-url') || (window.location.origin.includes('localhost') ? 'http://127.0.0.1:8000' : 'https://rhexa-api.onrender.com');

    if (!widgetKey) return;

    fetch(`${apiBase}/api/widget/config/${widgetKey}`)
        .then(r => r.json())
        .then(cfg => { if (cfg.is_enabled) initWidget(cfg); })
        .catch(err => console.error('RheXa Widget Error:', err));

    function initWidget(config) {
        const themeColor = config.theme_color || '#6366f1';
        const isRight = config.position ? config.position.includes('right') : true;

        // ─── HOST ELEMENT (outside Shadow DOM, positions the widget) ───
        const host = document.createElement('div');
        host.id = 'rhexa-widget-host';
        host.style.cssText = `
            position: fixed !important;
            ${isRight ? 'right: 24px !important;' : 'left: 24px !important;'}
            bottom: 24px !important;
            z-index: 2147483647 !important;
            width: auto !important;
            height: auto !important;
            margin: 0 !important;
            padding: 0 !important;
            border: none !important;
            background: none !important;
            font-size: 16px !important;
            line-height: 1.5 !important;
            box-sizing: border-box !important;
            display: flex !important;
            flex-direction: column !important;
            align-items: ${isRight ? 'flex-end' : 'flex-start'} !important;
            pointer-events: auto !important;
        `;
        document.body.appendChild(host);

        // ─── SHADOW DOM (full CSS isolation) ───
        const shadow = host.attachShadow({ mode: 'open' });

        // ─── STYLES ───
        const css = `
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

            :host {
                all: initial;
                font-family: 'Inter', system-ui, -apple-system, sans-serif;
                color: #1f2937;
                box-sizing: border-box;
            }

            *, *::before, *::after {
                box-sizing: border-box;
                margin: 0;
                padding: 0;
            }

            /* ─── THEME VARIABLES ─── */
            .rhexa-root {
                --rh-primary: ${themeColor};
                --rh-bg: #ffffff;
                --rh-bg-secondary: #f9fafb;
                --rh-text: #1f2937;
                --rh-text-secondary: #6b7280;
                --rh-border: #e5e7eb;
                --rh-input-bg: #f9fafb;
                --rh-input-text: #111827;
                --rh-input-placeholder: #9ca3af;
                --rh-msg-bot-bg: #f3f4f6;
                --rh-msg-bot-text: #1f2937;
                --rh-shadow: 0 25px 60px -12px rgba(0, 0, 0, 0.25);
                --rh-header-overlay: rgba(255,255,255,0.08);
            }

            .rhexa-root.dark {
                --rh-bg: #0f172a;
                --rh-bg-secondary: #1e293b;
                --rh-text: #f1f5f9;
                --rh-text-secondary: #94a3b8;
                --rh-border: #334155;
                --rh-input-bg: #1e293b;
                --rh-input-text: #f1f5f9;
                --rh-input-placeholder: #64748b;
                --rh-msg-bot-bg: #1e293b;
                --rh-msg-bot-text: #e2e8f0;
                --rh-shadow: 0 25px 60px -12px rgba(0, 0, 0, 0.6);
                --rh-header-overlay: rgba(0,0,0,0.15);
            }

            /* ─── CHAT BUBBLE (FUTURISTIC RGB BORDER) ─── */
            .rh-bubble {
                width: 54px;
                height: 54px;
                border-radius: 50%;
                background: var(--rh-primary);
                display: flex;
                align-items: center;
                justify-content: center;
                cursor: pointer;
                color: #fff;
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
                border: none;
                outline: none;
                position: relative;
                z-index: 10;
            }

            /* The spinning gradient layer (Ultra-thin & Professional) */
            .rh-bubble::before {
                content: '';
                position: absolute;
                inset: -1px; /* Whisper-thin 1px border */
                border-radius: 50%;
                background: conic-gradient(
                    from 0deg, 
                    #ffffff, #a1a1aa, #18181b, #ffffff, #52525b, #ffffff
                );
                z-index: -2;
                animation: rh-spin 4s linear infinite;
            }

            /* The mask to hollow out the gradient and keep only the 1px edge */
            .rh-bubble::after {
                content: '';
                position: absolute;
                inset: 0px; 
                border-radius: 50%;
                background: var(--rh-primary);
                z-index: -1;
            }

            /* An extra subtle outer glow for depth */
            .rh-bubble-glow {
                position: absolute;
                inset: -2px;
                border-radius: 50%;
                background: conic-gradient(
                    from 0deg, 
                    rgba(255,255,255,0.8), rgba(0,0,0,0.5), rgba(255,255,255,0.8)
                );
                z-index: -3;
                filter: blur(4px);
                opacity: 0.4;
                animation: rh-spin 4s linear infinite;
            }

            @keyframes rh-spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            .rh-bubble img {
                width: 100%;
                height: 100%;
                border-radius: 50%;
                object-fit: cover;
                pointer-events: none;
            }
            .rh-bubble svg { pointer-events: none; }


            /* ─── CHAT WINDOW ─── */
            .rh-window {
                width: 400px;
                height: 620px;
                max-height: calc(100vh - 100px);
                background: var(--rh-bg);
                border-radius: 20px;
                box-shadow: var(--rh-shadow);
                margin-bottom: 16px;
                display: none;
                flex-direction: column;
                overflow: hidden;
                border: 1px solid var(--rh-border);
                opacity: 0;
                transform: translateY(16px) scale(0.96);
                transition: opacity 0.35s ease, transform 0.35s ease;
            }
            .rh-window.open {
                display: flex;
                opacity: 1;
                transform: translateY(0) scale(1);
            }

            /* ─── HEADER ─── */
            .rh-header {
                padding: 20px 22px;
                background: var(--rh-primary);
                color: #fff;
                display: flex;
                align-items: center;
                justify-content: space-between;
                position: relative;
                flex-shrink: 0;
            }
            .rh-header::after {
                content: '';
                position: absolute;
                inset: 0;
                background: linear-gradient(135deg, var(--rh-header-overlay), transparent);
                pointer-events: none;
            }
            .rh-header-info {
                display: flex;
                align-items: center;
                gap: 12px;
            }
            .rh-header-logo {
                width: 38px;
                height: 38px;
                border-radius: 50%;
                border: 2px solid rgba(255,255,255,0.2);
                object-fit: cover;
            }
            .rh-header-text {
                display: flex;
                flex-direction: column;
            }
            .rh-header-text h4 {
                margin: 0;
                font-size: 17px;
                font-weight: 700;
                letter-spacing: -0.3px;
                color: #fff;
            }
            .rh-status {
                display: flex;
                align-items: center;
                gap: 6px;
                font-size: 12px;
                opacity: 0.9;
                margin-top: 3px;
                color: #fff;
            }
            .rh-status-dot {
                width: 7px;
                height: 7px;
                background: #34d399;
                border-radius: 50%;
                display: inline-block;
                box-shadow: 0 0 8px #34d399;
            }
            .rh-header-actions {
                display: flex;
                align-items: center;
                gap: 8px;
                z-index: 1;
            }
            .rh-header-btn {
                width: 34px;
                height: 34px;
                border-radius: 10px;
                background: rgba(255,255,255,0.15);
                border: none;
                color: #fff;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: background 0.2s;
            }
            .rh-header-btn:hover { background: rgba(255,255,255,0.25); }

            /* ─── MESSAGES ─── */
            .rh-messages {
                flex: 1;
                overflow-y: auto;
                padding: 20px;
                background: var(--rh-bg);
                display: flex;
                flex-direction: column;
                gap: 14px;
                scrollbar-width: thin;
                scrollbar-color: var(--rh-border) transparent;
            }
            .rh-messages::-webkit-scrollbar { width: 4px; }
            .rh-messages::-webkit-scrollbar-thumb { background: var(--rh-border); border-radius: 99px; }

            .rh-msg {
                max-width: 82%;
                padding: 12px 16px;
                font-size: 14px;
                line-height: 1.6;
                border-radius: 18px;
                animation: rh-slide-in 0.25s ease-out;
                word-wrap: break-word;
                color: var(--rh-msg-bot-text);
            }
            @keyframes rh-slide-in {
                from { opacity: 0; transform: translateY(8px); }
                to { opacity: 1; transform: translateY(0); }
            }
            .rh-msg-user {
                background: var(--rh-primary);
                color: #fff;
                align-self: flex-end;
                border-bottom-right-radius: 4px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }
            .rh-msg-bot {
                background: var(--rh-msg-bot-bg);
                color: var(--rh-msg-bot-text);
                align-self: flex-start;
                border-bottom-left-radius: 4px;
                border: 1px solid var(--rh-border);
            }

            /* ─── TYPING INDICATOR ─── */
            .rh-typing {
                padding: 8px 20px;
                display: none;
                align-items: center;
                gap: 5px;
                background: var(--rh-bg);
                flex-shrink: 0;
            }
            .rh-typing.active { display: flex; }
            .rh-typing-dot {
                width: 6px;
                height: 6px;
                background: var(--rh-text-secondary);
                border-radius: 50%;
                animation: rh-bounce 1.4s infinite ease-in-out both;
            }
            .rh-typing-dot:nth-child(2) { animation-delay: 0.16s; }
            .rh-typing-dot:nth-child(3) { animation-delay: 0.32s; }
            @keyframes rh-bounce {
                0%, 80%, 100% { transform: scale(0.4); opacity: 0.4; }
                40% { transform: scale(1); opacity: 1; }
            }

            /* ─── INPUT AREA ─── */
            .rh-input-area {
                padding: 16px 18px;
                background: var(--rh-bg);
                border-top: 1px solid var(--rh-border);
                display: flex;
                gap: 10px;
                align-items: center;
                flex-shrink: 0;
            }
            .rh-input {
                flex: 1;
                border: 1.5px solid var(--rh-border);
                background: var(--rh-input-bg);
                color: var(--rh-input-text);
                -webkit-text-fill-color: var(--rh-input-text);
                border-radius: 14px;
                padding: 11px 16px;
                outline: none;
                font-size: 14px;
                font-family: 'Inter', system-ui, -apple-system, sans-serif;
                transition: border-color 0.2s, box-shadow 0.2s;
                opacity: 1;
                appearance: none;
                -webkit-appearance: none;
            }
            .rh-input::placeholder {
                color: var(--rh-input-placeholder);
                -webkit-text-fill-color: var(--rh-input-placeholder);
                opacity: 1;
            }
            .rh-input:focus {
                border-color: var(--rh-primary);
                box-shadow: 0 0 0 3px color-mix(in srgb, var(--rh-primary) 15%, transparent);
            }
            .rh-send-btn {
                width: 42px;
                height: 42px;
                border-radius: 12px;
                background: var(--rh-primary);
                color: #fff;
                border: none;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: all 0.2s;
                flex-shrink: 0;
            }
            .rh-send-btn:hover { transform: translateY(-1px); box-shadow: 0 4px 14px rgba(0,0,0,0.15); }
            .rh-send-btn svg { pointer-events: none; }

            /* ─── BRANDING ─── */
            .rh-branding {
                text-align: center;
                padding: 8px;
                font-size: 10px;
                color: var(--rh-text-secondary);
                text-decoration: none;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 1.2px;
                background: var(--rh-bg-secondary);
                border-top: 1px solid var(--rh-border);
                display: block;
                flex-shrink: 0;
            }
            .rh-branding span { color: var(--rh-primary); font-weight: 800; }

            /* ─── RESPONSIVE ─── */
            @media (max-width: 480px) {
                :host {
                    right: 0 !important;
                    left: 0 !important;
                    bottom: 0 !important;
                    width: 100% !important;
                }
                .rh-window {
                    width: 100%;
                    height: 100dvh;
                    max-height: 100dvh;
                    border-radius: 0;
                    margin-bottom: 0;
                    position: fixed;
                    top: 0; left: 0; right: 0; bottom: 0;
                    border: none;
                }
                .rh-bubble {
                    position: fixed;
                    bottom: 20px;
                    ${isRight ? 'right: 20px;' : 'left: 20px;'}
                }
            }
        `;

        const styleEl = document.createElement('style');
        styleEl.textContent = css;
        shadow.appendChild(styleEl);

        // ─── ICON MAPPING ───
        const icons = {
            'MessageSquare': '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>',
            'MessageCircle': '<path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z"></path>',
            'Bot': '<rect width="18" height="14" x="3" y="6" rx="2"/><path d="M12 6V2"/><path d="M2 12h2"/><path d="M20 12h2"/><path d="M9 12v2"/><path d="M15 12v2"/>',
            'Sparkles': '<path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"/>',
            'Zap': '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>'
        };
        const bubbleSvg = `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">${icons[config.bubble_icon] || icons['MessageSquare']}</svg>`;

        // ─── HTML ───
        const root = document.createElement('div');
        root.className = 'rhexa-root';
        root.innerHTML = `
            <div class="rh-window" id="rh-window">
                <div class="rh-header">
                    <div class="rh-header-info">
                        <div class="rh-header-logo" style="display:flex;align-items:center;justify-content:center;background:rgba(255,255,255,0.1);color:#fff">${bubbleSvg}</div>
                        <div class="rh-header-text">
                            <h4>${config.bot_name || 'AI Assistant'}</h4>
                            <div class="rh-status">
                                <span class="rh-status-dot"></span>
                                Online
                            </div>
                        </div>
                    </div>
                    <div class="rh-header-actions">
                        <button class="rh-header-btn" id="rh-theme" title="Toggle theme">
                            <svg class="rh-icon-moon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path></svg>
                            <svg class="rh-icon-sun" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="display:none"><circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line><line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line></svg>
                        </button>
                        <button class="rh-header-btn" id="rh-close" title="Close">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
                        </button>
                    </div>
                </div>
                <div class="rh-messages" id="rh-messages">
                    <div class="rh-msg rh-msg-bot">${config.welcome_message || 'Hello! How can I help you today?'}</div>
                </div>
                <div class="rh-typing" id="rh-typing">
                    <span class="rh-typing-dot"></span>
                    <span class="rh-typing-dot"></span>
                    <span class="rh-typing-dot"></span>
                </div>
                <div class="rh-input-area">
                    <input type="text" class="rh-input" id="rh-input" placeholder="Ask anything..." autocomplete="off" />
                    <button class="rh-send-btn" id="rh-send" title="Send">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 2L11 13"></path><path d="M22 2L15 22L11 13L2 9L22 2Z"></path></svg>
                    </button>
                </div>
                ${config.show_branding ? '<a href="https://rhexa.ai" target="_blank" class="rh-branding">Powered by <span>RHEXA</span></a>' : ''}
            </div>
            <button class="rh-bubble" id="rh-bubble" title="Chat with us">
                <div class="rh-bubble-glow"></div>
                ${bubbleSvg}
            </button>
        `;
        shadow.appendChild(root);

        // ─── DOM REFS ───
        const bubble = shadow.getElementById('rh-bubble');
        const win = shadow.getElementById('rh-window');
        const closeBtn = shadow.getElementById('rh-close');
        const themeBtn = shadow.getElementById('rh-theme');
        const moonIcon = shadow.querySelector('.rh-icon-moon');
        const sunIcon = shadow.querySelector('.rh-icon-sun');
        const input = shadow.getElementById('rh-input');
        const sendBtn = shadow.getElementById('rh-send');
        const messages = shadow.getElementById('rh-messages');
        const typing = shadow.getElementById('rh-typing');

        // ─── THEME ───
        if (localStorage.getItem('rhexa_theme') === 'dark') {
            root.classList.add('dark');
            moonIcon.style.display = 'none';
            sunIcon.style.display = 'block';
        }

        themeBtn.addEventListener('click', () => {
            const isDark = root.classList.toggle('dark');
            localStorage.setItem('rhexa_theme', isDark ? 'dark' : 'light');
            moonIcon.style.display = isDark ? 'none' : 'block';
            sunIcon.style.display = isDark ? 'block' : 'none';
        });

        // ─── OPEN / CLOSE ───
        let sessionId = localStorage.getItem('rhexa_session_id');

        bubble.addEventListener('click', () => {
            if (win.classList.contains('open')) {
                win.classList.remove('open');
                setTimeout(() => { win.style.display = 'none'; }, 350);
            } else {
                win.style.display = 'flex';
                requestAnimationFrame(() => {
                    requestAnimationFrame(() => { win.classList.add('open'); });
                });
                if (window.innerWidth <= 480) bubble.style.display = 'none';
                input.focus();
            }
        });

        closeBtn.addEventListener('click', () => {
            win.classList.remove('open');
            setTimeout(() => {
                win.style.display = 'none';
                bubble.style.display = 'flex';
            }, 350);
        });

        // ─── MESSAGING ───
        const sendMessage = async () => {
            const text = input.value.trim();
            if (!text) return;

            input.value = '';
            appendMsg(text, 'user');
            typing.classList.add('active');
            messages.scrollTop = messages.scrollHeight;

            try {
                const res = await fetch(`${apiBase}/api/widget/chat`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'X-Widget-Key': widgetKey },
                    body: JSON.stringify({ message: text, session_id: sessionId })
                });
                const data = await res.json();
                typing.classList.remove('active');

                const reply = data.answer || "I'm sorry, I couldn't find a direct answer for that. How else can I assist you?";
                appendMsg(reply, 'bot');

                if (data.session_id) {
                    sessionId = data.session_id;
                    localStorage.setItem('rhexa_session_id', sessionId);
                }
            } catch (err) {
                typing.classList.remove('active');
                appendMsg("Connection issue — please try again in a moment.", 'bot');
            }
        };

        function appendMsg(text, type) {
            const el = document.createElement('div');
            el.className = `rh-msg rh-msg-${type}`;
            el.textContent = text;
            messages.appendChild(el);
            messages.scrollTop = messages.scrollHeight;
        }

        sendBtn.addEventListener('click', sendMessage);
        input.addEventListener('keydown', (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); } });
    }
})();
