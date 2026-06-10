"""1 oylik moliyaviy bashorat — statistik trend + Gemini AI sharhi."""
import json
from datetime import date
from decimal import Decimal

import requests
from django.conf import settings
from django.db.models import Sum
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from owner.views import owner_required
from finance.models import Expense, Income


HISTORY_MONTHS = 6  # ko'rinadigan oylar (joriy oy + oldingi 5)


def _month_start(d: date) -> date:
    return d.replace(day=1)


def _prev_month_start(d: date) -> date:
    """`d` (oyning 1-kuni) ning bir oy oldingi 1-kuni."""
    if d.month == 1:
        return date(d.year - 1, 12, 1)
    return date(d.year, d.month - 1, 1)


def _next_month_start(d: date) -> date:
    if d.month == 12:
        return date(d.year + 1, 1, 1)
    return date(d.year, d.month + 1, 1)


def _gather_history():
    """Oxirgi HISTORY_MONTHS oylik kirim/chiqim/foyda ro'yxati (eskidan yangiga)."""
    today = date.today()
    months = []
    cur = _month_start(today)
    for _ in range(HISTORY_MONTHS):
        months.append(cur)
        cur = _prev_month_start(cur)
    months.reverse()

    rows = []
    for m in months:
        end = _next_month_start(m)
        income = Income.objects.filter(date__gte=m, date__lt=end).aggregate(
            t=Sum('amount'))['t'] or Decimal('0')
        expense = Expense.objects.filter(date__gte=m, date__lt=end).aggregate(
            t=Sum('amount'))['t'] or Decimal('0')
        rows.append({
            'month':   m,
            'label':   m.strftime('%Y-%m'),
            'income':  int(income),
            'expense': int(expense),
            'profit':  int(income - expense),
        })
    return rows


def _linear_forecast(values):
    """Oddiy chiziqli regressiya: keyingi nuqtani prognoz qiladi.

    `values` — int yoki float ro'yxati. Kamida 2 ta qiymat kerak.
    Slope va intercept'ni ordinary least squares orqali topadi.
    """
    n = len(values)
    if n == 0:
        return 0
    if n == 1:
        return values[0]
    xs = list(range(n))
    mean_x = sum(xs) / n
    mean_y = sum(values) / n
    num = sum((xs[i] - mean_x) * (values[i] - mean_y) for i in range(n))
    den = sum((xs[i] - mean_x) ** 2 for i in range(n))
    if den == 0:
        return mean_y
    slope = num / den
    intercept = mean_y - slope * mean_x
    return intercept + slope * n  # keyingi indeks


def _trend_pct(current, predicted):
    """O'sish foizi. Joriy 0 bo'lsa va predicted ham 0 — 0."""
    if current == 0:
        return 0.0 if predicted == 0 else 100.0
    return round((predicted - current) / abs(current) * 100, 1)


def _gemini_narrative(history, predicted, growth_pct):
    """Gemini'dan o'zbekcha sharh oladi. Internet/API bo'lmasa fallback matn."""
    if not settings.GEMINI_API_KEY:
        return _fallback_narrative(history, predicted, growth_pct)

    prompt = (
        "Sen moyka biznesining moliyaviy maslahatchisisan. Quyidagi oylik "
        "kirim/chiqim ma'lumotlari va keyingi oy uchun statistik bashorat berilgan. "
        "Ulardan kelib chiqib, qisqa (3-5 jumla), aniq va o'zbek tilida tahlil ber: "
        "trend yuqorimi yoki pastmi, sabablari nima bo'lishi mumkin va moyka egasiga "
        "1-2 ta amaliy tavsiya. Raqamlarni qayta yozma — faqat sharh ber.\n\n"
        "Oylik tarix:\n"
    )
    for row in history:
        prompt += (
            f"- {row['label']}: kirim {row['income']:,} so'm, "
            f"chiqim {row['expense']:,} so'm, foyda {row['profit']:,} so'm\n"
        )
    prompt += (
        f"\nKeyingi oy bashorati: kirim {predicted['income']:,} so'm, "
        f"chiqim {predicted['expense']:,} so'm, foyda {predicted['profit']:,} so'm, "
        f"foyda o'zgarishi: {growth_pct:+.1f}%."
    )

    body = {
        'contents': [{'role': 'user', 'parts': [{'text': prompt}]}],
        'generationConfig': {'temperature': 0.5, 'maxOutputTokens': 400},
    }

    for model in [settings.GEMINI_MODEL, 'gemini-2.5-flash', 'gemini-2.0-flash']:
        if not model:
            continue
        url = (f"https://generativelanguage.googleapis.com/v1beta/"
               f"models/{model}:generateContent")
        try:
            resp = requests.post(
                url, params={'key': settings.GEMINI_API_KEY},
                json=body, timeout=25,
            )
        except requests.RequestException:
            continue
        if resp.status_code == 200:
            try:
                return resp.json()['candidates'][0]['content']['parts'][0]['text'].strip()
            except (KeyError, IndexError, TypeError):
                continue
    return _fallback_narrative(history, predicted, growth_pct)


def _fallback_narrative(history, predicted, growth_pct):
    direction = "o'sish" if growth_pct > 2 else ("pasayish" if growth_pct < -2 else "barqaror holat")
    last = history[-1] if history else None
    parts = [
        f"Statistik tahlil keyingi oyda foydaning {direction} kutilayotganini ko'rsatadi "
        f"({growth_pct:+.1f}%).",
    ]
    if last:
        parts.append(
            f"Joriy oyda foyda {last['profit']:,} so'm bo'lib, bashorat "
            f"{predicted['profit']:,} so'm atrofida."
        )
    if growth_pct > 5:
        parts.append("Marketing va xizmat sifatini saqlab qoling — ijobiy momentum davom etmoqda.")
    elif growth_pct < -5:
        parts.append("Chiqimlarni qayta ko'rib chiqing va onlayn buyurtmalarni rag'batlantiring.")
    else:
        parts.append("Daromad barqaror — yangi xizmatlar yoki aksiyalar bilan o'sishga harakat qiling.")
    return " ".join(parts)


@owner_required
@require_GET
def forecast(request):
    history = _gather_history()
    incomes  = [h['income']  for h in history]
    expenses = [h['expense'] for h in history]
    profits  = [h['profit']  for h in history]

    pred_income  = max(0, int(round(_linear_forecast(incomes))))
    pred_expense = max(0, int(round(_linear_forecast(expenses))))
    pred_profit  = pred_income - pred_expense

    current_profit = profits[-1] if profits else 0
    growth_pct = _trend_pct(current_profit, pred_profit)

    if growth_pct > 2:
        trend = 'up'
    elif growth_pct < -2:
        trend = 'down'
    else:
        trend = 'flat'

    predicted = {
        'income':  pred_income,
        'expense': pred_expense,
        'profit':  pred_profit,
    }
    next_label = _next_month_start(_month_start(date.today())).strftime('%Y-%m')

    narrative = _gemini_narrative(history, predicted, growth_pct)

    return JsonResponse({
        'history':       [{'label': r['label'], 'income': r['income'],
                           'expense': r['expense'], 'profit': r['profit']}
                          for r in history],
        'predicted':     predicted,
        'next_label':    next_label,
        'current_profit': current_profit,
        'growth_pct':    growth_pct,
        'trend':         trend,
        'narrative':     narrative,
        'gemini_used':   bool(settings.GEMINI_API_KEY),
    })
