const OPERATOR_LABELS = {
  bite: 'Bitė',
  telia: 'Telia',
  pildyk: 'Pildyk',
  ezys: 'Ežys',
  tele2: 'Tele2',
};

const topupForm = document.getElementById('topup-form');
const statusEl = document.getElementById('topup-status');
const yearEl = document.getElementById('year');

const PHONE_PATTERN = /^\+3706\d{7}$/;

function normalizePhone(raw) {
  return String(raw || '').replace(/[\s()/-]/g, '');
}

function formatPhone(phone) {
  return `${phone.slice(0, 4)} ${phone.slice(4, 7)} ${phone.slice(7)}`;
}

function setStatus(message, tone) {
  if (!statusEl) return;
  statusEl.textContent = message;
  statusEl.classList.remove('ok', 'err');
  if (tone) statusEl.classList.add(tone);
}

if (topupForm) {
  topupForm.addEventListener('submit', (event) => {
    event.preventDefault();

    const data = new FormData(topupForm);
    const operator = String(data.get('operator') || 'bite');
    const phone = normalizePhone(data.get('phone'));
    const amount = String(data.get('amount') || '');

    if (!PHONE_PATTERN.test(phone)) {
      setStatus('Įveskite galiojantį numerį formatu +3706XXXXXXX.', 'err');
      return;
    }

    if (!amount) {
      setStatus('Pasirinkite papildymo sumą.', 'err');
      return;
    }

    const label = OPERATOR_LABELS[operator] || operator;
    setStatus(
      `Papildymas pradėtas: ${label} numeris ${formatPhone(phone)} +${amount} €. ` +
        'Tai demo režimas – tikras mokėjimas neatliktas.',
      'ok'
    );
    topupForm.reset();
    topupForm.querySelector('input[name="amount"][value="5"]').checked = true;
  });
}

if (yearEl) {
  yearEl.textContent = String(new Date().getFullYear());
}
