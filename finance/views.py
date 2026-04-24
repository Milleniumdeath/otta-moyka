from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Sum
from datetime import timedelta, date
from owner.views import owner_required
from finance.models import Expense, Income

COMMUNAL_CATS = [
    ('gas',         'Gaz',           '🔥'),
    ('water',       'Suv',           '💧'),
    ('electricity', 'Elektr',        '⚡'),
]
RAW_CATS = [
    ('chemical',   'Kimyoviy modda', '🧪'),
    ('foam',       'Pena',           '🫧'),
    ('spare_part', 'Ehtiyot qism',   '🔩'),
    ('tool',       'Ish qurol',      '🔧'),
]


def get_period_dates(period):
    today = date.today()
    if period == 'daily':
        return today, today
    elif period == 'weekly':
        start = today - timedelta(days=today.weekday())
        return start, today
    else:  # monthly
        return today.replace(day=1), today


def get_summary(start, end):
    expenses = Expense.objects.filter(date__range=[start, end])
    incomes  = Income.objects.filter(date__range=[start, end])

    exp_communal = expenses.filter(group=Expense.Group.COMMUNAL).aggregate(t=Sum('amount'))['t'] or 0
    exp_raw      = expenses.filter(group=Expense.Group.RAW).aggregate(t=Sum('amount'))['t'] or 0
    exp_external = expenses.filter(group=Expense.Group.EXTERNAL).aggregate(t=Sum('amount'))['t'] or 0
    total_exp    = exp_communal + exp_raw + exp_external

    inc_offline  = incomes.filter(category=Income.Category.OFFLINE).aggregate(t=Sum('amount'))['t'] or 0
    inc_online   = incomes.filter(category=Income.Category.ONLINE).aggregate(t=Sum('amount'))['t'] or 0
    inc_extra    = incomes.filter(category=Income.Category.EXTRA).aggregate(t=Sum('amount'))['t'] or 0
    total_inc    = inc_offline + inc_online + inc_extra

    return {
        'exp_communal': exp_communal,
        'exp_raw':      exp_raw,
        'exp_external': exp_external,
        'total_exp':    total_exp,
        'inc_offline':  inc_offline,
        'inc_online':   inc_online,
        'inc_extra':    inc_extra,
        'total_inc':    total_inc,
        'profit':       total_inc - total_exp,
    }


@owner_required
def finance(request):
    period = request.GET.get('period', 'monthly')
    start, end = get_period_dates(period)

    summary  = get_summary(start, end)
    expenses = Expense.objects.filter(date__range=[start, end])
    incomes  = Income.objects.filter(date__range=[start, end])

    # Oxirgi 7 kun grafigi
    chart_labels, chart_income, chart_expense = [], [], []
    for i in range(6, -1, -1):
        d = date.today() - timedelta(days=i)
        chart_labels.append(d.strftime('%d.%m'))
        chart_income.append(
            int(Income.objects.filter(date=d).aggregate(t=Sum('amount'))['t'] or 0)
        )
        chart_expense.append(
            int(Expense.objects.filter(date=d).aggregate(t=Sum('amount'))['t'] or 0)
        )

    return render(request, 'owner/finance.html', {
        'period':        period,
        'start':         start,
        'end':           end,
        'summary':       summary,
        'expenses':      expenses,
        'incomes':       incomes,
        'chart_labels':  chart_labels,
        'chart_income':  chart_income,
        'chart_expense': chart_expense,
        'communal_cats': COMMUNAL_CATS,
        'raw_cats':      RAW_CATS,
        'today':         str(date.today()),
    })


@owner_required
def add_expense(request):
    if request.method == 'POST':
        category    = request.POST.get('category', '')
        description = request.POST.get('description', '').strip()
        amount      = request.POST.get('amount', 0)
        exp_date    = request.POST.get('date', str(date.today()))

        if not category or not amount:
            messages.error(request, "Kategoriya va miqdorni kiriting.")
            return redirect('owner:finance')

        communal = [c[0] for c in COMMUNAL_CATS]
        raw      = [c[0] for c in RAW_CATS]

        if category in communal:
            group = Expense.Group.COMMUNAL
        elif category in raw:
            group = Expense.Group.RAW
        else:
            group = Expense.Group.EXTERNAL

        Expense.objects.create(
            category=category, group=group,
            description=description,
            amount=int(amount), date=exp_date,
        )
        messages.success(request, f"Chiqim qo'shildi: {int(amount):,} so'm")
    return redirect('owner:finance')


@owner_required
def add_income(request):
    if request.method == 'POST':
        category    = request.POST.get('category', '')
        description = request.POST.get('description', '').strip()
        amount      = request.POST.get('amount', 0)
        inc_date    = request.POST.get('date', str(date.today()))

        if not category or not amount:
            messages.error(request, "Kategoriya va miqdorni kiriting.")
            return redirect('owner:finance')

        Income.objects.create(
            category=category, description=description,
            amount=int(amount), date=inc_date,
        )
        messages.success(request, f"Kirim qo'shildi: {int(amount):,} so'm")
    return redirect('owner:finance')


@owner_required
def delete_expense(request, pk):
    if request.method == 'POST':
        get_object_or_404(Expense, pk=pk).delete()
        messages.success(request, "Chiqim o'chirildi.")
    return redirect('owner:finance')


@owner_required
def delete_income(request, pk):
    if request.method == 'POST':
        inc = get_object_or_404(Income, pk=pk)
        if inc.category == Income.Category.ONLINE:
            messages.error(request, "Avtomatik kirimlarni o'chirib bo'lmaydi.")
            return redirect('owner:finance')
        inc.delete()
        messages.success(request, "Kirim o'chirildi.")
    return redirect('owner:finance')
