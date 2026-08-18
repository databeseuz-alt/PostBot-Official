/**
 * PostBot Official Website - Interactive Frontend Logic & Post Simulator
 */

// Multilingual Translations Dictionary
const translations = {
  uz: {
    nav_features: "Imkoniyatlar",
    nav_simulator: "Jonli Simulyator",
    nav_ai: "AI Yordamchi",
    nav_stats: "Statistika",
    nav_guide: "Qo'llanma",
    nav_faq: "FAQ",
    nav_open_bot: "Botga o'tish 🚀",
    
    hero_badge: "⚡ Telegram Kanallar Uchun #1 Boshqaruv & Avtomatlashtirish Boti",
    hero_title_1: "Telegram Kanallaringizni ",
    hero_title_accent: "Professional Darajada",
    hero_title_2: " Boshqaring",
    hero_desc: "Rich postlar, ChatGPT/Gemini AI tahrirchisi, avto imzo, suv belgilari, rejalashtirilgan nashr, turbo rejim va ko'p kanalli boshqaruv — barchasi bitta qulay botda.",
    hero_btn_start: "Botni ishga tushirish (Bepul)",
    hero_btn_demo: "Jonli Post Simulyatori 🎮",
    hero_pill_ai: "ChatGPT & Gemini AI Integratsiyasi",
    hero_pill_features: "20+ Kuchli Professional Funksiyalar",
    hero_pill_speed: "Tezkor, Ishonchli va Xavfsiz",

    sim_tag: "INTERAKTIV NAMOYISH",
    sim_title: "Post Tayyorlash Simulyatori",
    sim_subtitle: "Post yarating, tugmalar qo'shing, AI bilan sayqallang va Telegramda qanday ko'rinishini jonli ko'ring.",
    sim_tab_standard: "Oddiy Post",
    sim_tab_media: "Rasm & Media",
    sim_tab_poll: "Viktorina / Test",
    sim_label_text: "Post Matni (HTML/Emoji)",
    sim_placeholder_text: "Post matnini shu yerga yozing...\n\n🔥 <b>PostBot</b> yordamida kanalingizni rivojlantiring!\n👉 Batafsil quyidagi tugmada:",
    sim_btn_bold: "Qalin (B)",
    sim_btn_italic: "Kursiv (I)",
    sim_btn_link: "Havola",
    sim_btn_spoiler: "Spoiler",
    sim_label_button: "Inline Tugma (Nomi | Havola)",
    sim_label_sig: "Avtomatik Imzo",
    sim_label_wm: "Suv belgisi (Watermark)",
    sim_ai_btn: "✨ AI bilan mukammallashtirish",
    sim_ai_prompt_holder: "AI matnni chiroyli qiladi va emoji qo'shadi...",
    
    tg_channel_title: "Mening Telegram Kanalim",
    tg_subscribers: "12,450 obunachi",
    tg_inline_default: "Batafsil ma'lumot 🔗",
    
    feat_tag: "IMKONIYATLAR",
    feat_title: "Telegramdagi Eng Boy Funksiyalar To'plami",
    feat_subtitle: "Kanal administratorlari, marketologlar va kontent mualliflari uchun barcha qulayliklar.",
    filter_all: "Barchasi (20+)",
    filter_content: "Kontent & Media",
    filter_ai: "AI & Avtomatlashtirish",
    filter_ads: "Reklama & Kanallar",

    stats_users: "Foydalanuvchilar",
    stats_posts: "Nashr etilgan postlar",
    stats_channels: "Ulangan kanallar",
    stats_uptime: "Uptime & Ishonchlilik",

    steps_tag: "QADAM-BA-QADAM",
    steps_title: "Qanday Ishga Tushiriladi?",
    step_1_title: "1. Botni ishga tushiring",
    step_1_desc: "@PostBot ga kiring va /start buyrug'ini yuboring. O'zingizga qulay tilni tanlang.",
    step_2_title: "2. Kanalga admin qiling",
    step_2_desc: "Botni Telegram kanalingizga qo'shing va post chiqarish huquqini bering.",
    step_3_title: "3. Postlarni yarating & avtomatlashtiring",
    step_3_desc: "Shablonlar, AI yordamchi, jadval yoki turbo rejim bilan postlaringizni nashr qiling.",

    faq_tag: "SAVOLLARINGIZ BORMI?",
    faq_title: "Tez-tez Beriladigan Savollar",
    
    cta_title: "Kanal boshqaruvini bugunoq avtomatlashtiring",
    cta_desc: "Minglab muvaffaqiyatli kanal adminlari safiga qo'shiling va vaqtingizni tejang.",
    cta_btn: "Botni Bepul Ishga Tushirish 🚀"
  },

  ru: {
    nav_features: "Возможности",
    nav_simulator: "Онлайн Симулятор",
    nav_ai: "AI Помощник",
    nav_stats: "Статистика",
    nav_guide: "Инструкция",
    nav_faq: "FAQ",
    nav_open_bot: "Открыть бота 🚀",

    hero_badge: "⚡ Бот #1 для Управления и Автоматизации Telegram Каналов",
    hero_title_1: "Управляйте Telegram Каналами ",
    hero_title_accent: "на Профессиональном",
    hero_title_2: " Уровне",
    hero_desc: "Богатый редактор постов, AI-помощник Gemini/ChatGPT, авто-подпись, водяные знаки, отложенный постинг, турбо-режим и управление сетью каналов в одном боте.",
    hero_btn_start: "Запустить бота (Бесплатно)",
    hero_btn_demo: "Интерактивный Симулятор 🎮",
    hero_pill_ai: "Интеграция ChatGPT & Gemini AI",
    hero_pill_features: "Более 20 мощных функций",
    hero_pill_speed: "Быстро, Надежно и Безопасно",

    sim_tag: "ИНТЕРАКТИВНОЕ ДЕМО",
    sim_title: "Симулятор Создания Постов",
    sim_subtitle: "Создавайте посты, добавляйте кнопки, улучшайте с AI и сразу смотрите результат в Telegram.",
    sim_tab_standard: "Обычный пост",
    sim_tab_media: "Фото & Медиа",
    sim_tab_poll: "Опрос / Тест",
    sim_label_text: "Текст поста (HTML/Emoji)",
    sim_placeholder_text: "Введите текст поста здесь...\n\n🔥 Развивайте ваш канал с помощью <b>PostBot</b>!\n👉 Подробнее по кнопке ниже:",
    sim_btn_bold: "Жирный (B)",
    sim_btn_italic: "Курсив (I)",
    sim_btn_link: "Ссылка",
    sim_btn_spoiler: "Спойлер",
    sim_label_button: "Инлайн Кнопка (Текст | Ссылка)",
    sim_label_sig: "Автоматическая подпись",
    sim_label_wm: "Водяной знак (Watermark)",
    sim_ai_btn: "✨ Улучшить с помощью AI",
    sim_ai_prompt_holder: "AI сделает текст привлекательнее и расставит эмодзи...",

    tg_channel_title: "Мой Telegram Канал",
    tg_subscribers: "12,450 подписчиков",
    tg_inline_default: "Узнать подробнее 🔗",

    feat_tag: "ВОЗМОЖНОСТИ",
    feat_title: "Самый Богатый Набор Функций для Telegram",
    feat_subtitle: "Идеальный инструмент для администраторов каналов, маркетологов и авторов контента.",
    filter_all: "Все (20+)",
    filter_content: "Контент & Медиа",
    filter_ai: "AI & Автоматизация",
    filter_ads: "Реклама & Каналы",

    stats_users: "Пользователей",
    stats_posts: "Опубликовано постов",
    stats_channels: "Подключенных каналов",
    stats_uptime: "Аптайм & Надежность",

    steps_tag: "ШАГ ЗА ШАГОМ",
    steps_title: "Как Начать Работу?",
    step_1_title: "1. Запустите бота",
    step_1_desc: "Откройте @PostBot и отправьте команду /start. Выберите удобный язык интерфейса.",
    step_2_title: "2. Добавьте в канал",
    step_2_desc: "Сделайте бота администратором вашего Telegram канала с правами публикации.",
    step_3_title: "3. Создавайте & Автоматизируйте",
    step_3_desc: "Используйте шаблоны, AI-помощника, расписание или турбо-режим для публикаций.",

    faq_tag: "ВОПРОСЫ И ОТВЕТЫ",
    faq_title: "Часто Задаваемые Вопросы",

    cta_title: "Автоматизируйте управление каналом уже сегодня",
    cta_desc: "Присоединяйтесь к тысячам успешных администраторов и экономьте часы рутины каждый день.",
    cta_btn: "Запустить Бота Бесплатно 🚀"
  },

  en: {
    nav_features: "Features",
    nav_simulator: "Live Simulator",
    nav_ai: "AI Assistant",
    nav_stats: "Stats",
    nav_guide: "Guide",
    nav_faq: "FAQ",
    nav_open_bot: "Open in Telegram 🚀",

    hero_badge: "⚡ #1 Telegram Channel Management & Automation Suite",
    hero_title_1: "Manage Telegram Channels ",
    hero_title_accent: "Like a Pro",
    hero_title_2: " & Save Hours",
    hero_desc: "Rich post editor, Gemini & ChatGPT AI assistant, auto signature, watermarks, smart scheduling, turbo zero-click mode, and multi-channel networks.",
    hero_btn_start: "Start Bot (Free)",
    hero_btn_demo: "Interactive Post Simulator 🎮",
    hero_pill_ai: "Gemini & ChatGPT 4o AI Powered",
    hero_pill_features: "20+ Powerful Pro Features",
    hero_pill_speed: "Ultra Fast, Reliable & Secure",

    sim_tag: "INTERACTIVE DEMO",
    sim_title: "Live Telegram Post Builder",
    sim_subtitle: "Draft your post, add inline buttons, enhance with AI, and preview exactly how it appears on Telegram in real time.",
    sim_tab_standard: "Standard Post",
    sim_tab_media: "Photo & Media",
    sim_tab_poll: "Quiz / Test",
    sim_label_text: "Post Text (HTML / Emojis)",
    sim_placeholder_text: "Type your post here...\n\n🔥 Grow your Telegram channel with <b>PostBot</b>!\n👉 Click the button below to learn more:",
    sim_btn_bold: "Bold (B)",
    sim_btn_italic: "Italic (I)",
    sim_btn_link: "Link",
    sim_btn_spoiler: "Spoiler",
    sim_label_button: "Inline Button (Text | URL)",
    sim_label_sig: "Auto Signature",
    sim_label_wm: "Watermark Overlay",
    sim_ai_btn: "✨ Enhance with AI Assistant",
    sim_ai_prompt_holder: "AI will polish text, format layout, and add relevant emojis...",

    tg_channel_title: "My Official Channel",
    tg_subscribers: "12,450 subscribers",
    tg_inline_default: "Read More 🔗",

    feat_tag: "FEATURES",
    feat_title: "The Ultimate Feature Set for Telegram Creators",
    feat_subtitle: "Everything you need to automate, scale, and monetize your channels.",
    filter_all: "All (20+)",
    filter_content: "Content & Media",
    filter_ai: "AI & Automation",
    filter_ads: "Ads & Channels",

    stats_users: "Active Users",
    stats_posts: "Posts Published",
    stats_channels: "Connected Channels",
    stats_uptime: "Uptime & Reliability",

    steps_tag: "STEP BY STEP",
    steps_title: "How to Get Started?",
    step_1_title: "1. Start the Bot",
    step_1_desc: "Open @PostBot in Telegram and press /start. Select your preferred language.",
    step_2_title: "2. Add Bot as Admin",
    step_2_desc: "Add the bot to your Telegram channel as an administrator with posting permissions.",
    step_3_title: "3. Create & Automate",
    step_3_desc: "Publish instantly, use AI tools, setup scheduling queues, or turbo publish.",

    faq_tag: "HAVE QUESTIONS?",
    faq_title: "Frequently Asked Questions",

    cta_title: "Automate your channel workflow today",
    cta_desc: "Join thousands of successful channel owners and creators.",
    cta_btn: "Launch Bot for Free 🚀"
  }
};

let currentLang = 'uz';

// Change Language Function
function setLanguage(lang) {
  if (!translations[lang]) return;
  currentLang = lang;
  localStorage.setItem('postbot_lang', lang);

  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.getAttribute('data-i18n');
    if (translations[lang][key]) {
      if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') {
        el.placeholder = translations[lang][key];
      } else {
        el.innerHTML = translations[lang][key];
      }
    }
  });

  // Update current language label
  const labels = { uz: '🇺🇿 O\'zbekcha', ru: '🇷🇺 Русский', en: '🇬🇧 English' };
  const currentLangLabel = document.getElementById('current-lang-label');
  if (currentLangLabel) {
    currentLangLabel.textContent = labels[lang] || '🇺🇿 O\'zbekcha';
  }

  // Update active class in dropdown
  document.querySelectorAll('.lang-option').forEach(opt => {
    opt.classList.toggle('selected', opt.dataset.lang === lang);
  });
}

// Toast notification helper
function showToast(message, icon = '✅') {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.innerHTML = `<span>${icon}</span> <span>${message}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

// Initialize Application
document.addEventListener('DOMContentLoaded', () => {
  // 1. Language selector setup
  const savedLang = localStorage.getItem('postbot_lang') || 'uz';
  setLanguage(savedLang);

  const langBtn = document.getElementById('lang-btn');
  const langDropdown = document.getElementById('lang-dropdown');

  if (langBtn && langDropdown) {
    langBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      langDropdown.classList.toggle('active');
    });

    document.addEventListener('click', () => {
      langDropdown.classList.remove('active');
    });

    document.querySelectorAll('.lang-option').forEach(option => {
      option.addEventListener('click', () => {
        const lang = option.dataset.lang;
        setLanguage(lang);
        langDropdown.classList.remove('active');
        showToast(lang === 'uz' ? "Til o'zgartirildi!" : (lang === 'ru' ? "Язык переключен!" : "Language updated!"));
      });
    });
  }

  // 2. Mobile Navbar Toggle
  const mobileToggle = document.getElementById('mobile-toggle');
  const navLinks = document.getElementById('nav-links');
  if (mobileToggle && navLinks) {
    mobileToggle.addEventListener('click', () => {
      navLinks.classList.toggle('active');
    });
  }

  // 3. Navbar scroll blur effect
  window.addEventListener('scroll', () => {
    const navbar = document.querySelector('.navbar');
    if (navbar) {
      navbar.classList.toggle('scrolled', window.scrollY > 40);
    }
  });

  // 4. Interactive Post Simulator Logic
  initPostSimulator();

  // 5. Features Filter Logic
  initFeatureFilters();

  // 6. FAQ Accordion Logic
  initFAQ();

  // 7. Load Dynamic Stats from API
  fetchStats();
});

// Post Simulator Engine
function initPostSimulator() {
  const postTextInput = document.getElementById('sim-post-text');
  const postBtnInput = document.getElementById('sim-btn-text');
  const postSigInput = document.getElementById('sim-sig-text');
  const postWmInput = document.getElementById('sim-wm-text');

  const tgMsgText = document.getElementById('tg-msg-text');
  const tgInlineBtn = document.getElementById('tg-inline-btn');
  const tgSignature = document.getElementById('tg-signature');
  const tgWatermark = document.getElementById('tg-watermark');
  const tgMediaPreview = document.getElementById('tg-media-preview');

  const toggleSig = document.getElementById('toggle-sig');
  const toggleWm = document.getElementById('toggle-wm');
  const toggleMedia = document.getElementById('toggle-media');

  function updatePreview() {
    if (!tgMsgText) return;

    // Text formatting
    let rawText = postTextInput ? postTextInput.value : '';
    if (!rawText.trim()) {
      rawText = "Post matnini shu yerga yozing...\n\n🔥 <b>PostBot</b> bilan kanalingizni professional darajaga olib chiqing!";
    }
    tgMsgText.innerHTML = rawText;

    // Signature
    if (tgSignature && toggleSig) {
      if (toggleSig.checked && postSigInput && postSigInput.value.trim()) {
        tgSignature.style.display = 'block';
        tgSignature.textContent = postSigInput.value;
      } else {
        tgSignature.style.display = 'none';
      }
    }

    // Watermark
    if (tgWatermark && toggleWm) {
      if (toggleWm.checked && postWmInput && postWmInput.value.trim()) {
        tgWatermark.style.display = 'flex';
        tgWatermark.innerHTML = `<i class="fas fa-shield-alt"></i> ${postWmInput.value}`;
      } else {
        tgWatermark.style.display = 'none';
      }
    }

    // Media
    if (tgMediaPreview && toggleMedia) {
      tgMediaPreview.style.display = toggleMedia.checked ? 'flex' : 'none';
    }

    // Button
    if (tgInlineBtn && postBtnInput) {
      const btnVal = postBtnInput.value.trim();
      if (btnVal) {
        tgInlineBtn.parentElement.style.display = 'flex';
        tgInlineBtn.textContent = btnVal;
      } else {
        tgInlineBtn.parentElement.style.display = 'none';
      }
    }
  }

  // Event Listeners for Simulator Inputs
  if (postTextInput) postTextInput.addEventListener('input', updatePreview);
  if (postBtnInput) postBtnInput.addEventListener('input', updatePreview);
  if (postSigInput) postSigInput.addEventListener('input', updatePreview);
  if (postWmInput) postWmInput.addEventListener('input', updatePreview);
  if (toggleSig) toggleSig.addEventListener('change', updatePreview);
  if (toggleWm) toggleWm.addEventListener('change', updatePreview);
  if (toggleMedia) toggleMedia.addEventListener('change', updatePreview);

  // Formatting buttons (Bold, Italic, Link, Spoiler)
  document.querySelectorAll('.tool-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const tag = btn.dataset.tag;
      if (!postTextInput || !tag) return;

      const start = postTextInput.selectionStart;
      const end = postTextInput.selectionEnd;
      const selected = postTextInput.value.substring(start, end) || "matn";

      let replacement = "";
      if (tag === 'b') replacement = `<b>${selected}</b>`;
      else if (tag === 'i') replacement = `<i>${selected}</i>`;
      else if (tag === 'a') replacement = `<a href="https://t.me/postbot">${selected}</a>`;
      else if (tag === 'tg-spoiler') replacement = `<tg-spoiler>${selected}</tg-spoiler>`;

      postTextInput.setRangeText(replacement, start, end, 'end');
      updatePreview();
      showToast(`Format qo'shildi: <${tag}>`, '✨');
    });
  });

  // Reaction chip interactivity
  document.querySelectorAll('.tg-reaction-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      chip.classList.toggle('active');
      const countSpan = chip.querySelector('.count');
      if (countSpan) {
        let count = parseInt(countSpan.textContent) || 0;
        count = chip.classList.contains('active') ? count + 1 : count - 1;
        countSpan.textContent = count;
      }
    });
  });

  // AI Assistant Enhance Button
  const btnAiEnhance = document.getElementById('btn-ai-enhance');
  if (btnAiEnhance) {
    btnAiEnhance.addEventListener('click', async () => {
      if (!postTextInput) return;
      const originalText = postTextInput.value;
      
      btnAiEnhance.disabled = true;
      btnAiEnhance.innerHTML = `<i class="fas fa-spinner fa-spin"></i> AI ishlamoqda...`;

      try {
        const response = await fetch('/api/ai-preview', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text: originalText, lang: currentLang })
        });

        if (response.ok) {
          const data = await response.json();
          if (data.enhanced_text) {
            postTextInput.value = data.enhanced_text;
            updatePreview();
            showToast(currentLang === 'uz' ? "AI matnni chiroyli qildi!" : "AI улучшил ваш пост!", "🚀");
          }
        } else {
          // Fallback realistic AI enhancement
          fallbackAiEnhance(originalText);
        }
      } catch (err) {
        fallbackAiEnhance(originalText);
      } finally {
        btnAiEnhance.disabled = false;
        btnAiEnhance.innerHTML = `<i class="fas fa-magic"></i> <span data-i18n="sim_ai_btn">${translations[currentLang].sim_ai_btn}</span>`;
      }
    });
  }

  function fallbackAiEnhance(text) {
    const lines = (text || "PostBot - Telegram kanallaringiz uchun eng kuchli yordamchi").split('\n').filter(l => l.trim());
    const header = lines[0] || "🚀 Yangilik & Eksklyuziv";
    const polished = `✨ <b>${header.replace(/<[^>]*>?/gm, '')}</b>\n\n📌 Kanalingiz auditoriyasini qamrab oluvchi professional kontent.\n\n✅ <b>Afzalliklari:</b>\n• Yuqori qiziqish va qamrov\n• Chiroyli formatlash va zamonaviy uslub\n• Tezkor reaksiyalar va faollik\n\n💡 <i>@PostBot bilan har bir postingiz mukammal bo'ladi!</i>`;
    
    postTextInput.value = polished;
    updatePreview();
    showToast(currentLang === 'uz' ? "AI matnni chiroyli qildi!" : "AI улучшил ваш пост!", "🚀");
  }

  // Run initial preview
  updatePreview();
}

// Feature Filter Tabs
function initFeatureFilters() {
  const filterBtns = document.querySelectorAll('.filter-btn');
  const cards = document.querySelectorAll('.feature-card');

  filterBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      filterBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      const filter = btn.dataset.filter;
      cards.forEach(card => {
        if (filter === 'all' || card.dataset.category === filter) {
          card.style.display = 'flex';
          card.style.animation = 'fadeIn 0.4s ease';
        } else {
          card.style.display = 'none';
        }
      });
    });
  });
}

// FAQ Accordion
function initFAQ() {
  const faqItems = document.querySelectorAll('.faq-item');
  faqItems.forEach(item => {
    const question = item.querySelector('.faq-question');
    if (question) {
      question.addEventListener('click', () => {
        const isActive = item.classList.contains('active');
        faqItems.forEach(i => i.classList.remove('active'));
        if (!isActive) {
          item.classList.add('active');
        }
      });
    }
  });
}

// Fetch Live Statistics from Server API
async function fetchStats() {
  try {
    const res = await fetch('/api/stats');
    if (res.ok) {
      const data = await res.json();
      if (data.total_users) {
        animateCounter('stat-users', data.total_users);
      }
      if (data.total_posts) {
        animateCounter('stat-posts', data.total_posts);
      }
      if (data.active_channels) {
        animateCounter('stat-channels', data.active_channels);
      }
    }
  } catch (e) {
    // Graceful fallback defaults already in HTML
  }
}

function animateCounter(id, target) {
  const el = document.getElementById(id);
  if (!el) return;
  let count = 0;
  const speed = target / 30;
  const timer = setInterval(() => {
    count += speed;
    if (count >= target) {
      el.textContent = Number(target).toLocaleString() + "+";
      clearInterval(timer);
    } else {
      el.textContent = Math.floor(count).toLocaleString() + "+";
    }
  }, 30);
}
