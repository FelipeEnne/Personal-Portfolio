(function () {
  const CV_LINKS = {
    en: 'assets/doc/CV.pdf',
    pt: 'assets/doc/Currículo.pdf',
  };

  const translations = {
    en: {
      'nav.projects': 'Projects',
      'nav.contact': 'Contact',
      'nav.linkedin': 'LinkedIn',
      'nav.github': 'GitHub',
      'bio':
        'Full Stack Developer with 5+ years of experience building web applications, REST APIs, internal tools, automations, and integrations using JavaScript, TypeScript, Node.js, React, Python, PostgreSQL, MongoDB, and Salesforce.<br>Check out my <a href="#project">side-projects</a> below.',
      'terminal.location': 'Jacareí/SP, Brazil',
      'terminal.education':
        'Master\'s Degree in Logistics Systems Engineering — USP<br>Full Stack Web Development — Microverse',
      'terminal.skills':
        '[ "JavaScript", "TypeScript", "Python", "Node.js", "Express", "React", "PostgreSQL", "MongoDB", "Salesforce", "Docker", "Jest", "Git" ]',
      'terminal.resumeLabel': 'felipeenne.pdf',
      'projects.title': 'Projects',
      'proj.audiobook.title': 'Audiobook Production Automation',
      'proj.audiobook.desc':
        'Personal project for producing and publishing audiobooks at scale on YouTube, using Python, FastAPI, local TTS, and the YouTube API to automate audio generation, file organization, thumbnails, descriptions, playlists, and scheduled publishing.',
      'proj.audiobook.link': 'YouTube',
      'proj.wine.title': 'Wine Recommendation',
      'proj.wine.desc':
        'Wine recommendation system developed with Python/Jupyter, focused on data analysis, data processing, and recommendation logic based on product characteristics.',
      'proj.climb.title': 'Climbing the Volcano',
      'proj.climb.desc':
        '2D game developed with JavaScript and Phaser, including collision logic, item collection, character movement, and tests with Jest. Focused on frontend practice, programming logic, and interactive application structure.',
      'proj.demo': 'Demo',
      'proj.github': 'Github link',
      'contact.title': 'Contact me!',
      'footer.madeby': 'Made by Felipe Enne Mendes Ribeiro 2026',
    },
    pt: {
      'nav.projects': 'Projetos',
      'nav.contact': 'Contato',
      'nav.linkedin': 'LinkedIn',
      'nav.github': 'GitHub',
      'bio':
        'Desenvolvedor Full Stack com mais de 5 anos de experiência no desenvolvimento de aplicações web, APIs REST, ferramentas internas, automações e integrações usando JavaScript, TypeScript, Node.js, React, Python, PostgreSQL, MongoDB e Salesforce.<br>Confira meus <a href="#project">projetos</a> abaixo.',
      'terminal.location': 'Jacareí/SP, Brasil',
      'terminal.education':
        'Mestrado em Engenharia de Sistemas Logísticos — Universidade de São Paulo<br>Full Stack Web Development — Microverse',
      'terminal.skills':
        '[ "JavaScript", "TypeScript", "Python", "Node.js", "Express", "React", "PostgreSQL", "MongoDB", "Salesforce", "Docker", "Jest", "Git" ]',
      'terminal.resumeLabel': 'felipeenne.pdf',
      'projects.title': 'Projetos',
      'proj.audiobook.title': 'Plataforma de Automação para Produção de Audiolivros',
      'proj.audiobook.desc':
        'Projeto próprio para produção e publicação de audiolivros em escala no YouTube, utilizando Python, FastAPI, TTS local e API do YouTube para automatizar geração de áudio, organização de arquivos, thumbnails, descrições, playlists e agendamento de publicações.',
      'proj.audiobook.link': 'YouTube',
      'proj.wine.title': 'Wine Recommendation',
      'proj.wine.desc':
        'Sistema de recomendação de vinhos desenvolvido em Python/Jupyter, com foco em análise de dados, tratamento de informações e lógica de recomendação baseada em características dos produtos.',
      'proj.climb.title': 'Climbing the Volcano',
      'proj.climb.desc':
        'Jogo 2D desenvolvido com JavaScript e Phaser, com lógica de colisão, coleta de itens, movimentação de personagem e testes com Jest. Projeto voltado à prática de desenvolvimento front-end, lógica de programação e estruturação de aplicações interativas.',
      'proj.demo': 'Demo',
      'proj.github': 'Link no Github',
      'contact.title': 'Fale comigo!',
      'footer.madeby': 'Feito por Felipe Enne Mendes Ribeiro 2026',
    },
  };

  function getDefaultLang() {
    const saved = localStorage.getItem('portfolio-lang');
    if (saved === 'en' || saved === 'pt') return saved;
    return navigator.language && navigator.language.toLowerCase().startsWith('pt')
      ? 'pt'
      : 'en';
  }

  function applyTranslations(lang) {
    const dict = translations[lang];
    if (!dict) return;

    document.documentElement.lang = lang;

    document.querySelectorAll('[data-i18n]').forEach(function (el) {
      const key = el.getAttribute('data-i18n');
      if (dict[key] !== undefined) {
        el.textContent = dict[key];
      }
    });

    document.querySelectorAll('[data-i18n-html]').forEach(function (el) {
      const key = el.getAttribute('data-i18n-html');
      if (dict[key] !== undefined) {
        el.innerHTML = dict[key];
      }
    });

    const resumeLink = document.getElementById('resume-link');
    if (resumeLink) {
      resumeLink.setAttribute('href', CV_LINKS[lang]);
      resumeLink.textContent = dict['terminal.resumeLabel'];
    }

    document.querySelectorAll('[data-lang-btn]').forEach(function (btn) {
      const isActive = btn.getAttribute('data-lang-btn') === lang;
      btn.classList.toggle('lang-active', isActive);
      btn.setAttribute('aria-pressed', isActive ? 'true' : 'false');
    });
  }

  function setLang(lang) {
    localStorage.setItem('portfolio-lang', lang);
    applyTranslations(lang);
  }

  document.addEventListener('DOMContentLoaded', function () {
    const lang = getDefaultLang();
    applyTranslations(lang);

    document.querySelectorAll('[data-lang-btn]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        setLang(btn.getAttribute('data-lang-btn'));
      });
    });
  });
})();
