/**
 * PostBot Full-Screen Simulator — Complete Interactive Post Builder Engine
 * Mirrors the actual bot's post creation flow with all features
 */

const SIM = {
  // Post State
  postText: '',
  buttons: [],         // [{text, url, row}]
  signature: '',
  signatureEnabled: true,
  watermarkText: '',
  watermarkEnabled: true,
  mediaEnabled: true,
  spoilerEnabled: false,
  silentMode: false,
  pinPost: false,
  protectContent: false,
  disableComments: false,
  autoDelete: '',
  firstReaction: '',
  selectedReactions: ['❤️'],
  scheduleDate: '',
  scheduleTime: '',
  captionAbove: false,
  mediaUrl: 'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=800&auto=format&fit=crop&q=80',

  // AI
  aiPrompt: '',

  // Active panel
  activePanel: 'text-editor',

  init() {
    this.bindSidebar();
    this.bindTextEditor();
    this.bindButtonBuilder();
    this.bindSettings();
    this.bindReactions();
    this.bindAI();
    this.bindSchedule();
    this.bindSignature();
    this.bindWatermark();
    this.bindMedia();
    this.bindPreviewActions();
    this.updatePreview();
  },

  // Sidebar Navigation
  bindSidebar() {
    document.querySelectorAll('.sidebar-btn[data-panel]').forEach(btn => {
      btn.addEventListener('click', () => {
        const panel = btn.dataset.panel;
        this.showPanel(panel);
        document.querySelectorAll('.sidebar-btn[data-panel]').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
      });
    });
  },

  showPanel(panelId) {
    this.activePanel = panelId;
    document.querySelectorAll('.editor-panel').forEach(p => p.classList.add('hidden'));
    const target = document.getElementById(panelId);
    if (target) target.classList.remove('hidden');
  },

  // Text Editor
  bindTextEditor() {
    const textarea = document.getElementById('sim-main-text');
    if (!textarea) return;

    textarea.addEventListener('input', () => {
      this.postText = textarea.value;
      this.updateCharCount();
      this.updatePreview();
    });

    // Formatting toolbar buttons
    document.querySelectorAll('.toolbar-btn[data-format]').forEach(btn => {
      btn.addEventListener('click', () => {
        const format = btn.dataset.format;
        this.applyFormat(format);
      });
    });
  },

  applyFormat(format) {
    const textarea = document.getElementById('sim-main-text');
    if (!textarea) return;
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const selected = textarea.value.substring(start, end) || 'matn';

    const formats = {
      'bold': { open: '<b>', close: '</b>' },
      'italic': { open: '<i>', close: '</i>' },
      'underline': { open: '<u>', close: '</u>' },
      'strike': { open: '<s>', close: '</s>' },
      'code': { open: '<code>', close: '</code>' },
      'pre': { open: '<pre>', close: '</pre>' },
      'link': { open: '<a href="https://t.me/">', close: '</a>' },
      'spoiler': { open: '<tg-spoiler>', close: '</tg-spoiler>' },
      'blockquote': { open: '<blockquote>', close: '</blockquote>' },
    };

    const f = formats[format];
    if (!f) return;

    const replacement = f.open + selected + f.close;
    textarea.setRangeText(replacement, start, end, 'end');
    this.postText = textarea.value;
    this.updateCharCount();
    this.updatePreview();
  },

  updateCharCount() {
    const counter = document.getElementById('char-counter');
    const textarea = document.getElementById('sim-main-text');
    if (!counter || !textarea) return;
    const len = textarea.value.length;
    counter.textContent = `${len} / 4096`;
    counter.className = 'char-counter' + (len > 3800 ? ' danger' : len > 3000 ? ' warning' : '');
  },

  // Button Builder
  bindButtonBuilder() {
    const addUrlBtn = document.getElementById('add-url-btn');
    const addReactionBtn = document.getElementById('add-reaction-btn');

    if (addUrlBtn) {
      addUrlBtn.addEventListener('click', () => {
        this.buttons.push({ text: 'Batafsil 🔗', url: 'https://t.me/', row: this.buttons.length });
        this.renderButtonList();
        this.updatePreview();
      });
    }
    if (addReactionBtn) {
      addReactionBtn.addEventListener('click', () => {
        this.buttons.push({ text: '👍 Foydali', url: '', type: 'reaction', row: this.buttons.length });
        this.renderButtonList();
        this.updatePreview();
      });
    }
  },

  renderButtonList() {
    const container = document.getElementById('btn-builder-list');
    if (!container) return;

    container.innerHTML = '';
    this.buttons.forEach((btn, i) => {
      const item = document.createElement('div');
      item.className = 'btn-builder-item';
      item.innerHTML = `
        <input class="sim-input" value="${this.escapeHtml(btn.text)}" placeholder="Tugma matni" data-idx="${i}" data-field="text">
        <input class="sim-input" value="${this.escapeHtml(btn.url || '')}" placeholder="${btn.type === 'reaction' ? 'Reaksiya' : 'URL havola'}" data-idx="${i}" data-field="url">
        <button class="remove-btn-item" data-idx="${i}"><i class="fas fa-trash-alt"></i></button>
      `;
      container.appendChild(item);
    });

    // Bind events for dynamic fields
    container.querySelectorAll('input[data-idx]').forEach(input => {
      input.addEventListener('input', () => {
        const idx = parseInt(input.dataset.idx);
        const field = input.dataset.field;
        if (this.buttons[idx]) {
          this.buttons[idx][field] = input.value;
          this.updatePreview();
        }
      });
    });

    container.querySelectorAll('.remove-btn-item').forEach(btn => {
      btn.addEventListener('click', () => {
        const idx = parseInt(btn.dataset.idx);
        this.buttons.splice(idx, 1);
        this.renderButtonList();
        this.updatePreview();
      });
    });
  },

  // Publish Settings
  bindSettings() {
    const toggleMap = {
      'toggle-silent': 'silentMode',
      'toggle-pin': 'pinPost',
      'toggle-protect': 'protectContent',
      'toggle-comments': 'disableComments',
      'toggle-caption-above': 'captionAbove',
      'toggle-spoiler': 'spoilerEnabled',
    };

    Object.entries(toggleMap).forEach(([id, key]) => {
      const el = document.getElementById(id);
      if (el) {
        el.addEventListener('click', () => {
          this[key] = !this[key];
          el.classList.toggle('active', this[key]);
          this.updatePreview();
        });
      }
    });

    // Auto-delete input
    const autoDeleteInput = document.getElementById('auto-delete-time');
    if (autoDeleteInput) {
      autoDeleteInput.addEventListener('input', () => {
        this.autoDelete = autoDeleteInput.value;
      });
    }
  },

  // Reactions
  bindReactions() {
    document.querySelectorAll('.reaction-pick').forEach(btn => {
      btn.addEventListener('click', () => {
        const emoji = btn.dataset.emoji;
        if (this.selectedReactions.includes(emoji)) {
          this.selectedReactions = this.selectedReactions.filter(e => e !== emoji);
          btn.classList.remove('selected');
        } else {
          this.selectedReactions.push(emoji);
          btn.classList.add('selected');
        }
        this.updatePreview();
      });
    });
  },

  // AI Assistant
  bindAI() {
    const aiInput = document.getElementById('ai-prompt-input');
    const aiSendBtn = document.getElementById('ai-send-btn');
    if (!aiInput || !aiSendBtn) return;

    const enhanceText = async (prompt) => {
      aiSendBtn.disabled = true;
      aiSendBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
      try {
        const res = await fetch('/api/ai-preview', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text: this.postText + '\n\nKo\'rsatma: ' + prompt, lang: 'uz' })
        });
        if (res.ok) {
          const data = await res.json();
          if (data.enhanced_text) {
            const textarea = document.getElementById('sim-main-text');
            if (textarea) {
              textarea.value = data.enhanced_text;
              this.postText = data.enhanced_text;
              this.updateCharCount();
              this.updatePreview();
            }
          }
        }
      } catch (e) {
        // Fallback
        this.aiLocalEnhance(prompt);
      }
      aiSendBtn.disabled = false;
      aiSendBtn.innerHTML = '<i class="fas fa-paper-plane"></i> Yuborish';
    };

    aiSendBtn.addEventListener('click', () => {
      if (aiInput.value.trim()) enhanceText(aiInput.value);
    });

    aiInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        if (aiInput.value.trim()) enhanceText(aiInput.value);
      }
    });

    // Quick actions
    document.querySelectorAll('.ai-quick-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const action = btn.dataset.action;
        enhanceText(action);
      });
    });
  },

  aiLocalEnhance(prompt) {
    const header = this.postText.split('\n')[0] || 'Yangilik';
    const clean = header.replace(/<[^>]*>/g, '');
    const enhanced = `✨ <b>${clean}</b>\n\n📌 Professional va sifatli kontent.\n\n✅ <b>Afzalliklari:</b>\n• Yuqori qiziqish va qamrov\n• Chiroyli formatlash va zamonaviy uslub\n• Tezkor reaksiyalar va faollik\n\n💡 <i>PostBot bilan kanalingizni professional darajaga olib chiqing!</i>`;
    const textarea = document.getElementById('sim-main-text');
    if (textarea) {
      textarea.value = enhanced;
      this.postText = enhanced;
      this.updateCharCount();
      this.updatePreview();
    }
  },

  // Schedule
  bindSchedule() {
    const dateInput = document.getElementById('schedule-date');
    const timeInput = document.getElementById('schedule-time');
    if (dateInput) dateInput.addEventListener('change', () => { this.scheduleDate = dateInput.value; });
    if (timeInput) timeInput.addEventListener('change', () => { this.scheduleTime = timeInput.value; });
  },

  // Signature
  bindSignature() {
    const toggle = document.getElementById('toggle-sig-main');
    const input = document.getElementById('sig-input');

    if (toggle) {
      toggle.addEventListener('click', () => {
        this.signatureEnabled = !this.signatureEnabled;
        toggle.classList.toggle('active', this.signatureEnabled);
        this.updatePreview();
      });
    }
    if (input) {
      input.addEventListener('input', () => {
        this.signature = input.value;
        this.updatePreview();
      });
    }
  },

  // Watermark
  bindWatermark() {
    const toggle = document.getElementById('toggle-wm-main');
    const input = document.getElementById('wm-input');

    if (toggle) {
      toggle.addEventListener('click', () => {
        this.watermarkEnabled = !this.watermarkEnabled;
        toggle.classList.toggle('active', this.watermarkEnabled);
        this.updatePreview();
      });
    }
    if (input) {
      input.addEventListener('input', () => {
        this.watermarkText = input.value;
        this.updatePreview();
      });
    }
  },

  // Media
  bindMedia() {
    const toggle = document.getElementById('toggle-media-main');
    if (toggle) {
      toggle.addEventListener('click', () => {
        this.mediaEnabled = !this.mediaEnabled;
        toggle.classList.toggle('active', this.mediaEnabled);
        this.updatePreview();
      });
    }
  },

  // Preview Send Button
  bindPreviewActions() {
    const sendBtn = document.getElementById('preview-send-btn');
    if (sendBtn) {
      sendBtn.addEventListener('click', () => {
        const msg = '✅ Post simulyatsiyasi muvaffaqiyatli! Haqiqiy postni yaratish uchun botga o\'ting.';
        alert(msg);
      });
    }

    // Reaction chips in preview
    document.addEventListener('click', (e) => {
      if (e.target.closest('.tg-post-reaction')) {
        e.target.closest('.tg-post-reaction').classList.toggle('selected');
        const countEl = e.target.closest('.tg-post-reaction').querySelector('.r-count');
        if (countEl) {
          let n = parseInt(countEl.textContent) || 0;
          const isSelected = e.target.closest('.tg-post-reaction').classList.contains('selected');
          countEl.textContent = isSelected ? n + 1 : Math.max(0, n - 1);
        }
      }
    });
  },

  // === MAIN PREVIEW RENDERER ===
  updatePreview() {
    const container = document.getElementById('preview-post-container');
    if (!container) return;

    let html = '';

    // Pin badge
    if (this.pinPost) {
      html += `<div class="tg-pin-badge"><i class="fas fa-thumbtack"></i> Mahkamlangan xabar</div>`;
    }

    html += '<div class="tg-post-bubble">';

    // Media
    if (this.mediaEnabled) {
      html += '<div class="tg-post-media">';
      if (this.spoilerEnabled) {
        html += '<div class="spoiler-overlay"><i class="fas fa-eye-slash"></i>&nbsp; Spoiler — bosing</div>';
      }
      html += `<img src="${this.mediaUrl}" alt="Media">`;
      if (this.watermarkEnabled && this.watermarkText) {
        html += `<div class="watermark-badge"><i class="fas fa-shield-alt"></i> ${this.escapeHtml(this.watermarkText)}</div>`;
      }
      html += '</div>';
    }

    // Caption above
    if (this.captionAbove && this.mediaEnabled) {
      html += this.renderTextBlock();
      // (media already rendered above)
    } else {
      html += this.renderTextBlock();
    }

    // Signature
    if (this.signatureEnabled && this.signature) {
      html += `<div class="tg-post-signature">${this.escapeHtml(this.signature)}</div>`;
    }

    // Footer (views + time)
    const now = new Date();
    const timeStr = now.getHours().toString().padStart(2, '0') + ':' + now.getMinutes().toString().padStart(2, '0');
    html += `<div class="tg-post-footer">`;
    if (this.protectContent) html += `<i class="fas fa-lock" title="Himoyalangan" style="margin-right:4px;"></i>`;
    html += `<span>1,240 <i class="fas fa-eye"></i></span>`;
    html += `<span>${timeStr}</span>`;
    html += `</div>`;

    // Inline buttons
    if (this.buttons.length > 0) {
      html += '<div class="tg-post-buttons">';
      this.buttons.forEach(btn => {
        html += '<div class="tg-post-btn-row">';
        html += `<button class="tg-post-inline-btn">${this.escapeHtml(btn.text)}</button>`;
        html += '</div>';
      });
      html += '</div>';
    }

    html += '</div>'; // end bubble

    // Reactions
    if (this.selectedReactions.length > 0) {
      html += '<div class="tg-post-reactions">';
      this.selectedReactions.forEach((emoji, i) => {
        const count = Math.floor(Math.random() * 80) + 10;
        html += `<div class="tg-post-reaction${i === 0 ? ' selected' : ''}"><span>${emoji}</span> <span class="r-count">${count}</span></div>`;
      });
      html += '</div>';
    }

    container.innerHTML = html;
  },

  renderTextBlock() {
    let text = this.postText;
    if (!text.trim()) {
      text = '<span style="color:#708499;">Post matnini chap paneldagi muharrirga yozing...</span>';
    }
    return `<div class="tg-post-content"><div class="tg-post-text">${text}</div></div>`;
  },

  escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
};

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
  // Set default text
  const textarea = document.getElementById('sim-main-text');
  if (textarea) {
    textarea.value = `🔥 <b>PostBot</b> — Telegram kanallarni boshqarish bo'yicha eng kuchli platforma!

✅ <b>Asosiy afzalliklari:</b>
• Avtomatik imzo va suv belgilari
• ChatGPT & Gemini AI integratsiyasi
• 10+ kanallarga bir vaqtda nashr qilish
• Aqlli jadval va takroriy postlar

👇 <i>Batafsil ma'lumot olish uchun quyidagi tugmani bosing:</i>`;
    SIM.postText = textarea.value;
  }

  // Default button
  SIM.buttons = [{ text: "Batafsil ma'lumot 🔗", url: 'https://t.me/posto_robot', row: 0 }];
  SIM.signature = '👉 @Posto_News | Barcha huquqlar himoyalangan';
  SIM.watermarkText = '@Posto_News';

  // Init everything
  SIM.init();
  SIM.renderButtonList();
  SIM.updateCharCount();

  // Set initial active states
  document.getElementById('toggle-sig-main')?.classList.add('active');
  document.getElementById('toggle-wm-main')?.classList.add('active');
  document.getElementById('toggle-media-main')?.classList.add('active');
  document.querySelectorAll('.reaction-pick').forEach(r => {
    if (SIM.selectedReactions.includes(r.dataset.emoji)) r.classList.add('selected');
  });
});
