const ENDPOINT = 'https://script.google.com/macros/s/AKfycbziWAOxqe25FzQLAMdS-g3_LoTrvHaXDcjLb7vGA_IsCcXei_2h51SZxW2LZ01LELjpUA/exec';

const QUESTIONS = [
  {
    name:'q1', type:'multi', kicker:'01 / старт',
    title:'С чего для вас обычно начинается разработка нового блюда?',
    options:[
      'Задача от проекта / руководителя',
      'Сезонность',
      'Идея блюда или вкусовая концепция',
      'Конкретный продукт',
      'Анализ складских остатков'
    ]
  },
  {
    name:'q2', type:'single', kicker:'02 / первое действие',
    title:'Что вы обычно делаете первым после появления задачи или идеи?',
    options:[
      'Ищу рецепты и технологии',
      'Анализирую товарную матрицу',
      'Проверяю наличие продуктов и складские остатки',
      'Сразу приступаю к проработке блюда',
      'Обсуждаю задачу с командой'
    ]
  },
  {
    name:'q3', type:'multi', kicker:'03 / контекст проекта',
    title:'Какие данные о проекте важно учитывать ещё до начала проработки?',
    options:[
      'Товарная матрица',
      'Складские остатки',
      'Допустимая себестоимость блюда',
      'Закупочные цены и поставщики',
      'Доступное оборудование',
      'Время приготовления',
      'Текущее меню'
    ]
  },
  {
    name:'q4', type:'multi', kicker:'04 / тестовая проработка',
    title:'Что важно фиксировать непосредственно во время тестовой проработки блюда?',
    options:[
      'Количество ингредиентов и граммовки',
      'Фактические изменения по ходу проработки',
      'Комментарии по вкусу и текстуре',
      'Изменения в полуфабрикатах',
      'Время приготовления',
      'Использованное оборудование',
      'Выход продукта и потери'
    ]
  },
  {
    name:'q5', type:'multi', kicker:'05 / фиксация результатов',
    title:'Как вы обычно фиксируете результаты проработки?',
    options:[
      'В заметках на телефоне',
      'В бумажном журнале или блокноте',
      'В таблицах или документах',
      'В iiko / 1С / другой учётной системе',
      'В рабочих чатах или мессенджерах',
      'С помощью фото или видео',
      'Не фиксирую системно, держу в голове'
    ]
  },
  {
    name:'q6', type:'single', kicker:'06 / себестоимость',
    title:'На каком этапе себестоимость начинает влиять на разработку блюда?',
    options:[
      'Ещё до начала проработки',
      'При выборе продуктов и технологии',
      'После первой проработки',
      'После дегустации, перед вводом в меню',
      'Это не моя зона ответственности'
    ]
  },
  {
    name:'q7', type:'multi', kicker:'07 / дегустация',
    title:'Какие аспекты вы обычно фиксируете во время дегустации?',
    options:[
      'Вкус и баланс',
      'Аромат',
      'Текстура',
      'Температура подачи',
      'Соответствие концепции',
      'Внешний вид и подача',
      'Комментарии участников дегустации',
      'Ничего специально не фиксируем'
    ]
  },
  {
    name:'q8', type:'multi', kicker:'08 / после запуска',
    title:'Как вы обычно получаете обратную связь по блюду после запуска?',
    options:[
      'Напрямую от гостей',
      'Через официантов',
      'Через менеджера или управляющего',
      'Из отзывов на картах и других площадках',
      'Из отзывов в сервисах доставки',
      'По возвратам и недоеденным блюдам',
      'Практически не получаю обратную связь'
    ]
  },
  {
    name:'q9', type:'multi', kicker:'09 / цифровой помощник',
    title:'На каком этапе разработки блюда цифровой помощник был бы для вас наиболее полезен?',
    options:[
      'Поиск и адаптация рецептов',
      'Работа с ограничениями проекта',
      'Фиксация изменений во время проработки',
      'Сохранение и сравнение разных версий',
      'Расчёт себестоимости и выхода',
      'Дегустация и сбор комментариев',
      'Подготовка технологической карты',
      'Анализ обратной связи после запуска'
    ]
  },
  {
    name:'q10', type:'single', kicker:'10 / Yes, Chef!',
    title:'Что вы бы первым попробовали сделать через Yes, Chef!?',
    options:[
      'Найти и адаптировать рецептуру под условия проекта',
      'Зафиксировать проработку блюда голосом',
      'Сравнить несколько версий блюда',
      'Рассчитать себестоимость и выход',
      'Провести и зафиксировать дегустацию',
      'Собрать технологическую карту',
      'Разобрать обратную связь по уже запущенному блюду'
    ]
  }
];

const esc = (value) => String(value).replace(/[&<>"']/g, (char) => ({
  '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'
}[char]));

const form = document.getElementById('survey');
const questionsRoot = document.getElementById('questions');
const counter = document.getElementById('counter');
const progressBar = document.getElementById('progressBar');
const sink = document.getElementById('yeschefSink');
const preloader = document.getElementById('preloader');

questionsRoot.innerHTML = QUESTIONS.map((q, questionIndex) => {
  const options = [...q.options, 'Другое'];
  const isLast = questionIndex === QUESTIONS.length - 1;
  const selectionText = q.type === 'multi'
    ? 'Можно выбрать несколько вариантов'
    : 'Выберите один вариант';

  return `
    <section class="screen" data-key="${q.name}" data-type="${q.type}">
      <div class="eyebrow">${esc(q.kicker)}</div>
      <h2>${esc(q.title)}</h2>
      <div class="selection-note">${esc(selectionText)}</div>
      <div class="options">
        ${options.map(option => `
          <label class="option ${q.type === 'multi' ? 'multi' : ''}">
            <input type="${q.type === 'multi' ? 'checkbox' : 'radio'}" name="${q.name}" value="${esc(option)}">
            <span class="mark"></span>
            <span class="option__text">${esc(option)}</span>
          </label>
        `).join('')}
      </div>
      <div class="other-wrap">
        <input class="other-input" type="text" inputmode="text" name="${q.name}_other" placeholder="Укажите свой вариант">
      </div>
      <div class="error" aria-live="polite"></div>
      <div class="nav">
        <button class="btn btn--back" type="button" data-back aria-label="Назад">←</button>
        <button class="btn btn--primary" id="${isLast ? 'submitBtn' : ''}" type="button" ${isLast ? 'data-submit' : 'data-next'}>${isLast ? 'Отправить ответы' : 'Дальше'}</button>
      </div>
    </section>
  `;
}).join('');

const screens = [...document.querySelectorAll('.screen')];
const successIndex = screens.findIndex(screen => screen.dataset.key === 'success');
const submitBtn = document.getElementById('submitBtn');
let index = 0;
let submitting = false;
let submitTimeout = null;

let geo = {
  city:'', region:'', country:'', country_code:'',
  timezone:Intl.DateTimeFormat().resolvedOptions().timeZone || ''
};

function finishPreloader(){
  if(!document.body.classList.contains('is-loading')) return;
  preloader?.classList.add('is-done');
  document.body.classList.remove('is-loading');
  document.body.classList.add('is-ready');
  window.setTimeout(() => preloader?.remove(), 850);
}

const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
window.addEventListener('load', () => {
  window.setTimeout(finishPreloader, reducedMotion ? 50 : 1650);
});
window.setTimeout(finishPreloader, reducedMotion ? 120 : 2800);

async function detectRegion(){
  try{
    const response = await fetch('https://ipwho.is/?fields=success,city,region,country,country_code,timezone');
    if(!response.ok) return;
    const data = await response.json();
    if(!data.success) return;
    geo.city = data.city || '';
    geo.region = data.region || '';
    geo.country = data.country || '';
    geo.country_code = data.country_code || '';
    geo.timezone = typeof data.timezone === 'object' ? (data.timezone?.id || geo.timezone) : (data.timezone || geo.timezone);
  }catch(_){
    // Определение региона не должно мешать прохождению опроса.
  }
}
detectRegion();

function syncOption(input){
  const screen = input.closest('.screen');
  if(input.type === 'radio'){
    screen.querySelectorAll(`input[name="${input.name}"]`).forEach(item => {
      item.closest('.option')?.classList.toggle('selected', item.checked);
    });
  } else {
    input.closest('.option')?.classList.toggle('selected', input.checked);
  }

  const otherWrap = screen.querySelector('.other-wrap');
  if(!otherWrap) return;
  const otherChoice = [...screen.querySelectorAll(`input[name="${input.name}"]`)].find(item => item.value === 'Другое');
  const shouldShow = Boolean(otherChoice?.checked);
  otherWrap.classList.toggle('show', shouldShow);

  if(shouldShow){
    const field = otherWrap.querySelector('.other-input');
    window.setTimeout(() => {
      field.focus();
      field.scrollIntoView({behavior:'smooth', block:'center'});
    }, 80);
  }
}

form.addEventListener('change', event => {
  if(event.target.matches('.option input')) syncOption(event.target);
});

form.addEventListener('click', event => {
  const next = event.target.closest('[data-next]');
  const back = event.target.closest('[data-back]');
  const submit = event.target.closest('[data-submit]');

  if(next){
    event.preventDefault();
    if(validateCurrent()) goTo(index + 1);
  }

  if(back){
    event.preventDefault();
    goTo(index - 1);
  }

  if(submit){
    event.preventDefault();
    if(validateCurrent()) submitSurvey();
  }
});

function goTo(nextIndex){
  if(nextIndex < 0 || nextIndex >= screens.length) return;
  screens[index].classList.remove('active');
  index = nextIndex;
  screens[index].classList.add('active');
  document.activeElement?.blur();
  window.scrollTo({top:0, behavior:'auto'});
  updateProgress();
}

function updateProgress(){
  const key = screens[index].dataset.key;

  if(key === 'intro'){
    progressBar.style.width = '0%';
    counter.textContent = '2–3 минуты';
    return;
  }

  if(key === 'profile'){
    progressBar.style.width = '0%';
    counter.textContent = 'о вас';
    return;
  }

  if(key === 'success'){
    progressBar.style.width = '100%';
    counter.textContent = 'готово';
    return;
  }

  const questionNumber = QUESTIONS.findIndex(question => question.name === key) + 1;
  if(questionNumber > 0){
    progressBar.style.width = `${(questionNumber / QUESTIONS.length) * 100}%`;
    counter.textContent = `${String(questionNumber).padStart(2,'0')} / ${String(QUESTIONS.length).padStart(2,'0')}`;
  }
}

function validateCurrent(){
  const screen = screens[index];
  const error = screen.querySelector('.error');
  if(error) error.textContent = '';

  if(screen.dataset.key === 'profile'){
    const missing = [...screen.querySelectorAll('[required]')].find(field => !field.value.trim());
    if(missing){
      error.textContent = 'Заполните город, страну и должность.';
      missing.focus();
      return false;
    }
  }

  if(['single','multi'].includes(screen.dataset.type)){
    if(!screen.querySelector('input:checked')){
      error.textContent = screen.dataset.type === 'single'
        ? 'Выберите один вариант.'
        : 'Выберите хотя бы один вариант.';
      return false;
    }

    const otherSelected = screen.querySelector('input[value="Другое"]:checked');
    if(otherSelected){
      const otherField = screen.querySelector('.other-input');
      if(!otherField.value.trim()){
        error.textContent = 'Укажите свой вариант.';
        otherField.focus();
        return false;
      }
    }
  }

  return true;
}

function valueOf(name){
  const checked = [...form.querySelectorAll(`[name="${name}"]:checked`)];
  if(checked.length){
    return checked.map(item => {
      if(item.value !== 'Другое') return item.value;
      const custom = form.querySelector(`[name="${name}_other"]`)?.value.trim() || '';
      return `Другое: ${custom}`;
    }).join(' · ');
  }
  return form.querySelector(`[name="${name}"]`)?.value.trim() || '';
}

function payload(){
  return {
    name:'',
    city:valueOf('city'),
    country:valueOf('country'),
    role:valueOf('role'),
    geo_city:geo.city,
    geo_region:geo.region,
    geo_country:geo.country,
    geo_country_code:geo.country_code,
    geo_timezone:geo.timezone,
    q1:valueOf('q1'),
    q2:valueOf('q2'),
    q3:valueOf('q3'),
    q4:valueOf('q4'),
    q5:valueOf('q5'),
    q6:valueOf('q6'),
    q7:valueOf('q7'),
    q8:valueOf('q8'),
    q9:valueOf('q9'),
    q10:valueOf('q10'),
    comment:''
  };
}

function submitSurvey(){
  if(submitting) return;
  submitting = true;
  submitBtn.disabled = true;
  submitBtn.textContent = 'Отправляем…';

  const transport = document.createElement('form');
  transport.method = 'POST';
  transport.action = ENDPOINT;
  transport.target = 'yeschefSink';
  transport.style.display = 'none';

  Object.entries(payload()).forEach(([key, value]) => {
    const input = document.createElement('input');
    input.type = 'hidden';
    input.name = key;
    input.value = value == null ? '' : String(value);
    transport.appendChild(input);
  });

  document.body.appendChild(transport);
  transport.submit();

  submitTimeout = window.setTimeout(() => {
    if(!submitting) return;
    submitting = false;
    submitBtn.disabled = false;
    submitBtn.textContent = 'Отправить ответы';
    const error = screens[index].querySelector('.error');
    if(error) error.textContent = 'Не удалось подтвердить отправку. Проверьте интернет и попробуйте ещё раз.';
    transport.remove();
  }, 12000);

  window.setTimeout(() => transport.remove(), 15000);
}

sink.addEventListener('load', () => {
  if(!submitting) return;
  submitting = false;
  window.clearTimeout(submitTimeout);
  goTo(successIndex);
});

updateProgress();
