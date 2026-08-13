const ENDPOINT = 'https://script.google.com/macros/s/AKfycbziWAOxqe25FzQLAMdS-g3_LoTrvHaXDcjLb7vGA_IsCcXei_2h51SZxW2LZ01LELjpUA/exec';

const QUESTIONS = [
  {
    name:'q1', type:'single', kicker:'01 / старт',
    title:'С чего чаще начинается разработка нового блюда?',
    options:['Задача от ресторана / руководителя','Сезонность','Продукт или товарная матрица','Целевая себестоимость / food cost','Идея вкуса / собственная идея'],
    other:'Напиши свой вариант'
  },
  {
    name:'q2', type:'single', kicker:'02 / поиск',
    title:'Что ты обычно делаешь первым после получения задачи?',
    options:['Ищу рецепты и технологии','Проверяю продукты / товарную матрицу','Считаю себестоимость','Сразу делаю тест','Обсуждаю с командой'],
    other:'Напиши свой вариант'
  },
  {
    name:'q3', type:'multi', kicker:'03 / контекст',
    title:'Что приложение должно знать о твоём ресторане заранее?',
    options:['Товарная матрица','Оборудование кухни','Поставщики и закупочные цены','Допустимый food cost','Текущее меню','Время / возможности команды'],
    other:'Что ещё важно знать?'
  },
  {
    name:'q4', type:'multi', kicker:'04 / тест',
    title:'Что важно фиксировать прямо во время тестовой готовки?',
    options:['Количество ингредиентов','Все изменения по ходу','Отдельные полуфабрикаты / компоненты','Комментарии по вкусу / текстуре','Почему было принято решение','Время и технология'],
    other:'Что ещё фиксируешь?'
  },
  {
    name:'q5', type:'single', kicker:'05 / версии',
    title:'Как ты обычно различаешь версии одного блюда?',
    options:['Номера версий','Даты','По тому, что именно меняли','Фото / заметки','В основном держу в голове'],
    other:'Как именно?'
  },
  {
    name:'q6', type:'multi', kicker:'06 / дегустация',
    title:'Что было бы полезно от приложения во время дегустации?',
    options:['Различать участников по голосам','Записывать комментарии каждого','Собирать общий итог','Предлагать следующую доработку','Сразу учитывать себестоимость','Мне это не нужно'],
    other:'Что ещё?'
  },
  {
    name:'q7', type:'single', kicker:'07 / деньги',
    title:'Когда себестоимость начинает влиять на разработку?',
    options:['До выбора рецепта / концепции','Во время выбора вариантов','После первого теста','После успешной дегустации','Этим занимается не повар'],
    other:'Как у вас?'
  },
  {
    name:'q8', type:'multi', kicker:'08 / после запуска',
    title:'Откуда после запуска блюда до тебя реально доходит фидбек?',
    options:['Гости в ресторане','Официанты','Менеджер / управляющий','Отзывы доставки','Возвраты / недоеденные блюда','Почти никак не доходит'],
    other:'Откуда ещё?'
  },
  {
    name:'q9', type:'multi', kicker:'09 / доставка',
    title:'Что особенно важно отслеживать для доставки?',
    options:['Температура','Текстура после дороги','Внешний вид','Упаковка / протечки','Комплектность','Время в пути','У нас нет доставки'],
    other:'Что ещё?'
  },
  {
    name:'q10', type:'single', kicker:'10 / Yes, Chef!',
    title:'Что бы ты первым попробовал сделать через Yes, Chef!?',
    options:['Подобрать рецепты под условия ресторана','Записывать изменения во время готовки','Сравнивать версии блюда','Провести и разобрать дегустацию','Считать себестоимость и варианты замены','Собрать финальную ТТК','Анализировать фидбек гостей и доставки'],
    other:'Что именно?'
  }
];

const esc = (value) => String(value).replace(/[&<>"']/g, (char) => ({
  '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'
}[char]));

const form = document.getElementById('survey');
const questionsRoot = document.getElementById('questions');
const counter = document.getElementById('counter');
const progressBar = document.getElementById('progressBar');
const submitBtn = document.getElementById('submitBtn');
const sink = document.getElementById('yeschefSink');

questionsRoot.innerHTML = QUESTIONS.map((q, index) => {
  const options = [...q.options, 'Другое'];
  return `
    <section class="screen" data-key="${q.name}" data-type="${q.type}">
      <div class="eyebrow">${esc(q.kicker)}</div>
      <h2>${esc(q.title)}</h2>
      ${q.type === 'multi' ? '<p class="hint">Можно выбрать несколько.</p>' : ''}
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
        <input class="other-input" type="text" inputmode="text" name="${q.name}_other" placeholder="${esc(q.other)}">
      </div>
      <div class="error" aria-live="polite"></div>
      <div class="nav">
        <button class="btn btn--back" type="button" data-back>←</button>
        <button class="btn btn--primary" type="button" data-next>${index === QUESTIONS.length - 1 ? 'Последний' : 'Дальше'}</button>
      </div>
    </section>
  `;
}).join('');

const screens = [...document.querySelectorAll('.screen')];
const commentIndex = screens.findIndex(screen => screen.dataset.key === 'comment');
const successIndex = screens.findIndex(screen => screen.dataset.key === 'success');
let index = 0;
let submitting = false;
let submitTimeout = null;

let geo = {
  city:'', region:'', country:'', country_code:'',
  timezone:Intl.DateTimeFormat().resolvedOptions().timeZone || ''
};

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
    // Геолокация не должна мешать заполнению опроса.
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

  if(next){
    event.preventDefault();
    if(validateCurrent()) goTo(index + 1);
  }
  if(back){
    event.preventDefault();
    goTo(index - 1);
  }
});

submitBtn.addEventListener('click', () => {
  if(validateCurrent()) submitSurvey();
});

function goTo(nextIndex){
  if(nextIndex < 0 || nextIndex >= screens.length) return;
  screens[index].classList.remove('active');
  index = nextIndex;
  screens[index].classList.add('active');
  document.activeElement?.blur();
  window.scrollTo({top:0, behavior:'instant'});
  updateProgress();
}

function updateProgress(){
  const key = screens[index].dataset.key;
  if(key === 'intro'){
    progressBar.style.width = '0%';
    counter.textContent = '2–3 минуты';
    return;
  }
  if(key === 'success'){
    progressBar.style.width = '100%';
    counter.textContent = 'готово';
    return;
  }
  const visibleStep = Math.max(0, index - 1);
  const totalSteps = commentIndex - 1;
  progressBar.style.width = `${Math.min(100, (visibleStep / totalSteps) * 100)}%`;
  counter.textContent = index === 1 ? 'о вас' : `${index - 1} / ${QUESTIONS.length}`;
}

function validateCurrent(){
  const screen = screens[index];
  const error = screen.querySelector('.error');
  if(error) error.textContent = '';

  if(screen.dataset.key === 'profile'){
    const missing = [...screen.querySelectorAll('[required]')].find(field => !field.value.trim());
    if(missing){
      error.textContent = 'Заполни четыре поля.';
      missing.focus();
      return false;
    }
  }

  if(['single','multi'].includes(screen.dataset.type)){
    if(!screen.querySelector('input:checked')){
      error.textContent = 'Выбери хотя бы один вариант.';
      return false;
    }

    const otherSelected = screen.querySelector('input[value="Другое"]:checked');
    if(otherSelected){
      const otherField = screen.querySelector('.other-input');
      if(!otherField.value.trim()){
        error.textContent = 'Напиши свой вариант.';
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
    name:valueOf('name'),
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
    comment:valueOf('comment')
  };
}

function submitSurvey(){
  if(submitting) return;
  submitting = true;
  submitBtn.disabled = true;
  submitBtn.textContent = 'Отправляю…';

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
    submitBtn.textContent = 'Отправить';
    const error = screens[index].querySelector('.error');
    error.textContent = 'Не удалось подтвердить отправку. Проверь интернет и попробуй ещё раз.';
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
